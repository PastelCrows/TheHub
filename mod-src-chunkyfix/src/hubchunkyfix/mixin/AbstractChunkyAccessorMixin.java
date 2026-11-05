package hubchunkyfix.mixin;

import hubchunkyfix.ChunkyReady;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Makes Distant Horizons wait for Chunky instead of crashing the world.
 *
 * THE BUG, read out of both mods' bytecode rather than guessed.
 *
 * Chunky registers its API provider in its constructor, which NeoForge runs from
 * ServerStartingEvent. Minecraft fires that event AFTER loadLevel(), and loadLevel() is what
 * prints "Preparing start region" and generates the first chunks. So during world creation there
 * is a window in which chunks are being generated and Chunky's provider is still null.
 *
 * DH binds its Chunky listener from a chunk-load event, and its guard is:
 *
 *     public void tryRunFirstTimeSetup() {
 *         if (listenerBound) return;
 *         listenerBound = true;              // set BEFORE the attempt
 *         bindOnGenerationProgressEvent();   // ChunkyProvider.get() -> IllegalStateException
 *     }
 *
 * Two faults in four lines. The exception escapes into chunk promotion, which is why the crash
 * report says "Exception during promotion of chunk to FULL status" rather than naming Chunky.
 * And because listenerBound is set before the call, the binding could never be retried even if
 * the throw were swallowed.
 *
 * THE FIX. Cancel at HEAD while Chunky is not yet registered. listenerBound is still false at
 * that point, so nothing is consumed and DH tries again on the next chunk - which it does
 * constantly, via SharedApi.applyChunkUpdate. Once ServerStartingEvent has run and Chunky has
 * registered, the very next chunk binds the listener normally and the integration works as
 * intended.
 *
 * WHY NOT JUST REMOVE CHUNKY. That was the first thing tried and it was wrong: Chunky is here on
 * purpose, to pre-render chunks so DH can build LODs from them. Removing it removes the feature
 * and calls the crash fixed.
 *
 * require = 1: if DH renames this method, fail loudly rather than silently stop deferring and
 * bring the crash back.
 */
@Mixin(targets = "com.seibel.distanthorizons.core.wrapperInterfaces.modAccessor.AbstractChunkyAccessor",
       remap = false)
public abstract class AbstractChunkyAccessorMixin {

    @Inject(method = "tryRunFirstTimeSetup()V", at = @At("HEAD"), cancellable = true, require = 1)
    private void hubchunkyfix$waitForChunky(CallbackInfo ci) {
        if (!ChunkyReady.isReady()) {
            ci.cancel();
        }
    }
}
