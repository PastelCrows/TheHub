// NOTE: IIFE - KubeJS startup scripts share one global scope, same as server scripts.
(function () {
// The eight hub portal blocks: Twilight Forest's portal barrier texture, hue-rotated once per
// pocket, as 32-frame animated strips in kubejs/assets/hub/textures/block/.
//
// Why a custom block at all: there is no vanilla walkable portal block that is safe here.
// minecraft:nether_portal hands travel to vanilla nether code, and end_gateway is a block
// entity with its own teleport rules. These are inert decoration - hub_portals.js owns travel,
// detecting it from the player's position in the doorway - so the block only has to look right
// and let you walk into it.
//
// API verified against kubejs-neoforge-2101.7.2 with javap, not guessed:
//   texture/renderType     <- ModelledBuilderBase, enum is SOLID|CUTOUT|CUTOUT_MIPPED|TRANSLUCENT
//   noItem/noDrops/box     <- BlockBuilder
//   create(namespaced id)  <- RegistryKubeEvent.create(ctx, KubeResourceLocation)
//
// No loop builds these - Rhino silently fails to iterate objects and, in this pack, also
// failed on indexed array walks. Eight explicit calls instead.

  function portal(event, pocket) {
    event.create('hub:portal_' + pocket)
      .texture('hub:block/portal_' + pocket)
      .renderType('translucent')
      .lightLevel(0.75)
      .noCollision()      // you walk INTO it; that is what triggers travel
      .notSolid()
      .opaque(false)
      .fullBlock(false)
      .transparent(true)
      .hardness(-1.0)     // unbreakable in survival; creative ignores hardness entirely
      .resistance(3600000.0)
      .glassSoundType()
      // An item form IS registered (no .noItem() here) so the portal blocks can be picked up
      // in creative - middle-click a portal, or search "portal" in the creative inventory - and
      // the hub can be redesigned by hand later. Without an item, pick-block has nothing to
      // give you and the blocks are unobtainable.
      //
      // ItemBuilder.group() is NOT the way to put them in a tab: in this KubeJS version it is
      // deprecated and only logs "no longer supported, use StartupEvents.modifyCreativeTab".
      // Registered items always appear in the creative SEARCH tab regardless, which is enough.
      .noDrops()          // nothing drops in survival; irrelevant in creative
      .displayName(Text.gold(pocket.charAt(0).toUpperCase() + pocket.slice(1) + ' Portal'));
  }

  StartupEvents.registry('block', event => {
    portal(event, 'skyblock');
    portal(event, 'survival');
    portal(event, 'caveblock');
    portal(event, 'netherbound');
    portal(event, 'oceanblock');
    portal(event, 'lostcities');
    portal(event, 'onechunk');
    portal(event, 'gauntlet');
    // redstone land is a creative sandbox rather than a pocket dimension, but it is reached
    // through the hall like everything else, so it gets an arch and a portal block too
    portal(event, 'redstone');
    portal(event, 'oneblock');
    portal(event, 'horror');
    // The twelfth is the way HOME, and it is the only one that is not an arch in the hall: one
    // of these is placed in every pocket dimension on first arrival. Same block, same rules -
    // unbreakable, no drops, pick-up-able in creative so the hub can be rebuilt by hand.
    portal(event, 'hub');
    console.info('[hub] registered 12 portal blocks');
  });
})();
