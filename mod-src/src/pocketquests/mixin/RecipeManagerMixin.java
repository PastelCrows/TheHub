package pocketquests.mixin;

import java.util.Optional;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeInput;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import pocketquests.PocketRules;

/**
 * The crafting gate. Third attempt, and the first one that cannot fail quietly.
 *
 * The first two both sat on somebody's implementation of crafting rather than on crafting itself:
 *
 *   CraftingMenuMixin  vanilla CraftingMenu.slotChangedCraftingGrid - dead code in this pack,
 *                      because FastWorkbench @Overwrite's slotsChanged and never calls it.
 *   FastBenchMixin     FastWorkbench's own FastBenchUtil.findRecipe - correct target, correct
 *                      descriptor, and it still never fired. Both carried require = 0, so each
 *                      shipped a gate that did nothing and said nothing. Two smoke tests were
 *                      spent discovering that, the second one with the boot log reporting
 *                      "crafting gate: fastbench path" and "crafting rules: 6 dimensions,
 *                      96 patterns" - both true, both useless, because the lines only proved the
 *                      CONFIG had loaded.
 *
 * So the gate now sits on RecipeManager.getRecipeFor, which is where the question "what does this
 * grid make?" is actually answered - by vanilla, by FastWorkbench, and by anything else that asks
 * the recipe manager. Two properties matter more than elegance here:
 *
 *   It is VANILLA. The signature comes out of the deobfuscated client jar, not out of a mod that
 *   is free to rewrite itself on any update.
 *
 *   It is require = 1. If the descriptor ever stops matching, the game fails to start and says
 *   so. After two silent no-ops, a loud failure is the feature. Do not lower this.
 *
 * All three overloads are injected because they are reached by different callers and do not all
 * delegate to one another: vanilla's crafting grid takes the one with the cached RecipeHolder,
 * FastWorkbench takes the three-argument one, and the recipe book takes the one with a
 * ResourceLocation. Filtering at RETURN on each is idempotent - a nested call that was already
 * filtered returns empty and the outer filter simply sees nothing to do.
 *
 * Denying = returning Optional.empty(), which is exactly "no recipe matches". Every caller already
 * handles it: the output slot stays empty and no ingredient is ever consumed.
 *
 * SCOPE, deliberately unchanged: RecipeType.CRAFTING only. pocketrules.json has always documented
 * itself as covering the crafting grid and not furnaces, smithing tables or stonecutters, and the
 * quest chapters were verified against that reading. Widening it here would silently change what
 * horror's 91 namespaces mean.
 */
@Mixin(RecipeManager.class)
public abstract class RecipeManagerMixin {

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
            + "Lnet/minecraft/world/item/crafting/RecipeInput;"
            + "Lnet/minecraft/world/level/Level;)Ljava/util/Optional;",
            at = @At("RETURN"), cancellable = true, require = 1)
    private void pocketquests$gate3(RecipeType<?> type, RecipeInput input, Level level,
                                    CallbackInfoReturnable<Optional<RecipeHolder<?>>> cir) {
        pocketquests$filter(type, level, cir);
    }

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
            + "Lnet/minecraft/world/item/crafting/RecipeInput;"
            + "Lnet/minecraft/world/level/Level;"
            + "Lnet/minecraft/resources/ResourceLocation;)Ljava/util/Optional;",
            at = @At("RETURN"), cancellable = true, require = 1)
    private void pocketquests$gate4id(RecipeType<?> type, RecipeInput input, Level level,
                                      ResourceLocation id,
                                      CallbackInfoReturnable<Optional<RecipeHolder<?>>> cir) {
        pocketquests$filter(type, level, cir);
    }

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
            + "Lnet/minecraft/world/item/crafting/RecipeInput;"
            + "Lnet/minecraft/world/level/Level;"
            + "Lnet/minecraft/world/item/crafting/RecipeHolder;)Ljava/util/Optional;",
            at = @At("RETURN"), cancellable = true, require = 1)
    private void pocketquests$gate4last(RecipeType<?> type, RecipeInput input, Level level,
                                        RecipeHolder<?> last,
                                        CallbackInfoReturnable<Optional<RecipeHolder<?>>> cir) {
        pocketquests$filter(type, level, cir);
    }

    private static void pocketquests$filter(RecipeType<?> type, Level level,
                                            CallbackInfoReturnable<Optional<RecipeHolder<?>>> cir) {
        try {
            if (type != RecipeType.CRAFTING || level == null) {
                return;
            }
            Optional<RecipeHolder<?>> found = cir.getReturnValue();
            if (found == null || !found.isPresent()) {
                return;
            }
            ItemStack result = found.get().value().getResultItem(level.registryAccess());
            if (result == null || result.isEmpty()) {
                return;
            }
            String dim = level.dimension().location().toString();
            String item = BuiltInRegistries.ITEM.getKey(result.getItem()).toString();
            if (PocketRules.denied(dim, item)) {
                cir.setReturnValue(Optional.empty());
            }
        } catch (Throwable t) {
            // fail open - never break crafting because the gate misbehaved
        }
    }
}
