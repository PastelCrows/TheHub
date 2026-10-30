package pocketquests;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.neoforged.neoforge.event.entity.EntityJoinLevelEvent;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Confines entities to the pocket dimensions they belong to.
 *
 * Mods are global in the hub. That is fine for blocks and items, but it breaks any pocket
 * dimension whose premise IS its mobs: install the stalker mods for a horror pocket dimension and
 * the Cave Dweller hunts you in the skyblock pocket dimension too, which ruins both.
 *
 * Cave Dweller and The Obsessed happen to ship their own `dimensionWhitelist` config. ArPhEx,
 * Midnight Nightmares and Server-Side Horror do not. Rather than configure some mods one way and
 * leave the rest unsolved, this gates all of them uniformly from one list.
 *
 * The hook is EntityJoinLevelEvent, not FinalizeSpawnEvent, and that choice matters: stalker mods
 * do not spawn through the natural-spawn path - they construct the entity and add it to the level
 * directly, which FinalizeSpawnEvent never sees. Cancelling the join catches every route in.
 *
 * Config: config/pocketmobs.json
 *
 * <pre>
 * {
 *   "restrictToDimensions": {
 *     "arphex:*":                   ["hub:horror", "hub:horror_nether", "hub:horror_end"],
 *     "cave_dweller:cave_dweller":  ["hub:horror"]
 *   }
 * }
 * </pre>
 *
 * Semantics are an ALLOW-list per entity pattern: a listed entity may exist only in the listed
 * dimensions and is refused everywhere else. An entity matching no pattern is never touched, so
 * the default behaviour of a pack with no config is completely unchanged. A trailing <code>*</code>
 * wildcards, so <code>arphex:*</code> covers a whole mod's bestiary without naming every mob.
 *
 * Note the real dimensions: a pocket dimension's nether and end are separate ids
 * (`hub:horror_nether`, `hub:horror_end`) and must be listed explicitly if the mobs belong there
 * too. Listing only `hub:horror` confines them to that pocket dimension's overworld.
 *
 * Players are never gated, and everything fails OPEN.
 */
public final class PocketMobs {

    private static Map<String, Set<String>> allowed = null;

    private PocketMobs() {
    }

    private static synchronized void loadIfNeeded() {
        if (allowed != null) {
            return;
        }
        Map<String, Set<String>> built = new LinkedHashMap<>();
        try {
            Path p = Paths.get("config", "pocketmobs.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("restrictToDimensions")) {
                    JsonObject o = root.getAsJsonObject("restrictToDimensions");
                    for (Map.Entry<String, JsonElement> e : o.entrySet()) {
                        Set<String> dims = new HashSet<>();
                        JsonArray arr = e.getValue().getAsJsonArray();
                        for (int i = 0; i < arr.size(); i++) {
                            dims.add(arr.get(i).getAsString().trim());
                        }
                        built.put(e.getKey().trim(), dims);
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketmobs.json unreadable, mob gate off: " + ex);
            built = Collections.emptyMap();
        }
        allowed = built;
        System.out.println("[pocketquests] mob gate: " + built.size() + " entity patterns");
    }

    private static boolean matches(String pattern, String id) {
        if (pattern.equals("*")) {
            return true;
        }
        if (pattern.endsWith("*")) {
            return id.startsWith(pattern.substring(0, pattern.length() - 1));
        }
        return pattern.equals(id);
    }

    /** True when this entity must not exist in this dimension. */
    public static boolean refuse(String entityId, String dimensionId) {
        loadIfNeeded();
        if (allowed.isEmpty() || entityId == null || dimensionId == null) {
            return false;
        }
        for (Map.Entry<String, Set<String>> e : allowed.entrySet()) {
            if (matches(e.getKey(), entityId)) {
                return !e.getValue().contains(dimensionId);
            }
        }
        return false;    // matches no pattern -> not our business
    }

    public static void onEntityJoin(EntityJoinLevelEvent event) {
        try {
            Entity entity = event.getEntity();
            if (entity == null || entity instanceof Player) {
                return;
            }
            Level level = event.getLevel();
            if (level == null || level.isClientSide()) {
                return;
            }
            String id = EntityType.getKey(entity.getType()).toString();
            String dim = level.dimension().location().toString();
            if (refuse(id, dim)) {
                event.setCanceled(true);
            }
        } catch (Throwable t) {
            // fail open - never stop entities loading because the gate misbehaved
        }
    }

    /** Test seam: exercise the matcher without a running game. */
    static void loadForTest(Map<String, Set<String>> rules) {
        allowed = rules;
    }
}
