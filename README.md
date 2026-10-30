# The Hub

Every pack we built, merged into one instance. Each premise lives in its own **pocket
dimension**, and inside each pocket the normal dimensions exist separately — skyblock's End is
not survival's End, but both are reachable. Portals in portals.

- **Instance:** `%APPDATA%\PrismLauncher\instances\The Hub\`
- **MC / loader:** 1.21.1, NeoForge 21.1.265
- **Mods:** 247 jars / 232 declared mod ids, no duplicates
- **Quests:** one book — 83 chapters, 699 quests, 10 chapter groups

## Terminology

Used exactly, everywhere in this project:

- **the hub** — the master dimension, `hub:hub`. Never called a pocket dimension.
- **pocket dimension** — one per gamemode/modpack added to the hub (`hub:skyblock`, …).
- **real dimensions** — nether, overworld, end. Always denoted by the pocket dimension they sit
  inside: *the skyblock nether* (`hub:skyblock_nether`), *the survival end* (`hub:survival_end`).
  Never a bare "the nether".

## The ten pocket dimensions

| Pocket | Dimension | Start | Quests |
|---|---|---|---|
| Skyblock | `hub:skyblock` | island + chest | 98 |
| Survival | `hub:survival` | terrain, kit | 182 |
| Caveblock | `hub:caveblock` | carved pocket in solid rock | 75 |
| Netherbound | `hub:netherbound` | nether surface, thin kit | 59 |
| Oceanblock | `hub:oceanblock` | island + chest | 55 |
| Lost Cities | `hub:lostcities` | ruined city, kit | 50 |
| One Chunk | `hub:onechunk` | single 16×16 chunk | 51 |
| The Gauntlet | `hub:gauntlet` | terrain, combat kit | 44 |

Each also has its own **real dimensions** — `hub:<pocket>_nether` and `hub:<pocket>_end` — 25 dimensions counting the hub.

The hall is built for **ten** arches. One Block and Horror have frames in place but are **sealed** (crying obsidian) until those pocket dimensions exist.

Excluded on purpose: Kewz's Cobblemon (read-only, hosted by a friend), the creative pack on the
wrong MC version, and the Fabric packs.

### One Block and Horror

| Pocket dimension | Premise | Terrain | Quests |
|---|---|---|---|
| One Block | one regenerating block over the void | `oneblock:oneblock` generator, island at origin | 52 |
| Horror | stalkers and the dark | vanilla overworld rules, **different RNG** | 33 |

**One Block** reuses the mod's own generator and its 36-biome list verbatim, and its real
dimensions are oneblock generators too — matching what the standalone pack's world preset does,
so the nether and end are also single-block worlds. The block sits at the origin at y64
(`ONEBLOCK_Y`, read out of `OneBlockChunkGenerator`), which makes landing on top of it the one
arrival cell guaranteed to be solid.

The oneblock jar ships `data/minecraft/dimension/the_nether.json` and `the_end.json`, which
**replace the vanilla real dimensions for the whole instance**. Correct for a dedicated pack,
wrong here. `kubejs/data/minecraft/dimension/` restores both, and KubeJS's datapack loads after
mods so it wins.

**Horror** needed two things nothing else did:

1. *Distinct terrain without a new worldgen.* Its noise settings are vanilla overworld with one
   field changed — `legacy_random_source: false` → `true`. Same density functions, different RNG,
   therefore different terrain from the same world seed. 76 KB copied from the client jar with
   one boolean flipped.
2. *Its mobs confined.* Mods are global in the hub, so without gating the Cave Dweller would
   stalk you in the skyblock pocket dimension. `config/pocketmobs.json` allow-lists
   `arphex:*`, `cave_dweller:*`, `the_obsessed:*`, `mnightmares:*` and `serversidehorror:*` to
   the horror pocket dimension **and both of its real dimensions** — each real dimension is a
   separate id, so listing only `hub:horror` would have confined them to its overworld.

Horror is also the only pocket dimension with an exclusive texture pack: `horror-desaturated`,
generated from vanilla, assigned to `hub:horror` alone.

## How it works

**The hub** is its own dimension (`hub:hub`), a creative lobby with eight themed arches. It is
*not* an overworld override — world presets are read at world creation, before KubeJS's virtual
datapack exists, so an override there can never apply. Dimension JSONs, by contrast, are read at
server start, which is why the pockets can be defined in KubeJS at all.

**Travel** is positional. There is no safe walkable vanilla portal block —
`minecraft:nether_portal` hands travel to vanilla nether code and `end_gateway` is a block
entity with its own rules — so the arches are filled with eight custom inert blocks (the
Twilight Forest portal barrier texture, hue-rotated per pocket) and `hub_portals.js` watches the
doorway cells each tick. Arch coordinates are asserted against the room structure at build time,
so the two cannot drift apart.

**Per-pocket state** comes from DimSwap (inventory, XP, ender chest, position), with
`overrides.hub.position = false` — otherwise returning to the hub restores a position *inside*
an arch and loops you until you die. Gamemode is deliberately *not* DimSwap's: creative in the
hub, survival in pockets, enforced by `hub_gamemode.js`, because deterministic beats remembered.

**Per-pocket nether/end** comes from Dimension Link. All three keys (`overworld`, `the_nether`,
`the_end`) must be set per `[[worlds]]` entry; writing only `overworld` silently routes every
pocket to the shared vanilla nether.

**Quest gating** is PocketQuests (`mod-src/`), a small mixin mod on
`TeamData.setProgress`: a chapter whose filename starts with `<pocket>_` only progresses while
you stand in one of that pocket's dimensions. Chapters matching no prefix are never blocked.

**Seeding** happens once at world load, not on first entry. `place template` into an unvisited
dimension's unloaded chunks fails silently, and `runCommandSilent` eats the error — that is
exactly why Oceanblock had no island. `/hubseed` re-runs it without deleting the world.

## PocketQuests 1.8.0 — the custom mod

`mod-src/` is a purpose-written NeoForge mod doing three things vanilla and the mod ecosystem
cannot do per-dimension. It compiles against the real Minecraft classes via
`libraries/net/minecraft/client/1.21.1-*/client-1.21.1-*-srg.jar`, which holds the full game
with official names — that jar is what makes all of this possible rather than reflection
guesswork.

**1. Quest gating** (`TeamDataMixin` -> `PocketGate`). Mixin on `TeamData.setProgress`: a chapter
whose filename starts with `<pocket>_` only progresses while a team member stands in one of that
pocket's dimensions. Config `config/pocketquests.json`. `required` — a silent failure here would
be invisible, so it crashes loudly instead.

**2. Crafting gating** (`CraftingMenuMixin` -> `PocketRules`). Recipes are global: they load once
per datapack reload and have no idea where anyone is standing, so per-dimension recipes cannot be
expressed as recipes at all. The gate sits on
`CraftingMenu.slotChangedCraftingGrid(AbstractContainerMenu, Level, Player, CraftingContainer,
ResultContainer, RecipeHolder)` — static, and **called by `InventoryMenu` too**, so one injection
covers both the crafting table and the 2x2 inventory grid. Injected at RETURN, the result is
cleared, so the output slot simply stays empty: the craft is impossible rather than
possible-then-confiscated, and nothing is ever spent on it.

Config `config/pocketrules.json`, matched against the **result item id** because that is how a
person thinks about it. A trailing `*` wildcards, so `exdeorum:*` bans a mod and `*` bans
everything. Only `hub:hub` is filled in (`["*"]` — it is a creative lobby, and it doubles as the
easiest way to confirm the gate works). The pocket rules are gameplay decisions, left empty.

Does **not** cover furnaces, smithing tables, stonecutters or modded machine recipes — different
menus.

**3. Per-dimension resource packs and shaders** (`client/PocketSkins`). Both are global client
state in vanilla, so the only way to vary them per dimension is to change the global state and
reload. Config `config/pocketskins.json`.

- Resource packs: `Minecraft.getResourcePackRepository().setSelected(...)` +
  `reloadResourcePacks()`. `vanilla` is always first; an uninstalled pack id is skipped with a log
  line rather than wiping the selection.
- Shaders: Iris's **public API (IrisApi v0) can only toggle shaders on and off** — it cannot
  select a pack. So this reaches `Iris.getIrisConfig().setShaderPackName(...)`, `.save()` and
  `Iris.reload()`, which are public but internal, **by reflection** so a pack without Iris still
  loads the class and just skips the shader half.

**The two halves cost wildly different amounts, so they are now scheduled differently.** An
earlier draft of this file claimed the whole thing cost "roughly 2–5 seconds", which was wrong by
orders of magnitude and is worth recording as the reason for the design.

Shaders are cheap — `Iris.reload()` only recompiles the shaderpack, never touching the resource
manager — so the shader applies **immediately** on the dimension change. That is the instant
feedback walking through an arch.

Textures are not. `reloadResourcePacks()` re-stitches every texture atlas, re-parses every
GeckoLib animation, regenerates Every Compat's textures and rebuilds the **entire JEI index**, on
the render thread. Running that *during* a dimension change, while the server was still
generating chunks for a dimension nobody had visited, produced a **thirty-minute hang**. The cost
was never the problem by itself; stacking it on terrain loading was.

So the texture half is **deferred**. It is queued on the dimension change and fires only once the
`ReceivingLevelScreen` is gone, no loading overlay is up, the player is alive, their chunk is
loaded, and all of that has held for `switchDelayTicks` (60 = 3s) consecutive ticks — any of them
going false resets the counter. To be precise about what that buys: deferring does **not** make
the reload faster, it makes it a defined pause after you land instead of an open-ended hang
mid-teleport. The reload is now **timed**, and the real figure is logged and echoed to chat —
measure, don't guess.

**A pack is a property of the pocket dimension.** A real dimension with no entry of its own
inherits its pocket's skin (`PocketSkins.skinFor`), so `hub:skyblock_nether` follows
`hub:skyblock` automatically. This replaced 32 hand-written entries that were already wrong on
the first try: `hub:horror` had the desaturated pack and `hub:horror_nether` had nothing, so
dropping into the horror nether fell through to the default and reloaded *into vanilla* — losing
the look and paying a full reload to lose it, then another on the way back. The same trap was
sitting under skyblock, onechunk, caveblock, gauntlet and oceanblock.

**Cost scales with transitions, not with packs.** A reload happens only when the desired pack set
*differs* from what is already selected, so two pocket dimensions sharing a pack switch between
each other for free, and an empty list (vanilla) is a perfectly good shared baseline. Travel goes
through the hub, so a round trip to a pocket with its own pack costs two reloads and one sharing
the hub's costs none. `tools/verify_skins.py` prints exactly which transits pause, resolves the
inheritance the same way the mod does, and checks every pack and shader name against what is
actually installed — a typo'd pack id is otherwise skipped with one log line nobody reads.

`PocketSkins` and `PocketBook` fail **silently** by design; the two gates do not. A book on the
wrong chapter or an unswapped shader is a cosmetic annoyance — ungated progress is invisible.


### PocketEffects — ambient horror, fenced

`PocketMobs` fences horror *creatures*. It cannot touch the mods that have no entity at all and
work by acting on the world or the chat. Those were global, which is how **"Help me" appeared in
chat in redstone land** — a creative redstone sandbox. Two mods, two shapes, and neither has a
dimension option of its own.

**Horror Messages** is an MCreator mod, so its logic is a static procedure — and an unusually
tidy one to gate. Both public entry points, the `LevelTickEvent` handler and the
`/forcehorrormessage` command, funnel into a single private
`execute(Event, LevelAccessor)`. `HorrorMessagesMixin` cancels at the head of that: one
injection covers the timer and the command, before the cooldown bookkeeping runs, so a
suppressed message is not also a consumed one. The level arrives as an argument, so the test is
exact — the message is dropped for the level it was headed to, not for the server.

**Server-Side Horror** has no such funnel. Its effects are inlined into its *own* mixins on
`MinecraftServer.tickServer`, `ServerLevel.tickServer` and `ServerPlayer.tick`, so there is no
one method to cancel and no dimension config to set. Removing it from the hub was the obvious
call and the wrong one: every effect is read from a `public static boolean <effect>_enable`
field, fresh each tick. So `PocketEffects` flips the switches instead — all 23 of them restored
to their configured values while a player is in a horror dimension, forced false otherwise.
Nothing is patched, the mod behaves exactly as its own config says whenever it is live, and it
comes with a side benefit no mixin would have given: **a horror base is no longer burned down or
stripped of torches while you are away in another pocket dimension**, because the effects are
off whenever nobody is there to see them.

The configured values are re-read from the live fields on every tick where the switches are
*up* — exactly when those fields hold the mod's values rather than ours — so an in-game config
reload is picked up instead of being overwritten from a stale snapshot. Nothing happens until a
player is online, and an **unlisted key is allowed everywhere**, so a mod nobody configured is
never touched.

Config: `config/pocketeffects.json`. Verified by `tools/verify_effects.py`, which checks the
mixin descriptor against the real target jar (the injection carries `require = 0`, so a mismatch
would otherwise fail silently) and runs 16 decision assertions against the real config file.

## Gotchas worth remembering

**NeoForge reverts external config edits while the game is running.** A config pass wrote six
files, the verification confirmed all six, and `cave_dweller/server_config.toml` was back to its
old value moments later — NeoForge had rewritten it from its in-memory copy. Server configs are
bound to the loaded world and are the ones it actively keeps in sync; the common configs
happened to survive, but that is luck. `tools/fix_dimension_configs.py` now refuses to write
while `javaw.exe` is running.

**`java` on PATH here is a JRE 8 shim** (Oracle `java8path`) while `javac` is Adoptium 21, so
anything that compiles then runs must take `javac`'s sibling `java` rather than trusting PATH.

**Heredocs in this shell mangle apostrophes.** Writing Java or Python with an apostrophe in a
comment through `<<'EOF'` fails with "unexpected EOF"; use a file-writing tool instead.


Every KubeJS script here is IIFE-wrapped, keeps its own tick counter, and contains **zero
loops**. That is not style — shared global scope, a non-existent `player.age` binding, and
Rhino's refusal to iterate objects (and, here, indexed arrays) each produced a script that
logged "loaded, 0 errors" and did nothing. `commandRegistry` also only fires at server start,
so debug commands are stale after `/kubejs reload` and will lie to you. Restart to test.

## Layout

- `mod-src/` — PocketQuests source (javac 21, built against `neoforge-21.1.265-universal.jar`)
- `tools/` — build and validation scripts
