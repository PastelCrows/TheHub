package hubclientperf.mixin.cobblemon;

import hubclientperf.ExistsCache;
import net.minecraft.server.packs.resources.ReloadInstance;
import net.minecraft.server.packs.resources.ReloadableResourceManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Empties the exists-cache whenever the resource packs are reloaded.
 *
 * <p>This is not an optimisation; it is what keeps the cache CORRECT. "Does this texture exist"
 * is only a stable answer for a fixed pack set, and enabling or disabling a resource pack changes
 * it. Without this, a cached "no" would outlive the pack being switched on and the texture would
 * stay invisible until a restart - a cache without invalidation is just a bug with better
 * latency.
 *
 * <p>It lives in the cobblemon mixin config rather than the vanilla one on purpose: the only
 * cache it clears is the one Cobblemon's {@code exists} fills, so in a pack without Cobblemon
 * there is nothing here worth hooking.
 *
 * <p>Signature verified in Prism's deobfuscated jar:
 *
 * <pre>public ReloadInstance createReload(Executor, Executor, CompletableFuture&lt;Unit&gt;,
 *                                   List&lt;PackResources&gt;)</pre>
 */
@Mixin(ReloadableResourceManager.class)
public abstract class ReloadableResourceManagerMixin {

    @Inject(method = "createReload(Ljava/util/concurrent/Executor;Ljava/util/concurrent/Executor;"
            + "Ljava/util/concurrent/CompletableFuture;Ljava/util/List;)"
            + "Lnet/minecraft/server/packs/resources/ReloadInstance;",
            at = @At("RETURN"), require = 1)
    private void hubclientperf$invalidateExistsCache(CallbackInfoReturnable<ReloadInstance> cir) {
        ExistsCache.clear();
    }
}
