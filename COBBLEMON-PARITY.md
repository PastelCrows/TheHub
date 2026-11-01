# Cobblemon on NeoForge — how close is 1:1?

The twelfth arch was always meant to be Kewz's Cobblemon pack, and it was never going to work:
his is Fabric, The Hub is NeoForge. So the real question is what a from-scratch NeoForge build of
the same thing would be missing. This is the measured answer, not an impression.

Measured 2026-11-01 by `tools/cobblemon_parity.py`, which hashes every jar in his mods folder and
looks each one up on Modrinth by sha512 — identifying the exact file rather than guessing from
the filename. His instance is read-only and nothing was written to it.

## The short version

**Cobblemon itself ships for NeoForge 1.21.1 and is current.** `Cobblemon-neoforge-1.8.4+1.21.1`,
released 2026-10-27. Kewz runs Fabric 1.8.2, so you are not behind — you are one minor version
ahead of what he is playing.

## His pack, by the numbers

370 jars. **77 of them carry his name**, and the first audit lumped them together as "recompiles".
That was wrong, and the distinction turns out to be the whole story:

| | count | what it is |
|---|---|---|
| `+kewz.` suffix on an upstream jar | **58** | his recompiles of other people's mods |
| **`kewz-` prefix** | **16** | **mods he wrote from scratch** |
| other infix forms | 3 | recompiles with different naming |
| Resolve to a project publishing NeoForge + 1.21.1 | **224** | direct swaps |
| Fabric-only or unlisted | **72** | broken down below |

Of those 72: **37 already covered** (Fabric plumbing NeoForge does not need, or mods The Hub
already has — EMI is JEI, Trinkets is Curios, and Sophisticated Backpacks/Core/Storage appear as
"Unofficial Fabric port", which are ports *of NeoForge mods* we already run), **14
Cobblemon-specific**, **21 decorative**.

## The sixteen mods he wrote himself

This is the part that cannot be downloaded, ported, or replaced by picking a different mod. Each
is tiny — one to twenty classes — and each kills one specific papercut:

| mod | what it does |
|---|---|
| `airhaze-shadergate` | turns Atmospherics' haze off automatically when a shader is active |
| `chat-time` | timestamps every chat line in your own timezone |
| `client-perf` | removes the freeze when opening the creative inventory |
| `evolution-info` | an info button on the Cobblemon summary screen |
| `kit-fastdraw` | draws the restyled menus (Perfect Partners, CobbleBase) without the stall |
| `legacy-blocks` | keeps six Gravelmon ore/storage block ids alive after they were removed |
| `lootr-retrofit` | converts already-generated structure chests to Lootr |
| `native-tm-teaching` | staged, species- and form-restricted native TM extension |
| `render-guard` | guards incomplete world-render and CobbleDollars HUD states |
| `shader-profiles` | keeps Grassier Grass in step with the active Iris shaderpack |
| `subtle-effects-stub` | lets you join the server when Subtle Effects is switched off |
| `tm-filter` | hides TM entries whose move silently fell back to Tackle |
| `tower-trainer-spot` | makes the Battle Tower trainer stand on the battle position |
| `worldgen-compat` | repairs legacy and malformed jigsaw pool identifiers |
| `hologram-target`, `terminal-layout` | no description shipped |

**Read that list again and notice what most of it is.** Shader gating, worldgen id repair, legacy
block ids, a stub for a disabled mod, a guard against half-initialised render state. That is not
a feature set — it is **scar tissue from one specific 370-mod Fabric stack**. Those bugs exist
because of what he combined, and a NeoForge build would not inherit them.

So the honest conclusion is not "we must reproduce 16 mods". It is: **you cannot port his fixes,
and you would not want to — you would develop your own set, for your own papercuts.** What *is*
worth stealing is the handful that are design rather than repair: `evolution-info`, `tm-filter`,
`native-tm-teaching`, `tower-trainer-spot`, `chat-time`. Those are decisions about how a Pokemon
pack should feel, and they would port as ideas.

