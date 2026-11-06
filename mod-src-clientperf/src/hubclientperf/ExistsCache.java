package hubclientperf;

import net.minecraft.resources.ResourceLocation;

import java.util.concurrent.ConcurrentHashMap;

/**
 * Remembers whether a resource exists, until the next resource reload.
 *
 * <p>Cobblemon's {@code ClientDistributionUtilsKt.exists(ResourceLocation)} is simply:
 *
 * <pre>Minecraft.getInstance().getResourceManager().getResource(loc).isPresent()</pre>
 *
 * On the client that resource manager is a stack of packs, so each call walks the stack and
 * allocates an {@code Optional} to answer a yes/no question. Cobblemon asks it per variant
 * texture while rendering, which across 4,900 species is thousands of identical questions per
 * frame.
 *
 * <p>The answer only changes when the pack set changes, which is exactly a resource reload - so
 * {@link hubclientperf.mixin.cobblemon.ReloadableResourceManagerMixin} empties this on every
 * reload. Without that invalidation the cache would be a correctness bug rather than an
 * optimisation: enabling a resource pack mid-session would not take effect.
 *
 * <p>From Kewz's {@code kewz-client-perf}; his version is the same shape.
 */
public final class ExistsCache {

    private static final ConcurrentHashMap<ResourceLocation, Boolean> ANSWERS =
            new ConcurrentHashMap<>();

    private ExistsCache() {
    }

    /** null means "not asked yet", not "does not exist". */
    public static Boolean get(ResourceLocation id) {
        return ANSWERS.get(id);
    }

    public static void put(ResourceLocation id, boolean exists) {
        ANSWERS.put(id, exists);
    }

    public static void clear() {
        ANSWERS.clear();
    }
}
