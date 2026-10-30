package pocketquests;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

/**
 * Entrypoint. The quest gate and the crafting gate live entirely in mixins; the only thing that
 * needs wiring here is the client-side skin switcher, which polls for dimension changes.
 *
 * The listener is registered behind a Dist check, and the client class is named only from inside
 * a lambda, so a dedicated server never loads a class that touches Minecraft client types.
 */
@Mod("pocketquests")
public class PocketQuests {

    public PocketQuests() {
        // Entity gating is common: mods are global in the hub, so a pocket dimension whose
        // premise is its mobs needs them confined. EntityJoinLevelEvent catches programmatic
        // spawns, which is how stalker mods actually work.
        NeoForge.EVENT_BUS.addListener(PocketMobs::onEntityJoin);

        // Modded dimensions are a single shared instance across every pocket dimension unless
        // something stops them. These two keep Twilight Forest, the Aether, the Undergarden and
        // the rest out of pocket dimensions whose standalone pack never had the mod.
        NeoForge.EVENT_BUS.addListener(PocketWorlds::onTravel);
        NeoForge.EVENT_BUS.addListener(PocketWorlds::onChangedDimension);

        // Ambience mods act on the world and the chat rather than through an entity, so
        // PocketMobs cannot reach them. This flips Server-Side Horror effect switches
        // according to where the players actually are; the Horror Messages half is a
        // mixin and needs no wiring. See PocketEffects for why each takes its own route.
        NeoForge.EVENT_BUS.addListener(
                (ServerTickEvent.Post event) -> PocketEffects.onServerTick(event.getServer()));

        // Difficulty is a property of the WORLD, one value in level.dat, so a per-pocket
        // difficulty has to be applied as you travel. Villager halls need HARD to get
        // reliable zombification; the hub and redstone land want PEACEFUL. Applied on the
        // change and re-checked each second, because a command can move it underneath us.
        NeoForge.EVENT_BUS.addListener(PocketDifficulty::onChangedDimension);
        NeoForge.EVENT_BUS.addListener(
                (ServerTickEvent.Post e2) -> PocketDifficulty.onServerTick(e2.getServer()));

        if (FMLEnvironment.dist == Dist.CLIENT) {
            NeoForge.EVENT_BUS.addListener(
                    (ClientTickEvent.Post event) -> pocketquests.client.PocketSkins.tick());
            System.out.println("[pocketquests] client skin switcher registered");
        }
    }
}
