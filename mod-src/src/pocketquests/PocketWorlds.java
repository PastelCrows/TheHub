package pocketquests;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.levelgen.Heightmap;
import net.neoforged.neoforge.common.extensions.IEntityExtension;
import net.neoforged.neoforge.event.entity.EntityTravelToDimensionEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Keeps modded dimensions separated between pocket dimensions.
 *
 * Dimension Link separates each pocket dimension's three real dimensions. It does nothing for
 * modded ones: Twilight Forest, the Aether, the Undergarden and Tartarus are each a SINGLE shared
 * instance any pocket dimension can walk into. That breaks the premise twice over, and the two
 * halves need different answers.
 *
 * -------------------------------------------------------------------------------------------
 * HALF ONE - ACCESS. A pocket dimension whose standalone pack never had the mod should not be
 * able to reach it at all. Travel is refused unless the traveller came from a pocket dimension
 * that owns that mod. Ownership was derived by diffing each standalone instance against the hub,
 * not guessed. Config: "restrictToPockets", keyed by POCKET DIMENSION NAME rather than dimension
 * id, because entering the Twilight Forest from the survival nether is still entering it from the
 * survival pocket dimension.
 *
 * -------------------------------------------------------------------------------------------
 * HALF TWO - SEPARATION. Several pocket dimensions legitimately own the same mod: survival,
 * lostcities and gauntlet all have Twilight Forest. Gating access does not separate those.
 *
 * Duplicating the dimension per pocket does not survive contact with the mods - Twilight Forest
 * alone has sixteen classes comparing against TFDimension.DIMENSION_KEY. So each pocket dimension
 * instead gets its own REGION of the real dimension, a million blocks from the next. The
 * dimension stays genuinely twilightforest:twilight_forest, so every internal check still passes,
 * while separate spawn points, separate terrain and mutually invisible builds all fall out of
 * being a million blocks apart.
 *
 * -------------------------------------------------------------------------------------------
 * THE OFFSET MUST BE SCALED ON THE WAY OUT. This was wrong until measured, and it would have
 * stranded people.
 *
 * A dimension has a `coordinate_scale`, and vanilla portal code multiplies position by
 * DimensionType.getTeleportationScale when crossing. Two shared dimensions here are not 1.0:
 * Twilight Forest is 0.125 (so entering multiplies by 8 and leaving divides by 8) and the
 * Undergarden is 4.0 (entering divides by 4, leaving multiplies by 4).
 *
 * Adding a flat offset on entry and subtracting the SAME flat offset on exit is therefore not an
 * inverse. With a million-block offset into Twilight Forest it left the player 875,000 blocks
 * from their base: enter at x, arrive at 8x + C, leave to (8x + C)/8 = x + C/8, subtract C, land
 * at x - 875000.
 *
 * The correct inverse subtracts `offset * scale(shared -> pocket)`, because that is the same
 * factor the portal applied to everything else on the way out. Entering stays unscaled: the mod
 * has already applied its scale by the time this runs, and the offset is defined in the shared
 * dimension's own coordinates. This assumes the mod uses vanilla teleportation scaling, which
 * Twilight Forest demonstrably does.
 *
 * -------------------------------------------------------------------------------------------
 * THE REMEMBERED POCKET IS PERSISTED. It used to live only in a HashMap, which meant logging out
 * inside a shared dimension and restarting lost it - and then leaving applied no offset at all
 * and left the player a million blocks from home. It now also goes in the player's persistent
 * data, so it survives a restart.
 *
 * Every failure path fails OPEN, and a dimension not listed in the config is never touched.
 */
public final class PocketWorlds {

    private static Map<String, Set<String>> allowed = null;
    private static Map<String, int[]> offsets = null;
    private static final Map<UUID, String> lastPocket = new HashMap<>();

    /** Key in the player's NeoForge persistent data, so a restart does not lose the origin. */
    private static final String NBT_KEY = "pocketquests_lastPocket";

    private PocketWorlds() {
    }

