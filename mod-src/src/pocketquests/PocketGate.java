package pocketquests;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.ftb.mods.ftbquests.quest.Chapter;
import dev.ftb.mods.ftbquests.quest.TeamData;
import dev.ftb.mods.ftbquests.quest.task.Task;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * Decides whether a quest task may make progress right now.
 *
 * A chapter belongs to a pocket when its filename starts with a configured prefix. If it
 * does, progress only counts while someone on the team is standing in one of that pocket's
 * dimensions. A chapter matching no prefix is never blocked, so shared chapters behave
 * normally and a broken or missing config fails OPEN rather than bricking the quest book.
 *
 * Minecraft types are reached by reflection on purpose. The only chain needed is
 * player.level().dimension().location().toString(), and going through reflection means this
 * compiles against FTB Quests and gson alone - no Minecraft or NeoForge jar on the compile
 * classpath, and nothing to break if those are remapped.
 */
public final class PocketGate {

    private static Map<String, Set<String>> prefixToDims = null;
    private static Field filenameField = null;
    private static Method levelM, dimensionM, locationM;
    private static boolean reflectionBroken = false;

    private PocketGate() {
    }

    static synchronized void loadIfNeeded() {
        if (prefixToDims != null) {
            return;
        }
        Map<String, Set<String>> built = new LinkedHashMap<>();
        try {
            Path p = Paths.get("config", "pocketquests.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("chapterPrefixes")) {
                    JsonObject groups = root.getAsJsonObject("chapterPrefixes");
                    for (Map.Entry<String, JsonElement> e : groups.entrySet()) {
                        Set<String> dims = new HashSet<>();
                        JsonArray arr = e.getValue().getAsJsonArray();
                        for (int i = 0; i < arr.size(); i++) {
                            dims.add(arr.get(i).getAsString());
                        }
                        built.put(e.getKey(), dims);
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] config unreadable, gating disabled: " + ex);
        }
        prefixToDims = built;
        System.out.println("[pocketquests] loaded " + built.size() + " chapter prefixes");
    }

    static String filenameOf(Chapter chapter) {
        try {
            if (filenameField == null) {
                Field f = Chapter.class.getDeclaredField("filename");
                f.setAccessible(true);
                filenameField = f;
            }
            Object v = filenameField.get(chapter);
            return v == null ? null : v.toString();
        } catch (Exception ex) {
            return null;
        }
    }

    /** player.level().dimension().location().toString(), without importing Minecraft. */
    static String dimensionOf(Object player) {
        if (reflectionBroken) {
            return null;
        }
        try {
            if (levelM == null) {
                levelM = player.getClass().getMethod("level");
            }
            Object level = levelM.invoke(player);
            if (dimensionM == null) {
                dimensionM = level.getClass().getMethod("dimension");
            }
            Object key = dimensionM.invoke(level);
            if (locationM == null) {
                locationM = key.getClass().getMethod("location");
            }
            return String.valueOf(locationM.invoke(key));
        } catch (Exception ex) {
            reflectionBroken = true;
            System.out.println("[pocketquests] dimension lookup failed, gating disabled: " + ex);
            return null;
        }
    }

    /** The configured prefix -> dimension-id map, loaded on first use. Shared with PocketBook. */
    static Map<String, Set<String>> prefixMap() {
        loadIfNeeded();
        return prefixToDims;
    }

    public static boolean allowed(TeamData data, Task task) {
        loadIfNeeded();
        if (prefixToDims.isEmpty() || task == null || data == null) {
            return true;
        }
        Chapter chapter;
        try {
            chapter = task.getQuestChapter();
        } catch (Throwable t) {
            return true;
        }
        if (chapter == null) {
            return true;
        }
        String filename = filenameOf(chapter);
        if (filename == null) {
            return true;
        }
        Set<String> dims = null;
        for (Map.Entry<String, Set<String>> e : prefixToDims.entrySet()) {
            if (filename.startsWith(e.getKey())) {
                dims = e.getValue();
                break;
            }
        }
        if (dims == null) {
            return true;
        }
        Collection<?> members;
        try {
            members = data.getOnlineMembers();
        } catch (Throwable t) {
            return true;
        }
        if (members == null || members.isEmpty()) {
            return true;
        }
        for (Object player : members) {
            String here = dimensionOf(player);
            if (here == null) {
                return true;   // reflection failed - fail open
            }
            if (dims.contains(here)) {
                return true;
            }
        }
        return false;
    }
}
