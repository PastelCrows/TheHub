package pocketquests;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.MapColor;
import net.minecraft.world.level.material.PushReaction;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;
import net.minecraft.world.phys.shapes.Shapes;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;

/**
 * Portal blocks you walk into, one per destination.
 *
 * WHY THIS EXISTS. Travel used to be POSITIONAL: hub_portals.js scanned every player's
 * coordinates once a tick against a table of arch positions that build_hub_room_v6.py wrote into
 * it. That had three costs, and this block removes all three at once.
 *
 *   1. It was slow to fire. A tick scan plus the scheduling around it is why portals
 *      "occasionally take a long time to go off". A block that reacts in entityInside fires on
 *      the tick you touch it.
 *   2. The hall could not be redesigned. Arch coordinates were compiled into a script, so moving
 *      an arch meant regenerating the room AND the script. Now the block IS the portal: pick it
 *      up in creative, put it somewhere else, and that is the whole operation.
 *   3. Return portals were impossible without yet another coordinate table. Now a pocket
 *      dimension gets a way home by having one of these placed in it.
 *
 * NOT OBTAINABLE IN SURVIVAL, deliberately. No loot table, so breaking one drops nothing;
 * unbreakable by hand (-1 hardness, blast resistance of bedrock); no recipe anywhere. They exist
 * in the creative menu under their own tab, which is the only place they come from - the same
 * deal vanilla gives nether portal blocks.
 *
 * WHAT IT DOES NOT DO. It does not teleport by itself. Arrival in a pocket dimension is a whole
 * procedure - gamemode, DimSwap inventory group, starter kit, briefing, difficulty - and all of
 * that already lives in hub_portals.js. Reimplementing it here would be two sources of truth for
 * the same rules, which is how the crafting gate went wrong twice. So the block TRIGGERS: it
 * runs `hubgo <destination>` as the server, and the existing script does what it already does.
 *
 * The cooldown is per entity and deliberately generous. Standing in a portal must not re-fire it
 * every tick, and a player who arrives inside a return portal must be able to step out rather
 * than be bounced home again.
 */
public final class PocketPortal {

    public static final String MODID = "pocketquests";

    /** destination id -> display name. The id is what gets passed to `hubgo`. */
    public static final Map<String, String> DESTINATIONS = new LinkedHashMap<>();

    static {
        DESTINATIONS.put("hub", "Hub Portal");
        DESTINATIONS.put("skyblock", "Skyblock Portal");
        DESTINATIONS.put("survival", "Survival Portal");
        DESTINATIONS.put("caveblock", "Caveblock Portal");
        DESTINATIONS.put("netherbound", "Netherbound Portal");
        DESTINATIONS.put("oceanblock", "Oceanblock Portal");
        DESTINATIONS.put("lostcities", "Lost Cities Portal");
        DESTINATIONS.put("onechunk", "One Chunk Portal");
        DESTINATIONS.put("gauntlet", "Gauntlet Portal");
        DESTINATIONS.put("redstone", "Redstone Land Portal");
        DESTINATIONS.put("oneblock", "One Block Portal");
        DESTINATIONS.put("horror", "Horror Portal");
    }

    private static final DeferredRegister.Blocks BLOCKS =
            DeferredRegister.createBlocks(MODID);
    private static final DeferredRegister.Items ITEMS =
            DeferredRegister.createItems(MODID);
    private static final DeferredRegister<CreativeModeTab> TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MODID);

    private static final List<Block> REGISTERED = new ArrayList<>();

    private PocketPortal() {
    }

    /** Called from the mod constructor, before registries freeze. */
    public static void register(IEventBus modBus) {
        for (Map.Entry<String, String> e : DESTINATIONS.entrySet()) {
            final String dest = e.getKey();
            String name = "portal_" + dest;

            var block = BLOCKS.register(name, () -> new PortalBlock(dest,
                    BlockBehaviour.Properties.of()
                            .mapColor(MapColor.COLOR_PURPLE)
                            .noCollission()
                            .noLootTable()
                            .strength(-1.0F, 3600000.0F)
                            .lightLevel(s -> 11)
                            .pushReaction(PushReaction.BLOCK)));

            ITEMS.register(name, () -> new BlockItem(block.get(), new Item.Properties()));
        }

        TABS.register("portals", () -> CreativeModeTab.builder(CreativeModeTab.Row.TOP, 0)
                .title(Component.literal("The Hub"))
                .icon(() -> new ItemStack(
                        net.minecraft.core.registries.BuiltInRegistries.ITEM.get(
                                ResourceLocation.fromNamespaceAndPath(MODID, "portal_hub"))))
                .displayItems((params, out) -> {
                    for (String dest : DESTINATIONS.keySet()) {
                        out.accept(net.minecraft.core.registries.BuiltInRegistries.ITEM.get(
                                ResourceLocation.fromNamespaceAndPath(MODID, "portal_" + dest)));
                    }
                })
                .build());

        BLOCKS.register(modBus);
        ITEMS.register(modBus);
        TABS.register(modBus);
        System.out.println("[pocketquests] portals: " + DESTINATIONS.size()
                + " destination blocks registered");
    }

    /** The block itself. One class, one destination string per instance. */
    public static class PortalBlock extends Block {

        private static final VoxelShape NOTHING = Shapes.empty();

        /** entity id -> game time at which it may travel again. */
        private static final Map<Integer, Long> COOLDOWN = new LinkedHashMap<>();
        private static final long COOLDOWN_TICKS = 60L;

        private final String destination;

        public PortalBlock(String destination, BlockBehaviour.Properties props) {
            super(props);
            this.destination = destination;
        }

        public String destination() {
            return this.destination;
        }

        @Override
        public VoxelShape getCollisionShape(BlockState state, net.minecraft.world.level.BlockGetter level,
                                            BlockPos pos, CollisionContext ctx) {
            return NOTHING;
        }

        @Override
        protected void entityInside(BlockState state, Level level, BlockPos pos, Entity entity) {
            if (level.isClientSide || !(entity instanceof ServerPlayer player)) {
                return;
            }
            try {
                long now = level.getGameTime();
                Long until = COOLDOWN.get(player.getId());
                if (until != null && now < until) {
                    return;
                }
                COOLDOWN.put(player.getId(), now + COOLDOWN_TICKS);

                MinecraftServer server = player.getServer();
                if (server == null) {
                    return;
                }
                // The script owns arrival. See the class comment: one source of truth.
                server.getCommands().performPrefixedCommand(
                        server.createCommandSourceStack().withSuppressedOutput(),
                        "hubgo " + this.destination + " " + player.getScoreboardName());
            } catch (Throwable t) {
                System.out.println("[pocketquests] portal trigger failed: " + t);
            }
        }
    }

    /** Test seam: the destinations a build is carrying, without a running game. */
    static List<String> destinationIds() {
        return new ArrayList<>(DESTINATIONS.keySet());
    }

    static List<Block> registeredBlocks() {
        return REGISTERED;
    }

    /** The dimension a destination id maps to, for scripts and docs. */
    public static ResourceKey<Level> levelOf(String dest) {
        return ResourceKey.create(Registries.DIMENSION,
                ResourceLocation.fromNamespaceAndPath("hub", dest));
    }
}
