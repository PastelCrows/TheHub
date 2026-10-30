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
 * Sends an Aether return portal back to the pocket dimension you actually came from.
 *
 * Exactly the same bug as Twilight Forest, in exactly the same shape. The Aether reads
 * `portal_return_dimension_ID` - one string for the whole server - through
 * `LevelUtil.returnDimension()`, and `AetherPortalBlock.getPortalDestination` hands that to
 * `MinecraftServer.getLevel`. It ships as "minecraft:overworld", which DimSwap groups with the
 * LOBBY, so returning crossed an inventory boundary into a world belonging to no gamemode; and
 * even aimed at a real pocket dimension it can only name one, while survival, lostcities and
 * gauntlet all own the Aether.
 *
 * So: the same single `getLevel` redirect as TFPortalMixin, for the same reasons - the method
 * derives the world border, the teleportation scale and the transition from the level it
 * resolved, so substituting the level fixes all of it with nothing duplicated and no Aether
 * classes needed on the compile classpath.
 *
 * NOT the whole story, deliberately. Falling off the edge of the Aether is a separate path that
 * runs through the Aether's OWN mixin on Entity (a merged `entityFell` helper), which is not a
 * reliable injection target - patching another mod's merged mixin method depends on mixin
 * internals and application order. That path is covered instead by the escape-hatch net in
 * PocketWorlds.onTravel, which catches ANY attempt to leave a shared modded dimension for a
 * vanilla one and redirects it in a single dimension change. Between the two, both ways out of
 * the Aether land in the right pocket dimension.
 *
 * Fails OPEN throughout, and `require = 0` because this patches another mod.
 */
@Mixin(targets = "com.aetherteam.aether.block.portal.AetherPortalBlock", remap = false)
public class AetherPortalMixin {

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
            // Only on the way OUT. Entering resolves to the Aether, which is correct.
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
