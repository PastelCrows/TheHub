package pocketquests;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Difficulty;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Per-pocket-dimension difficulty.
 *
 * Difficulty in Minecraft is a property of the WORLD, not of a dimension - one value in
 * level.dat for everything. So "hard in the Gauntlet, peaceful in the hub" cannot be configured;
 * it has to be applied as you travel, which is what this does.
 *
 * The reason it is worth doing is mechanical, not cosmetic. A villager killed by a zombie
 * converts to a zombie villager 100% of the time on HARD, only sometimes on NORMAL, and never on
 * EASY - and curing a converted villager is what gives the permanent trading discount a trading
 * hall is built around. So every pocket dimension where a villager hall is viable wants HARD;
 * the few whose premise fights one (a void island, a single 16x16 chunk, one regenerating block)
 * gain nothing from it and are left on NORMAL. The hub and redstone land are creative, so they
 * get PEACEFUL and simply have no hostiles.
 *
 * SINGLE PLAYER IS THE DESIGNED CASE, and the limitation is worth stating plainly rather than
 * hiding: because the setting is global, with several players in different pocket dimensions at
 * once there is only one value to give. This follows the player who most recently changed
 * dimension, falling back to the first player in the list. With one player that is exactly
 * right; with several it is a compromise, and no amount of cleverness makes a single global
 * field per-player.
 *
 * Applied on the dimension change AND re-checked once a second, because difficulty is something
 * a command, a mod or the pause menu can change underneath us - the same self-healing approach
 * the starter kits needed.
 *
 * A real dimension with no entry of its own inherits its POCKET DIMENSION's difficulty, so
 * hub:survival_nether follows hub:survival without being listed. Same rule as PocketSkins.
 *
 * If the world has its difficulty LOCKED, this does nothing at all and says so once. That is a
 * deliberate choice by whoever locked it and not ours to override.
 *
 * Config: config/pocketdifficulty.json
 */
public final class PocketDifficulty {

    private static Map<String, Difficulty> byDim = null;
    private static Difficulty fallback = null;
    private static boolean lockedWarned = false;
    private static int ticks = 0;
    private static String lastMovedDim = null;

    private PocketDifficulty() {
    }

    private static Difficulty parse(String s) {
        if (s == null) {
            return null;
        }
        try {
            return Difficulty.valueOf(s.trim().toUpperCase(java.util.Locale.ROOT));
        } catch (Exception ex) {
            System.out.println("[pocketquests] unknown difficulty \"" + s + "\", ignored");
            return null;
        }
    }

    private static synchronized void loadIfNeeded() {
        if (byDim != null) {
            return;
        }
        Map<String, Difficulty> built = new LinkedHashMap<>();
        Difficulty def = null;
        try {
            Path p = Paths.get("config", "pocketdifficulty.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("default")) {
                    def = parse(root.get("default").getAsString());
                }
                if (root.has("byDimension") && root.get("byDimension").isJsonObject()) {
                    for (Map.Entry<String, JsonElement> e
                            : root.getAsJsonObject("byDimension").entrySet()) {
                        Difficulty d = parse(e.getValue().getAsString());
                        if (d != null) {
                            built.put(e.getKey().trim(), d);
                        }
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketdifficulty.json unreadable, off: " + ex);
            built = Collections.emptyMap();
            def = null;
        }
        byDim = built;
        fallback = def;
        System.out.println("[pocketquests] difficulty: " + built.size() + " dimensions"
                + (def != null ? " (+ default " + def.getKey() + ")" : "") + " " + built);
    }

    /** Exact entry, else the entry for the dimension's POCKET DIMENSION, else the default. */
    static Difficulty forDimension(String dimId) {
        loadIfNeeded();
        Difficulty d = byDim.get(dimId);
        if (d != null) {
            return d;
        }
        if (dimId != null && dimId.startsWith("hub:")) {
            String name = dimId.substring(4);
            String parent = null;
            if (name.endsWith("_nether")) {
                parent = name.substring(0, name.length() - 7);
            } else if (name.endsWith("_end")) {
                parent = name.substring(0, name.length() - 4);
            }
            if (parent != null) {
                d = byDim.get("hub:" + parent);
                if (d != null) {
                    return d;
                }
            }
        }
        return fallback;
    }

    private static void apply(MinecraftServer server, String dimId) {
        Difficulty want = forDimension(dimId);
        if (want == null) {
            return;                            // unconfigured -> never interfere
        }
        try {
            if (server.getWorldData().isDifficultyLocked()) {
                if (!lockedWarned) {
                    lockedWarned = true;
                    System.out.println("[pocketquests] world difficulty is LOCKED; "
                            + "per-dimension difficulty disabled");
                }
                return;
            }
            if (server.getWorldData().getDifficulty() == want) {
                return;                        // already right - no packet, no level.dat write
            }
            server.setDifficulty(want, true);
            System.out.println("[pocketquests] difficulty -> " + want.getKey()
                    + " for " + dimId);
        } catch (Throwable t) {
            System.out.println("[pocketquests] could not set difficulty: " + t);
        }
    }

    /** Immediate, so the new dimension's rules are in force before anything ticks in it. */
    public static void onChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event) {
        try {
            if (!(event.getEntity() instanceof ServerPlayer)) {
                return;
            }
            ServerPlayer sp = (ServerPlayer) event.getEntity();
            lastMovedDim = event.getTo().location().toString();
            apply(sp.getServer(), lastMovedDim);
        } catch (Throwable t) {
            // never break a dimension change over difficulty
        }
    }

    /** Self-heal once a second: a command or another mod can change this underneath us. */
    public static void onServerTick(MinecraftServer server) {
        try {
            if (++ticks % 20 != 0 || server == null) {
                return;
            }
            List<ServerPlayer> players = server.getPlayerList().getPlayers();
            if (players.isEmpty()) {
                return;
            }
            String dim = null;
            if (lastMovedDim != null) {
                for (ServerPlayer p : players) {
                    if (p.level().dimension().location().toString().equals(lastMovedDim)) {
                        dim = lastMovedDim;    // the traveller is still there
                        break;
                    }
                }
            }
            if (dim == null) {
                dim = players.get(0).level().dimension().location().toString();
            }
            apply(server, dim);
        } catch (Throwable t) {
            // never break the server tick over difficulty
        }
    }

    /** Test seam. */
    static void loadForTest(Map<String, Difficulty> rules, Difficulty def) {
        byDim = rules;
        fallback = def;
    }
}
