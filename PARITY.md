# Parity pass — hub vs the standalone packs

Question: does each pocket dimension still deliver the experience its standalone pack did, now
that every mod is global in the hub?

## Quest books — clean

Every standalone book is fully represented, nothing lost across three separate merges:

| Pocket dimension | standalone | in the hub |
|---|---|---|
| skyblock | 8 ch / 98 | 8 ch / 98 |
| survival | 13 ch / 182 | 13 ch / 182 |
| caveblock | 8 ch / 75 | 8 ch / 75 |
| netherbound | 8 ch / 59 | 8 ch / 59 |
| oceanblock | 8 ch / 55 | 8 ch / 55 |
| lostcities | 8 ch / 50 | 8 ch / 50 |
| onechunk | 8 ch / 51 | 8 ch / 51 |
| gauntlet | 8 ch / 44 | 8 ch / 44 |
| oneblock | 8 ch / 52 | 8 ch / 52 |
| horror | 6 ch / 33 | 6 ch / 33 |

**83 chapters / 699 quests.** All ids unique, all dependencies resolve, every chapter gated by a
`pocketquests.json` prefix.

## Recipes — restraint was the finding

The obvious move was to diff each pocket dimension's mod set against its standalone and deny
everything extra. That diff says ~50 extra item-adding namespaces per pocket dimension, 91 for
horror. Enforcing all of it would have been wrong.

The mod sets say why:

| comparison | result |
|---|---|
| Oceanblock / One Chunk / Skyblock vs Caveblock | **124 jars, zero differences** |
| One Block vs Caveblock | 2 added, 2 removed (deliberate) |
| The Gauntlet vs Survival | **165 jars, zero differences** |
| Lost Cities vs Survival | 1 added, 2 removed |
| **Horror vs Survival** | **29 added, 111 removed — deliberately stripped** |

The five block packs were built from one identical base and The Gauntlet's set *equals*
Survival's. Their "extras" in the hub exist only because the hub also contains the other tier's
mods — **nobody ever chose to exclude them.** Restricting them would invent rules the originals
never had, and the crafting gate only covers the crafting grid anyway (not furnaces, smithing
tables, stonecutters or modded machines), so the enforcement would be half-visible and confusing.

So only the two pocket dimensions with *intentional* exclusions get rules:

- **`hub:horror`** — 91 namespaces denied. Its standalone deliberately stripped 111 mods to keep
  you under-equipped; Create and AE2 dissolve that premise instantly. Safe to enforce because the
  horror quest book references **only `minecraft:` items** — verified before writing the rules.
- **`hub:oneblock`** — `exdeorum:*` denied. Its standalone deliberately dropped Ex Deorum because
  sieves are a parallel resource ladder undercutting "the block is the only source". Create,
  Mekanism and AE2 stay, because the One Block book requires all three.

Everything else is deliberately unrestricted. `hub:hub` denies everything — it is a creative
lobby, and it doubles as the quickest way to confirm the gate works.

Verified with 15 assertions run against the real `config/pocketrules.json`, loaded exactly as the
game loads it: horror blocks Create/Mekanism/AE2 but allows vanilla, its own mobs and the quest
book; oneblock blocks Ex Deorum but allows its three book mods; the unrestricted ones stay open.

## Dimension separation

### Real dimensions — all distinct now

Every pocket dimension's nether and end previously shared `minecraft:nether` / `minecraft:end`.
A dimension has no seed of its own, so identical settings meant **identical terrain** — ten
nethers laid out exactly the same.

There is no seed-offset knob in worldgen, so differentiation means different settings. Three
vanilla-schema levers, kept close to vanilla so nothing becomes unplayable:

| lever | effect |
|---|---|
| `legacy_random_source` | switches the RNG outright — same density functions, a completely different noise field. The biggest and safest lever. |
| `noise.size_vertical` | vertical scale of formations |
| `noise.size_horizontal` | horizontal scale — wider or tighter caverns |

**The end was treated conservatively on purpose.** Its `noise_router` is left byte-identical to
vanilla, which is what the central island and the dragon fight ride on — those survive untouched,
while the outer islands and end-city terrain differ per pocket dimension.

Three cases are not noise-driven and were left alone: skyblock's and One Chunk's nethers are
**flat void** (a void cannot be varied by noise, so they are differentiated by *biome* instead —
nether wastes vs crimson forest, which changes mobs, fog and ambience), and One Block's real
dimensions use the `oneblock:oneblock` generator by design.

**All 32 dimensions now have a distinct generator config. None share.**

### Modded dimensions — access gated

Dimension Link separates only the overworld/nether/end trio. Twilight Forest, the Aether, the
Undergarden, Tartarus and the rest were each a **single shared instance** every pocket dimension
could walk into. Ownership, derived by diffing each standalone pack's mod list against the hub's:

