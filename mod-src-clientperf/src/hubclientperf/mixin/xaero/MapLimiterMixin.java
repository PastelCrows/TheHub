package hubclientperf.mixin.xaero;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Rate-limits Xaero's VRAM query to once a second.
 *
 * <p>Verified present in xaeroworldmap-neoforge-1.21.1-1.47.0:
 *
 * <pre>public void updateAvailableVRAM()</pre>
 *
 * <p>Asking how much VRAM is free goes through the graphics driver, and a driver query issued on
 * the render thread can stall the pipeline while it answers. The figure does not meaningfully
 * change between consecutive frames, so asking once a second produces the same behaviour without
 * paying for it every frame.
 *
 * <p>The one-second interval and the "always allow the first call" flag are Kewz's, read out of
 * his bytecode as a literal {@code 1000000000L} nanosecond comparison rather than invented here.
 * The first call always runs, so Xaero still has a real number before it needs one.
 *
 * <p>Both fields are {@code @Unique} and per-instance, matching his: a MapLimiter is per map, and
 * a static timestamp would let one map's query suppress another's.
 */
@Mixin(targets = "xaero.map.MapLimiter", remap = false)
public abstract class MapLimiterMixin {

    @Unique
    private long hubclientperf$lastQueryNanos;

    @Unique
    private boolean hubclientperf$queried;

    @Inject(method = "updateAvailableVRAM()V", at = @At("HEAD"), cancellable = true, require = 1)
    private void hubclientperf$onceASecond(CallbackInfo ci) {
        long now = System.nanoTime();
        if (this.hubclientperf$queried
                && now - this.hubclientperf$lastQueryNanos < 1_000_000_000L) {
            ci.cancel();
            return;
        }
        this.hubclientperf$queried = true;
        this.hubclientperf$lastQueryNanos = now;
    }
}
