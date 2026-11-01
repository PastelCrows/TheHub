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

### Still not launched

Validation is static: it proves the dependency graph closes and nothing declares war on
anything else. It does not prove the game starts. That is the next step.

## Then: the world

Eleven regions as continents, gyms, Elite Four, champions, legendary quests. Still not a mod —
a world, a quest book and structure NBT. But the pieces that make it buildable are now in
place: **RCT gives trainers and gym battles, Rad Gyms gives gym structure, Cobblemon Quests
wires progression into FTB Quests, and Legends Untold gives legendary structures.**

And The Hub already merges eleven quest books into one and seeds structures per dimension.
Region-per-continent is the same shape of problem, solved eleven times already.
