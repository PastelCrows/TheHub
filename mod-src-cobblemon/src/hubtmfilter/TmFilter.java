package hubtmfilter;

import com.cobblemon.mod.common.api.moves.Moves;
import com.cobblemon.mod.common.api.tms.TechnicalMachine;
import com.cobblemon.mod.common.api.tms.TechnicalMachines;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Drops Cobblemon TM entries whose JSON names a move the game does not know.
 *
 * <p>WHY THIS IS NEEDED, MEASURED RATHER THAN ASSUMED. Cobblemon resolves a TM's move by name and
 * falls back rather than failing, so a TM file naming a move nothing defines silently becomes a
 * TM that teaches Tackle. Across this pack that is <b>17 of 781 TM files</b>, every one of them
 * from Gravels Extended Battles - TMs whose move definitions GEB does not ship. Checked against
 * the real move registry, which is the union of Cobblemon's bundled
 * {@code data/cobblemon/showdown.zip} (1,113 ids) and the one-file-per-move layout
 * {@code data/<ns>/moves/<id>.js} that GEB and the fakemon packs use (another 1,224) - 2,337 ids
 * in total. GEB's {@code move_substitutions} were checked too; none of the 17 is covered there.
 *
 * <p>This is a port of Kewz's {@code kewz-tm-filter}, whose injection points and logic were read
 * out of his jar's bytecode. Credit to him for finding the problem and the fix.
 *
 * <p>WHY IT RE-READS THE JSON INSTEAD OF USING THE FILE NAME. Every TM file but one is named after
 * the move it grants, which makes {@code Moves.getByName(key.getPath())} look like a tidy
 * shortcut. It is wrong: {@code tms/dustdevil.json} names the move {@code dustdevillc}. One
 * exception in 781 is exactly the sort of thing a shortcut gets silently wrong forever, so the
 * written name is read from the file, as his implementation does.
 *
 * <p>WHY IT CANNOT READ {@code getMoveName()} INSTEAD. By the time the TM map exists the fallback
 * has already happened, so the entry reports Tackle and the original name is gone. The only place
 * the intended move survives is the JSON, which is why this runs while the ResourceManager from
 * the enclosing reload is still reachable.
 */
public final class TmFilter {

    private static final Logger LOG = LoggerFactory.getLogger("hubtmfilter");

    /**
     * The ResourceManager of the reload in progress.
     *
     * <p>ThreadLocal, and not a static field, because a data reload is not guaranteed to be the
     * only one in flight - integrated server plus client reload can overlap - and a shared field
     * would let one reload filter against the other's resources. Cleared on the way out even
     * when filtering throws.
     */
    private static final ThreadLocal<ResourceManager> MANAGER = new ThreadLocal<>();

    private TmFilter() {
    }

    public static void begin(ResourceManager manager) {
        MANAGER.set(manager);
    }

    public static void end() {
        MANAGER.remove();
    }

    /** Called when Cobblemon has finished filling the TM map. */
    public static void filter() {
        ResourceManager manager = MANAGER.get();
        if (manager == null) {
            // reload(Map) can be called directly, e.g. by a sync from a server, with no
            // enclosing resource reload. There is nothing to read the written names from, so
            // leave the map exactly as Cobblemon built it rather than guess.
            return;
        }
        try {
            run(manager);
        } catch (RuntimeException | LinkageError e) {
            // Never let this break a data load. A pack that boots with 17 bad TMs is strictly
            // better than a pack that does not boot.
            LOG.error("hubtmfilter refused; the TM map is left as Cobblemon loaded it", e);
        }
    }

    private static void run(ResourceManager manager) {
        Map<ResourceLocation, String> written = writtenMoveNames(manager);
        Map<ResourceLocation, TechnicalMachine> tms = TechnicalMachines.INSTANCE.getTmMap();

        int before = tms.size();
        List<ResourceLocation> drop = new ArrayList<>();
        List<String> unreadable = new ArrayList<>();

        for (Map.Entry<ResourceLocation, TechnicalMachine> entry : tms.entrySet()) {
            String name = written.get(entry.getKey());
            if (name == null) {
                // The TM exists in the map but its source file was not found. Not a reason to
                // delete someone's content - report it and move on.
                unreadable.add(entry.getKey().toString());
                continue;
            }
            if (Moves.getByName(name) == null) {
                drop.add(entry.getKey());
            }
        }

        for (ResourceLocation key : drop) {
            tms.remove(key);
        }

        if (!drop.isEmpty()) {
            LOG.info("hubtmfilter removed {} of {} TMs naming an unknown move", drop.size(), before);
            for (ResourceLocation key : drop) {
                LOG.info("   dropped {} (named move '{}')", key, written.get(key));
            }
        }
        if (!unreadable.isEmpty()) {
            LOG.info("hubtmfilter could not read the source of {} TMs; left alone", unreadable.size());
        }
    }

    /**
     * TM id -> the move name written in its JSON.
     *
     * <p>Keyed by the same ResourceLocation Cobblemon uses for the map: namespace of the file,
     * path with the {@code tms/} prefix and {@code .json} suffix removed. That is read off
     * {@link TechnicalMachines#getResourcePath()} rather than hardcoded as "tms", so a Cobblemon
     * update that moves the folder does not quietly turn this into a no-op.
     */
    private static Map<ResourceLocation, String> writtenMoveNames(ResourceManager manager) {
        String folder = TechnicalMachines.INSTANCE.getResourcePath();
        Map<ResourceLocation, String> out = new HashMap<>();

        for (Map.Entry<ResourceLocation, Resource> e
                : manager.listResources(folder, p -> p.getPath().endsWith(".json")).entrySet()) {
            ResourceLocation file = e.getKey();
            String path = file.getPath();
            String trimmed = path.substring(folder.length() + 1, path.length() - ".json".length());
            ResourceLocation id = ResourceLocation.fromNamespaceAndPath(file.getNamespace(), trimmed);

            try (BufferedReader reader = e.getValue().openAsReader()) {
                JsonObject json = JsonParser.parseReader(reader).getAsJsonObject();
                String name = readMoveName(json);
                if (name != null) {
                    out.put(id, name);
                }
            } catch (Exception ex) {
                // A single unparseable TM file must not take the whole filter down with it;
                // without an entry here it simply gets left alone below.
                LOG.warn("hubtmfilter could not read {}", file, ex);
            }
        }
        return out;
    }

    /** Cobblemon's own DTO field is moveName; the others are what third-party packs use. */
    private static String readMoveName(JsonObject json) {
        for (String key : new String[]{"moveName", "move", "move_name"}) {
            if (json.has(key) && json.get(key).isJsonPrimitive()) {
                return json.get(key).getAsString();
            }
        }
        return null;
    }
}
