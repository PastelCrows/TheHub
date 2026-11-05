# Smoke test

Updated 2026-11-05. Covers every instance. Replaces the older ad-hoc lists.

**The rule this list exists to enforce:** validation proves a dependency graph closes, and the
title screen proves mods construct. Neither proves a world loads. Both P0 bugs in the last round
lived in that gap. So **every instance has a world-creation gate, and it comes before anything
else.**

Mark each line pass / fail / skipped. A fail is more useful than a guess — paste the log line.

---

## 0. Gate: does a world load at all?

Do this first for every instance. If it fails, stop testing that instance and report — nothing
after it is meaningful.

| Instance | World creates | First minute without crash | Notes |
|---|---|---|---|
| The Hub | ☐ | ☐ | Chunky removed; was `IllegalStateException: Chunky is not loaded` |
| Cobblemon NeoForge | ☐ | ☐ | EMI stack removed; was a 6,218-NPE loop. Watch for `hubtmfilter removed 17 of … TMs` in the log — that is the TM filter proving itself |
| Skyblock | ☐ | ☐ | |
| Caveblock | ☐ | ☐ | |
| Oceanblock | ☐ | ☐ | Expect an atoll, **not** a survival spawn |
| Netherbound | ☐ | ☐ | Expect a nether start, **not** void-on-a-tree |
| One Block | ☐ | ☐ | reported fine previously |
| One Chunk | ☐ | ☐ | |
| Lost Cities | ☐ | ☐ | Expect **cities** |
| Survival | ☐ | ☐ | reported fine previously |
| The Gauntlet | ☐ | ☐ | |
| Horror | ☐ | ☐ | **crashes on launch** — expected to fail until diagnosed |
| Creative Forge | ☐ | ☐ | reported fine |
| Creative Modern | ☐ | ☐ | reported fine |
| Creative Maximum | ☐ | ☐ | also: does the content actually appear? |
| Knock-off HermitCraft | ☐ | ☐ | reported fine |

---

## 1. Starting kits — the `count` fix

Fixed but unplayed. Open the starting chest and check quantities, which should now be:

| Instance | Expected |
|---|---|
| Caveblock | oak_log **4**, oak_sapling **4**, dirt **16**, ice **2**, lava_bucket 1, torch **32**, wheat_seeds **4**, bone_meal **16**, bread **8** |
| Skyblock | ice 1, lava_bucket 1, sand **32**, melon_slice 1, pumpkin_seeds 1, sugar_cane 1, cactus 1, bamboo 1, obsidian **10** |
| One Chunk | oak_sapling **4**, lava_bucket 1, torch **32**, wheat_seeds **4**, bone_meal **16**, bread **8**, obsidian **10**, dirt **16** |
| Oceanblock | atoll chest, counts as authored |

☐ Any chest still showing 1 of everything → the fix didn't take; say which instance.

---

## 2. Known-open bugs — confirm they're still broken (or quietly fixed)

| Item | Instance | Check |
|---|---|---|
| No ores anywhere | Caveblock | ☐ dig out and look; also check if ore features are present at all |
| Phantom advancements on first block placed | all except The Hub | ☐ place one block, watch for 2 unearned advancements |
| No coliseum | The Gauntlet | ☐ |
| Not cities | Lost Cities | ☐ |
| Void start on a tree | Netherbound | ☐ |
| Survival spawn instead of atoll | Oceanblock | ☐ |
| Crash on launch | Horror | ☐ attach the crash report |

---

## 3. Cross-instance parity

| Check | |
|---|---|
| Each standalone has the Hub's shaders for its own gamemode | ☐ |
| Each standalone has the Hub's texture packs for itself | ☐ |
| Every instance has a custom icon in Prism | ☐ |
| Main menu matches the intended design | ☐ |

---

## 4. The Hub specifically

Still largely unplayed. These have never been confirmed in game:

| Check | |
|---|---|
| Hub lobby spawns correctly | ☐ |
| All 11 portal blocks transit to the right pocket | ☐ |
| Return portal in each pocket goes home | ☐ |
| Crafting gate blocks a denied recipe (watch for `crafting gate LIVE:`) | ☐ |
| Quest book shows only the current pocket's chapters | ☐ |
| Lost Cities pocket generates cities | ☐ |
| Distant Horizons LOD renders (and no Chunky crash) | ☐ |
| Five FancyMenu screens render | ☐ |

---

## 5. Cobblemon instance specifically

| Check | |
|---|---|
| `hubtmfilter removed 17 of … TMs` appears on world load | ☐ |
| JEI opens and indexes without freezing | ☐ |
| Pokémon spawn, and spawn variety looks sane | ☐ |
| Creative inventory opens without a long freeze | ☐ *(this is what `kewz-client-perf` would fix — measure before and after)* |
| No mod is missing that you expect from Kewz's pack | ☐ |

---

## How to report

For any fail, the useful thing is:

1. which instance
2. what you did
3. the matching log line, or the crash report path

`latest.log` and `crash-reports/` are both under
`%APPDATA%\PrismLauncher\instances\<name>\minecraft\`.

A fail with a log line is worth more than ten passes.