| modded dimension | may be entered from |
|---|---|
| `twilightforest:twilight_forest` | survival, lostcities, gauntlet |
| `aether:the_aether` | survival, lostcities, gauntlet |
| `undergarden:undergarden` | survival, lostcities, gauntlet |
| `irons_spellbooks:pocket_dimension` | survival, lostcities, gauntlet |
| `woot:tartarus` | skyblock, caveblock, netherbound, oceanblock, onechunk, oneblock |
| `arphex:the_crawling`, `arphex:the_webrooms` | horror |
| `the_obsessed:obsessed_lair` | horror |
| `lostcities:lostcity` | lostcities |
| `oneblock:overworld` | oneblock |

Enforced by `PocketWorlds` on `EntityTravelToDimensionEvent` (cancellable, fires before travel),
config `config/pocketdims.json`. Values are pocket dimension *names*, not dimension ids, because
entering the Twilight Forest from the survival nether is still entering it from the survival
pocket dimension.

Two subtleties that took a second pass:

- **Never strand a player.** Once you stand in the Twilight Forest your current dimension belongs
  to no pocket dimension, so a naive check would refuse all onward travel. Each player's last
  known pocket dimension is remembered, and a genuinely unknown origin fails **open**.
- **The lobby and redstone land own nothing, which is different from unknown.** Conflating the
  two left the creative sandbox as a backdoor into every modded dimension. They now return a
  distinct sentinel and travel from them is refused, while unknown origins still fail open.

Verified by 16 assertions against the real config.

### Separation - private regions

Gating access is not enough on its own. Survival, Lost Cities and Gauntlet all legitimately own
Twilight Forest, so all three could still walk into the *same chunks* - same spawn point, and a
build made from one standing there when you arrive from another.

**Duplicating the dimension does not work.** Twilight Forest has **sixteen classes** comparing
against `TFDimension.DIMENSION_KEY` - portal return, progression gating, structure protection,
enforced home points. A copy under a different id fails every one of those checks, and that is
bespoke per-mod surgery repeated for the Aether, the Undergarden and Tartarus.

So each pocket dimension gets its own **region** of the real dimension instead, a million blocks
from the next along a diagonal:

| pocket dimension | region | pocket dimension | region |
|---|---|---|---|
| survival | origin | netherbound | 5,000,000 |
| lostcities | 1,000,000 | oceanblock | 6,000,000 |
| gauntlet | 2,000,000 | onechunk | 7,000,000 |
| skyblock | 3,000,000 | oneblock | 8,000,000 |
| caveblock | 4,000,000 | horror | 9,000,000 |

The dimension stays genuinely `twilightforest:twilight_forest`, so **every internal check the mod
makes still passes** - while separate spawns, separate terrain and mutually invisible builds all
follow from the distance. World coordinates reach 29,999,984, so ten pocket dimensions use 30% of
one axis.

The offset is applied on arrival and **removed on the way back**, so a return portal does not
strand you a million blocks from your base. Landing uses the surface heightmap rather than your
old Y, so you never arrive inside terrain or in the void.

Verified by 13 assertions against the real config: the three Twilight Forest owners each hold a
distinct region a million blocks apart, and the access gating is unaffected.

**What this still shares:** one set of region files, so anything a mod stores per *world* rather
than per *region* remains common. For Twilight Forest that mostly means boss progression tied to
specific structures - and since each pocket dimension gets its own structures in its own region,
that largely separates too. Worth watching during play.

The block pocket dimensions also use **hand-authored starting structures** rather than
SkyblockBuilder (absent from the hub) — equivalent in content, not identical in layout.

## Mod configs that name a vanilla dimension — a whole class of silent breakage

Found while chasing why the Cave Dweller never appeared. Dozens of mods take a dimension
allow-list, and they all ship it as `["minecraft:overworld"]`. In a normal pack that is correct.
In the hub **nothing is `minecraft:overworld`** — every pocket dimension is its own `hub:<name>`
with `hub:<name>_nether` and `hub:<name>_end` beside it — so each of those settings matches no
dimension a player can ever stand in, and the feature it guards is simply off everywhere. No
error, no log line.

`tools/fix_dimension_configs.py` inventories them and rewrites the ones that can be rewritten.
It found **42** settings across 9 config files. Ownership is derived the same way
`modded_dims.json` was — by checking which standalone instance actually ships the jar — so a
setting is only widened to the pocket dimensions whose pack genuinely had that mod.

| Config | Setting | Was dead everywhere | Now |
|---|---|---|---|
| `sereneseasons/seasons.toml` | `whitelisted_dimensions` | seasons never changed | survival, lostcities, gauntlet |
| `mowziesmobs-common.toml` | `dimensions` ×7 | bosses never spawned | survival, lostcities, gauntlet |
| `quark-common.toml` | `Dimensions` ×28 | stone clusters etc. never generated | survival, lostcities, gauntlet |
| `waystones-common.toml` | `wildWaystonesDimensionAllowList` | wild waystones never generated | all 10 pockets |
| `alexsmobs-common.toml` | `voidWormSpawnDimensions` | void worms never spawned | the three owners' ends |
| `cave_dweller/server_config.toml` | `dimensionWhitelist` | **the Cave Dweller never came** | horror |

