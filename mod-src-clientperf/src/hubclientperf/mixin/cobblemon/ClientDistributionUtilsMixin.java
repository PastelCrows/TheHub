package hubclientperf.mixin.cobblemon;

import hubclientperf.ExistsCache;
import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Answers Cobblemon's resource-exists question from a cache.
 *
 * <p>Verified present in Cobblemon-neoforge-1.8.4+1.21.1 with exactly this descriptor:
 *
 * <pre>public static final boolean exists(net.minecraft.resources.ResourceLocation)</pre>
 *
 * <p>Its body is one line - {@code getResourceManager().getResource(loc).isPresent()} - which on
 * the client walks the whole pack stack and allocates an Optional to answer yes or no. Cobblemon
 * asks it per variant texture while rendering.
 *
 * <p>Targeted by STRING, and the config that owns it is {@code required: false}, because this
 * class also has to load in the twelve instances that have no Cobblemon at all. Mixin skips a
 * non-required config whose target is missing; the injector keeps {@code require = 1} so that if
 * Cobblemon IS present and has renamed the method, it fails loudly instead of silently dropping
 * the cache.
 */
@Mixin(targets = "com.cobblemon.mod.common.client.util.ClientDistributionUtilsKt", remap = false)
public abstract class ClientDistributionUtilsMixin {

    @Inject(method = "exists(Lnet/minecraft/resources/ResourceLocation;)Z",
            at = @At("HEAD"), cancellable = true, require = 1)
    private static void hubclientperf$fromCache(ResourceLocation id,
                                                CallbackInfoReturnable<Boolean> cir) {
        Boolean known = ExistsCache.get(id);
        if (known != null) {
            cir.setReturnValue(known);
        }
    }

    @Inject(method = "exists(Lnet/minecraft/resources/ResourceLocation;)Z",
            at = @At("RETURN"), require = 1)
    private static void hubclientperf$toCache(ResourceLocation id,
                                              CallbackInfoReturnable<Boolean> cir) {
        ExistsCache.put(id, cir.getReturnValue());
    }
}
