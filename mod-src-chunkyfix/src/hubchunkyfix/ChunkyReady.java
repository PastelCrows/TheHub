package hubchunkyfix;

import java.lang.reflect.Field;

/**
 * Is Chunky's API provider registered yet?
 *
 * <p>Answered by READING Chunky's field, not by calling its getter. {@code ChunkyProvider.get()}
 * throws {@code IllegalStateException("Chunky is not loaded.")} when the provider is unset, and
 * using an exception as a test is what caused the crash this mod exists to fix - the throw
 * escaped into chunk promotion. The field is read directly so the question can be asked without
 * anything being thrown.
 *
 * <p>Reflection rather than a compile-time reference, for two reasons: it keeps Chunky off this
 * mod's classpath so it stays a soft dependency, and if Chunky is absent entirely the lookup
 * simply fails and reports "not ready" - which is also the correct answer, since there is nothing
 * for Distant Horizons to bind to.
 */
public final class ChunkyReady {

    private static final String PROVIDER = "org.popcraft.chunky.ChunkyProvider";
    private static final String FIELD = "instance";

    /** Resolved once. null means Chunky is not present at all. */
    private static Field instanceField;
    private static boolean looked = false;

    private ChunkyReady() {
    }

    public static synchronized boolean isReady() {
        if (!looked) {
            looked = true;
            try {
                Class<?> provider = Class.forName(PROVIDER);
                Field f = provider.getDeclaredField(FIELD);
                f.setAccessible(true);
                instanceField = f;
            } catch (Throwable t) {
                // Chunky absent, or its internals moved. Either way: never ready, never crash.
                instanceField = null;
            }
        }
        if (instanceField == null) {
            return false;
        }
        try {
            return instanceField.get(null) != null;
        } catch (Throwable t) {
            return false;
        }
    }
}
