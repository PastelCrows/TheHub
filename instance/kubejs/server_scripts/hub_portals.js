// NOTE: IIFE - KubeJS server scripts share one global scope.
(function () {
// v5. No loops, no array indexing, no object iteration, `var` only - Rhino fails silently
// on all three (see v1-v3 history in git... or in the scars).
//
// Arrival is the thing v4 got wrong. Two completely different problems:
//
//   SEEDED pockets (skyblock, caveblock, oceanblock, onechunk) are void or solid rock, so
//   there is nothing to land on until the starting structure exists. The old fixed coords
//   were also simply wrong - caveblock's (0,62,0) is INSIDE the stone, which is what was
//   suffocating you. Correct cells are computed from each template's own spawn point.
//
//   TERRAIN pockets (survival, lostcities, gauntlet, netherbound) generate real ground at
//   an unpredictable height, so ANY fixed Y is a coin flip between mid-air and buried.
//   spreadplayers finds a safe surface spot instead; the nether needs `under` so it does
//   not drop you on the roof.

  console.info('[hub] portals v5 loaded');

  var HUB = 'hub:hub';
  var cooldown = {};
  var seeded = {};
  var inArch = {};
  var ticks = 0;

  function near(a, b) { return Math.abs(a - b) <= 1; }

  // Seeding happens once at world load in hub_setup.js, NOT here - placing into an
  // unvisited pocket's unloaded chunks fails silently, which is how you ended up in open
  // ocean with no island. By the time anyone can walk through an arch, the structure exists.
  function seedAndLand(event, player, name, dim, tpl, sx, sy, sz, ax, ay, az) {
    event.server.runCommandSilent(
      'execute in ' + dim + ' run tp ' + player.username + ' ' + ax + ' ' + ay + ' ' + az);
    console.info('[hub] -> ' + name + ' at ' + ax + ' ' + ay + ' ' + az);
  }

  function surfaceLand(event, player, name, dim, nether) {
    var server = event.server;
    var who = player.username;
    // get them into the dimension first, then let spreadplayers pick safe ground
    server.runCommandSilent('execute in ' + dim + ' run tp ' + who + ' 0 250 0');
    if (nether) {
      server.runCommandSilent('execute in ' + dim + ' run spreadplayers 0 0 0 200 under 100 false ' + who);
    } else {
      server.runCommandSilent('execute in ' + dim + ' run spreadplayers 0 0 0 200 false ' + who);
    }
    console.info('[hub] -> ' + name + ' via spreadplayers');
  }


  // First-entry starting kit, once per pocket per player.
  //
  // This used to run inside enter(), alongside the teleport - so `give` landed in the HUB
  // inventory a tick before the dimension actually changed, and DimSwap then swapped that
  // inventory away. The items went into the creative hub and vanished. A delay would have
  // been a guess about how long the teleport and the swap take.
  //
  // So there is no timer: the tick watcher hands over the kit whenever it sees you standing
  // in the pocket without having received it. That cannot land in the wrong inventory, and it
  // self-heals - a kit missed for any reason is granted the next time you are in there.
  //
  // skyblock / caveblock / oceanblock / onechunk are absent on purpose: each of their starting
  // structures contains a stocked chest, so a kit as well would double the start.
  //
  // survival, gauntlet, horror, oneblock, redstone and the hub get NOTHING, by decision.
  // Survival used to hand out stone tools and bread; it no longer does - a survival start is
  // supposed to be a survival start. See BALANCE.md.
  //
  // Netherbound gets a deliberately thin kit rather than nothing. Its premise is scavenging,
  // but arriving empty-handed somewhere with no trees is a dead end, so it gets just enough
  // to reach crimson stems and start cooking.
  //
  // The flag is `kitv2_`, not `kit_`: the old name is already set to true for kits that were
  // granted into the hub and lost, and those players should still get a real one.
  function kit(server, who, dim, items) {
    server.runCommandSilent(
      'execute as ' + who + ' at @s if dimension ' + dim + ' run give ' + who + ' ' + items);
  }

  function giveKit(event, player, name, dim) {
    var flag = 'kitv2_' + name;
    if (player.persistentData.getBoolean(flag)) return;
    var server = event.server;
    var who = player.username;

    if (name === 'lostcities') {
      kit(server, who, dim, 'minecraft:iron_pickaxe');
      kit(server, who, dim, 'minecraft:stone_sword');
      kit(server, who, dim, 'minecraft:torch 64');
      kit(server, who, dim, 'minecraft:bread 16');
      kit(server, who, dim, 'minecraft:ladder 16');
    } else if (name === 'gauntlet') {
      // Deliberately EMPTY. The Gauntlet is one of the pocket dimensions that starts you with
      // absolutely nothing; the briefing below is information, not equipment. Everything the
      // first Gate Pearl needs - redstone, two mushrooms, an ender pearl, three bottles - is
      // obtainable in its own amplified terrain, so an empty start is a grind rather than a
      // dead end. (The pearl itself could never have been handed over anyway: its gateway is
      // bound by a custom gateways:gate_recipe, so a plain `give` yields a blank pearl.)
    } else if (name === 'netherbound') {
      kit(server, who, dim, 'minecraft:stone_pickaxe');
      kit(server, who, dim, 'minecraft:crafting_table');
      kit(server, who, dim, 'minecraft:cooked_porkchop 8');
      kit(server, who, dim, 'minecraft:torch 16');
    } else {
      return;   // the four block-pockets start from their chest
    }
    player.persistentData.putBoolean(flag, true);
    // The Gauntlet deliberately receives no items, so announcing a kit there would be a lie.
    if (name !== 'gauntlet') {
      player.tell(Text.gold('Starting kit for ' + name + '.'));
    }

    // The Gauntlet is terrain like any other world - its premise lives entirely in the
    // Gateways loop, so without a word of explanation it just looks like a vanilla overworld
    // with some odd structures in it. Say the loop out loud, once.
    if (name === 'gauntlet') {
      player.tell(Text.gold('--- The Gauntlet ---'));
      player.tell(Text.white('This pocket is run-based. You do not progress by exploring.'));
      player.tell(Text.white('Craft a Gate Pearl, drop it on the gold centre of the arena, and survive.'));
      player.tell(Text.white('Each clear pays out gear; each pearl tier needs loot from the one below.'));
      player.tell(Text.gray('You have the materials for the first pearl. The Coliseum is around you.'));
    }
    console.info('[hub] kit -> ' + who + ' / ' + name);
  }

  // Called every time the watcher sees a player outside the hub. Explicit checks, no loop.
  function kitCheck(event, player, dim) {
    if (dim.indexOf('hub:lostcities') !== -1)  { giveKit(event, player, 'lostcities',  'hub:lostcities');  return; }
    if (dim.indexOf('hub:gauntlet') !== -1)    { giveKit(event, player, 'gauntlet',    'hub:gauntlet');    return; }
    if (dim.indexOf('hub:netherbound') !== -1) { giveKit(event, player, 'netherbound', 'hub:netherbound'); return; }
  }

  // ------------------------------------------------------- return portals
  //
  // ONE-WAY, back to the hub. Not a second mouth of a two-way portal, deliberately: you are
  // meant to arrive in One Block standing on the block and in skyblock on the island, not step
  // out of a doorway, and a two-way portal would need an arrival anchor in every pocket to
  // teleport you onto. One-way is strictly simpler and gives exactly the arrival that was asked
  // for.
  //
  // Placed RELATIVE TO WHERE YOU ACTUALLY LAND, with `execute at`, rather than at a table of
  // fixed coordinates. Four pocket dimensions (survival, lost cities, horror, netherbound)
  // arrive via spreadplayers and have no fixed spawn at all, so a coordinate table could not
  // cover them; `execute at` covers all eleven with one mechanism and keeps the portal close by
  // wherever you come down.
  //
  // ON THE VOID POCKETS IT IS JUST THE PORTAL. Two blocks hanging in the air a few paces off,
  // nothing under them, no frame - a platform would be free blocks in a pack whose whole premise
  // is that you have none, and a frame would be a free stack of whatever it was made of.
  // Terrain pockets get a modest frame of their own arch material, where a few blocks of
  // cracked stone brick or red nether brick change nothing.
  //
  // Once per pocket per world, tracked in the server's persistent data. Breaking one is
  // permanent by design - they cannot be crafted, and that is the player's problem to avoid,
  // the same as any other one-off structure in the pack.
  var RETURN_FLAG = 'hubReturnPortal_';

  function setb(server, dim, who, dx, dy, dz, block) {
    server.runCommandSilent('execute in ' + dim + ' at ' + who
      + ' run setblock ~' + dx + ' ~' + dy + ' ~' + dz + ' ' + block + ' replace');
  }

  // No loops anywhere in here: Rhino's iteration is not trusted in this codebase, and a frame
  // that silently places nothing is exactly the kind of failure that hides for weeks.
  function clearAround(server, dim, who, dx, dz) {
    setb(server, dim, who, dx, 0, dz, 'minecraft:air');
    setb(server, dim, who, dx, 1, dz, 'minecraft:air');
    setb(server, dim, who, dx, 2, dz, 'minecraft:air');
    setb(server, dim, who, dx - 1, 0, dz, 'minecraft:air');
    setb(server, dim, who, dx - 1, 1, dz, 'minecraft:air');
    setb(server, dim, who, dx + 1, 0, dz, 'minecraft:air');
    setb(server, dim, who, dx + 1, 1, dz, 'minecraft:air');
  }

  function placeReturn(server, dim, who, dx, dz, frame) {
    if (frame) {
      clearAround(server, dim, who, dx, dz);
      // posts either side, a lintel over, a sill under - the smallest thing that reads as a door
      setb(server, dim, who, dx - 1, 0, dz, frame);
      setb(server, dim, who, dx - 1, 1, dz, frame);
      setb(server, dim, who, dx + 1, 0, dz, frame);
      setb(server, dim, who, dx + 1, 1, dz, frame);
      setb(server, dim, who, dx - 1, 2, dz, frame);
      setb(server, dim, who, dx, 2, dz, frame);
      setb(server, dim, who, dx + 1, 2, dz, frame);
      setb(server, dim, who, dx, -1, dz, frame);
    }
    setb(server, dim, who, dx, 0, dz, 'hub:portal_hub');
    setb(server, dim, who, dx, 1, dz, 'hub:portal_hub');
    console.info('[hub] return portal placed in ' + dim + ' near ' + who);
  }

  // pocket -> [dimension, offset x, offset z, frame material or null for the void pockets]
  var RETURNS = {
    skyblock:    ['hub:skyblock',    5,  0, null],
    caveblock:   ['hub:caveblock',   4,  0, 'minecraft:polished_deepslate'],
    oceanblock:  ['hub:oceanblock',  5,  0, null],
    onechunk:    ['hub:onechunk',    5,  0, null],
    oneblock:    ['hub:oneblock',    4,  0, null],
    survival:    ['hub:survival',    4,  0, 'minecraft:stripped_oak_wood'],
    lostcities:  ['hub:lostcities',  4,  0, 'minecraft:cracked_stone_bricks'],
    netherbound: ['hub:netherbound', 4,  0, 'minecraft:red_nether_bricks'],
    horror:      ['hub:horror',      4,  0, 'minecraft:blackstone'],
    gauntlet:    ['hub:gauntlet',    5,  0, 'minecraft:gilded_blackstone'],
    redstone:    ['hub:redstone',    5,  0, 'minecraft:redstone_block']
  };

  function ensureReturn(server, player, name) {
    var spec = RETURNS[name];
    if (!spec) { return; }
    var flag = RETURN_FLAG + name;
    if (server.persistentData.getBoolean(flag)) { return; }
    server.persistentData.putBoolean(flag, true);
    // Late enough that the teleport (and spreadplayers, which resolves over a few ticks) has
    // actually put the player where they are going. Placing it at the moment of travel puts the
    // portal next to where they LEFT, which is the hub.
    server.scheduleInTicks(40, () => {
      placeReturn(server, spec[0], player.username, spec[1], spec[2], spec[3]);
      player.tell(Text.gold('A way back to the hub stands a few paces away.'));
    });
  }

  function enter(event, player, name) {
    var key = '' + player.username;
    cooldown[key] = ticks;
    player.persistentData.putString('lastPocket', name);
    player.tell(Text.gold('Entering ' + name + '...'));
    console.info('[hub] MATCHED ' + name);
    ensureReturn(event.server, player, name);

    if (name === 'skyblock')    { seedAndLand(event, player, name, 'hub:skyblock',   'hub:skyblock_start',  -4, 64, -4,  2, 67, 1); return; }
    if (name === 'caveblock')   { seedAndLand(event, player, name, 'hub:caveblock',  'hub:caveblock_start', -7, 60, -7,  1, 61, 1); return; }
    if (name === 'oceanblock')  { seedAndLand(event, player, name, 'hub:oceanblock', 'hub:oceanblock_start',-5, 64, -5,  1, 67, 1); return; }
    if (name === 'onechunk')    { seedAndLand(event, player, name, 'hub:onechunk',   'hub:onechunk_start',  -8, 64, -8,  1, 86, 1); return; }
    if (name === 'survival')    { surfaceLand(event, player, name, 'hub:survival',   false); return; }
    if (name === 'lostcities')  { surfaceLand(event, player, name, 'hub:lostcities', false); return; }
    // The gauntlet arrives INSIDE the Coliseum, just within the south entrance, rather than
    // at a random surface spot. The arena is the whole point of the pocket dimension, and
    // spreadplayers was dropping you somewhere in the amplified hills with no idea it existed.
    if (name === 'gauntlet')    { event.server.runCommandSilent('execute in hub:gauntlet run tp ' + player.username + ' 0 65 19');
                                  console.info('[hub] -> gauntlet, Coliseum south entrance'); return; }
    if (name === 'netherbound') { surfaceLand(event, player, name, 'hub:netherbound', true); return; }
    // Redstone land: flat stone with its surface at y 63, so y 64 is standing height. No
    // structure to seed and no kit - it is a creative sandbox, and hub_gamemode.js puts you
    // in creative on arrival the same way it does in the hub.
    if (name === 'redstone')    { event.server.runCommandSilent('execute in hub:redstone run tp ' + player.username + ' 0 64 0');
                                  console.info('[hub] -> redstone land at 0 64 0'); return; }
    // One Block: the mod's own generator puts THE block at the origin, y 64 (ONEBLOCK_Y read
    // straight out of OneBlockChunkGenerator), and generates a small island around it. Landing
    // on top of the block is the one cell guaranteed to be solid - it is the premise of the
    // pocket dimension, so it cannot be missing. No seeding, no kit: the block is the kit.
    if (name === 'oneblock')    { event.server.runCommandSilent('execute in hub:oneblock run tp ' + player.username + ' 0 65 0');
                                  console.info('[hub] -> oneblock, stood on the block'); return; }
    // Horror generates ordinary (if differently-seeded) terrain, so the surface has to be found
    // rather than assumed - same treatment as the survival pocket dimension.
    if (name === 'horror')      { surfaceLand(event, player, name, 'hub:horror', false); return; }
  }

  // ------------------------------------------------------------------ hubgo
  //
  // The command the PORTAL BLOCKS call. PocketPortal registers one block per destination and
  // each one runs `hubgo <destination> <player>` when a player walks into it.
  //
  // The block deliberately does not teleport by itself. Arrival is a whole procedure - seeding,
  // landing spot, gamemode, DimSwap inventory group, kit, briefing - and every bit of it already
  // lives in enter() below. Reimplementing it in Java would be a second source of truth for the
  // same rules, which is exactly how the crafting gate went wrong twice. So the block is a
  // trigger and this is the one door it knocks on.
  //
  // Permission 2, same as the test commands, and it takes an explicit player name because the
  // block runs it as the SERVER - there is no "sender" to infer a player from.
  ServerEvents.commandRegistry(event => {
    const { commands: Commands, arguments: Arguments } = event;
    event.register(Commands.literal('hubgo')
      .requires(src => src.hasPermission(2))
      .then(Commands.argument('destination', Arguments.STRING.create(event))
        .then(Commands.argument('who', Arguments.STRING.create(event))
          .executes(ctx => {
            var dest = Arguments.STRING.getResult(ctx, 'destination');
            var who = Arguments.STRING.getResult(ctx, 'who');
            var server = ctx.source.server;
            var player = server.getPlayer(who);
            if (!player) {
              console.warn('[hub] hubgo: no player named ' + who);
              return 0;
            }
            if (dest === 'hub') {
              // Going home is hub_return.js's job; run its command as the player so the
              // return path stays in one place too.
              server.runCommandSilent('execute as ' + who + ' at ' + who + ' run hub');
              return 1;
            }
            // enter() only ever uses event.server, so a shim with that one field is enough.
            enter({ server: server }, player, dest);
            return 1;
          }))));
  });

  PlayerEvents.tick(event => {
    var player = event.player;
    ticks = ticks + 1;
    // Sampled EVERY tick, not every fifth. At 5-tick intervals you can cross the 3-wide arch
    // between samples - and when the server is running 50+ ticks behind (as the log showed) the
    // gaps are far worse, which is why standing in a portal sometimes did nothing for minutes
    // while other times it fired instantly. The check below is a handful of float comparisons;
    // sampling it every tick costs nothing measurable.
    if (!player) return;
        var dimStr = '' + player.level.dimension;
    if (dimStr.indexOf(HUB) === -1) {
      // in a pocket (or anywhere else): settle any kit we still owe, then stop
      kitCheck(event, player, dimStr);
      return;
    }

    var key = '' + player.username;
    var x = player.x, y = player.y, z = player.z;
    if (typeof x !== 'number') return;
    var px = Math.floor(x), py = Math.floor(y), pz = Math.floor(z);

    // ---------------------------------------------------------------- detection
    //
    // WHAT BLOCK ARE YOU STANDING IN. This replaced a table of arch coordinates that
    // build_hub_room_v6.py compiled into this file, and it fixes three things at once:
    //
    //   the portal that "took a long time to go off" - the old check compared floats against
    //   arch positions with a one-block tolerance, so clipping a corner or a laggy tick could
    //   miss entirely. A block lookup is exact and fires the tick you are inside it.
    //
    //   the hall could not be redesigned - coordinates were compiled in, so moving an arch meant
    //   regenerating the room AND this script. Now the BLOCK is the portal. Pick one up in
    //   creative, put it anywhere, and it works, in any dimension.
    //
    //   return portals - a hub:portal_hub placed in a pocket dimension sends you home, and
    //   needed no new mechanism at all.
    //
    // The blocks are the ones hub_blocks.js has always registered, with their animated
    // hue-rotated textures. They used to be inert decoration; the only thing they lacked was
    // this.
    var hit = null;
    var home = false;
    var standing = player.level.getBlock(px, py, pz);
    var bid = standing ? '' + standing.id : '';
    if (bid.indexOf('hub:portal_') === 0) {
      var target = bid.substring(11);
      if (target === 'hub') { home = true; } else { hit = target; }
    }

    if (home) {
      if (cooldown[key] && ticks - cooldown[key] < COOLDOWN) return;
      cooldown[key] = ticks;
      event.server.runCommandSilent('execute as ' + key + ' at ' + key + ' run hub');
      return;
    }
    if (!hit) return;
    if (cooldown[key] && ticks - cooldown[key] < COOLDOWN) return;
    enter(event, player, hit);
  });
})();