## The ecosystem is about half the size, not a tenth

Cobblemon-related projects for 1.21.1 on Modrinth:

```
any loader   2265
Fabric       1316
NeoForge      646
```

NeoForge has roughly half of Fabric's Cobblemon ecosystem. That is a real gap and not a fatal one.

## The fourteen real losses, and whether anything replaces them

Searched NeoForge + 1.21.1 for each feature his Fabric-only mods provide:

| feature | NeoForge equivalent? |
|---|---|
| Badges / trophies | **yes** — 9 projects (Cobblemon Pokemon Badges, Gym Badges, PokeBadges) |
| Pasture loot | **yes** — 8, one literally named *Cobblemon Pasture Loot NeoForged* |
| Pokédex app | **yes** — 4 (Cobbledex, Pokedex Network) |
| Raids | **yes** — 8 (Cobblemon Raid Dens) |
| Mega evolution | **yes** — 16 (Mega Showdown) |
| Battle improvements | **yes** — 35 (Battle Extras, Battle Tower) |
| Fishing | **yes** — 1 (Legendary Fishing) |
| Extra content / additions | thin — 1 |
| **Food / cuisine** (Cobblemon Delight, CobbleCuisine) | **nothing** |

Eight of nine have an answer. One does not.

## What this actually means

**Parity on mods is achievable and not the hard part.** The hard part is the two things the
measurement cannot buy:

**His 77 custom jars** — 58 recompiles and 16 original mods. The recompiles carry tags like
`+kewz.dex1`, `+kewz.sheetfix3`, `+kewz.cd181`: sprite-sheet fixes, Pokédex behaviour, pins to
a specific Cobblemon build — maintenance against a moving target. The 16 originals are listed
above, and most are compatibility glue for his stack rather than portable features.

**The gating.** Pokémon-specific items and spawns confined to one pocket dimension is the roughest
part, and it is roughest in a way The Hub is unusually well prepared for: `PocketMobs` already
gates entity spawns per dimension by pattern, `PocketRules` already gates crafting per dimension,
and `PocketWorlds` already gates access to modded dimensions. A Cobblemon pocket needs the same
three levers pointed at `cobblemon:*`, not a new mechanism.

## What 17 jars is NOT

It is the **mechanics layer** and nothing else. Calling it a recreation of his pack was wrong.
Here is the scale it is measured against, counted rather than estimated:

| | |
|---|---|
| **1,924 species JSONs** across his mods | 1,025 from Cobblemon itself, ~900 from fakemon and romhack packs |
| **34 datapacks**, of which **27 are his own** | a whole second layer of custom work the first audit never looked at |
| 370 mods | of which 77 carry his name |

His species packs: Gravelmon **331**, Gravel's Extended Battles **142**, SpaceworldMons **94**,
Cobblemon AFP **87**, Lively 'Mons **73**, Laser's Fakemon **70**, Mega Showdown **53**,
Silent's Minemons **25**, Fai's Mythical Monstrosities **24**.

And his 27 datapacks are the same kind of work as his 16 mods, in data instead of code:
`fakemon-riding`, `gravelmon-scrub`, `mega-stone-recipes`, `starter-filter`, `form-removals`,
`structure-loot-fixes`, `end-spawn-balance`, `rocket-biome-fix`, `missing-ability-scripts`.

### The content layer mostly CAN come across

| pack | species | NeoForge? |
|---|---|---|
| Gravelmon | 331 | yes |
| Gravel's Extended Battles | 142 | yes |
| SpaceworldMons | 94 | yes |
| Lively 'Mons | 73 | yes |
| Laser's Fakemon | 70 | yes |
| Silent's Minemons | 25 | yes |
| Cobblemon AFP | 87 | not found under that name |
| Fai's Mythical Monstrosities | 24 | **Fabric only** |

About **1,813 of 1,924 species — 94% — are reachable on NeoForge.** The species layer is a
bigger win than the mechanics layer and was not part of the 17.

