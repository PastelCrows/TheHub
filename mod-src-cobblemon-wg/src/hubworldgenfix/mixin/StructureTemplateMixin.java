package hubworldgenfix.mixin;

import hubworldgenfix.PoolRepair;
import net.minecraft.core.HolderGetter;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Repairs the structure NBT before vanilla reads it.
 *
 * HEAD, not RETURN: the pool string has to be valid before the palette and block entities are
 * parsed, because that parse is what throws on a malformed id. Fixing it afterwards would be
 * fixing a structure that already failed to load.
 *
 * The signature was read out of Prism's deobfuscated srg jar, not recalled:
 *
 *     public void load(net.minecraft.core.HolderGetter<Block>, net.minecraft.nbt.CompoundTag)
 *
 * Kewz's Fabric build names the same method method_15183(class_7871, class_2487); these are the
 * same method under different mappings.
 *
 * require = 1 so a vanilla rename fails the build loudly rather than leaving a dead fix.
 */
@Mixin(StructureTemplate.class)
public abstract class StructureTemplateMixin {

    @Inject(method = "load(Lnet/minecraft/core/HolderGetter;Lnet/minecraft/nbt/CompoundTag;)V",
            at = @At("HEAD"), require = 1)
    private void hubworldgenfix$repairJigsawPools(HolderGetter<Block> blocks, CompoundTag tag,
                                                  CallbackInfo ci) {
        PoolRepair.repair(tag);
    }
}
