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

## Still open

- **Quest reward economy.** 699 quests across 83 chapters, rewards inherited from eleven separate
  books. Nothing has been normalised, and under decision 1 that is arguably correct — but it has
  not been *looked at*, which is different from having been decided.
- **Starter kit generosity** per pocket, same situation.
- Difficulty here is the vanilla setting only. Per-pocket mob health/damage scaling (via the mob
  config of individual mods) has not been touched.