### The part that is not downloadable at all

Eleven regions as continents in a hand-built map. Every gym, Elite Four and champion. Quests
tied to every legendary, mythical and mega. Custom structures and worldgen to match.

**None of that is a mod.** It is a world, a quest book and a pile of structure NBT — authored,
not installed. No amount of parity analysis touches it, and it is the actual reason his pack
is his pack. The honest estimate for that layer is months, and the mod list is the easy part
that comes first.

The one thing that transfers is the METHOD: The Hub already merges eleven quest books into one
and seeds structures per dimension. A region-per-continent map with gyms is the same shape of
problem as eleven pocket dimensions with their own starts.


## Status: 69 jars, and 91.8% of his roster

Prism instance **Cobblemon NeoForge**, MC 1.21.1 / NeoForge 21.1.265, 6 GB.
**69 jars, 66 modIds, 0 duplicates, 0 missing dependencies, 0 conflicts — VALIDATION PASSED.**

### Species

| | distinct species names |
|---|---|
| ours | **4,904** |
| his | 1,446 |
| shared | 1,328 |
| only he has | **118** |

**91.8% of his roster, and 3,576 species he does not have.** The raw file counts (11,155 vs
1,953) are not comparable — Gravelmon ships every regional form as its own JSON, and his
`+kewz.strip1.forms1.r1047` tags mean he deliberately pruned exactly that. Distinct names is
the honest measure.

The 118 he has and we do not are almost entirely Cobblemon AFP (87 species, not on Modrinth
under any findable name) and Fai's Mythical Monstrosities (24, Fabric only).

### What is in it

| layer | mods |
|---|---|
| core | Cobblemon 1.8.4NF |
| species | Gravelmon, Gravel's Extended Battles, SpaceworldMons, Lively 'Mons, Laser's Fakemon, Silent's Minemons, HiddenMons, MissingMons |
| trainers + gyms | **RCT API, Radical Cobblemon Trainers (1500+ trainers), More Radical Trainers, Rad Gyms** |
| quests | **Cobblemon Quests** — an FTB Quests bridge, and The Hub already runs FTB Quests |
| legendaries | Legendary Monuments, Legends Untold (structures), Myths and Legends |
| progression | Cobbreeding, SimpleTMs, CobbleDollars, Cobbleloots, Capture XP, PlayerXP, Unchained, Alpha Project, Cobblemarks+, Bottle Caps, Box Link, SafePastures |
| mechanics | Mega Showdown, Navas ZA Megas, NoValidation, Raid Dens, Battle Extras, BadgeBox, Pasture Loot, Legendary Fishing, Mount Mastery, Size Variations, Fight or Flight, Trials Edition |
| interface | Cobbledex + JEI bridge, PokeNav, MoreCobblemonTweaks, Cobblepedia, Catch Rate Display, Catch Indicator, Counter, Spawn Notification, Wiki GUI |
| flavour | CobbleFurnies, Cafe Remix forms, Armory |

### Four REAL conflicts the validator caught

Not missing dependencies — mods that declare each other incompatible and would have failed at
launch:

| dropped | why |
|---|---|
| AllTheMons | declares itself incompatible with Mega Showdown |
| CobbleStats | Battle Extras refuses to coexist |
| Move Inspector | same — Battle Extras supersedes it |
| Ride On | requires Cobblemon [1.7,), we are on 1.8.4 |

### One version pin, and the reason

**Gravelmon is pinned to 4.0.0-Alpha.8.** Every build from Alpha.10 onward is 1.4 MB and
contains **zero** species JSONs — the content was moved out of the jar mid-alpha and is not
published anywhere on Modrinth as a separate pack. Alpha.8 is 92 MB and carries the lot. Found
by downloading each build and counting, not by reading release notes.

Three mods come from **maven.ftb.dev**, not Modrinth — FTB publish nowhere else, the same
finding as the packwiz build.

A third pin was added after the boot hang: **gravels-extended-battles 2.0.0-Alpha.15**, because
Gravelmon pins it exactly. See below.

