// NOTE: wrapped in an IIFE because KubeJS server scripts share a single global
// scope - top-level `const` in two files collides and kills the second one.
(function () {
// The world spawn lives in minecraft:overworld, which is NOT the hub - the hub is its own
// dimension because a world_preset override cannot apply through KubeJS (presets are read
// at world creation, before the virtual pack exists).
//
// So: anyone who logs in outside a pocket gets moved to the hub. Done on a short delay so
// the hub room has been placed first.

const HUB_DIM = 'hub:hub';
const HUB_X = 3, HUB_Y = 65, HUB_Z = 3;

PlayerEvents.loggedIn(event => {
  const player = event.player;
  const dim = String(player.level.dimension);
  // already somewhere intentional? leave them alone
  if (dim === HUB_DIM || dim.startsWith('hub:')) return;

  event.server.scheduleInTicks(40, () => {
    event.server.runCommandSilent(
      `execute in ${HUB_DIM} run tp ${player.username} ${HUB_X} ${HUB_Y} ${HUB_Z}`);

    // The hub is a creative lobby, so it starts empty. Mods that hand out a starting item
    // in void worlds (Ex Deorum's torch and watering can) would otherwise follow you in.
    // Once only - never touches an inventory you have actually built up.
    if (!player.persistentData.getBoolean('hubCleared')) {
      player.persistentData.putBoolean('hubCleared', true);
      event.server.runCommandSilent(`clear ${player.username}`);
    }
    player.tell(Text.gold('Welcome to the hub.'));
  });
});

})();
