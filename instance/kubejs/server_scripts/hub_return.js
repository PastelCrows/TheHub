// NOTE: wrapped in an IIFE because KubeJS server scripts share a single global
// scope - top-level `const` in two files collides and kills the second one.
(function () {
// Getting BACK to the hub.
//
// The travel pads are one-way: hub -> pocket. Dimension Link wires portals inside a pocket
// but has no concept of the hub, so without this you would be stranded in whichever pocket
// you stepped into.
//
// Three ways back, deliberately overlapping so none of them being broken strands you:
//   /hub            works from anywhere, any dimension
//   world spawn     set to the hub, so dying and respawning returns you there
//   /pockets        lists the pocket ids, in case you want to /execute in one manually

const HUB_DIM = 'hub:hub';
// The hub platform's floor is world y 64, so you stand at y 65. (3,65,3) is plain
// platform - not on top of a pad, which would re-trigger a pad on arrival.
const HUB_X = 3, HUB_Y = 65, HUB_Z = 3;

const POCKETS = [
  'skyblock', 'survival', 'caveblock', 'netherbound',
  'oceanblock', 'lostcities', 'onechunk', 'gauntlet'
];

ServerEvents.commandRegistry(event => {
  const { commands: Commands } = event;

  event.register(
    Commands.literal('hub').executes(ctx => {
      const player = ctx.source.player;
      if (!player) return 0;
      ctx.source.server.runCommandSilent(
        `execute in ${HUB_DIM} run tp ${player.username} ${HUB_X} ${HUB_Y} ${HUB_Z}`);
      player.tell(Text.gold('Returned to the hub.'));
      return 1;
    })
  );


  event.register(
    Commands.literal('hubdebug').executes(ctx => {
      const player = ctx.source.player;
      if (!player) return 0;
      let x = player.x, gx = (typeof player.getX === 'function') ? player.getX() : 'n/a';
      player.tell(Text.gold('--- hub debug ---'));
      player.tell(Text.white('player.x = ' + x + '   getX() = ' + gx));
      player.tell(Text.white('typeof player.x = ' + (typeof player.x)));
      player.tell(Text.white('player.level.dimension = ' + player.level.dimension));
      player.tell(Text.white('String(...) = ' + String(player.level.dimension)));
      const fx = Math.floor(player.x), fy = Math.floor(player.y), fz = Math.floor(player.z);
      player.tell(Text.white('floored = ' + fx + ' ' + fy + ' ' + fz));
      player.tell(Text.white('y in range 65-68 = ' + (fy >= 65 && fy <= 68)));
      player.tell(Text.gray('An arch matches when |dx|<=1 AND |dz|<=1 of its doorway.'));
      return 1;
    })
  );

  // array, not an object - object `for...in` does not iterate under KubeJS's Rhino
  event.register(
    Commands.literal('pockets').executes(ctx => {
      const player = ctx.source.player;
      if (!player) return 0;
      player.tell(Text.gold('Pockets: ') .append(Text.white(POCKETS.join(', '))));
      player.tell(Text.gray('Each has its own nether and end. /hub returns you here.'));
      return 1;
    })
  );
});

// Respawn in the hub rather than wherever the pocket decides.
ServerEvents.loaded(event => {
  event.server.scheduleInTicks(60, () => {
    event.server.runCommandSilent(
      `execute in ${HUB_DIM} run setworldspawn ${HUB_X} ${HUB_Y} ${HUB_Z}`);
  });
});

})();