### Launched — and it took three attempts, because it was hung

Static validation proves the dependency graph closes and nothing declares war on anything else.
It does not prove the game starts. The game did not start.

Two boots stopped dead at the same point with a frozen log, no error, no crash report, and a
live `javaw`. A JVM thread dump (`jstack -l`, using Prism's own JDK) named the cause outright:

```
Render thread         ModLoader.waitForFuture / constructMods      waiting
modloading-worker-0   ProcessSelectionPrompt.next()                parked forever
                      OnDemandRunner.readSelection
                      GravelsExtendedBattles.initialize
```

**Gravels Extended Battles 2.0.0-Alpha.37 asks the client for a selection code on stdin during
mod construction.** Under `javaw` there is no stdin, so it parks forever — and because it parks
inside a parallel mod-construction task, the entire load waits behind it. Its own config says so:
*"A client asks for it when it is empty."*

The mistake was mine, and it is a general one worth keeping. **Gravelmon 4.0.0-Alpha.8 does not
declare a version RANGE for GEB — it pins one exact version id**, `MMwKsJoI` = `2.0.0-Alpha.15`.
The resolver took "newest for neoforge/1.21.1" and got Alpha.37, twenty-two releases past what
Gravelmon asked for. Verified by reading both jars rather than trusting version numbers:

| | ondemand classes | prompt classes |
|---|---|---|
| Alpha.15 (pinned) | 0 | 0 |
| Alpha.37 (installed) | 139 | 13 |

This also corrects an earlier finding recorded here as a broken release: **Gravelmon Alpha.10+
being 1.4 MB instead of 92 MB is not a mispackaged jar** — it is the same redesign, species moved
to on-demand download. Alpha.8 + GEB Alpha.15 is the last pair that ships its species in the jar.

`tools/check_version_pins.py` now lists every unmet exact pin after a build, so this cannot
happen silently again.

With the pin honoured, the third boot reached the title screen:

```
Backend library: LWJGL version 3.3.3+5
OpenAL initialized on device OpenAL Soft on Speakers
Sound engine started
```

**0 crash reports, 166 mod configs written.** Eight ERROR lines, all benign: six are `Invalid
path in pack` for asset filenames containing spaces inside Cobblemon's and Gravelmon's own jars
(upstream packaging, cosmetic — those individual assets don't load), one is a ModernFix timing
warning, one is Xaero's online version check failing to reach the network.

What the boot proved beyond "it starts", because CobbleDex walks every jar's data at init:

```
JarDataCache: parsed 23,351 spawns from 6,973 files (0 failed)
              2,072 habitat spawns from 52 pools
              2,529 base + 1,314 form evolutions from 6,722 species files (0 failed)
              779 native TMs, 183 marks, 18 fossils, 376 mega stones
ready in 2.7s - 4,807 species with spawns, 4,904 with breeding/dex traits
```

**0 failed on both parses.** Every species file and every spawn file in 133 jars is
well-formed and mutually consistent — that is the thing a hand-assembled 4,900-species roster
is most likely to get wrong, and it is clean.

The mixin warnings in the log are all `ClassNotFoundException` for mods we deliberately do not
ship — Controlify, MidnightControls, TerraFirmaCraft, Create, Aether. Those are optional-compat
mixins declining to apply, which is the correct behaviour, not a fault.

## The gap, measured instead of guessed

`tools/cobblemon_gap.py` resolves both packs to Modrinth projects and lists what he has, we lack,
and NeoForge publishes. 255 projects separate us. The split is the surprise:

| | count |
|---|---|
| **Cobblemon-specific** | **16** |
| general survival/client layer | 192 |
| no NeoForge build | 47 |

All 16 Cobblemon ones are now installed. Of the 192 general ones, **43 are already in The Hub** —
and since this is going to live inside The Hub, that layer arrives with the merge rather than
needing to be rebuilt here. Only 149 are new to the project at all, and they are Sodium, Jade,
Waystones, Handcrafted, Lootr, storage and QoL — a survival pack underneath the Pokemon one.

**87 jars, 82 modIds, 0 duplicates, 0 missing, 0 version mismatches, 0 conflicts.**

## Regions: the mechanics already exist

The spawn format was read out of the Cobblemon jar. Condition fields available:

```
dimensions   biomes   structures   labels   timeRange   moonPhase
minX maxX    minY maxY    minZ maxZ    isSlimeChunk
```

Three things follow, and together they make the eleven-region plan tractable:

**1. Species are already labelled by generation.** `pikachu.json` carries
`"labels": ["gen1", "kantonian_form"]`, and the counts are exact: **gen1 = 151**. That is Kanto,
with no hand-mapping of a Pokedex. gen2 = 100, gen3 = 135, gen4 = 107, gen5 = 156, gen6 = 72,
gen7 = 86, gen8 = 89, gen9 = 120. Nine regions fall straight out of data Cobblemon already ships,
and the fakemon packs bring their own.

**2. "Only Kanto mons in Kanto" is a spawn-pool override, not a mod.** There are 1,591 spawn pool
files in base Cobblemon, one per species, each already carrying biome conditions. A datapack that
rewrites each pool's `condition` to add its region's fence is **generated, not authored** — read
the label, look up the region, emit the file. That is a tool, and it is the same shape as every
other generator in this repo.

**3. The fence can be coordinates OR dimensions, and The Hub has already chosen.** `minX/maxX` and
`minZ/maxZ` mean continents separated by ocean in ONE world work exactly as you described.
`dimensions` means a region could instead be its own pocket — which is the thing this project has
done thirty-two times. Either is expressible; the continent version is the one you want and costs
nothing extra in the spawn data.

**"Lavender city in a lavender forest"** is the remaining hard part, and it is honest to say so:
that is biomes plus structures plus placement, authored per region. Aio's Extra Structures and
Legends Untold give raw material; `structures` as a spawn condition means a Pokemon can be made to
spawn only at a specific structure. But the map itself is hand work.

## Then: the world

Eleven regions as continents, gyms, Elite Four, champions, legendary quests. Still not a mod —
a world, a quest book and structure NBT. But the pieces that make it buildable are now in
place: **RCT gives trainers and gym battles, Rad Gyms gives gym structure, Cobblemon Quests
wires progression into FTB Quests, and Legends Untold gives legendary structures.**

And The Hub already merges eleven quest books into one and seeds structures per dimension.
Region-per-continent is the same shape of problem, solved eleven times already.

## The survival layer, and Oritech

You asked for his whole survival layer, not just the Pokemon half, and specifically whether
Oritech is a Forge mod.

**Oritech publishes `fabric` AND `neoforge` for 1.21.1.** It comes over directly —
`oritech-neoforge-1.21.1-1.2.13.jar` is installed.

The backpacks are the opposite surprise: **Sophisticated Backpacks, Core and Storage are
NeoForge-native.** They were Forge-first mods, and the jars in his pack are unofficial Fabric
ports. So that whole family is *more* at home here than there.

Installed from his survival layer: Oritech, Sophisticated Backpacks/Core/Storage, Waystones,
Lootr (+ Lootrmon), Comforts, Handcrafted, Supplementaries, Farmer's Delight, Jade, JEI,
Xaero's minimap + worldmap, Sodium (+ Extra, + Reese's options), FerriteCore, ModernFix.

## What the other Cobblemon packs do that his does not

Two packs were pulled and diffed by Modrinth project id rather than by name:

| pack | mods | overrides | projects we lacked |
|---|---|---|---|
| COBBLEVERSE | 168 | 1,647 (1,234 of them shaderpack files) | 140 |
| Cobblemon Official (NeoForge) | 75 | — | 73 |

The honest read: **almost none of it is content.** Both lists are overwhelmingly
client/performance/QoL — Sodium, Iris, FerriteCore, Lithium, FancyMenu, JEI, zoom mods. Neither
pack carries Pokemon content Kewz lacks; his content layer is genuinely ahead of both.

Two exceptions worth taking, and both packs ship them:

- **Entity Texture Features (ETF)**
- **Entity Model Features (EMF)**

These let entity textures and models be overridden per-variant from a resource pack. For a pack
whose whole point is 4,900 creatures with forms, shinies and regional variants, that is the
difference between "a texture pack can reskin Pokemon" and "it cannot." Both are installed.

Also swapped on the way in: Continuity → **Fusion** (Continuity is Fabric-only), zoomify →
**Just Zoom**, plus the nine libraries the new entries pull in.

**133 jars, 142 modIds, 578 MB, 0 duplicates, 0 missing deps, 0 version mismatches,
0 declared conflicts.**

## Next: the progression layer

The roster is effectively done. What is missing is not mods, it is *shape* — the thing that makes
it feel like playing the games back to back rather than a very large creature sandbox:

1. **Region-locked spawns** — generated, not authored (see above). The first real build.
2. **Gym ladder** — RCT trainers + Rad Gyms structures + Cobblemon Quests into FTB Quests, eight
   badges per region gating the next region's entry.
3. **The map** — eleven continents, one ocean. Hand work, and the long pole.
4. **Mystery Dungeon** — a pocket inside a pocket. Settled: it is NOT a thirteenth arch in The
   Hub. It is a pocket *within* the Pokemon pocket, reached from inside it, because its rules
   differ from the overworld's (no human player character, procedurally generated floors, a
   party rather than a trainer) while still belonging to the Pokemon pack.

