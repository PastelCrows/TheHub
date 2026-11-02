package hubworldgenfix;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Repairs invalid jigsaw pool identifiers inside structure NBT as it is read.
 *
 * <p>WHY, MEASURED. A jigsaw block stores its target pool as a plain string in the structure's
 * NBT. Nothing validates it at save time, so a structure can ship an id that is not a legal
 * ResourceLocation, and parsing it throws while the structure is being placed. Scanning all
 * <b>1,928 structure .nbt files across 303 jars</b> in this pack found <b>4</b> real cases, all
 * in Legendary Monuments, all with the pool literally {@code "minecraft:"} - a namespace and an
 * empty path:
 *
 * <pre>
 *   traditional_village/pagoda/burned_tower_2.nbt
 *   traditional_village/pagoda/burned_tower_3.nbt
 *   traditional_village/pagoda/burned_tower_4.nbt
 *   turnback_cave/connectors/connector.nbt
 * </pre>
 *
 * <p>This is a port of the generic half of Kewz's {@code kewz-worldgen-compat}, read out of his
 * jar's bytecode. His version also remaps {@code bca:feature/berries} to
 * {@code bca:general/berries}; that is deliberately NOT here, because the BCA mod is not in this
 * pack and a remap for a mod nobody runs is dead code pretending to be a fix.
 *
 * <p>WHERE THIS GENERALISES HIS VERSION, AND WHY THAT IS JUSTIFIED. He tests for the exact string
 * {@code "minecraft:"}. Our four bad files come from a different mod than his did, which is the
 * evidence that this malformation is not one mod's quirk - so rather than match a literal, any
 * pool that {@link ResourceLocation#tryParse} rejects is replaced. That strictly contains his
 * check and costs nothing.
 *
 * <p>{@code minecraft:empty} is the replacement because it is vanilla's real, always-present
 * empty pool: a jigsaw pointing at it simply places nothing, which is the intended behaviour for
 * a connector whose pool was never set. Deleting the jigsaw block instead would change the
 * structure's shape.
 */
public final class PoolRepair {

    private static final Logger LOG = LoggerFactory.getLogger("hubworldgenfix");
    private static final String EMPTY_POOL = "minecraft:empty";

    /** Logged once rather than 1,928 times; a fix that spams is a fix people turn off. */
    private static boolean reported = false;

    private PoolRepair() {
    }

    public static void repair(CompoundTag root) {
        if (root == null || !root.contains("blocks", Tag.TAG_LIST)) {
            return;
        }
        ListTag blocks = root.getList("blocks", Tag.TAG_COMPOUND);
        int fixed = 0;

        for (int i = 0; i < blocks.size(); i++) {
            CompoundTag block = blocks.getCompound(i);
            if (!block.contains("nbt", Tag.TAG_COMPOUND)) {
                continue;
            }
            CompoundTag blockEntity = block.getCompound("nbt");
            if (!blockEntity.contains("pool", Tag.TAG_STRING)) {
                continue;
            }
            String pool = blockEntity.getString("pool");
            if (pool.isEmpty() || ResourceLocation.tryParse(pool) == null) {
                blockEntity.putString("pool", EMPTY_POOL);
                fixed++;
            }
        }

        if (fixed > 0 && !reported) {
            reported = true;
            LOG.info("hubworldgenfix replaced {} invalid jigsaw pool id(s) with {}"
                    + " (logged once; further repairs are silent)", fixed, EMPTY_POOL);
        }
    }
}
