package pocketquests;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelAccessor;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Confines ambient horror AMBIENCE to the pocket dimensions that asked for it.
 *
 * PocketMobs already fences the creatures. What it cannot touch is the class of mod that has no
 * entity at all and works purely by acting on the world or the chat: a message from nobody, a
 * torch that goes out, a house that burns down. Those mods are global, so building the horror
 * pack into the hub made them global too. The symptom that found this was the words "Help me"
 * appearing in chat in redstone land, which is a creative sandbox and about as far from the
 * horror premise as the hub gets.
 *
 * Two mods, two completely different shapes, and neither has a dimension option of its own.
 *
 * -------------------------------------------------------------------------------------------
 * HORROR MESSAGES is a MCreator mod, so its logic is a static procedure. Both public entry
 * points - the level tick handler and the /forcehorrormessage command - funnel into one private
 * execute(Event, LevelAccessor), which is therefore the single place worth gating, and
 * HorrorMessagesMixin cancels it there. That method receives the level, so the decision is
 * exact: the message is suppressed in the level it was about to be sent to, not globally.
 *
 * -------------------------------------------------------------------------------------------
 * SERVER-SIDE HORROR has no such funnel. Its effects are inlined into its own mixins on
 * MinecraftServer.tickServer, ServerLevel.tickServer and ServerPlayer.tick, so there is no one
 * method to cancel, and injecting into another mod mixin per effect would be a dozen fragile
 * injections against code that is private even though it is not obfuscated.
 *
 * It does, however, read every effect from a `public static boolean <effect>_enable` field on
 * its config class, fresh on each tick. So instead of gating the effects, this flips the
 * switches: the booleans are restored to their configured values while a player is somewhere
 * horror is wanted, and forced false the rest of the time. Nothing is patched, the mod behaves
 * exactly as its own config says whenever it is live, and - a side benefit no mixin would give -
 * a horror base is no longer quietly burned down or stripped of torches while you are away in
 * another pocket dimension, because the effects are off whenever nobody is there to see them.
 *
 * The configured values are re-read from the live fields on every tick where the switches are
 * currently UP, which is exactly when those fields hold the mod values rather than ours, so a
 * config reload in game is picked up instead of being overwritten from a stale snapshot.
 *
 * Nothing happens until a player is actually online, which keeps the first read clear of mod
 * setup; and an unlisted key is allowed everywhere, so a mod nobody configured is never touched.
 *
 * Config: config/pocketeffects.json
 *
 * <pre>
 * {
 *   "horror_messages":  ["hub:horror", "hub:horror_nether", "hub:horror_end"],
 *   "serversidehorror": ["hub:horror", "hub:horror_nether", "hub:horror_end"]
 * }
 * </pre>
 */
public final class PocketEffects {

    public static final String HORROR_MESSAGES = "horror_messages";
    public static final String SERVERSIDE_HORROR = "serversidehorror";

    private static final String SSH_CONFIG = "com.mars.serversidehorror.ServersideHorrorConfig";
    private static final String ENABLE_SUFFIX = "_enable";

    private static Map<String, Set<String>> rules = null;

    /** Configured value of each effect switch, as the mod itself last had it. */
    private static Map<Field, Boolean> sshConfigured = null;
    private static boolean sshUnavailable = false;
    /** True while WE hold the switches down, i.e. the live fields are ours and not theirs. */
    private static boolean sshSuppressed = false;
    private static int ticks = 0;

    private PocketEffects() {
    }

    // ------------------------------------------------------------------ config
    private static synchronized void loadIfNeeded() {
        if (rules != null) {
            return;
        }
        Map<String, Set<String>> built = new LinkedHashMap<>();
        try {
            Path p = Paths.get("config", "pocketeffects.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                for (Map.Entry<String, JsonElement> e : root.entrySet()) {
                    if (!e.getValue().isJsonArray() || e.getKey().startsWith("_")) {
                        continue;             // "_comment" is an array too, and is not an effect
                    }
                    Set<String> dims = new HashSet<>();
                    JsonArray arr = e.getValue().getAsJsonArray();
                    for (int i = 0; i < arr.size(); i++) {
                        dims.add(arr.get(i).getAsString().trim());
                    }
                    built.put(e.getKey().trim(), dims);
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketeffects.json unreadable, ambience gate off: "
                    + ex);
            built = Collections.emptyMap();
        }
        rules = built;
        System.out.println("[pocketquests] ambience: " + built.size()
                + " effects dimension-gated " + built.keySet());
    }

