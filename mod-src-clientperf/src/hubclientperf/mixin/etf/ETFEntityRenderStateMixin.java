package hubclientperf.mixin.etf;

import hubclientperf.NbtTickCache;
import net.minecraft.nbt.CompoundTag;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import java.util.UUID;
import java.util.function.Supplier;

/**
 * Serves ETF's per-render entity NBT from a one-tick cache.
 *
 * <p>Verified present in entity_texture_features-7.2.6-1.21-neoforge:
 *
 * <pre>public CompoundTag cacheEntityNBTForState(UUID, Supplier&lt;CompoundTag&gt;)</pre>
 *
 * <p>Despite the method name, what ETF keeps is rebuilt per render rather than per tick, so the
 * tag is recomputed every frame for data that cannot change inside a tick. On a screen full of
 * Pokemon that is the dominant cost of ETF's variant selection.
 *
 * <p>All the safety lives in {@link NbtTickCache}: entity-identity key, render thread only, and
 * the passed UUID must match the entity's own. A null from it means "no usable cached answer", and
 * this injector then simply does not cancel, so ETF computes it exactly as before.
 */
@Mixin(targets = "traben.entity_texture_features.features.state.ETFEntityRenderStateViaReference",
       remap = false)
public abstract class ETFEntityRenderStateMixin {

    @Inject(method = "cacheEntityNBTForState(Ljava/util/UUID;Ljava/util/function/Supplier;)"
            + "Lnet/minecraft/nbt/CompoundTag;",
            at = @At("HEAD"), cancellable = true, require = 1)
    private void hubclientperf$fromTickCache(UUID uuid, Supplier<CompoundTag> supplier,
                                             CallbackInfoReturnable<CompoundTag> cir) {
        CompoundTag cached = NbtTickCache.get(this, uuid, supplier);
        if (cached != null) {
            cir.setReturnValue(cached);
        }
    }
}