## The shape of the Pokemon pocket

This is now decided, and it is a three-level nesting rather than the usual two:

```
The Hub  ──arch──▶  Pokemon pocket
                        │
                        ├── region hub  ──teleport──▶  Kanto      (overworld)
                        │                ──teleport──▶  Johto      (overworld)
                        │                ──teleport──▶  ... x11
                        │
                        └── pocket  ──────────────────▶  Mystery Dungeon  (own dimension)
```

Two things fall out of that, and they are not the same mechanism:

**The eleven region teleports are overworld teleports, not portals.** The regions are continents
in ONE world separated by ocean, reachable by flight or boat the long way round — the teleports
exist so you can *choose your next region* without the voyage. At least one per region. That
means they are a command/waystone-shaped problem, not a dimension-portal problem, and it is
much cheaper than what The Hub's arches do: no dimension registration, no `coordinate_scale`
arithmetic, no return-portal placement. A fixed destination per region and a hub room to stand
in. The spawn fence is `minX/maxX` + `minZ/maxZ`, which the spawn format already supports.

**Mystery Dungeon IS a dimension**, and so it is the one piece here that reuses The Hub's
machinery directly — the same portal-block pattern, the same per-dimension rule gating that
PocketQuests already does for eleven pockets. Its entrance lives in the region hub.

