# Balance

Four decisions, taken deliberately rather than drifted into.

## 1. Faithful to each pack, not a unified curve

Every pocket dimension keeps the difficulty curve its standalone pack was designed around. The
hub is a **container**, not a rebalance.

That makes most of the balancing work *verification* rather than redesign, and it is the same
principle `PARITY.md` has been enforcing all along — the quest ladders, the mod sets and the
starting conditions each came from a real pack, and there is no reason to flatten them into one
shape. A player picking the Gauntlet is choosing a combat pack; a player picking Skyblock is
choosing a scarcity pack. Those are supposed to feel different.

Rejected: a single unified curve (overrides what made each pack distinct) and an easy→hard ladder
across the eleven (turns the hub itself into the game rather than a launcher for eleven of them).

## 2. All arches open from the start

No pocket dimension is gated behind another. Walk through whichever arch you like on a brand new
world.

This is what the build already did, and it is also what keeps the testing loop usable — a
sequential unlock would mean ten of eleven arches sealed on every fresh world.

## 3. Difficulty — per pocket dimension, and the reason is mechanical

Minecraft difficulty is a property of the **world**: one value in `level.dat` for everything. So
"hard in the Gauntlet, peaceful in the hub" cannot be configured — it has to be applied as you
travel. `PocketDifficulty` does that, on the dimension change and re-checked once a second
because a command or another mod can move it underneath us.

**Why hard is the majority.** A villager killed by a zombie converts to a zombie villager 100% of
the time on HARD, only sometimes on NORMAL, and never on EASY — and curing a converted villager
is what grants the permanent trading discount a trading hall is built around. So every pocket
dimension where a villager hall is viable is HARD. The three on NORMAL are the ones whose premise
*fights* a trading hall, not the ones meant to be gentle.

| Difficulty | Pocket dimensions | Reason |
|---|---|---|
| **Hard** | survival · lostcities · netherbound · caveblock · oceanblock · gauntlet · horror | Villager halls viable, so 100% zombification is wanted. Gauntlet and horror also simply exist to punish. |
| **Normal** | skyblock · onechunk · oneblock | Premise fights a trading hall: a void start, a single 16×16 chunk, one regenerating block. Hard buys nothing and only punishes the opening. |
| **Peaceful** | the hub · redstone land | Creative sandboxes. No hostiles, no hunger. |

7 of 10 hard, 3 normal — "most hard, a few normal", which is what was asked for.

Each pocket's nether and end **inherit** its difficulty (same rule as `PocketSkins`), so
`hub:survival_nether` is hard without being listed. 32 dimensions resolve: 12 explicit, 20
inherited, none falling through to the default.

Single player is the designed case, and the limitation is worth stating rather than hiding:
because the setting is global, several players spread across pocket dimensions have only one
value available. It follows whoever changed dimension last. No amount of cleverness makes a
single global field per-player.

If the world's difficulty is **locked**, this does nothing and says so once in the log. That is a
deliberate choice by whoever locked it.

## 4. Recipe gating — premise protection only, and the audit found exactly one real break

The hub is the union of eleven packs, so every pocket dimension can suddenly see **91–129
namespaces its own pack never had**. The temptation is to deny all of them per pocket. That was
considered and rejected: it invents rules the originals never had, and produces frustrating dead
ends across 290 mods.

So the rule is narrower — deny only where craftability *defeats the premise*, and derive it from
what each standalone pack actually shipped rather than from taste. Diffing all ten standalone
instances against the hub turned up one genuine break:

**Ex Deorum.** Owned legitimately by skyblock, caveblock, oceanblock, onechunk and netherbound —
sieving is their resource ladder. **Not** owned by survival, lostcities or gauntlet, which are the
161-jar exploration group. In the hub those three could otherwise sieve dirt for diamonds, which
is a strict shortcut past the ore-mining progression they were built around. Now denied there.

| Pocket | Denied | Why |
|---|---|---|
| hub | `*` | A creative lobby; nothing should be crafted there at all |
| horror | 91 namespaces | Its standalone deliberately stripped 111 mods — that scarcity *is* the premise |
| oneblock | `exdeorum:*` | Its standalone deliberately dropped Ex Deorum; sieves undercut "the block is the only source" |
| survival · lostcities · gauntlet | `exdeorum:*` | **New.** Their standalone packs never had it; sieving bypasses ore mining |
| skyblock · caveblock · oceanblock · onechunk · netherbound | — | They own Ex Deorum legitimately |