    private static synchronized void loadIfNeeded() {
        if (allowed != null) {
            return;
        }
        Map<String, Set<String>> built = new LinkedHashMap<>();
        Map<String, int[]> off = new LinkedHashMap<>();
        try {
            Path p = Paths.get("config", "pocketdims.json");
            if (Files.exists(p)) {
                String raw = new String(Files.readAllBytes(p), StandardCharsets.UTF_8);
                JsonObject root = JsonParser.parseString(raw).getAsJsonObject();
                if (root.has("restrictToPockets")) {
                    JsonObject o = root.getAsJsonObject("restrictToPockets");
                    for (Map.Entry<String, JsonElement> e : o.entrySet()) {
                        Set<String> pockets = new HashSet<>();
                        JsonArray arr = e.getValue().getAsJsonArray();
                        for (int i = 0; i < arr.size(); i++) {
                            pockets.add(arr.get(i).getAsString().trim());
                        }
                        built.put(e.getKey().trim(), pockets);
                    }
                }
                if (root.has("regionOffsets")) {
                    JsonObject o = root.getAsJsonObject("regionOffsets");
                    for (Map.Entry<String, JsonElement> e : o.entrySet()) {
                        JsonArray arr = e.getValue().getAsJsonArray();
                        off.put(e.getKey().trim(),
                                new int[]{arr.get(0).getAsInt(), arr.get(1).getAsInt()});
                    }
                }
            }
        } catch (Exception ex) {
            System.out.println("[pocketquests] pocketdims.json unreadable, gate off: " + ex);
            built = Collections.emptyMap();
            off = Collections.emptyMap();
        }
        allowed = built;
        offsets = off;
        System.out.println("[pocketquests] modded dimensions: " + built.size()
                + " access-gated, " + off.size() + " region offsets");
    }

    /**
     * "hub:survival_nether" -> "survival".
     *
     * Two different negatives, and conflating them left a hole: the hub and redstone land own no
     * modded dimensions and travel from them should be REFUSED, whereas a genuinely unknown
     * origin (standing inside a modded dimension with nothing remembered) must fail OPEN or a
     * player gets stranded. So those return the OWNS_NOTHING sentinel and null respectively.
     */
    static final String OWNS_NOTHING = "__owns_nothing__";

    private static String pocketOf(String dimId) {
        if (dimId == null || !dimId.startsWith("hub:")) {
            return null;
        }
        String name = dimId.substring(4);
        if (name.equals("hub") || name.equals("redstone")) {
            return OWNS_NOTHING;   // the lobby and the creative sandbox own no modded dimensions
        }
        if (name.endsWith("_nether")) {
            name = name.substring(0, name.length() - 7);
        } else if (name.endsWith("_end")) {
            name = name.substring(0, name.length() - 4);
        }
        return name;
    }

    // ------------------------------------------------------------- remembered origin
    /**
     * getPersistentData() is a NeoForge addition on IEntityExtension. NeoForge makes Entity
     * implement it at runtime, but this compiles against the VANILLA srg jar where Entity does
     * not declare it, so the call goes through an explicit interface cast.
     */
    private static void remember(Entity e, String pocket) {
        lastPocket.put(e.getUUID(), pocket);
        try {
            ((IEntityExtension) e).getPersistentData().putString(NBT_KEY, pocket);
        } catch (Throwable t) {
            // in-memory is still better than nothing
        }
    }

    /** Which pocket dimension did this traveller come from? Survives a restart. */
    public static String rememberedPocket(Entity e) {
        if (e == null) {
            return null;
        }
        String p = lastPocket.get(e.getUUID());
        if (p != null) {
            return p;
        }
        try {
            CompoundTag tag = ((IEntityExtension) e).getPersistentData();
            if (tag.contains(NBT_KEY)) {
                p = tag.getString(NBT_KEY);
                if (p != null && !p.isEmpty()) {
                    lastPocket.put(e.getUUID(), p);
                    return p;
                }
            }
        } catch (Throwable t) {
            // fall through
        }
        return null;
    }

    /**
     * The overworld of the traveller's own pocket dimension, or null if unknown.
     *
     * Used by TFPortalMixin: Twilight Forest sends everyone back to ONE configured dimension for
     * the whole server, which in the hub would mean every pocket returning to the same place.
     */
    public static ServerLevel pocketOverworldFor(MinecraftServer server, Entity e) {
        if (server == null) {
            return null;
        }
        String pocket = rememberedPocket(e);
        if (pocket == null || OWNS_NOTHING.equals(pocket)) {
            return null;
        }
        try {
            return server.getLevel(ResourceKey.create(Registries.DIMENSION,
                    ResourceLocation.fromNamespaceAndPath("hub", pocket)));
        } catch (Throwable t) {
            return null;
        }
    }

