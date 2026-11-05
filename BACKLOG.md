# Backlog

Everything outstanding across all instances, with status. Updated 2026-11-05 after the
full-instance test pass.

Status key: **DONE** verified · **FIXED** changed but not yet played · **OPEN** not started ·
**DIAG** cause known, fix not written · **BIG** project-sized

**Standing rule:** any task given and not finished in the same response is written here
immediately. The user drafts tasks elsewhere and deletes them the moment they are sent, so this
file is the only copy. Nothing is "remembered for later" outside it.

---

## P0 — stopped you playing

| # | Item | Status | Notes |
|---|---|---|---|
| 1 | Cobblemon hangs forever on world creation, endless log, eats disk | **FIXED** | EMI NPE-loop. `VanillaPlugin.addRecipeSafe` → `ClientLevel.registryAccess()` before the level exists; Reliable EMI's retry wrapper made one NPE into 6,218. EMI + 5 addons + remi removed; JEI stays. **My fault** — I added EMI alongside JEI and claimed they coexist without testing. |
| 2 | The Hub crashes on world creation | **DONE** | `IllegalStateException: Chunky is not loaded`. Chunky registers its provider in `onServerStarting`, which NeoForge fires AFTER `loadLevel()` — but `loadLevel()` generates the start region, so DH's chunk-load handler calls `ChunkyProvider.get()` first. DH's guard sets `listenerBound = true` *before* the attempt, so it also never retried. **First attempt removed Chunky, which deleted the feature we chose it for — reversed.** Now fixed properly with `hubchunkyfix`: cancels the bind attempt while Chunky is unregistered, so DH retries on the next chunk. Verified A/B on the headless server — control crashes 4×, with the fix `Done (3.570s)!`, 0 occurrences, world created, and DH still logs `Registered mod compatibility accessor for: [chunky]`. |
| 3 | Standalone Horror crashes on launch | **FIXED** | `cave_dweller-1.4-rc2` hard-references `me.fzzyhmstrs.fzzy_config` **46 times** while declaring only neoforge + minecraft. Mod construction failed → Sodium bailed → resource reload failed → recovery screen → `utilitarian` read its config before load → crash. Installed fzzy-config 0.7.7. **Same undeclared-dependency class as Beachparty→Curios.** Verified: reaches the title screen, 0 crash reports. |

**Launcher gotcha found while verifying #3:** a stale `prismlauncher.exe` silently refuses
`--launch` — no log, no `javaw`, which reads exactly like a crash. Kill it and relaunch before
concluding anything from a silent launch.

**The process failure behind #1 and #2:** I verified mods reached the *title screen* and reported
them working. Neither bug is visible there. World creation is a different code path. The smoke
test below now has a world-creation gate for every instance.

---

## P1 — wrong content / wrong world

| # | Item | Status | Notes |
|---|---|---|---|
| 4 | Starting chests give 1 of everything (Caveblock, One Chunk, Skyblock, Oceanblock) | **FIXED** | 1.20.5 renamed item NBT `Count` (byte) → `count` (int); old key silently defaults to 1. **70 stacks across 16 files** — including 8 copies inside The Hub that a narrower scan had missed. Caveblock now gets 4 logs / 2 ice as authored. |
| 5 | Caveblock: no ores spawning anywhere | **OPEN** | Separate from #4. Need to check whether ore features are stripped by the caveblock worldgen or genuinely absent. |
| 6 | Lost Cities standalone "still isn't cities" | **OPEN** | The Hub's `hub:lostcities=default` profile fix was applied to the Hub only. The standalone needs its own profile check. |
| 7 | Nether standalone: void start on top of a tree | **OPEN** | Classic wrong-spawn-structure symptom. |
| 8 | Oceanblock standalone: regular survival spawn | **OPEN** | Island template exists (`atoll.nbt`, chest now fixed) but isn't being used for spawn. |
| 9 | Phantom advancements on first block placed — **every instance except The Hub** | **FIXED** | Your bet was right. `fix_advancements.py` had the Hub's path hardcoded; it now walks every instance. **16 override files across 8 instances** (Caveblock, Creative Forge, Netherbound, Oceanblock, One Block, One Chunk, Skyblock, The Hub). The 7 instances without Cyclic came back genuinely clean. |
| 10 | Gauntlet has no coliseum | **OPEN** | `tools/build_coliseum.py` exists — likely never run against the instance, or its output isn't loaded. |

