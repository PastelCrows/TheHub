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

370 jars. **74 of them are his own recompiles** — every jar with `+kewz` in the name is a custom
build he made, which is the single most important fact here: a large part of that pack does not
exist anywhere to download, on any loader.

| | count | |
|---|---|---|
| Resolve to a project that publishes NeoForge + 1.21.1 | **224** | direct swaps |
| Kewz's own recompiles | **74** | do not exist to download, any loader |
| Fabric-only or unlisted | **72** | broken down below |

Of those 72:

| | count | |
|---|---|---|
| Already covered | **37** | Fabric plumbing that NeoForge does not need, or mods The Hub *already has* |
| Cobblemon-specific content | **14** | the actual work |
| Other content, mostly decorative | **21** | replaceable or droppable |

The 37 are worth naming because they look alarming in a raw list and are not losses at all: Fabric
API, Fabric Language Kotlin, MixinExtras and CICADA are loader plumbing. EMI is JEI. Trinkets is
Curios. Farmer's Delight Refabricated is Farmer's Delight. The FTB mods are the FTB mods. And
**Sophisticated Backpacks / Core / Storage appear as "Unofficial Fabric port"** — those are ports
*of NeoForge mods*, and The Hub already runs the originals.

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

**His 74 custom builds.** Recompiles, rebalances and fixes he made himself — `+kewz.dex1`,
`+kewz.keys1`, `+kewz.sheetfix3`. Some are bug fixes that may be upstream by now; some are his own
design decisions baked into a jar. Matching those means either doing the same work or deciding you
do not need it.

**The gating.** Pokémon-specific items and spawns confined to one pocket dimension is the roughest
part, and it is roughest in a way The Hub is unusually well prepared for: `PocketMobs` already
gates entity spawns per dimension by pattern, `PocketRules` already gates crafting per dimension,
and `PocketWorlds` already gates access to modded dimensions. A Cobblemon pocket needs the same
three levers pointed at `cobblemon:*`, not a new mechanism.

## Suggested order, if this becomes real

1. A standalone NeoForge Cobblemon instance first — Cobblemon alone, then the eight replacement
   addons. Get it playable before thinking about the hub.
2. Measure *that* against his pack rather than against this document.
3. Fold it in as the twelfth arch only once it stands up alone, exactly as the other eleven were.

Do not try to build it inside The Hub. Every one of the eleven pockets was a working instance
first, and the one that was not — the Cobblemon one — is the one that never happened.