    // ------------------------------------------------------------- access gate
    /** Decide whether travel into a restricted dimension is permitted. */
    public static boolean permitted(String targetDim, String currentDim, String remembered) {
        loadIfNeeded();
        if (allowed.isEmpty() || targetDim == null) {
            return true;
        }
        Set<String> owners = allowed.get(targetDim);
        if (owners == null) {
            return true;                       // unlisted -> not our business
        }
        String pocket = pocketOf(currentDim);
        if (pocket == null) {
            pocket = remembered;               // already inside a modded dimension
        }
        if (pocket == null) {
            return true;                       // genuinely unknown origin -> fail OPEN
        }
        if (OWNS_NOTHING.equals(pocket)) {
            return false;                      // the lobby / redstone land own no modded worlds
        }
        return owners.contains(pocket);
    }

    /** Is this a modded dimension that pocket dimensions share by region? */
    static boolean isShared(String dimId) {
        loadIfNeeded();
        return allowed.containsKey(dimId);
    }

    /** Public form of {@link #isShared}, for mixins in the other package. */
    public static boolean isSharedLevel(String dimId) {
        return isShared(dimId);
    }

    /** The (x, z) region offset for a pocket dimension, or null for the origin region. */
    static int[] offsetFor(String pocket) {
        loadIfNeeded();
        if (pocket == null) {
            return null;
        }
        int[] o = offsets.get(pocket);
        if (o == null || (o[0] == 0 && o[1] == 0)) {
            return null;
        }
        return o;
    }

    /**
     * The factor the portal applied to position when crossing, which the offset removal must
     * match. 1.0 whenever anything is unknown, which is also the right answer for every shared
     * dimension whose coordinate_scale is 1.0.
     */
    static double teleportScale(MinecraftServer server, ResourceKey<Level> from,
                                ResourceKey<Level> to) {
        try {
            if (server == null) {
                return 1.0;
            }
            ServerLevel a = server.getLevel(from);
            ServerLevel b = server.getLevel(to);
            if (a == null || b == null) {
                return 1.0;
            }
            return DimensionType.getTeleportationScale(a.dimensionType(), b.dimensionType());
        } catch (Throwable t) {
            return 1.0;
        }
    }

