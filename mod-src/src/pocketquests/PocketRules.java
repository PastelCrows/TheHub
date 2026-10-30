package pocketquests;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

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
 * Per-dimension crafting rules.
 *
 * The point of this is that "you cannot use a sieve here" should be enforced at the bench, not
 * discovered after you have spent the materials. Recipes themselves are global - they are loaded
 * once per datapack reload and have no idea which dimension anyone is standing in - so the gate
 * has to sit on the crafting menu instead. See CraftingMenuMixin.
 *
 * Config: config/pocketrules.json
 *
 * <pre>
 * {
 *   "denyByDimension": {
 *     "hub:netherbound": ["exdeorum:*", "minecraft:water_bucket"],
 *     "hub:onechunk":    ["minecraft:ender_chest"]
 *   }
 * }
 * </pre>
 *
 * Entries are matched against the crafting RESULT's item id, because that is how a person thinks
 * about it ("no sieves in here"), not against recipe ids. A trailing <code>*</code> wildcards the
 * rest, so <code>exdeorum:*</code> bans a whole mod and <code>*</code> bans everything.
 *
 * Fails OPEN in every direction: a missing, empty or malformed config denies nothing. A pack
 * where the gate silently stops working is annoying; one that silently blocks all crafting is
 * unplayable.
 */
public final class PocketRules {

    private static Map<String, Set<String>> denyByDim = null;

    private PocketRules() {
    }

    private static synchronized void loadIfNeeded() {
        if (denyByDim != null) {
            return;
        }
        Map<String, Set<String>> built = new LinkedHashMap<>();
        try {
            Path p = Paths.get("config", "pocketrules.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("denyByDimension")) {
                    JsonObject byDim = root.getAsJsonObject("denyByDimension");
                    for (Map.Entry<String, JsonElement> e : byDim.entrySet()) {
                        Set<String> pats = new HashSet<>();
                        JsonArray arr = e.getValue().getAsJsonArray();
                        for (int i = 0; i < arr.size(); i++) {
                            pats.add(arr.get(i).getAsString().trim());
                        }
                        if (!pats.isEmpty()) {
                            built.put(e.getKey(), pats);
                        }
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketrules.json unreadable, crafting gate off: " + ex);
            built = Collections.emptyMap();
        }
        denyByDim = built;
        int total = 0;
        for (Set<String> s : built.values()) {
            total += s.size();
        }
        System.out.println("[pocketquests] crafting rules: " + built.size()
                + " dimensions, " + total + " patterns");
    }

    private static boolean matches(String pattern, String itemId) {
        if (pattern.equals("*")) {
            return true;
        }
        if (pattern.endsWith("*")) {
            return itemId.startsWith(pattern.substring(0, pattern.length() - 1));
        }
        return pattern.equals(itemId);
    }

    /**
     * Has the gate ever actually stopped anything? The boot lines say the CONFIG loaded, which
     * two smoke tests proved is a different question from whether the MIXIN fired. This prints
     * once, the first time a craft is really denied, and is therefore the only line in the log
     * that is evidence of the gate working rather than of it existing.
     */
    private static boolean announced = false;

    /** True when this item must not be craftable in this dimension. */
    public static boolean denied(String dimensionId, String itemId) {
        loadIfNeeded();
        if (denyByDim.isEmpty() || dimensionId == null || itemId == null) {
            return false;
        }
        Set<String> pats = denyByDim.get(dimensionId);
        if (pats == null) {
            return false;
        }
        for (String pattern : pats) {
            if (matches(pattern, itemId)) {
                if (!announced) {
                    announced = true;
                    System.out.println("[pocketquests] crafting gate LIVE: denied " + itemId
                            + " in " + dimensionId + " (pattern " + pattern + ")");
                }
                return true;
            }
        }
        return false;
    }

    /**
     * Says at server start which path is expected to enforce these rules, and loads them.
     *
     * Worth a line in the log because the gate has now failed silently once. CraftingMenuMixin
     * targets vanilla's CraftingMenu.slotChangedCraftingGrid, which FastWorkbench replaces
     * wholesale, so with FastWorkbench installed the vanilla injector is inert and FastBenchMixin
     * is the one doing the work. Both carry require = 0, so neither announces itself.
     *
     * Calling loadIfNeeded() here also means "crafting rules: N dimensions, M patterns" appears
     * at boot rather than on the first craft, which is when it is actually useful.
     */
    public static void logGatePath() {
        loadIfNeeded();
        System.out.println("[pocketquests] crafting gate: RecipeManager.getRecipeFor,"
                + " require=1 (a descriptor mismatch would have crashed startup)");
    }

    /** Test seam: lets the patterns be exercised without a running game. */
    static void loadForTest(Map<String, Set<String>> rules) {
        denyByDim = rules;
    }
}
