package pocketquests.mixin;

import net.minecraft.world.level.LevelAccessor;
import net.neoforged.bus.api.Event;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import pocketquests.PocketEffects;

/**
 * Keeps the Horror Messages mod from whispering into pocket dimensions that are not horror.
 *
 * The mod posts a line of chat from nobody on a timer, with no notion of where the player is -
 * which is how "Help me" turned up in redstone land, a creative redstone sandbox.
 *
 * MCreator generates one static procedure class per behaviour, and this one is unusually tidy to
 * gate: BOTH public entry points, the LevelTickEvent handler and the /forcehorrormessage command,
 * call through to a single private execute(Event, LevelAccessor). Cancelling at the head of that
 * covers the timer and the command in one injection, before the cooldown bookkeeping runs, so a
 * suppressed message is not also a consumed one.
 *
 * The level comes in as an argument, so the test is exact: the message is dropped for the level it
 * was about to be posted to rather than for the server as a whole. Nothing is suppressed inside
 * the horror pocket dimension, where the mod is the point.
 *
 * `remap = false` and `targets` by name: this patches another mod, which is already in official
 * names at runtime and has no mapping to apply. `require = 0` because a failed injection here
 * means slightly misplaced ambience, and crashing the pack over that would be the worse outcome;
 * the PocketEffects log line reports whether the gate loaded.
 */
@Mixin(targets = "net.mcreator.horrormessagesneoforge.procedures.SendHorrorMessageProcedure",
        remap = false)
public class HorrorMessagesMixin {

    @Inject(method = "execute(Lnet/neoforged/bus/api/Event;Lnet/minecraft/world/level/LevelAccessor;)V",
            at = @At("HEAD"), cancellable = true, remap = false, require = 0)
    private static void pocketquests$gateHorrorMessage(Event event, LevelAccessor level,
                                                       CallbackInfo ci) {
        if (!PocketEffects.allowedIn(PocketEffects.HORROR_MESSAGES, level)) {
            ci.cancel();
        }
    }
}
