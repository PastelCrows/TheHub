package pocketquests.mixin;

import dev.ftb.mods.ftbquests.client.gui.quests.QuestScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import pocketquests.PocketBook;

/**
 * When the quest book opens, jump to the pocket the player is standing in.
 *
 * Injected at RETURN of onInit so the chapter panel exists before a chapter is selected.
 * `require = 0` on purpose: if FTB Quests renames onInit this silently stops working rather
 * than crashing the client, which is the right trade for a convenience.
 */
@Mixin(QuestScreen.class)
public abstract class QuestScreenMixin {

    @Inject(method = "onInit", at = @At("RETURN"), require = 0)
    private void pocketquests$openCurrentPocket(CallbackInfoReturnable<Boolean> cir) {
        PocketBook.selectForCurrentDimension((QuestScreen) (Object) this);
    }
}