    /** Is this effect wanted in this dimension? An unlisted effect is wanted everywhere. */
    public static boolean allowed(String key, String dimId) {
        loadIfNeeded();
        Set<String> dims = rules.get(key);
        if (dims == null) {
            return true;                       // not configured -> not our business
        }
        return dimId != null && dims.contains(dimId);
    }

    /** The same question asked with a level rather than a dimension id. Fails OPEN. */
    public static boolean allowedIn(String key, LevelAccessor level) {
        try {
            if (!(level instanceof Level)) {
                return true;
            }
            return allowed(key, ((Level) level).dimension().location().toString());
        } catch (Throwable t) {
            return true;
        }
    }

    // ------------------------------------------- server-side horror switch flipping
    private static boolean findSwitches() {
        if (sshConfigured != null) {
            return true;
        }
        if (sshUnavailable) {
            return false;
        }
        try {
            Class<?> c = Class.forName(SSH_CONFIG);
            Map<Field, Boolean> found = new LinkedHashMap<>();
            for (Field f : c.getDeclaredFields()) {
                if (!f.getName().endsWith(ENABLE_SUFFIX)) {
                    continue;
                }
                if (f.getType() != boolean.class || !Modifier.isStatic(f.getModifiers())) {
                    continue;
                }
                f.setAccessible(true);
                found.put(f, (Boolean) f.get(null));
            }
            if (found.isEmpty()) {
                sshUnavailable = true;         // class shape changed; leave the mod alone
                System.out.println("[pocketquests] serversidehorror config has no "
                        + ENABLE_SUFFIX + " switches; ambience gate skipped");
                return false;
            }
            sshConfigured = found;
            System.out.println("[pocketquests] serversidehorror: " + found.size()
                    + " effect switches under dimension control");
            return true;
        } catch (ClassNotFoundException notInstalled) {
            sshUnavailable = true;
            return false;
        } catch (Throwable t) {
            sshUnavailable = true;
            System.out.println("[pocketquests] serversidehorror switches unreachable: " + t);
            return false;
        }
    }

    /** Only valid while the switches are UP; below that the live fields are all false. */
    private static void refreshConfiguredFromLive() {
        try {
            for (Map.Entry<Field, Boolean> e : sshConfigured.entrySet()) {
                e.setValue((Boolean) e.getKey().get(null));
            }
        } catch (Throwable t) {
            // keep the previous snapshot
        }
    }

    private static void applySwitches(boolean on) {
        try {
            for (Map.Entry<Field, Boolean> e : sshConfigured.entrySet()) {
                e.getKey().setBoolean(null, on && e.getValue());
            }
            sshSuppressed = !on;
            System.out.println("[pocketquests] serversidehorror effects "
                    + (on ? "live (a player is in a horror dimension)" : "suppressed"));
        } catch (Throwable t) {
            System.out.println("[pocketquests] could not flip serversidehorror switches: " + t);
            sshUnavailable = true;
        }
    }

    /**
     * Should the switches be up? True when any player is where the effects are wanted.
     *
     * Split from the player loop so the decision can be tested without a running server:
     * ServerPlayer cannot be constructed outside one, and this is the half worth asserting.
     */
    static boolean wantedIn(Iterable<String> dimIds) {
        loadIfNeeded();
        if (rules.get(SERVERSIDE_HORROR) == null) {
            return true;                       // unconfigured -> never interfere
        }
        for (String dim : dimIds) {
            if (allowed(SERVERSIDE_HORROR, dim)) {
                return true;
            }
        }
        return false;
    }

    private static boolean wanted(Iterable<ServerPlayer> players) {
        List<String> dims = new ArrayList<>();
        for (ServerPlayer p : players) {
            dims.add(p.level().dimension().location().toString());
        }
        return wantedIn(dims);
    }

    /** Called from the server tick. Cheap: one field read per effect, once a second. */
    public static void onServerTick(MinecraftServer server) {
        try {
            if (++ticks % 20 != 0 || server == null) {
                return;
            }
            if (server.getPlayerList().getPlayerCount() == 0) {
                return;                        // also keeps the first read clear of mod setup
            }
            if (!findSwitches()) {
                return;
            }
            boolean want = wanted(server.getPlayerList().getPlayers());
            if (!sshSuppressed) {
                refreshConfiguredFromLive();   // their values, so trust them
            }
            if (want == !sshSuppressed) {
                return;                        // already in the right state
            }
            applySwitches(want);
        } catch (Throwable t) {
            // never break the server tick over ambience
        }
    }

    /** Test seam. */
    static void loadForTest(Map<String, Set<String>> r) {
        rules = r;
        sshConfigured = null;
        sshUnavailable = false;
        sshSuppressed = false;
    }
}
