package pocketquests.mixin;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.CraftingContainer;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import pocketquests.PocketRules;

/**
 * Blocks a craft outright when the current dimension disallows its result.
 *
 * Why here: recipes are global. They load once per datapack reload and carry no notion of where
 * the player is, so "no sieves in the nether pocket" cannot be expressed as a recipe at all.
 * `slotChangedCraftingGrid` is the one place where a recipe result, a player and a level meet -
 * and it is shared, so a single injection covers BOTH the crafting table (CraftingMenu) and the
 * 2x2 inventory grid (InventoryMenu calls this same static method).
 *
 * Injected at RETURN, after vanilla has placed the result, and the result is then cleared. The
 * output slot simply stays empty, which is the behaviour actually wanted: the craft is impossible
 * rather than possible-then-confiscated, so nothing is ever spent on it.
 *
 * `require = 0` on purpose. A failed injection here means recipes are not gated - a design
 * disappointment - whereas crashing the game over it would be worse. The log line in PocketRules
 * says whether the rules loaded, which is the thing to check if gating seems inactive.
 *
 * Not covered, deliberately: furnaces, smithing tables, stonecutters and modded machine recipes
 * all use different menus. This gates the crafting grid only.
 */
@Mixin(net.minecraft.world.inventory.CraftingMenu.class)
public abstract class CraftingMenuMixin {

    @Inject(method = "slotChangedCraftingGrid", at = @At("RETURN"), require = 0)
    private static void pocketquests$gateCrafting(AbstractContainerMenu menu,
                                                  Level level,
                                                  Player player,
                                                  CraftingContainer craftSlots,
                                                  ResultContainer resultSlots,
                                                  RecipeHolder<CraftingRecipe> recipe,
                                                  CallbackInfo ci) {
        try {
            if (level == null || resultSlots == null) {
                return;
            }
            ItemStack result = resultSlots.getItem(0);
            if (result == null || result.isEmpty()) {
                return;
            }
            String dim = level.dimension().location().toString();
            String item = BuiltInRegistries.ITEM.getKey(result.getItem()).toString();
            if (PocketRules.denied(dim, item)) {
                resultSlots.setItem(0, ItemStack.EMPTY);
            }
        } catch (Throwable t) {
            // fail open - never break crafting because the gate misbehaved
        }
    }
}
