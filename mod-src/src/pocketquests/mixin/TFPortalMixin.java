package pocketquests.mixin;

import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

import pocketquests.PocketWorlds;

/**
 * Sends a Twilight Forest return portal back to the pocket dimension you actually came from.
 *
 * Twilight Forest has ONE origin dimension for the whole server. `TFConfig.originDimension` is a
 * single string, `TFPortalBlock` caches it into a single `ResourceKey<Level>`, and
 * `getPortalDestination` hands that key to `MinecraftServer.getLevel` whenever you leave. In an
 * ordinary pack that is exactly right. In the hub it is wrong twice:
 *
 *   1. shipped as "minecraft:overworld", which is not a pocket dimension at all - DimSwap groups
 *      the vanilla three with the LOBBY, so returning there crosses an inventory boundary into a
 *      world that is not part of any gamemode; and
 *   2. even pointed at a real pocket dimension it can only name ONE, so survival, lostcities and
 *      gauntlet - all three of which own the mod - would come home to the same place.
 *
 * Config cannot express "whichever pocket dimension the traveller came from", so this does.
 *
 * WHY A REDIRECT RATHER THAN AN INJECT. `getPortalDestination` takes the level it resolved and
 * then derives the world border, the teleportation scale and finally the transition itself from
 * it. Redirecting the single `getLevel` call substitutes the destination before any of that, so
 * the border clamp, the coordinate scaling and TF's own portal search all run against the right
 * level with no logic duplicated here - and nothing from the Twilight Forest jar is needed on the
 * compile classpath.
 *
 * Only the OUTBOUND trip is touched. Travel INTO the Twilight Forest already resolves to
 * `TFDimension.DIMENSION_KEY`, which is correct and shared; it is the separation into per-pocket
 * regions that keeps those arrivals apart, and PocketWorlds handles that on the dimension-change
 * event. So the substitution is gated on the player currently standing in the dimension being
 * left - if `getLevel` was called for anything other than leaving a shared dimension, the
 * original result is returned untouched.
 *
 * Fails OPEN in every direction: an unknown origin, a pocket dimension whose level does not
 * exist, or any throwable at all yields Twilight Forest's own answer. Being sent to the
 * configured dimension is a disappointment; being sent nowhere is a lost session.
 *
 * `require = 0` because this patches another mod. The access gate in PocketWorlds still prevents
 * pocket dimensions that do not own Twilight Forest from reaching it, so a failed injection here
 * degrades to "returns to the configured dimension", not to a hole in the separation.
 */
@Mixin(targets = "twilightforest.block.TFPortalBlock", remap = false)
public class TFPortalMixin {

    @Redirect(
            method = "getPortalDestination",
            at = @At(value = "INVOKE",
                     target = "Lnet/minecraft/server/MinecraftServer;getLevel"
                            + "(Lnet/minecraft/resources/ResourceKey;)"
                            + "Lnet/minecraft/server/level/ServerLevel;"),
            remap = false, require = 0)
    private ServerLevel pocketquests$returnToOwnPocket(MinecraftServer server,
                                                       ResourceKey<Level> key,
                                                       ServerLevel current,
                                                       Entity entity,
                                                       BlockPos pos) {
        ServerLevel original = server.getLevel(key);
        try {
            // Only on the way OUT. Entering resolves to the Twilight Forest key, which is right.
            if (current == null
                    || !PocketWorlds.isSharedLevel(current.dimension().location().toString())) {
                return original;
            }
            ServerLevel home = PocketWorlds.pocketOverworldFor(server, entity);
            return home != null ? home : original;
        } catch (Throwable t) {
            return original;
        }
    }
}