Two traps worth recording:

**Blacklists must not be rewritten.** Quark pairs every dimension list with an `"Is Blacklist"`
flag in the same table. Inverting one of those would exclude the feature from exactly the
dimensions that should have it. The tool checks the flag per occurrence, not per file, because
one file holds dozens of these sections with their own flags.

**A file-wide string replace is wrong.** `quark-common.toml` line 813 is
`"Blocks To Replace" = [..., "minecraft:netherrack|minecraft:the_nether", ...]` — a *block* list
that happens to contain dimension ids inside compound values. Only the exact lines the scan
identified as dimensional list settings are touched.

### The two scalar settings

Two settings name a single dimension and so cannot express "whichever pocket dimension the
player came from". Both are **left alone**, because a config edit would hard-wire every pocket
dimension to one of them, which is worse than the current state:

- `twilightforest-common.toml` — `originDimension = "minecraft:overworld"`, with
  `allowPortalsInOtherDimensions = false`. **Twilight Forest portals cannot currently be lit in
  any pocket dimension at all**, so the dimension is unreachable in all three packs that own it,
  and the region-offset separation built for it has never been exercised. `TFPortalBlock` caches
  `originDimension` into one `ResourceKey<Level>` for the whole server
  (`private static ResourceKey<Level> cachedOriginDimension`) and `getPortalDestination` returns
  that, so even allowing portals elsewhere would send all three pockets home to the same place.
  The fix is a mixin on `getPortalDestination` returning a `DimensionTransition` for the
  traveller's remembered pocket — not a config change.
- `aether-server.toml` — `"Sets portal return dimension" = "minecraft:overworld"`. Same shape,
  same fix needed. Note DimSwap groups the vanilla three into the **hub** group, so returning to
  `minecraft:overworld` would also cross an inventory boundary.

Doing it by post-hoc teleport on `PlayerChangedDimensionEvent` was rejected: the player would
land in the wrong dimension first, which fires DimSwap's inventory swap, and then again on the
correction. Two swaps around a wrong dimension is how inventories get lost.

## Twilight Forest - fixed, and it uncovered a worse bug

Twilight Forest portals could not be lit in any pocket dimension at all:
`allowPortalsInOtherDimensions` was false and `originDimension` was `minecraft:overworld`, so the
dimension was unreachable in all three packs that own it. Two things were needed.

**1. The return destination.** `TFPortalBlock` caches `TFConfig.originDimension` into a single
`ResourceKey<Level>` for the whole server and `getPortalDestination` hands that to
`MinecraftServer.getLevel`. One dimension, server-wide - so even pointed at a real pocket
dimension it could only name one, and survival, lostcities and gauntlet would all come home to
the same place. `TFPortalMixin` `@Redirect`s that single `getLevel` call to the traveller's own
pocket overworld. A redirect rather than an inject because the method derives the world border,
the teleportation scale and the transition itself from the level it resolved - substituting the
level means all of that downstream work runs against the right one, with no logic duplicated and
nothing from the Twilight Forest jar needed on the compile classpath.

**2. The offset arithmetic was wrong, and would have stranded people.** This is the real find.

A dimension has a `coordinate_scale`, and portal code multiplies position by
`DimensionType.getTeleportationScale` when crossing. Two shared dimensions are not 1.0:

| Dimension | coordinate_scale | entering | leaving |
|---|---|---|---|
| `twilightforest:twilight_forest` | 0.125 | x8 | /8 |
| `undergarden:undergarden` | 4.0 | /4 | x4 |

Adding a flat million-block offset on entry and subtracting the *same flat offset* on exit is
therefore not an inverse. Enter at x, arrive at 8x + C, leave to (8x + C)/8 = x + C/8, subtract C
and land at **x - 875,000**. Nothing would have reported it - the portal just comes out in the
wrong place, which reads as "the separation is broken" rather than "the arithmetic is wrong".

The correct inverse subtracts `offset * scale(shared -> pocket)`, the same factor the portal
applied to everything else on the way out. Entering stays unscaled, since the mod has already
applied its scale by the time the handler runs and the offset is defined in the shared
dimension's coordinates. `tools/verify_worlds.py` runs the real arithmetic over all 90
(dimension, pocket) combinations and asserts the player lands within half a block of where they
started - and separately asserts that the old flat subtraction still produces the ~1M-block
error, so the regression is named rather than merely absent.

**3. The remembered origin is now persisted.** It lived only in a HashMap, so logging out inside
a shared dimension and restarting lost it - and then leaving applied no offset at all and left
the player a million blocks from home. It now also goes in the player's NeoForge persistent data.
