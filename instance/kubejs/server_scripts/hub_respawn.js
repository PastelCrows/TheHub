// NOTE: IIFE - KubeJS server scripts share one global scope.
(function () {
// Respawn belongs to the pocket you died in.
//
// Vanilla always respawns you at minecraft:overworld's world spawn, and `setworldspawn`
// cannot point at another dimension - which is why every death dropped you on that tree
// regardless of where you were. The only fix is to move the player after respawn.
//
// Dying in a pocket returns you to that pocket. Dying anywhere else returns you to the hub.
// A bed or respawn anchor still wins, because this only fires when vanilla sent you to the
// overworld, which is exactly the "no valid spawn point" case.

  console.info('[hub] respawn handler loaded');

  var HUB = 'hub:hub';

  function send(server, who, name) {
    if (name === 'skyblock')    { server.runCommandSilent('execute in hub:skyblock run tp '   + who + ' 2 67 1'); return; }
    if (name === 'caveblock')   { server.runCommandSilent('execute in hub:caveblock run tp '  + who + ' 1 61 1'); return; }
    if (name === 'oceanblock')  { server.runCommandSilent('execute in hub:oceanblock run tp ' + who + ' 1 67 1'); return; }
    if (name === 'onechunk')    { server.runCommandSilent('execute in hub:onechunk run tp '   + who + ' 1 86 1'); return; }
    if (name === 'survival')    { server.runCommandSilent('execute in hub:survival run tp '   + who + ' 0 250 0');
                                  server.runCommandSilent('execute in hub:survival run spreadplayers 0 0 0 200 false ' + who); return; }
    if (name === 'lostcities')  { server.runCommandSilent('execute in hub:lostcities run tp ' + who + ' 0 250 0');
                                  server.runCommandSilent('execute in hub:lostcities run spreadplayers 0 0 0 200 false ' + who); return; }
    // respawn inside the Coliseum, where the runs happen
    if (name === 'gauntlet')    { server.runCommandSilent('execute in hub:gauntlet run tp ' + who + ' 0 65 19'); return; }
    if (name === 'oneblock')    { server.runCommandSilent('execute in hub:oneblock run tp ' + who + ' 0 65 0'); return; }
    if (name === 'horror')      { server.runCommandSilent('execute in hub:horror run tp '   + who + ' 0 250 0');
                                  server.runCommandSilent('execute in hub:horror run spreadplayers 0 0 0 200 false ' + who); return; }
    if (name === 'netherbound') { server.runCommandSilent('execute in hub:netherbound run tp ' + who + ' 0 250 0');
                                  server.runCommandSilent('execute in hub:netherbound run spreadplayers 0 0 0 200 under 100 false ' + who); return; }
    server.runCommandSilent('execute in ' + HUB + ' run tp ' + who + ' 3 65 3');
  }

  PlayerEvents.respawned(event => {
    var player = event.player;
    if (!player) return;
    var server = player.server;
    var who = '' + player.username;
    var pocket = '' + player.persistentData.getString('lastPocket');

    // a short delay: vanilla finishes placing the respawned player first
    event.server.scheduleInTicks(10, () => {
      var where = ('' + player.level.dimension);
      // if something already put them in a pocket (bed, anchor), leave it alone
      if (where.indexOf('hub:') !== -1 && where.indexOf(HUB) === -1) return;
      send(event.server, who, pocket);
      if (pocket && pocket !== 'null' && pocket !== '') {
        player.tell(Text.gold('Respawned in ' + pocket + '.'));
      } else {
        player.tell(Text.gold('Respawned in the hub.'));
      }
    });
  });
})();
