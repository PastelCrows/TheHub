package hubtmfilter.mixin;

import com.cobblemon.mod.common.api.tms.TechnicalMachines;
import hubtmfilter.TmFilter;
import net.minecraft.server.packs.resources.ResourceManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.Map;

/**
 * Hooks Cobblemon's TM data registry so bad TM entries can be dropped after it loads.
 *
 * Both overloads were verified present in Cobblemon-neoforge-1.8.4+1.21.1 with exactly these
 * descriptors, read with javap rather than assumed:
 *
 *     public void reload(net.minecraft.server.packs.resources.ResourceManager)
 *     public void reload(java.util.Map<ResourceLocation, TechnicalMachine>)
 *
 * The Cobblemon class path is identical on Fabric and NeoForge because Cobblemon is multiloader
 * via Architectury; only the Minecraft type changed, from the intermediary class_3300 in Kewz's
 * Fabric build to the official ResourceManager here. That is the whole of the port.
 *
 * require = 1 on every injector, deliberately. A silently dead mixin is the failure mode that has
 * cost the most time on this project; if Cobblemon renames reload, this must fail loudly at
 * startup rather than leave the filter quietly doing nothing.
 */
@Mixin(TechnicalMachines.class)
public abstract class TechnicalMachinesMixin {

    @Inject(method = "reload(Lnet/minecraft/server/packs/resources/ResourceManager;)V",
            at = @At("HEAD"), require = 1)
    private void hubtmfilter$dataLoadStarts(ResourceManager manager, CallbackInfo ci) {
        TmFilter.begin(manager);
    }

    @Inject(method = "reload(Ljava/util/Map;)V", at = @At("RETURN"), require = 1)
    private void hubtmfilter$mapFilled(Map<?, ?> map, CallbackInfo ci) {
        TmFilter.filter();
    }

    @Inject(method = "reload(Lnet/minecraft/server/packs/resources/ResourceManager;)V",
            at = @At("RETURN"), require = 1)
    private void hubtmfilter$dataLoadEnds(ResourceManager manager, CallbackInfo ci) {
        TmFilter.end();
    }
}
