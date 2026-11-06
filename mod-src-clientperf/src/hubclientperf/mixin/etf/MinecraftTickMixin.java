package hubclientperf.mixin.etf;

import hubclientperf.NbtTickCache;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Drops the entity-NBT cache once per client tick.
 *
 * <p>This is what makes it a one-tick cache rather than a leak. The cache is keyed on live
 * {@code Entity} objects, so without a hard clear every tick it would hold references to
 * entities that have died or despawned, and would eventually serve a stale tag for a reused
 * object.
 *
 * <p>It sits in the ETF mixin config rather than the vanilla one on purpose: in a pack without
 * ETF nothing fills this cache, so there is no reason to hook the client tick at all.
 */
@Mixin(Minecraft.class)
public abstract class MinecraftTickMixin {

    @Inject(method = "tick()V", at = @At("HEAD"), require = 1)
    private void hubclientperf$clearNbtCache(CallbackInfo ci) {
        NbtTickCache.onClientTick();
    }
}