So the region hub does double duty: eleven same-world teleports and one real portal.

## The 370-vs-286 accounting, in full

The fair question was: how is this pack so much smaller than his, and what is still being
skipped? Here is the whole arithmetic, from `tools/cobblemon_gap.py` with per-version
verification rather than project-level guessing.

| | jars / projects |
|---|---|
| his pack | **370 jars** |
| of those, resolvable on Modrinth | 271 |
| **not resolvable at all** | **99** |
| ours | **286 jars** |

**The 99 are the real answer to "why is his bigger".** They are not downloadable by anyone:
74 are `+kewz` recompiles of other people's mods, 16 are `kewz-` prefixed originals he wrote,
and the rest are CurseForge-only or unpublished snapshots (his EMI is a fabric SNAPSHOT build,
which is why a hash lookup cannot see it). A pack cannot be "caught up to" on that column; it
has to be rebuilt, mod by mod, which is the long-term work.

Of the 271 that *are* resolvable, 55 are projects we do not have:

| | count |
|---|---|
| **no NeoForge build exists** | **52** |
| deliberately excluded, documented | 3 |

The 52 are the loader tax, and it is mostly structural rather than content: fabric-api,
Fabric Language Kotlin, Mod Menu, Krypton, C2ME, Debugify, Enhanced Block Entities, Trinkets,
and the unofficial *Fabric ports* of Sophisticated Backpacks/Core/Storage — which we run as the
NeoForge originals instead, so those three are a gain, not a loss. Real content losses are a
short list: Cobblemon Additions, COBBLEVERSE Badges & Trophies, Pokeblocks, Casino Rocket,
Cobblemon Pasture Loot, Cobblemon Delight, CobbleCuisine Delight.

