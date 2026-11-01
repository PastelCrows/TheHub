# Performance pass

## The hardware decides everything here

Measured, not assumed:

| | |
|---|---|
| CPU | **AMD Ryzen 7 2700** — Zen+, 2018. 8c/16t, 3.2 GHz base |
| RAM | **32 GB**, fixed 10 GB heap (`MinMemAlloc = MaxMemAlloc = 10240`) |
| GPU | **RTX 3050, 4 GB VRAM** |
| Disk | WD_BLACK SN770 NVMe |

Two of those shape every decision below.

**The CPU is the TPS ceiling.** The Ryzen 2700 has plenty of cores but weak single-thread
throughput by modern standards, and Minecraft's server thread is single-threaded. So server-tick
savings are worth more in this pack than anywhere else, and extra cores buy little.

**4 GB of VRAM is the real constraint** — and it just took on 64x vanilla textures plus a
shaderpack in every pocket dimension. Anything that spends VRAM is the wrong direction, which is
why one popular "performance" mod is refused outright below.

RAM is comfortable. 10 GB of a 32 GB machine, with 16 GB free at idle, is not over-committed, so
there is nothing to win by changing the heap.

## What was already here

The pack was already close to saturated on optimisation mods. An early grep of mine understated
this list and it is worth recording in full so the next pass does not re-tread it:

Sodium · Sodium Extra · Sodium Extras · Sodium Options API · Sodium Dynamic Lights · Iris ·
Lithium · ModernFix · FerriteCore · EntityCulling · MoreCulling · ImmediatelyFast ·
BadOptimizations · Dynamic FPS · Noisium · Clumps · Particle Core · Alternate Current ·
Leaves Be Gone · Better Block Entities · Better Beds · Modern UI · Chunky · Spark

So the headroom was in **configuration**, not in more jars, and the additions below are a short
list by design.

## Added — four jars

| Mod | Why, for this machine | Risk |
|---|---|---|
| **Let Me Despawn** 1.3.2 | Mob despawn tuning. Server tick, where the CPU is the ceiling. | release, 83 KB, **zero dependencies** |
| **AI Improvements** 0.5.3 | Vanilla mob AI goal-selector tuning. Again server tick. | release, 30 KB |
| **Packet Fixer** 3.3.1 | Raises packet/NBT size limits — 251 mods make a very large registry sync. | release |
| **Remove Reloading Screen** 5.0.11 | Resource packs reload **in the background**. Directly shortens the `PocketSkins` texture-swap pause. | **beta** — the one risk here |

Two notes on those.

**Let Me Despawn needed a version downgrade, and the validator caught it.** The current build
(1.26.10.2) requires two libraries, `almanac` and `dungeonconfig` — `validate_instance.py`
reported `missing required: 2` immediately. Pulling in two library jars for a despawn tweak is a
bad trade, and version **1.3.2** does the same job with zero dependencies. That is the one
installed.

**RRLS was installed, then removed on 2026-10-31 — and the reason is worth keeping.** It made
`reloadResourcePacks()` non-blocking by hiding the loading overlay entirely
(`hideOverlays = "ALL"`) and drawing a small progress line over the still world instead. That
worked exactly as advertised, and it is precisely why the texture swap was reported as *"laggy"*
and *"stuttery"*: for eighty to a hundred seconds the world sat there looking frozen, with no
screen saying otherwise. Its progress message was still the shipped placeholder, `Edit in
config!`.

The replacement is the opposite bet. DrippyLoadingScreen renders a branded loading screen for
that same moment, which means the pause is visibly a pause. RRLS hides the screen Drippy draws,
so the two cannot both be installed — this is a straight trade of *invisible but non-blocking*
for *blocking but legible*, and legible won. If that turns out to be the wrong call in play, the
reverse is one jar each way; `add_performance_mods.py` still carries the entry as a comment.

The `reloading` flag in `PocketSkins` is the real re-entrancy guard, not the loading-overlay
check, so neither choice affects the gate.

## A second pass, 2026-10-31 — from a launch, not from guesses

The pack was launched to the title screen and closed. 102 seconds from process start to the menu
with no world loaded: 50s of mod loading, then 52s of the first resource reload. The log was then
read rather than theorised about.

**Four ModernFix options turned on.** Its config file lists every option with its shipped
default, so these were read, not guessed:

| option | why this pack specifically |
|---|---|
| `perf.deduplicate_location` | 294 modIds worth of ResourceLocation objects, mostly duplicates |
| `perf.deduplicate_climate_parameters` | 32 dimensions through TerraBlender, Terralith, Tectonic and Biolith |
| `bugfix.skip_redundant_saves` | the log saves **every one of 30-odd levels** on each autosave |
| `bugfix.packet_leak` | a known packet leak; this pack already needed PacketFixer for registry-sync size |

