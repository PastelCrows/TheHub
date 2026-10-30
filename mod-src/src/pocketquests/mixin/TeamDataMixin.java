package pocketquests.mixin;

import dev.ftb.mods.ftbquests.quest.TeamData;
import dev.ftb.mods.ftbquests.quest.task.Task;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import pocketquests.PocketGate;

/**
 * setProgress is the single chokepoint: addProgress does nothing but read, add and call it,
 * so gating here covers every route to quest progress.
 */
@Mixin(TeamData.class)
public abstract class TeamDataMixin {

    @Inject(
        method = "setProgress(Ldev/ftb/mods/ftbquests/quest/task/Task;J)V",
        at = @At("HEAD"),
        cancellable = true
    )
    private void pocketquests$gateProgress(Task task, long progress, CallbackInfo ci) {
        TeamData self = (TeamData) (Object) this;
        if (!PocketGate.allowed(self, task)) {
            ci.cancel();
        }
    }
}