    /** Land the player on the surface at (x, z) rather than inside terrain or in the void. */
    private static void placeSafely(ServerPlayer sp, double x, double z) {
        int bx = (int) Math.floor(x);
        int bz = (int) Math.floor(z);
        int y = sp.serverLevel().getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, bx, bz);
        int minY = sp.serverLevel().getMinBuildHeight() + 1;
        int maxY = sp.serverLevel().getMaxBuildHeight() - 2;
        if (y <= minY || y >= maxY) {
            // a closed-roof dimension reports its roof; keep the player inside the world
            y = Math.max(minY, Math.min(maxY, (int) sp.getY()));
        }
        sp.teleportTo(bx + 0.5, y, bz + 0.5);
    }

    /** Remember the pocket dimension, and move the player into or out of its private region. */
    public static void onChangedDimension(PlayerEvent.PlayerChangedDimensionEvent event) {
        try {
            if (!(event.getEntity() instanceof ServerPlayer)) {
                return;
            }
            ServerPlayer sp = (ServerPlayer) event.getEntity();
            String to = event.getTo().location().toString();
            String from = event.getFrom().location().toString();

            String toPocket = pocketOf(to);
            if (toPocket != null && !OWNS_NOTHING.equals(toPocket)) {
                remember(sp, toPocket);
            }

            boolean entering = isShared(to);
            boolean leaving = isShared(from);
            if (entering == leaving) {
                return;                        // not crossing the boundary we care about
            }

            String pocket;
            if (entering) {
                String p = pocketOf(from);
                pocket = (p != null && !OWNS_NOTHING.equals(p)) ? p : rememberedPocket(sp);
            } else {
                pocket = rememberedPocket(sp);
            }
            int[] off = offsetFor(pocket);
            if (off == null) {
                return;                        // this pocket dimension uses the origin region
            }

            if (entering) {
                // the mod has already applied its own scale; the offset is in shared-dim coords
                placeSafely(sp, sp.getX() + off[0], sp.getZ() + off[1]);
                System.out.println("[pocketquests] " + pocket + " entered region "
                        + off[0] + "," + off[1] + " of " + to);
            } else {
                double scale = teleportScale(sp.getServer(), event.getFrom(), event.getTo());
                placeSafely(sp, sp.getX() - off[0] * scale, sp.getZ() - off[1] * scale);
                System.out.println("[pocketquests] " + pocket + " left region "
                        + off[0] + "," + off[1] + " of " + from + " (scale " + scale + ")");
            }
        } catch (Throwable t) {
            // never break a dimension change over bookkeeping
        }
    }

    /** Players currently being redirected, so cancelling and re-teleporting cannot recurse. */
    private static final Set<UUID> redirecting = new HashSet<>();

    /**
     * The escape-hatch net: leaving a shared modded dimension for a VANILLA one.
     *
     * No mod in this pack has a legitimate reason to send a player to minecraft:overworld, since
     * every real destination here is a hub: dimension. When one does, it is because the mod has a
     * single server-wide "return dimension" setting - and landing there is doubly wrong, because
     * DimSwap groups the vanilla three with the LOBBY, so it also crosses an inventory boundary.
     *
     * The portal paths are fixed precisely, by TFPortalMixin and AetherPortalMixin. This catches
     * everything else, including the Aether's fall-off-the-edge path, which runs through the
     * Aether's own merged mixin helper on Entity and is not a sound injection target.
     *
     * CANCEL AND TELEPORT, rather than correct afterwards. Letting the wrong change happen and
     * fixing it on arrival means TWO dimension changes, and therefore two DimSwap inventory
     * swaps around a dimension in the lobby's group - which is how a Twilight Forest haul gets
     * saved into the hub's inventory and lost. Cancelling first means exactly one change.
     */
    private static boolean redirectVanillaEscape(Player p, String current, String target) {
        if (!(p instanceof ServerPlayer)) {
            return false;
        }
        if (!isShared(current) || !target.startsWith("minecraft:")) {
            return false;
        }
        ServerPlayer sp = (ServerPlayer) p;
        if (redirecting.contains(sp.getUUID())) {
            return false;                      // our own teleport re-entering this handler
        }
        String pocket = rememberedPocket(sp);
        if (pocket == null || OWNS_NOTHING.equals(pocket)) {
            return false;                      // unknown origin -> fail OPEN, let it happen
        }
        ServerLevel home = pocketOverworldFor(sp.getServer(), sp);
        if (home == null) {
            return false;
        }
        int[] off = offsetFor(pocket);
        double scale = teleportScale(sp.getServer(), sp.level().dimension(), home.dimension());
        double x = sp.getX() * scale;
        double z = sp.getZ() * scale;
        if (off != null) {
            x -= off[0] * scale;
            z -= off[1] * scale;
        }
        redirecting.add(sp.getUUID());
        try {
            int bx = (int) Math.floor(x);
            int bz = (int) Math.floor(z);
            int y = home.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, bx, bz);
            int minY = home.getMinBuildHeight() + 1;
            int maxY = home.getMaxBuildHeight() - 2;
            if (y <= minY || y >= maxY) {
                y = Math.max(minY, Math.min(maxY, (int) sp.getY()));
            }
            sp.teleportTo(home, bx + 0.5, y, bz + 0.5, sp.getYRot(), sp.getXRot());
            System.out.println("[pocketquests] " + pocket + " redirected out of " + current
                    + " away from " + target + " to " + home.dimension().location());
        } finally {
            redirecting.remove(sp.getUUID());
        }
        return true;
    }

    public static void onTravel(EntityTravelToDimensionEvent event) {
        try {
            Entity e = event.getEntity();
            if (!(e instanceof Player)) {
                return;                        // gate players; let their mobs follow
            }
            if (e.level() == null || e.level().isClientSide()) {
                return;
            }
            String target = event.getDimension().location().toString();
            String current = e.level().dimension().location().toString();
            String remembered = rememberedPocket(e);
            if (!permitted(target, current, remembered)) {
                event.setCanceled(true);
                ((Player) e).displayClientMessage(
                        Component.literal("That place does not exist in this pocket dimension."),
                        true);
                return;
            }
            if (redirectVanillaEscape((Player) e, current, target)) {
                event.setCanceled(true);
            }
        } catch (Throwable t) {
            // fail open - never trap a player because the gate misbehaved
        }
    }

    /** Test seam. */
    static void loadForTest(Map<String, Set<String>> rules, Map<String, int[]> regionOffsets) {
        allowed = rules;
        offsets = regionOffsets == null ? Collections.<String, int[]>emptyMap() : regionOffsets;
    }

    /** Test seam: the round trip that was silently wrong. Returns the landing coordinate. */
    static double roundTripX(double startX, int offsetX, double scaleOut) {
        double intoShared = startX;            // after the mod's own scaling
        double afterOffset = intoShared + offsetX;
        double backOut = afterOffset * scaleOut;
        return backOut - offsetX * scaleOut;
    }
}
