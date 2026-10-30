// NOTE: IIFE - KubeJS server scripts share one global scope.
(function () {
// Builds the hub room AND seeds the four empty pockets, once, at world load.
//
// Seeding used to happen on first entry, which is a race: `place template` needs the target
// chunks to exist, and a pocket nobody has visited has none. forceload does not take effect
// until the following tick, so even forceload-then-place in one call failed silently - which
// is why Oceanblock dropped you into open water with no island anywhere in sight. The tp
// worked (teleporting loads chunks), the place did not, and runCommandSilent ate the error.
//
// Doing it at load removes the race: forceload at tick 0, place at tick 40, unpin at tick 120.
// Once the blocks are written they are on disk, so the chunks need not stay pinned.
//
// The schedules are all registered flat off the loaded event rather than nested inside each
// other - nesting scheduleInTicks is an assumption this codebase has not verified, and the
// failure mode would be another silent one.

  console.info('[hub] setup v2 loaded');

  // Two independent flags on purpose.
  //
  // ROOM_FLAG carries a version number: bumping it re-places the lobby so changes to the
  // structure (new portal blocks, connected-glass backing) land in worlds that already exist.
  // The lobby is not somewhere anyone builds, so overwriting it is free.
  //
  // SEED_FLAG is separate and is NOT bumped, because re-placing a pocket's starting structure
  // would overwrite whatever has been built on top of it. Use /hubseed to force that.
  var ROOM_FLAG = 'hubRoomVersion6';
  var SEED_FLAG = 'hubWorldSeeded';
  // Structures added AFTER a world already exists need their own versioned flag. Putting them
  // inside seedPockets would mean they never place: that flag is set the first time a world
  // loads, so anything appended to it is silently skipped forever.
  var EXTRAS_FLAG = 'hubExtrasVersion2';
  var AREA = '-16 -16 16 16';
  // The lobby's own window, wide enough for the 65x29 room at -32,64,-14.
  var ROOM_AREA = '-32 -32 32 32';

  // Verified against each template's own block data: feet in air, 2 blocks of headroom,
  // solid ground below, inside the island footprint. Do not hand-edit - re-run the checker.
  function seed(server, dim, tpl, x, y, z) {
    server.runCommandSilent('execute in ' + dim + ' run forceload add ' + AREA);
    server.scheduleInTicks(40, () => {
      server.runCommandSilent('execute in ' + dim + ' run place template ' + tpl + ' ' + x + ' ' + y + ' ' + z);
      console.info('[hub] seeded ' + dim + ' <- ' + tpl + ' at ' + x + ' ' + y + ' ' + z);
    });
    server.scheduleInTicks(120, () => {
      server.runCommandSilent('execute in ' + dim + ' run forceload remove ' + AREA);
    });
  }

  // The lobby needs its chunks to EXIST while `place template` runs, exactly like every pocket
  // seed does - see the note at the top of this file about the Oceanblock island.
  //
  // It used to get that for free: the hub was permanently forceloaded, so at world load the
  // chunks were already there. Releasing that pin (correctly - 25 chunks of permanent random
  // ticks for a room nobody stands in while away) took the guarantee with it, and the next
  // fresh world came up with no lobby at all: "hub didnt spawn for some reason, had to seed it
  // on this fresh world". /hubseed worked because by then the player was standing in it.
  //
  // So the room gets the same temporary window the pockets get: pin at tick 0, place at 40,
  // release at 120. The blocks are on disk once written, so nothing stays pinned.
  //
  // hub_room.nbt is 65x8x29 placed at -32,64,-14, so it spans x -32..32, z -14..14 - inside
  // ROOM_AREA's chunks either way.
  function placeRoom(server) {
    server.runCommandSilent('execute in hub:hub run forceload add ' + ROOM_AREA);
    server.scheduleInTicks(40, () => {
      server.runCommandSilent('execute in hub:hub run place template hub:hub_room -32 64 -14');
      console.info('[hub] placed the hub room');
    });
    server.scheduleInTicks(120, () => {
      server.runCommandSilent('execute in hub:hub run forceload remove ' + ROOM_AREA);
    });
  }

  // Oceanblock only: wipe the spawn area before placing the island.
  //
  // `structure_overrides` now keeps towns_and_towers:pillager_outpost_ocean (a ship full of
  // vindicators) out of this dimension, but that only affects chunks generated from now on -
  // a world that already generated one still has it sitting on the spawn island. These two
  // fills restore the area to plain ocean so /hubseed can repair an existing world.
  //
  // The layer stack is bedrock at -64, then deepslate, stone, gravel, sand, and water from
  // y36 to y65 - so y65 is the sea surface and the island's grass belongs at y66. Each fill is
  // 33x30x33 = 32670 blocks, just inside the 32768 limit for a single /fill.
  function clearOceanSpawn(server) {
    var dim = 'hub:oceanblock';
    server.runCommandSilent('execute in ' + dim + ' run fill -16 36 -16 16 65 16 minecraft:water replace');
    server.runCommandSilent('execute in ' + dim + ' run fill -16 66 -16 16 95 16 minecraft:air replace');
    console.info('[hub] cleared the oceanblock spawn area back to open ocean');
  }

  // The Coliseum sits in the gauntlet pocket dimension, which generates amplified terrain -
  // dropping a 67x67 arena straight into that would half-bury it. So the pad is levelled first:
  // everything above is cleared and everything below is filled to solid stone, then the arena is
  // placed. The gauntlet keeps its wild terrain (and its scouting chapter); the arena gets a
  // deliberate, level stage.
  //
  // /fill is capped at 32768 blocks and the pad is 67x67 = 4489 per layer, so each command can
  // cover at most 7 layers. Hence a helper called explicitly several times rather than a loop -
  // Rhino's loop handling is not trusted anywhere in this codebase.
  function cut(server, y1, y2, block) {
    server.runCommandSilent('execute in hub:gauntlet run fill -33 ' + y1 + ' -33 33 ' + y2
      + ' 33 ' + block + ' replace');
  }

  function seedColiseum(server) {
    server.runCommandSilent('execute in hub:gauntlet run forceload add -48 -48 48 48');
    server.scheduleInTicks(40, () => {
      cut(server, 63, 69, 'minecraft:air');
      cut(server, 70, 76, 'minecraft:air');
      cut(server, 77, 83, 'minecraft:air');
      cut(server, 84, 90, 'minecraft:air');
      cut(server, 91, 97, 'minecraft:air');
      cut(server, 98, 104, 'minecraft:air');
      cut(server, 105, 111, 'minecraft:air');
      cut(server, 112, 118, 'minecraft:air');
      cut(server, 119, 125, 'minecraft:air');
      cut(server, 126, 132, 'minecraft:air');
      cut(server, 133, 139, 'minecraft:air');
      cut(server, 140, 146, 'minecraft:air');
      cut(server, 147, 150, 'minecraft:air');
      cut(server, 40, 46, 'minecraft:stone');
      cut(server, 47, 53, 'minecraft:stone');
      cut(server, 54, 60, 'minecraft:stone');
      cut(server, 61, 62, 'minecraft:stone');
      console.info('[hub] levelled the coliseum pad in the gauntlet pocket dimension');
    });
    server.scheduleInTicks(100, () => {
      server.runCommandSilent('execute in hub:gauntlet run place template hub:coliseum -33 63 -33');
      console.info('[hub] placed the Coliseum at -33 63 -33');
    });
    server.scheduleInTicks(200, () => {
      server.runCommandSilent('execute in hub:gauntlet run forceload remove -48 -48 48 48');
    });
  }

  // The texture-pack showcase lives in redstone land, well clear of its 0,64,0 spawn: a swatch
  // gallery of 160 blocks in 16 material rows, plus build scenes (a house corner with a roof and
  // windows, a path, a garden, a tree, water and lava). Swap packs in the resource pack menu and
  // walk it - swatches alone do not tell you how a pack reads in an actual build.
  function seedShowcase(server) {
    server.runCommandSilent('execute in hub:redstone run forceload add 112 -40 200 48');
    server.scheduleInTicks(60, () => {
      server.runCommandSilent('execute in hub:redstone run place template hub:showcase 120 63 -30');
      console.info('[hub] placed the texture showcase in redstone land at 120 63 -30');
    });
    server.scheduleInTicks(160, () => {
      server.runCommandSilent('execute in hub:redstone run forceload remove 112 -40 200 48');
    });
  }

  function seedPockets(server) {
    seed(server, 'hub:skyblock',   'hub:skyblock_start',   -4, 64, -4);
    seed(server, 'hub:caveblock',  'hub:caveblock_start',  -7, 60, -7);
    // oceanblock is seeded by hand so the clear happens between the forceload and the place
    server.runCommandSilent('execute in hub:oceanblock run forceload add ' + AREA);
    server.scheduleInTicks(40, () => {
      clearOceanSpawn(server);
      server.runCommandSilent('execute in hub:oceanblock run place template hub:oceanblock_start -5 64 -5');
      console.info('[hub] seeded hub:oceanblock <- hub:oceanblock_start at -5 64 -5');
    });
    server.scheduleInTicks(120, () => {
      server.runCommandSilent('execute in hub:oceanblock run forceload remove ' + AREA);
    });
    seed(server, 'hub:onechunk',   'hub:onechunk_start',   -8, 64, -8);

  }

  ServerEvents.loaded(event => {
    var server = event.server;
    // The hub is NOT pinned. It used to be, on the reasoning "you are standing in it" - which
    // is backwards: if you are standing in it, it is loaded anyway, so the forceload only did
    // work while you were somewhere else, which is exactly when the lobby does not need to
    // tick. It cost 25 chunks of permanent random ticks and block-entity ticks on a CPU whose
    // single-thread throughput is the bottleneck. Issued as a REMOVE rather than deleted so
    // that worlds created before this change get cleaned up on load too.
    server.runCommandSilent('execute in hub:hub run forceload remove ' + ROOM_AREA);

    if (!server.persistentData.getBoolean(ROOM_FLAG)) {
      server.persistentData.putBoolean(ROOM_FLAG, true);
      placeRoom(server);
    } else {
      console.info('[hub] lobby already current');
    }

    if (!server.persistentData.getBoolean(SEED_FLAG)) {
      server.persistentData.putBoolean(SEED_FLAG, true);
      seedPockets(server);
    } else {
      console.info('[hub] pocket dimensions already seeded (/hubseed to redo)');
    }

    // The Coliseum and the texture showcase are newer than the first worlds, so they get their
    // own flag rather than riding on the pocket-dimension one.
    if (!server.persistentData.getBoolean(EXTRAS_FLAG)) {
      server.persistentData.putBoolean(EXTRAS_FLAG, true);
      seedColiseum(server);
      seedShowcase(server);
    } else {
      console.info('[hub] coliseum + showcase already placed');
    }
  });

  // Re-place everything without deleting the world. Registered at server start, so it is
  // present from launch - but like every KubeJS command it will NOT exist if you only
  // /kubejs reload server_scripts; that needs a full restart.
  ServerEvents.commandRegistry(event => {
    const { commands: Commands } = event;
    event.register(Commands.literal('showcase').executes(ctx => {
      // redstone land is creative, so a straight teleport is fine
      ctx.source.server.runCommandSilent('execute in hub:redstone run tp '
        + ctx.source.player.username + ' 125 65 -25');
      ctx.source.sendSuccess(Text.gold('Texture showcase: 16 swatch rows along +z, build scenes to the east.'), false);
      return 1;
    }));
    event.register(Commands.literal('hubseed').executes(ctx => {
      placeRoom(ctx.source.server);
      seedPockets(ctx.source.server);
      seedColiseum(ctx.source.server);
      seedShowcase(ctx.source.server);
      ctx.source.sendSuccess(Text.gold('Re-placing hall, pocket starts, Coliseum and showcase.'), false);
      return 1;
    }));
  });
})();