**Three left off on purpose.** `perf.faster_item_rendering` is a real FPS win and the single most
likely thing to break a pack with this many custom item renderers (Apotheosis, Sophisticated\*,
Create, AE2, JEI overlays) — worth trying as its own test, not folded into a change meant to be
safe. `perf.dynamic_entity_renderers` has the same shape of risk. `stability_level=BETA` is not
something to put on an untested pack.

**The biggest remaining lever is `renderDistance`, and it is not mine to pull.** It sits at **20**,
which is high for 254 mods and shaders on an RTX 3050, and it is the one setting
`tune_settings.py` explicitly refuses to touch — the previous pass listed it under "settings we
must NOT have disturbed" because it is a look-of-the-game choice, not a config value. Dropping it
to 14–16 would be the largest single FPS change available and would directly shorten the
"laggy while initial chunks are loading" complaint. Everything around it is already tuned down:
`simulationDistance 8`, `entityDistanceScaling 0.75`, `entityShadows false`, `particles 1`,
`mipmapLevels 2`.

**Sound Physics Remastered is enabled** and raytraces reverb per sound. `evaluate_ambient_sounds`
is already off, which is the expensive half. On an eight-core Ryzen 2700 the rest is noticeable
but not dominant, and it is doing real work in the horror pocket — flagged, not changed.

**Not worth chasing:** 256 `missing model for variant` warnings and 31 unloadable models. They
are upstream bugs in Industrial Foregoing's `latex` fluid (160), Cyclic's fluids (96) and a few
mods referencing models under the wrong namespace. They cost log noise at load, not frames.

## Distant Horizons — and a refusal that rested on a wrong number

The first performance pass refused Distant Horizons for "VRAM on 4GB". **The card has 8 GB.**
`Win32_VideoController.AdapterRAM` is a 32-bit field that saturates at 4 GB, so it reports 4 for
any card with 4 or more; `nvidia-smi` and the driver registry both say 8192 MiB. The refusal was
made on an artefact of how Windows reports VRAM.

**What was actually wanted:** the Cobblemon server's look, where a huge portion of the world is
visible at once. That is **Voxy**, and Voxy is Fabric-only — Kewz runs
`voxy-0.2.19-beta+1.21.1-fabric`, and Modrinth lists no NeoForge build at any version. Distant
Horizons is the NeoForge equivalent of the idea: `DistantHorizons-3.3.3-1.21.1-fabric-neoforge`,
release, no dependencies.

**Render distance was never the lever for this.** It renders *real* chunks — full geometry,
lighting, block entities, ticking — so raising it multiplies the cost of everything. An LOD mod
renders a cheap approximation of terrain far beyond it. Wanting the Voxy look and reaching for
`renderDistance` is reaching for the expensive half of the effect.

**Shader support is not optional and it is not universal.** DH only renders through shaders
"built with DH support in mind". Checked by looking inside the zips for `dh_terrain` / `dh_water`
programs rather than trusting a compatibility list:

| shaderpack | dh_ programs |
|---|---|
| BSL, Complementary Reimagined, Complementary Unbound, MakeUp UltraFast, Spooklementary | yes |
| **Nostalgia v5.1** | **no** — and it is the only 1.21.1 build there is |

Nostalgia was survival's and oceanblock's, so those two would have had no distant terrain at all,
silently. Both moved to **Complementary Unbound**, which was already installed, already unused,
already pinned motion-blur-off and already in the pack. Nostalgia stays shipped; swapping back is
one line of `pocketskins.json`. `verify_skins.py` now fails if any shader in use lacks `dh_`.

**The cost worth knowing before the next session.** DH builds its LOD database by exploring, and
stores it per world and per dimension. A pack where a fresh world gets made for most tests sees
almost none of the benefit — the LODs are rebuilt from nothing every time. This is the first
thing in the backlog that genuinely argues for settling on a world worth keeping.

DH ships no config until it has run once, so it is deliberately unconfigured, the same as the
splash screen was.

## Refused — and the judgement matters more than the download counts

| Mod | Downloads | Why not |
|---|---|---|
| **ScalableLux** | 16.7M | A Starlight-derived **lighting engine**, and the only NeoForge 1.21.1 build is an *alpha devbuild*. Replacing the lighting engine is exactly the change that can corrupt light data across 32 dimensions. Not worth some chunk-load time in a pack being actively played. Revisit at release. |
| **Distant Horizons** | 38.9M | An LOD renderer that **raises** total VRAM, with experimental Iris compatibility. On a 4 GB card already running 64x textures plus shaders this is the wrong direction entirely. |
| **Embeddium** | 38.5M | A direct alternative to Sodium; the two conflict. Sodium is already here. |
| **Chloride** | 19.7M | A fourth Sodium add-on on top of three. Marginal gain, more surface to break. |

## Changed — three client settings

