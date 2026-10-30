package pocketquests;

import dev.ftb.mods.ftbquests.client.ClientQuestFile;
import dev.ftb.mods.ftbquests.client.gui.quests.QuestScreen;
import dev.ftb.mods.ftbquests.quest.Chapter;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Opens the quest book on the pocket you are actually standing in.
 *
 * Without this the book restores whatever chapter was last viewed, which in a merged
 * eight-pocket book is almost never the one you want: walking into the Gauntlet and being shown
 * Skyblock's chapters reads as a broken book, especially since PocketQuests correctly refuses to
 * let Skyblock quests progress while you are somewhere else.
 *
 * The pocket is matched with the same `chapterPrefixes` config the progress gate uses, so the
 * two can never disagree about which chapters belong where.
 *
 * Everything here is best-effort and fails silently: a book that opens on the wrong chapter is a
 * small annoyance, and crashing a client over it would be far worse. That is the opposite of the
 * progress gate, which is `required` precisely because silently not gating would be invisible.
 */
public final class PocketBook {

    private PocketBook() {
    }

    /** Minecraft.getInstance().player, via reflection - keeps Minecraft off the compile path. */
    private static Object clientPlayer() {
        try {
            Class<?> mcClass = Class.forName("net.minecraft.client.Minecraft");
            Object mc = mcClass.getMethod("getInstance").invoke(null);
            if (mc == null) {
                return null;
            }
            return mcClass.getField("player").get(mc);
        } catch (Throwable t) {
            return null;
        }
    }

    public static void selectForCurrentDimension(QuestScreen screen) {
        try {
            if (screen == null || !ClientQuestFile.exists()) {
                return;
            }
            Object player = clientPlayer();
            if (player == null) {
                return;
            }
            String here = PocketGate.dimensionOf(player);
            if (here == null) {
                return;
            }

            // which pocket owns this dimension?
            String prefix = null;
            for (Map.Entry<String, Set<String>> e : PocketGate.prefixMap().entrySet()) {
                if (e.getValue().contains(here)) {
                    prefix = e.getKey();
                    break;
                }
            }
            if (prefix == null) {
                return;   // the hub, or anywhere unmapped: leave the book where it was
            }

            // already showing the right pocket? then do not fight the player's own navigation
            Chapter current = screen.getSelectedChapter().orElse(null);
            if (current != null) {
                String f = PocketGate.filenameOf(current);
                if (f != null && f.startsWith(prefix)) {
                    return;
                }
            }

            List<Chapter> chapters = ClientQuestFile.INSTANCE.getAllChapters();
            if (chapters == null) {
                return;
            }
            for (Chapter c : chapters) {
                String f = PocketGate.filenameOf(c);
                if (f != null && f.startsWith(prefix)) {
                    screen.selectChapter(c);
                    return;
                }
            }
        } catch (Throwable t) {
            // deliberately swallowed - see the class comment
        }
    }
}
