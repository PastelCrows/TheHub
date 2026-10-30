// NOTE: wrapped in an IIFE because KubeJS server scripts share a single global
// scope - top-level `const` in two files collides and kills the second one.
(function () {
// Test kits. These exist so the gates added to PocketQuests can be smoke-tested without
// grinding for the materials first, which is the only reason they would ever get skipped.
//
//   /tftest   everything needed to build a Twilight Forest portal, to prove TFPortalMixin
//             sends you home to your own pocket dimension instead of minecraft:overworld.
//   /extest   everything needed to craft an Ex Deorum sieve, to prove the per-dimension
//             crafting deny-list works: this should FAIL in survival, lostcities and
//             gauntlet, and SUCCEED in skyblock, caveblock, oceanblock, onechunk and
//             netherbound.
//
// Every item below was read out of the mods' own data, not remembered:
//   twilightforest/tags/block/portal/fluid.json       -> minecraft:water
//   twilightforest/tags/block/portal/edge.json        -> #minecraft:dirt (grass_block qualifies)
//   twilightforest/tags/block/portal/decoration.json  -> 38 entries, including
//                                                        #minecraft:flowers and #minecraft:saplings
//   twilightforest/tags/item/portal/activator.json    -> #c:gems/diamond
//   exdeorum oak_sieve.json    -> 4 oak planks + 1 oak slab + 2 wooden rods
//   exdeorum string_mesh.json  -> 9 string
//
// Each kit is sized to exactly fill the hotbar from an empty inventory, so `/clear` first if
// you want them in reach. Water buckets do not stack, hence four separate slots.
//
// commandRegistry only fires at SERVER START. After editing this file a full restart is
// required - `/kubejs reload server_scripts` will leave the old commands registered and lie
// to you about it. Permission level 2, so these are op-only.

  function give(server, who, what) {
    server.runCommandSilent('give ' + who + ' ' + what);
  }

  // No loops anywhere: Rhino will not iterate an array here, and a loop that silently does
  // nothing is the single most expensive mistake in this codebase.
  function tfKit(server, who) {
    give(server, who, 'minecraft:iron_shovel');
    give(server, who, 'minecraft:water_bucket');
    give(server, who, 'minecraft:water_bucket');
    give(server, who, 'minecraft:water_bucket');
    give(server, who, 'minecraft:water_bucket');
    give(server, who, 'minecraft:grass_block 64');
    give(server, who, 'minecraft:oak_sapling 16');
    give(server, who, 'minecraft:poppy 16');
    give(server, who, 'minecraft:diamond 3');
  }

  function exKit(server, who) {
    give(server, who, 'minecraft:crafting_table');
    give(server, who, 'minecraft:oak_planks 32');
    give(server, who, 'minecraft:oak_slab 16');
    give(server, who, 'minecraft:stick 16');
    give(server, who, 'minecraft:string 32');
    give(server, who, 'minecraft:dirt 64');
  }

  ServerEvents.commandRegistry(event => {
    const { commands: Commands } = event;

    event.register(Commands.literal('tftest')
      .requires(src => src.hasPermission(2))
      .executes(ctx => {
        var player = ctx.source.player;
        if (!player) { return 0; }
        var server = ctx.source.server;
        tfKit(server, player.username);
        player.tell(Text.gold('--- Twilight Forest portal ---'));
        player.tell(Text.white('1. Dig or build a 2x2 pool and fill it with all four buckets.'));
        player.tell(Text.white('2. Rim the pool with grass blocks (any #minecraft:dirt works).'));
        player.tell(Text.white('3. Plant saplings or flowers on the blocks around it.'));
        player.tell(Text.white('4. Throw a diamond into the water. Expect lightning.'));
        player.tell(Text.gray('Then step in, walk a little, and come back through.'));
        player.tell(Text.gray('You should land where you left - not 875,000 blocks away.'));
        console.info('[hub] /tftest -> ' + player.username);
        return 1;
      }));

    event.register(Commands.literal('extest')
      .requires(src => src.hasPermission(2))
      .executes(ctx => {
        var player = ctx.source.player;
        if (!player) { return 0; }
        var server = ctx.source.server;
        exKit(server, player.username);
        var dim = String(player.level.dimension);
        var denied = (dim.indexOf('survival') !== -1
                   || dim.indexOf('lostcities') !== -1
                   || dim.indexOf('gauntlet') !== -1
                   || dim.indexOf('horror') !== -1
                   || dim.indexOf('oneblock') !== -1
                   || dim.indexOf('hub:hub') !== -1);
        player.tell(Text.gold('--- Ex Deorum sieve ---'));
        player.tell(Text.white('Sieve:  O O  /  O_O  /  I I   (O planks, _ slab, I stick)'));
        player.tell(Text.white('Mesh:   9 string in a full grid.'));
        if (denied) {
          player.tell(Text.red('This dimension DENIES exdeorum. The sieve output slot'));
          player.tell(Text.red('should stay empty - that is the gate working.'));
        } else {
          player.tell(Text.green('This dimension ALLOWS exdeorum. The sieve should craft'));
          player.tell(Text.green('normally - put the mesh in it and sieve the dirt.'));
        }
        console.info('[hub] /extest -> ' + player.username + ' in ' + dim
                     + ' (expect ' + (denied ? 'DENY' : 'ALLOW') + ')');
        return 1;
      }));
  });

})();