The 3 excluded, each with a reason that was checked:

- **Continuity** — its single neoforge 1.21.1 build requires Sinytra Connector plus Forgified
  Fabric API. Fusion is installed in its place.
- **Do A Barrel Roll** — all four neoforge builds declare `fabric_api` mandatory with no
  version range. Same underlying reason as Continuity.
- **Rolling Down in the Deep** — an addon to Do A Barrel Roll.

So the honest statement is: **we are 3 installable projects short of his downloadable pack**,
52 behind on things NeoForge does not have at all, and 99 behind on work he wrote himself.

### Two tool bugs this exposed

The gap was mis-measured twice, in opposite directions, and both tools are now fixed:

- **`cobblemon_gap.py` over-reported by 6.** Asking "does the project list neoforge, and does it
  list 1.21.1" is satisfied by a project that shipped neoforge for 1.20 and fabric for 1.21.1.
  Six mods went onto a build list and quietly failed to download. It now queries the version
  endpoint, and treats a Connector-requiring build as unavailable, because for this pack it is.
- **`validate_instance.py` invented 5 failures.** It kept the FIRST version of a modId it
  scanned, so a YACL 3.6.6 nested inside fragmentum's JarJar shadowed the 3.8.2 sitting in
  `mods/`, failing three mods that were satisfied. It now keeps the highest, which is what
  NeoForge actually resolves. It also could not compare versions with the game version embedded
  in them (`1.21.1-3.7.2` against `[1.21-2.29.33,)`), which it now strips - dash-delimited only,
  because a substring strip turns the bare game version `1.21.1` into `.1`, and the self-test
  caught exactly that.

### And the ceiling of static validation

With 286 jars the set validated completely clean — 0 missing, 0 duplicates, 0 mismatches,
0 conflicts — and then crashed on launch.