**What is deliberately NOT denied.** The exploration group's own mods — Twilight Forest, the
Aether, Iron's Spellbooks — are left craftable in the block packs. Their items need materials from
dimensions `PocketWorlds` already refuses entry to, so they gate themselves; denying them as well
would be belt-and-braces that only adds dead ends. Likewise AE2, Mekanism and Woot are left
available to survival/lostcities/gauntlet: they change those packs' character, but there is no
scarcity premise there for them to bypass.

### The check that makes this safe

Blocking a recipe a quest requires produces a dead end that surfaces hours later with no error
anywhere. So `tools/verify_balance.py` cross-references **every** deny pattern against the quest
chapters of that same pocket dimension:

```
survival       1 patterns, 13 chapters -> no quest references any denial
lostcities     1 patterns,  8 chapters -> no quest references any denial
gauntlet       1 patterns,  8 chapters -> no quest references any denial
oneblock       1 patterns,  8 chapters -> no quest references any denial
horror        91 patterns,  6 chapters -> no quest references any denial
```

95 deny patterns across 10 pocket dimensions, zero collisions with the 699-quest book.

## 5. Starter kits — most pockets get nothing

| Pocket dimension | Start | Why |
|---|---|---|
| the hub · redstone | nothing | Creative sandboxes |
| **survival** | nothing | A survival start is supposed to be a survival start. It used to hand out stone tools, bread, torches and saplings; that is gone. |
| **gauntlet** | nothing | Explicitly empty. The briefing still prints — that is *information*, not equipment. Everything the first Gate Pearl needs (redstone, two mushrooms, an ender pearl, three bottles) is obtainable in its own amplified terrain, so an empty start is a grind rather than a dead end. |
| horror | nothing | Its premise is being under-equipped |
| oneblock | nothing | Standard for the gamemode — the block is the only source |
| skyblock · caveblock · oceanblock · onechunk | stocked chest in the starting structure | A kit *as well* would double the start |
| lostcities | iron pickaxe, stone sword, torches, bread, ladders | Kept. You spawn in a ruined city to scavenge, and the ladders in particular are what make a tower descendable. |
| netherbound | stone pickaxe, crafting table, cooked porkchop, torches | Kept, deliberately thin. Its premise is scavenging, but arriving empty-handed somewhere with no trees is a dead end rather than a challenge. |

One implementation note worth keeping: `give <player> minecraft:air` is an **invalid item**, so
writing it as a way of saying "no kit" fails silently through `runCommandSilent`. The gauntlet
branch is genuinely empty instead, and it no longer announces a kit it did not give.

## Smoke-test commands

Two op-only KubeJS commands exist purely so the gates above can be tested without grinding for
materials, since that is the only reason a test would get skipped:

- **`/tftest`** — exactly fills the hotbar with a Twilight Forest portal: an iron shovel, four
  water buckets (they do not stack), 64 grass blocks, 16 saplings, 16 poppies, 3 diamonds. Every
  item was read out of the mod's own tags — `portal/fluid.json`, `portal/edge.json`,
  `portal/decoration.json`, `portal/activator.json` — not remembered.
- **`/extest`** — crafting table, oak planks, slabs, sticks, string and dirt: the inputs to
  `exdeorum:oak_sieve` (4 planks + 1 slab + 2 rods) and `exdeorum:string_mesh` (9 string), read
  from the recipe JSONs. It also prints whether the *current* dimension should DENY or ALLOW the
  craft — and `verify_testkits.py` asserts that inline prediction still matches
  `pocketrules.json`, because a test command that confidently lies is worse than none.

`commandRegistry` only fires at **server start**, so a full restart is needed after editing —
`/kubejs reload server_scripts` leaves the old commands registered and lies about it.

## Still open

- **Quest reward economy.** 699 quests across 83 chapters, rewards inherited from eleven separate
  books. Deliberately left alone: they were balanced when each pack was built, inventories are
  already fully separated per pocket, so them behaving exactly as they did standalone *is* the
  intended outcome under decision 1.
- **Mob health and damage scaling** — left to the vanilla difficulty setting by decision, rather
  than per-mod mob configs.
- **onechunk and netherbound starts** were the two nobody was certain about. onechunk keeps its
  stocked chest and netherbound its thin kit; both are one line to change if they feel wrong in
  play.