---

## P2 — parity between instances

| # | Item | Status | Notes |
|---|---|---|---|
| 11 | No standalone has the Hub's shaders or texture packs | **OPEN** | Each standalone should at least match the Hub's version of itself. |
| 12 | Custom instance icons for every instance | **OPEN** | Brand assets exist (`tools/build_brand_assets.py`); need one icon per instance + set in Prism. |
| 13 | Vanilla-style main menu with a rotating still of the hub | **OPEN** | FancyMenu layouts already authored; this is a different, simpler direction than the current gothic hall. |
| 14 | Knock-off HermitCraft: Faithful64 layered on top + shaders | **OPEN** | Needs a coverage check that Faithful64 exists for its MC version. |
| 15 | Creative Maximum: confirm all content actually loads | **OPEN** | Validates clean; "a lot of content" unverified in play. |

---

## P3 — Cobblemon parity (ongoing)

| # | Item | Status | Notes |
|---|---|---|---|
| 16 | His 27 datapacks | **DONE** | 1,533 files ported. |
| 17 | His 8 no-compile recompiles | **DONE** | 4 as a datapack, 4 as repackaged `mod-ports/` jars. |
| 18 | 20 mods he runs that the hash-based gap measurement was blind to | **DONE** | Found by comparing modIds instead of hashes. |
| 19 | `hubtmfilter` (his `kewz-tm-filter`) | **DONE** | Verified end-to-end on the headless server: removed 17 of 704, exactly the static prediction. |
| 20 | `hubworldgenfix` (his `kewz-worldgen-compat`) | **SHELVED** | Built, not installed. The malformation is real in 4 files but inert through template load *and* full jigsaw assembly. See `mod-src-cobblemon-wg/UNPROVEN.md`. |
| 21 | `kewz-client-perf` — mixin 1 of 6: `NonNullList.clear()` | **DONE** | The headline fix. Vanilla is genuinely O(n²): `clear()` with a null default calls `AbstractList.clear()` → `removeRange` → one-at-a-time removal, each shifting the backing ArrayList. **Measured: 56× at n=1,000, 235× at 50,000, 725× at 100,000.** Shipped as `hubclientperf`, installed in all 13 NeoForge instances. Both of his guards kept (`defaultValue == null`, exact-class check) and why they matter is written into the source. |
| 21a | `kewz-client-perf` mixins 2–3: Cobblemon texture-exists cache | **OPEN** | `ClientDistributionUtilsKt.exists(ResourceLocation)` at HEAD+RETURN with a cache, plus `ReloadableResourceManager.createReload` at RETURN to invalidate it. Cobblemon-specific; needs its own optional mixin config. |
| 21b | `kewz-client-perf` mixins 4–5: ETF NBT tick cache | **OPEN** | `EtfNbtTickCacheMixin` + `MinecraftTickMixin`, in his optional `etf` config. ETF is installed here. |
| 21c | `kewz-client-perf` mixin 6: Xaero VRAM query | **OPEN** | `XaeroVramQueryMixin`, his optional `xaero` config. Xaero's is installed here. |
| 21d | Verify the perf win in game | **OPEN** | Client-side, so the headless harness cannot measure it. Needs a before/after on opening the creative inventory in the Cobblemon pack. |
| 22 | Remaining 13 of his originals | **OPEN** | 2 are moot (Atmospherics, Subtle Effects absent); 1 he hasn't finished himself (`native-tm-teaching`, "Runtime validation pending"). |
| 23 | His 33 code recompiles | **OPEN** | The long pole. |

---

## P4 — the region project