**[Let's Do] Beachparty's NeoForge main class hard-references Curios in its constructor, and
its toml declares only neoforge, minecraft and architectury.** No curios entry, required or
optional. Construction threw `NoClassDefFoundError`, which aborted the parallel task, which left
registries frozen before cobblenav had registered its items — so the crash report blamed
cobblenav and ModelBakery, two mods innocent of the cause.

No static check can catch a declaration that is simply wrong. Launching is not a formality after
validation; it tests a different thing.

## It boots at 286 jars

```
Backend library: LWJGL version 3.3.3+5
OpenAL initialized on device OpenAL Soft on Speakers
Sound engine started
```

**0 crash reports.** 14 ERROR lines, and all 14 are benign — but worth naming rather than
waving at:

| count | what | verdict |
|---|---|---|
| 7 | `Invalid path in pack` — asset filenames with spaces inside Gravelmon's and Cobblemon's own jars | upstream packaging; those individual assets don't load. One of them is a stray `Quick access - Shortcut.lnk` shipped inside Cobblemon's sounds folder. |
| 5 | CraftPresence probing for Curse/ATLauncher/MCUpdater/Modrinth pack metadata | self-labelled "ignore if not using" |
| 1 | Xaero's online version check | no network reply |
| 1 | ModernFix: a mod called `registerReloadListener` on the wrong thread | **real, upstream** — see below |

**The one to keep an eye on: Rad Gyms 0.5.2** calls `registerReloadListener` off-thread during
init. ModernFix catches it and warns it can cause random concurrency crashes. That is an upstream
bug, not a packaging choice here, and Rad Gyms is load-bearing for the gym ladder — so it stays,
flagged. If unexplained reload crashes ever appear, this is the first thing to suspect.

Memory raised 6 GB → 8 GB (the machine has 32 GB; The Hub runs 12).

## His custom work, reproduced

### The datapacks: 27 ported, 1,533 files

22 needed no change. 5 used Fabric load conditions; 232 files converted. The mapping was read
off shipped jars, not recalled — Carved Wood ships BOTH spellings in one recipe, which settles it.
His sentinel trick (disable a recipe by requiring a mod that cannot exist) is kept verbatim
rather than collapsed to `neoforge:false`: the sentinel's NAME carries the reason
(`kewz_pokedolls_are_found_not_crafted`), and a datapack could later define it to switch the
behaviour back on.

### The recompiles: classified by cost, not counted

| bucket | jars | what it takes |
|---|---|---|
| DATA | 4 | a datapack — **done**, 86 JSON files |
| DATA+ASSETS | 4 | repackage the jar — **done**, `mod-ports/` |
| CODE | 33 | read his bytecode, reimplement |
| unresolved | 14 | explained below |
| his own originals | 16 | write from scratch |

**The eight no-compile ones split on one fact: a datapack can override a file inside a mod jar
but can never delete one.** Four are pure overrides and became `kewz-dex-fixes-ported.zip`. The
other four are mostly deletions — his `strip1`, `nomodel1`, `newonly1` tags — so the jar itself
had to change, which is exactly why *he* recompiles. `tools/repack_kewz_mods.py` replays his
data/asset diff onto our NeoForge jar: **324 removals, 319 overrides, 56 additions**.

Three applied at 100%. silents-minemons is 25 of 29 because his edit targeted 4.4.2 and ours is
4.6.1 — four species he deleted no longer exist upstream. Reported and skipped, never silently
ignored.

**What the removals were actually for, confirmed empirically:** 324 files deleted cost only
**3 net species** (4,917 → 4,914). They were deduplication between overlapping fakemon packs, not
content loss. That is what "strip" means, and it is now measured rather than assumed.

### The 14 unresolved, explained

2 are his own originals. 1 is a voxy build he compiled himself
(`0.2.19-beta+mc1.21.1-leaf-tint-fog-fade-test`, never published). 11 have no Fabric 1.21.1
release on Modrinth, cross-checked by slug and by display name.

## Two boot failures, both self-inflicted

**`ftb-quests-cobblemon-entity` is out.** He runs 2.0.0 on Fabric; NeoForge has exactly one
build, 1.0.0, whose `CommandRewardMixin` throws `InvalidInjectionException` against FTB Quests
2101.1.37 — the descriptor it injects on is gone. A fatal mixin failure aborts mod construction,
so one mod killed the whole boot. **The quest bridge is a real loss on NeoForge**, recorded as one.

**FancyMenu is pinned to 3.8.1.** 3.9.14 broke `satisfying_buttons`, which was already installed
and working: its `@WrapOperation` targets `ExtendedButton.renderBackground`, gone in 3.9.x.
Satisfying Buttons has shipped nothing since Sep 2024. The version was not guessed — **Kewz runs
both**, at FancyMenu 3.8.1 and satisfying_buttons 1.1.2.

## Verified state

```
302 jars   28 datapacks   0 duplicates   0 missing   0 mismatches   0 conflicts
OpenAL initialized -> Sound engine started      0 crash reports
4,914 species with spawns
all four +hub repackaged jars confirmed loaded by name in the log
```

14 ERROR lines, the same benign set throughout: 7 asset filenames containing spaces inside
Gravelmon's and Cobblemon's own jars, 5 CraftPresence launcher probes it labels ignorable, 1
Xaero network check, 1 Rad Gyms off-thread reload listener (upstream, flagged).

Dream Displays downloads FFmpeg on first launch — completed normally, worth knowing because it
is an outbound fetch during boot.
