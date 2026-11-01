# mod-ports

Repackaged NeoForge jars that carry Kewz's content decisions.

These are not new mods and not recompiles. Each one is the **upstream NeoForge jar** of a mod,
with his `data/**` and `assets/**` edits applied - files he deleted, deleted; files he changed,
changed; files he added, added. No class is touched, no mixin config, no mod metadata. Built by
`tools/repack_kewz_mods.py`, which reads his Fabric jar, diffs it against the upstream Fabric
release it was built from, and replays that diff onto our NeoForge jar.

## Why a jar and not a datapack

A datapack can override a file inside a mod jar. It cannot delete one. These four recompiles are
mostly deletions - his `strip1`, `nomodel1` and `newonly1` tags - which is how he resolves
collisions between overlapping fakemon packs: two packs shipping the same species, or one
shipping a model a better pack also provides. There is no way to express a deletion as data, so
the jar itself has to change. That is why he recompiles rather than writing a datapack, and the
only honest way to reproduce it is to repackage.

His other data-only edits DID become a datapack - `kewz-dex-fixes-ported.zip`, 86 JSON files -
because they are pure overrides with no deletions.

## What is here

| jar | removals | overrides | additions |
|---|---|---|---|
| SpaceworldMons-4.0.1-1.21.1+hub | 242 of 242 | 27 | 55 |
| cobblemon-journey-mounts-1.7.2+hub | 31 of 31 | 279 | 0 |
| cobblemon-horizon-mons-1.1.1+hub | 26 of 26 | 8 | 0 |
| silents-minemons-4.6.1+hub | 25 of 29 | 5 | 1 |

The `+hub` suffix exists so one of these is never mistaken for an upstream release.

**silents-minemons is 25 of 29 on purpose.** His edit targeted 4.4.2; ours is 4.6.1, and four of
the species he deleted no longer exist upstream - they were removed or renamed between those
versions. Those four are reported and skipped rather than ignored, because a removal list that
quietly matches nothing looks like success while changing nothing.
