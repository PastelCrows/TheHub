// NOTE: wrapped in an IIFE because KubeJS server scripts share a single global
// scope - top-level `const` in two files collides and kills the second one.
(function () {
// Per-pocket placement restrictions.
//
// Recipes CANNOT be gated per dimension - they resolve globally at datapack load, and the
// mods that used to do it (GameStages / RecipeStages) do not exist on 1.21.1. What IS
// enforceable is placement and use, which is the thing that actually breaks a premise:
// the problem is not that a sieve recipe exists in JEI, it is a sieve running in the
// Lost Cities.
//
// Keep this list SURGICAL. Banning a whole mod from a pocket reads as arbitrary; banning
// the two or three specific premise-breakers reads as design.

const DENY = {
  // Scavenging is the premise. Sieving matter out of gravel and growing iron as a crop
  // both bypass the entire point of looting a ruined city.
  'hub:lostcities': {
    match: id => id.startsWith('exdeorum:') || id.startsWith('mysticalagriculture:'),
    reason: 'Nothing grows or sifts in the Lost Cities. Take what the city left behind.'
  },
  // Gear should come out of runs, not out of a farm.
  'hub:gauntlet': {
    match: id => id.startsWith('mysticalagriculture:'),
    reason: 'No resource farms in the Gauntlet. Earn it in the arena.'
  },
  // The hub is a lobby, not a world. No portals, no bases, no ninth pocket by accident.
  'hub:hub': {
    match: id => id === 'minecraft:obsidian' || id === 'minecraft:end_portal_frame',
    reason: 'The hub is a lobby. Step onto a pad to go somewhere.'
  }

  // Every other pocket is deliberately unrestricted:
  //   onechunk  - scarcity IS the premise; escaping it legitimately is the whole pack
  //   caveblock / oceanblock / skyblock - Ex Deorum is load-bearing in all three
  //   netherbound - its gate is physics (no water, so no obsidian), already airtight
  //   survival  - the baseline
};

BlockEvents.placed(event => {
  const rule = DENY[event.level.dimension];
  if (!rule) return;
  const id = String(event.block.id);
  if (!rule.match(id)) return;
  event.cancel();
  if (event.player) event.player.tell(Text.red(rule.reason));
});

})();