| Setting | Was | Now | Effect |
|---|---|---|---|
| `simulationDistance` | 10 | **8** | The biggest server-tick lever. Ticking chunks scale with the square of the distance, so this is about a third fewer chunks ticking entities, block entities and random ticks. **No visual change** — render distance stays at 12. |
| `mipmapLevels` | 4 | **2** | Texture memory, on a 4 GB card now running 64x vanilla textures beside 247 mods' worth of 16x. Level 2 still keeps enough of the chain to stop distant shimmer. |
| `entityShadows` | true | **false** | The vanilla blob shadow under every entity. With a shaderpack on in every dimension the shader draws real shadows anyway, so this is close to visually free. |

`renderDistance` (12), `entityDistanceScaling` (0.75) and `particles` (decreased) were already
sensible and are asserted unchanged. Applied by `tools/tune_settings.py`, which keeps a
`.prehubtune` backup and **refuses to run while the game is open** — Minecraft rewrites
`options.txt` on exit and would undo the edit, exactly as NeoForge does with its configs.

## The JVM args are already right

```
-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200
-XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC
-XX:G1NewSizePercent=40 -XX:G1MaxNewSizePercent=50 -XX:G1HeapRegionSize=16M
-XX:G1ReservePercent=15 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4
-XX:InitiatingHeapOccupancyPercent=20 -XX:G1MixedGCLiveThresholdPercent=90
-XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32
-XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1
```

This is the standard Aikar flag set, and min heap equals max heap so G1 never resizes. Nothing
here needs changing. `-XX:+AlwaysPreTouch` is the usual next suggestion and is **deliberately not
added**: it pre-faults the whole 10 GB at startup, and launch time is already a sore point.

## Opt-in levers, not applied

Each of these is a real gain with a real cost, so they are yours to call rather than a silent
edit. All are one-line changes.

| Lever | Gain | Cost |
|---|---|---|
| `entityculling.json` → `"safeMode": false` | Moves entity-data extraction off the render thread onto the async culling thread — a genuine FPS win. Verified in `CullTask`: it extracts there only when `!safeMode`, and on the client tick when `safeMode`. | Can race with the entity list. The mod author defaults it **on** for exactly that reason, and this pack has 251 mods' worth of entities. |
| `options.txt` → `graphicsMode:0` (Fast) | Solid GPU win. | Visibly changes clouds, leaves and water — and matters much less with shaders on. |
| `sodium-options.json` → `"leaves_quality": "FAST"` | Opaque leaves, fewer faces drawn. | Visual change, and Leaves Be Gone + MoreCulling already cover much of this. |
| `entityculling.json` → `"solidLeaves": true` | Leaves occlude, so more entities get culled behind foliage. | Visual side effects on leaf rendering. |
| **Faithful 64x → 32x** | Quarters the vanilla atlas. | This is the lever to pull **first** if VRAM stutter appears — but not pre-emptively, since 64x was the point. |

## Measure it rather than trust this document

**Spark is already installed**, which means none of the above has to stay a guess:

- `/spark tps` — is the server thread keeping up? This is the number the Ryzen 2700 limits.
- `/spark profiler start` … `/spark profiler stop` — where server-thread time actually goes. Run
  it in the pocket dimension that feels worst, not in the hub.
- `/spark healthreport` — TPS, MSPT, GC counts and heap in one summary.
- F3 in game for client FPS, and the `C:` line for chunk-update cost.

Nothing in this pass was benchmarked on this machine — it cannot be, from outside the game. The
mod choices and settings follow from the measured hardware and from what the configs actually do,
and `/spark` is how to confirm or overturn any of it. The texture-swap duration now reports itself
in chat too, so that one figure arrives on its own.

## Verification, and a false pass that nearly slipped through

After the four jars went in:

| Check | Result |
|---|---|
| `validate_instance.py` | 251 jars, 290 mods, **0** duplicate modIds, **0** missing required, **0** real conflicts |
| `check_incompatible.py` | 251 jars scanned, **CLEAN** (5 declarations ruled out by version range) |
| `verify_worlds.py` · `verify_skins.py` · `verify_effects.py` | all pass |
| `tune_settings.py` | all three settings applied, the three untouched ones asserted unchanged |

That second row is the interesting one. `check_incompatible.py` was first run with the
**instance** directory while the function expected a **mods** directory - so it listed
`instance.cfg` and `mmc-pack.json`, found zero jars, and printed `0 jars CLEAN`. A pass
indistinguishable from a real one, and it was briefly used to claim the pack had no
incompatibilities. The no-argument code path in the same file had always appended
`minecraft/mods` correctly; only the CLI path was wrong.

It now resolves either form, and **refuses to report at all on an empty scan** rather than
reporting clean. Re-run against the real 251 jars the answer is still CLEAN - the conclusion
held, but it is now actually evidence for it.