| # | Item | Status | Notes |
|---|---|---|---|
| 24 | 11 regions, each **exact** to its game counterpart, scaled up huge for Minecraft | **BIG** | Confirmed shape: normal worldgen fills the blank space between regions; ocean separates each region into its own continent. To be built with a **Minecraft world-map design application**, not hand-placed. Needs: pick the tool, establish a scale factor, source canon region maps, decide how authored terrain and generated terrain meet at the coastlines. |
| 25 | Region-locked spawns | **OPEN** | Generated, not authored — `gen1` label is exactly 151 = Kanto. Cheapest real step and already specified. |
| 26 | Region hub with 11 overworld teleports | **OPEN** | Same-world teleports, not portals — continents stay reachable by boat/flight. |
| 27 | Mystery Dungeon as a pocket *inside* the Pokémon pocket | **OPEN** | The only piece needing real dimension machinery. |
| 28 | Gyms / Elite Four / champions / legendary quests | **BIG** | RCT + Rad Gyms + Cobblemon Quests are installed. |

**Established about his world:** he has **no custom biome set** (zero custom biome definitions;
his whole biome footprint is two tag bugfixes), and his saves folder is empty — the 11-region map
is server-side on `kewz.modded.fun` and cannot be read from the client. The world is ours to
design either way, which he has confirmed is the plan: migrate to his later.

---

## Tooling built along the way

| Tool | What it does |
|---|---|
| `tools/test_server.py` | Headless NeoForge server: generates worlds, resolves missing deps from the loader's own error messages, runs commands via a `minecraft:load` datapack function. **This is how world-load behaviour gets tested without a GUI.** |
| `tools/fix_stack_counts.py` | Finds and fixes pre-1.20.5 `Count` keys in any structure NBT, instance-wide. |
| `tools/build_mod.py` | Profiles: `pocketquests`, `hubtmfilter`, `hubworldgenfix`. Classpath resolved from Prism's meta cache, never globbed. |
| `tools/validate_instance.py` | Dependency/conflict validation. Keeps the highest provided version; strips embedded game versions when comparing. |
| `tools/cobblemon_gap.py` | Gap vs his pack, with per-version verification and Connector-requiring builds counted as unavailable. |
| `tools/repack_kewz_mods.py` | Replays his data/asset edits onto our NeoForge jars (removals a datapack cannot express). |
| `tools/test_server.py --profile` | Named profiles (`tm`, `chunky`, `chunky-control`) each with their own source instance, seed set and world — so a fix can be proven by running the pair with and without it. |
| `tools/find_undeclared_deps.py` | Catches the bug class that has now broken two instances: a mod that USES a library it never DECLARES. Parses class constant pools, so it sees what a mod actually calls rather than what it claims. Validated against the real case — it flags cave_dweller→fzzy_config (46 refs, 0 declarations). |

## Standing lesson

Validation proves a dependency graph closes. The title screen proves mods construct. **Neither
proves a world loads.** Both P0 bugs lived in the gap between those, and both were mine.

---

## Tool debt

| # | Item | Status | Notes |
|---|---|---|---|
| 29 | `test_server.py` reuses a world across different seed sets | **OPEN** | Caused 37 bogus "Unknown biome" errors when the `tm` profile ran against a world generated while extra biome mods were present. Worked around by deleting the world; should delete it automatically when the seed set changes. |
| 30 | `hubworldgenfix` still shelved | **OPEN** | See `mod-src-cobblemon-wg/UNPROVEN.md`. Now that `--profile` exists, a `worldgen` profile could retry the jigsaw path properly. |

## Process notes earned the hard way

1. **Validation proves a graph closes. The title screen proves mods construct. Neither proves a
   world loads.** Both Cobblemon's hang and The Hub's crash lived in that gap.
2. **A mod chosen for a feature is not "unused" because nothing declares it.** Removing Chunky
   to stop a crash deleted the LOD pre-render it was installed for. Fix the interaction.
3. **A stale `prismlauncher.exe` refuses `--launch` silently** — no log, no `javaw`, reads as a
   crash.
4. **Measure before porting.** `hubtmfilter` predicted 17 and found 17. `hubclientperf` was
   benchmarked at 235×. `hubworldgenfix` could not be shown to fix anything and is shelved.
