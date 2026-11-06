package hubclientperf;

import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.Entity;

import java.util.IdentityHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;

/**
 * Holds an entity's NBT for the length of one client tick.
 *
 * <p>Entity Texture Features reads an entity's NBT to decide which texture variant applies, and
 * it does so per render rather than per tick. Building that tag copies the entity's data; with a
 * screen full of Pokemon it is the same work repeated every frame for data that cannot change
 * between frames of the same tick.
 *
 * <p>Keyed by entity IDENTITY, not UUID, so no hashing of the key is involved and two entities
 * can never collide. Cleared wholesale once per client tick, which is also what bounds its size -
 * there is no eviction policy to get wrong and nothing survives a tick boundary.
 *
 * <p>Three guards, all from Kewz's version and all load-bearing:
 * <ul>
 *   <li>the key must actually be an {@link Entity} - ETF's state object is passed as Object</li>
 *   <li>render thread only, which is what makes a plain IdentityHashMap safe here</li>
 *   <li>the supplied UUID must match the entity's own, so a stale or mismatched state object
 *       falls through to the real call rather than being answered from the wrong entity</li>
 * </ul>
 * Any guard failing returns null, which the mixin treats as "no cached answer, do it properly".
 */
public final class NbtTickCache {

    private static final Map<Entity, CompoundTag> TAGS = new IdentityHashMap<>();

    private NbtTickCache() {
    }

    /** Called at the head of each client tick. */
    public static void onClientTick() {
        if (!TAGS.isEmpty()) {
            TAGS.clear();
        }
    }

    public static CompoundTag get(Object key, UUID uuid, Supplier<CompoundTag> compute) {
        if (!(key instanceof Entity entity)) {
            return null;
        }
        if (!RenderSystem.isOnRenderThread()) {
            return null;
        }
        if (uuid == null || !uuid.equals(entity.getUUID())) {
            return null;
        }
        CompoundTag tag = TAGS.get(entity);
        if (tag == null) {
            tag = compute.get();
            if (tag != null) {
                TAGS.put(entity, tag);
            }
        }
        return tag;
    }
}
