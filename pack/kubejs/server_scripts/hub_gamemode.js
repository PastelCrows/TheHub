// NOTE: wrapped in an IIFE - KubeJS server scripts share one global scope.
(function () {
// Creative in the hub AND in redstone land; survival in every pocket dimension and
// all of their real dimensions.
//
// Rewritten to depend on almost no KubeJS API. The previous version used `player.age`,
// which is not a binding - `undefined % 10 !== 0` is NaN !== 0, which is TRUE, so every
// call returned immediately and the script did nothing while reporting "loaded, 0 errors".
// That is the worst kind of bug, so this version owns its own counter and asks the GAME
// about the dimension via `execute if dimension`, rather than trusting a property name.

  // Two creative dimensions, not one: the hub (master dimension) and redstone land, a
  // strictly-creative flat stone sandbox for building and testing machines.
  const HUB = 'hub:hub';
  const REDSTONE = 'hub:redstone';
  const EVERY = 20;          // ticks
  let ticks = 0;

  PlayerEvents.tick(event => {
    ticks = ticks + 1;
    if (ticks % EVERY !== 0) return;

    const player = event.player;
    if (!player) return;
    const name = player.username;
    const server = event.server;

    // Only fires when the mode is actually wrong, so it costs nothing in the common case
    // and never spams. Spectator is left alone on purpose.
    server.runCommandSilent(
      `execute as ${name} at @s if dimension ${HUB} unless entity @s[gamemode=creative] ` +
      `unless entity @s[gamemode=spectator] run gamemode creative ${name}`);

    server.runCommandSilent(
      `execute as ${name} at @s if dimension ${REDSTONE} unless entity @s[gamemode=creative] ` +
      `unless entity @s[gamemode=spectator] run gamemode creative ${name}`);

    // survival anywhere that is neither creative dimension
    server.runCommandSilent(
      `execute as ${name} at @s unless dimension ${HUB} unless dimension ${REDSTONE} ` +
      `unless entity @s[gamemode=survival] unless entity @s[gamemode=spectator] ` +
      `run gamemode survival ${name}`);
  });
})();
