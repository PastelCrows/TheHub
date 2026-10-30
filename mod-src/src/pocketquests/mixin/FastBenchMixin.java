package pocketquests.mixin;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import pocketquests.PocketRules;

/**
 * The crafting gate, for the path the pack actually runs.
 *
 * CraftingMenuMixin was correct and still never fired. FastWorkbench 9.1.3 is installed, and its
 * MixinCraftingMenu carries an {@code @Overwrite} on {@code slotsChanged} that routes to
 * {@code FastBenchUtil.queueSlotUpdate} instead of vanilla's
 * {@code CraftingMenu.slotChangedCraftingGrid}. The vanilla method is dead code in this pack, so
 * the injection point sat on something that is never executed - and because the injector carries
 * {@code require = 0}, nothing said so. The symptom was a sieve crafting happily in survival with
 * {@code exdeorum:*} denied, and no {@code [pocketquests] crafting rules:} line in the log, since
 * that line is only printed on the gate's first lookup.
 *
 * Verified against the jar rather than guessed:
 * <pre>
 *   MixinCraftingMenu    @Overwrite slotsChanged -> FastBenchUtil.queueSlotUpdate
 *   MixinInventoryMenu   @Overwrite              -> FastBenchUtil.queueSlotUpdate / handleShiftCraft
 *   MixinBackpackMenu    (targets=...)           -> FastBenchUtil.handleShiftCraft
 *   FastBenchUtil.queueSlotUpdate -> slotChangedCraftingGrid -> findRecipe(CraftingInput, Level)
 * </pre>
 *
 * So all three menus - the crafting table, the 2x2 inventory grid and Sophisticated Backpacks'
 * grid - funnel through one method, and {@code findRecipe} is the single narrowest point that
 * covers every one of them. Shift-crafting is covered too: it reads the result that was already
 * placed, and if the lookup returned nothing there is nothing to bulk-craft.
 *
 * {@code findRecipe} takes and returns only vanilla types, which is what makes this targetable at
 * all - the build classpath deliberately excludes the mods being patched, so a hook on
 * {@code slotChangedCraftingGrid} (which takes FastWorkbench's own CraftingInventoryExt) could
 * not be written without adding FastWorkbench to it.
 *
 * It already returns null for "no recipe", so denying is just returning null: the output slot
 * stays empty and nothing is ever spent. {@code require = 0} because FastWorkbench is optional -
 * without it CraftingMenuMixin handles the vanilla path. PocketRules.logGatePath() prints which
 * of the two is expected to be in control at server start, so a silent failure is now visible.
 */
@Mixin(targets = "dev.shadowsoffire.fastbench.util.FastBenchUtil", remap = false)
public abstract class FastBenchMixin {

    @Inject(method = "findRecipe", at = @At("RETURN"), cancellable = true,
            remap = false, require = 0)
    private static void pocketquests$gateFastBench(
            CraftingInput input,
            Level level,
            CallbackInfoReturnable<RecipeHolder<CraftingRecipe>> cir) {
        try {
            RecipeHolder<CraftingRecipe> holder = cir.getReturnValue();
            if (holder == null || level == null) {
                return;
            }
            ItemStack result = holder.value().getResultItem(level.registryAccess());
            if (result == null || result.isEmpty()) {
                return;
            }
            String dim = level.dimension().location().toString();
            String item = BuiltInRegistries.ITEM.getKey(result.getItem()).toString();
            if (PocketRules.denied(dim, item)) {
                cir.setReturnValue(null);
            }
        } catch (Throwable t) {
            // fail open - never break crafting because the gate misbehaved
        }
    }
}
