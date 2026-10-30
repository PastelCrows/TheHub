package pocketquests.client;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.ReceivingLevelScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.server.packs.repository.PackRepository;

import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Swaps the shaderpack and the resource pack when you change pocket dimension.
 *
 * Both are global client state in vanilla - there is no per-dimension texture or shader setting
 * to configure - so the only way to get one is to change the global state and reload.
 *
 * THE TWO HALVES HAVE VERY DIFFERENT COSTS, and they are now scheduled differently.
 *
 * Shaders are cheap: `Iris.reload()` recompiles the shaderpack and never touches the resource
 * manager, so it is applied IMMEDIATELY on the dimension change. That is the instant visual
 * feedback when you step through an arch.
 *
 * Resource packs are not cheap. `reloadResourcePacks()` re-stitches every texture atlas,
 * re-parses every GeckoLib animation, regenerates Every Compat's textures and rebuilds the whole
 * JEI index - all on the render thread. Running that DURING a dimension change, while the server
 * is still generating chunks for a dimension nobody has visited, is what produced the
 * thirty-minute hang that made the pocket dimension unreachable. The cost was never the problem
 * on its own; stacking it on top of terrain loading was.
 *
 * So the resource pack half is DEFERRED. On a dimension change it is only queued; it fires once
 * the client is actually in the world and quiet:
 *
 *   - the "Downloading terrain" screen (ReceivingLevelScreen) is gone,
 *   - no loading overlay is up - in particular not one from a reload already running,
 *   - the player exists, is alive, and the chunk they are standing in is loaded,
 *   - and all of that has held steady for `switchDelayTicks` consecutive ticks.
 *
 * Any of those going false resets the counter, so the reload cannot start while the game is
 * still busy. To be clear about what this does and does not buy: deferring does not make the
 * reload FASTER, it makes it happen once, in a predictable place, with the rest of the game
 * already settled - a defined pause after you land instead of an open-ended hang mid-teleport.
 *
 * Because the previous estimate in this file was wrong by orders of magnitude (it claimed "2-5
 * seconds"), the reload is now TIMED and the real figure is logged and shown in chat. Measure,
 * do not guess. A chat line also goes out before the pause so it does not read as a crash.
 *
 * Nothing is reloaded unless the dimension changed AND the desired pack set differs from what is
 * already selected, so walking back into a pocket dimension that uses the same textures is free.
 *
 * Config: config/pocketskins.json
 *
 * <pre>
 * {
 *   "allowResourcePackSwitching": true,
 *   "switchDelayTicks": 60,
 *   "default": { "shadersEnabled": false, "resourcePacks": [] },
 *   "byDimension": {
 *     "hub:horror": { "shader": "ComplementaryReimagined_r5.9.3.zip",
 *                     "shadersEnabled": true,
 *                     "resourcePacks": ["file/horror-desaturated"] }
 *   }
 * }
 * </pre>
 *
 * "vanilla" is always selected first whether listed or not, and any pack id that is not actually
 * installed is skipped with a log line rather than wiping the selection - a typo should not leave
 * you staring at a half-loaded game.
 *
 * Iris is reached by reflection on purpose. Its public API (IrisApi v0) can only toggle shaders
 * on and off - it cannot select a pack - so this has to use Iris.getIrisConfig() and
 * Iris.reload(), which are public but internal. Reflection means a pack without Iris installed
 * still loads this class fine and simply skips the shader half.
 */
public final class PocketSkins {

    private static final class Skin {
        String shader;                 // null = leave the selected pack alone
        Boolean shadersEnabled;        // null = leave enabled/disabled alone
        List<String> packs;            // null = leave resource packs alone
    }

    private static Map<String, Skin> byDim = null;
    private static Skin fallback = null;

    /**
     * Every pack id this file is allowed to switch between, plus vanilla.
     *
     * The selection in the repository is NOT just these: it also holds every mod's own resource
     * pack and KubeJS's virtual packs, 250-odd required entries that are always on. Those have to
     * be filtered out before the current selection can be compared with the desired one.
     */
    private static Set<String> managed = null;
    private static boolean allowPackSwitch = false;
    private static int switchDelayTicks = 60;      // 3 seconds of calm after landing

    private static String lastDim = null;
    private static int ticks = 0;
    private static boolean irisWarned = false;

    /** The queued resource pack swap, waiting for the client to settle. */
    private static Skin pending = null;
    private static int settled = 0;
    private static boolean reloading = false;

    private PocketSkins() {
    }

    // ------------------------------------------------------------------ config
    private static Skin readSkin(JsonObject o) {
        Skin s = new Skin();
        if (o.has("shader") && !o.get("shader").isJsonNull()) {
            s.shader = o.get("shader").getAsString();
        }
        if (o.has("shadersEnabled") && !o.get("shadersEnabled").isJsonNull()) {
            s.shadersEnabled = o.get("shadersEnabled").getAsBoolean();
        }
        if (o.has("resourcePacks") && o.get("resourcePacks").isJsonArray()) {
            List<String> l = new ArrayList<>();
            JsonArray arr = o.getAsJsonArray("resourcePacks");
            for (int i = 0; i < arr.size(); i++) {
                l.add(arr.get(i).getAsString());
            }
            s.packs = l;
        }
        return s;
    }

    private static synchronized void loadIfNeeded() {
        if (byDim != null) {
            return;
        }
        Map<String, Skin> built = new LinkedHashMap<>();
        Skin def = null;
        try {
            Path p = Paths.get("config", "pocketskins.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("allowResourcePackSwitching")) {
                    allowPackSwitch = root.get("allowResourcePackSwitching").getAsBoolean();
                }
                if (root.has("switchDelayTicks")) {
                    switchDelayTicks = Math.max(0, root.get("switchDelayTicks").getAsInt());
                }
                if (root.has("default") && root.get("default").isJsonObject()) {
                    def = readSkin(root.getAsJsonObject("default"));
                }
                if (root.has("byDimension") && root.get("byDimension").isJsonObject()) {
                    for (Map.Entry<String, JsonElement> e
                            : root.getAsJsonObject("byDimension").entrySet()) {
                        if (e.getValue().isJsonObject()) {
                            built.put(e.getKey(), readSkin(e.getValue().getAsJsonObject()));
                        }
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketskins.json unreadable, skins off: " + ex);
        }
        Set<String> owned = new LinkedHashSet<>();
        owned.add("vanilla");
        for (Skin s : built.values()) {
            if (s.packs != null) {
                owned.addAll(s.packs);
            }
        }
        if (def != null && def.packs != null) {
            owned.addAll(def.packs);
        }
        managed = owned;

        byDim = built;
        fallback = def;
        System.out.println("[pocketquests] skins: " + built.size() + " dimensions configured"
                + (def != null ? " (+ default)" : "")
                + "; resource pack switching "
                + (allowPackSwitch
                   ? "on, deferred " + switchDelayTicks + " ticks after landing"
                   : "off"));
    }

    // ------------------------------------------------------------------ apply
    private static void notice(Minecraft mc, String msg) {
        try {
            if (mc.gui != null) {
                mc.gui.getChat().addMessage(Component.literal("[pockets] " + msg));
            }
        } catch (Throwable t) {
            // a missing chat line is not worth an exception
        }
    }

    private static boolean applyResourcePacks(Minecraft mc, Skin skin) {
        if (skin.packs == null || !allowPackSwitch) {
            return false;
        }
        PackRepository repo = mc.getResourcePackRepository();
        Collection<String> available = repo.getAvailableIds();

        Set<String> desired = new LinkedHashSet<>();
        desired.add("vanilla");                       // always first, always present
        for (String id : skin.packs) {
            if (available.contains(id)) {
                desired.add(id);
            } else {
                System.out.println("[pocketquests] resource pack not installed, skipped: " + id);
            }
        }
        // Compare only the packs this file controls. getSelectedIds() returns the REQUIRED packs
        // too - every mod's own assets, KubeJS's virtual packs - which setSelected() re-adds by
        // itself and which no config here ever names. Comparing the raw selection meant the sets
        // could never be equal, so the early return never fired and EVERY transit paid a full
        // reload, including the ones between two pocket dimensions sharing a pack that this file
        // promises are free. The 2026-10-29 log shows it plainly: [vanilla, Faithful 64x] loaded
        // at 20:32:55 in 92850 ms, then loaded AGAIN at 20:34:34 in 80448 ms, to arrive at
        // exactly what was already on screen.
        Set<String> currentManaged = new LinkedHashSet<>();
        for (String id : repo.getSelectedIds()) {
            if (managed.contains(id)) {
                currentManaged.add(id);
            }
        }
        if (currentManaged.equals(desired)) {
            return false;                             // already correct - no reload, no pause
        }

        repo.setSelected(desired);
        // NOT "brief". It was measured at 80-98 seconds on this pack (92850, 80448, 97930 ms),
        // and a message promising a brief pause before a minute and a half of frozen client is
        // worse than no message: it reads as a hang. Say the real number.
        notice(mc, "swapping textures for this pocket dimension - about a minute and a half,"
                + " the client will not respond until it finishes");
        System.out.println("[pocketquests] resource packs -> " + desired);

        final long t0 = System.nanoTime();
        reloading = true;
        mc.reloadResourcePacks().thenRun(() -> {
            final long ms = (System.nanoTime() - t0) / 1000000L;
            reloading = false;
            System.out.println("[pocketquests] resource reload completed in " + ms + " ms");
            // chat must be touched on the client thread
            mc.execute(() -> notice(mc, "textures applied in " + (ms / 1000L) + "s"));
        });
        return true;
    }

    /** Iris by reflection: its public API cannot select a pack, only toggle shaders. */
    private static void applyShader(Minecraft mc, Skin skin) {
        if (skin.shader == null && skin.shadersEnabled == null) {
            return;
        }
        try {
            Class<?> iris = Class.forName("net.irisshaders.iris.Iris");

            if (skin.shader != null) {
                String currentName = String.valueOf(
                        iris.getMethod("getCurrentPackName").invoke(null));
                if (!skin.shader.equals(currentName)) {
                    Object cfg = iris.getMethod("getIrisConfig").invoke(null);
                    cfg.getClass().getMethod("setShaderPackName", String.class)
                            .invoke(cfg, skin.shader);
                    cfg.getClass().getMethod("save").invoke(cfg);
                    iris.getMethod("reload").invoke(null);
                    System.out.println("[pocketquests] shaderpack -> " + skin.shader);
                }
            }
            if (skin.shadersEnabled != null) {
                Object cfg = iris.getMethod("getIrisConfig").invoke(null);
                boolean on = (Boolean) cfg.getClass().getMethod("areShadersEnabled").invoke(cfg);
                if (on != skin.shadersEnabled) {
                    Method toggle = iris.getMethod("toggleShaders", Minecraft.class, boolean.class);
                    toggle.invoke(null, mc, skin.shadersEnabled);
                    System.out.println("[pocketquests] shaders -> " + skin.shadersEnabled);
                }
            }
        } catch (ClassNotFoundException notInstalled) {
            if (!irisWarned) {
                irisWarned = true;
                System.out.println("[pocketquests] Iris not installed; shader switching skipped");
            }
        } catch (Throwable t) {
            System.out.println("[pocketquests] shader switch failed: " + t);
        }
    }

    /**
     * The skin for a dimension: exact entry, else the one for its POCKET DIMENSION, else default.
     *
     * Inheritance rather than 32 hand-written entries, because the hand-written version was
     * already wrong the first time. hub:horror had the desaturated pack and hub:horror_nether had
     * nothing, so walking down into the horror nether fell through to the default and reloaded
     * into vanilla - losing the look AND paying a full reload to lose it, then another on the way
     * back. The same trap was sitting under skyblock, onechunk, caveblock, gauntlet and oceanblock.
     *
     * A pack is a property of the pocket dimension, which is how it is thought about, so a real
     * dimension takes its pocket's skin unless it says otherwise. Setting an explicit entry for
     * hub:survival_nether still overrides, which is what you would want for a nether that should
     * look different from its own overworld.
     */
    private static Skin skinFor(String dim) {
        Skin s = byDim.get(dim);
        if (s != null) {
            return s;
        }
        if (dim.startsWith("hub:")) {
            String name = dim.substring(4);
            String parent = null;
            if (name.endsWith("_nether")) {
                parent = name.substring(0, name.length() - 7);
            } else if (name.endsWith("_end")) {
                parent = name.substring(0, name.length() - 4);
            }
            if (parent != null) {
                s = byDim.get("hub:" + parent);
                if (s != null) {
                    return s;
                }
            }
        }
        return fallback;
    }

    /**
     * Is the client actually in the world and quiet enough to take a resource reload?
     *
     * Deliberately NOT just "mc.screen == null": the inventory or pause menu being open is no
     * reason to wait, whereas the terrain screen and a loading overlay very much are.
     */
    private static boolean readyForReload(Minecraft mc) {
        if (reloading) {
            return false;                             // one already running
        }
        if (mc.screen instanceof ReceivingLevelScreen) {
            return false;                             // still "Downloading terrain"
        }
        if (mc.getOverlay() != null) {
            return false;                             // a loading overlay is up
        }
        if (mc.player == null || !mc.player.isAlive() || mc.level == null) {
            return false;
        }
        // hasChunk(chunkX, chunkZ), not the deprecated hasChunkAt(BlockPos)
        return mc.level.hasChunk(mc.player.getBlockX() >> 4, mc.player.getBlockZ() >> 4);
    }

    /** Called from a client tick. Cheap unless the dimension actually changed. */
    public static void tick() {
        ticks++;
        try {
            Minecraft mc = Minecraft.getInstance();
            if (mc == null || mc.level == null || mc.player == null) {
                lastDim = null;
                pending = null;
                settled = 0;
                return;
            }
            String dim = mc.level.dimension().location().toString();

            if (!dim.equals(lastDim)) {
                lastDim = dim;
                loadIfNeeded();
                Skin skin = skinFor(dim);
                if (skin == null) {
                    pending = null;
                    settled = 0;
                    return;
                }
                applyShader(mc, skin);                // cheap - do it now
                pending = skin;                       // expensive - wait until we have landed
                settled = 0;
            }

            if (pending == null) {
                return;
            }
            if (!readyForReload(mc)) {
                settled = 0;                          // still busy; start the count again
                return;
            }
            if (++settled < switchDelayTicks) {
                return;
            }
            Skin go = pending;
            pending = null;
            settled = 0;
            applyResourcePacks(mc, go);
        } catch (Throwable t) {
            // never break the client tick over cosmetics
        }
    }
}
