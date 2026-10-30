# -*- coding: utf-8 -*-
"""Verify the balance decisions: per-dimension difficulty, and that no recipe denial breaks a quest.

The dangerous half is the crafting deny-list. Blocking a recipe that a quest chapter requires
produces a dead end that only shows up when a player reaches that quest - possibly hours in, and
with no error anywhere. So section 2 reads every deny pattern and cross-references it against the
quest chapters belonging to that same pocket dimension. A pattern that matches an item a quest
mentions is reported loudly; it is the one failure here that would cost real play time.

Section 1 checks the difficulty map covers every pocket dimension, resolves inheritance the same
way PocketDifficulty does, and asserts the intent the choice was made for: HARD wherever a
villager hall is viable (100% zombification, which is what makes curing-for-discounts work), and
the two creative sandboxes PEACEFUL.
"""
import glob
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
CHAPTERS = os.path.join(MC, "config", "ftbquests", "quests", "chapters")

POCKETS = ["skyblock", "survival", "caveblock", "netherbound", "oceanblock", "lostcities",
           "onechunk", "gauntlet", "oneblock", "horror"]
SANDBOXES = ["hub", "redstone"]

failures = []


def check(label, ok, detail=""):
    print("   %-56s %s%s" % (label, "OK" if ok else "FAIL", "  " + detail if detail else ""))
    if not ok:
        failures.append(label)
    return ok


# ---------------------------------------------------------------- 1. difficulty
print("1. per-dimension difficulty")
dp = os.path.join(MC, "config", "pocketdifficulty.json")
if not check("pocketdifficulty.json present", os.path.exists(dp)):
    sys.exit(1)
diff = json.load(io.open(dp, encoding="utf-8"))
by = diff.get("byDimension") or {}
default = diff.get("default")

VALID = {"peaceful", "easy", "normal", "hard"}
bad = {k: v for k, v in by.items() if str(v).lower() not in VALID}
check("every value is a real difficulty", not bad, str(bad) if bad else "")
check("a default is set", default is not None, str(default))

dd = os.path.join(MC, "kubejs", "data", "hub", "dimension")
real_dims = {"hub:" + f[:-5] for f in os.listdir(dd) if f.endswith(".json")}


def pocket_of(dim):
    name = dim[4:]
    for suffix in ("_nether", "_end"):
        if name.endswith(suffix):
            return "hub:" + name[: -len(suffix)]
    return None


def difficulty_for(dim):
    """Mirror of PocketDifficulty.forDimension: exact, else the pocket, else default."""
    if dim in by:
        return str(by[dim]).lower(), "explicit"
    parent = pocket_of(dim)
    if parent and parent in by:
        return str(by[parent]).lower(), "inherited"
    return (str(default).lower() if default else None), "default"


missing = [p for p in POCKETS + SANDBOXES if ("hub:" + p) not in by]
check("every pocket dimension and sandbox is listed", not missing, str(missing))

# the intent: hard where a villager hall is viable, peaceful in the creative sandboxes
EXPECT_HARD = {"survival", "lostcities", "netherbound", "caveblock", "oceanblock",
               "gauntlet", "horror"}
EXPECT_NORMAL = {"skyblock", "onechunk", "oneblock"}
wrong = []
for p in POCKETS:
    got = difficulty_for("hub:" + p)[0]
    want = "hard" if p in EXPECT_HARD else "normal"
    if got != want:
        wrong.append((p, got, want))
check("villager-hall pockets are hard, the cramped three normal", not wrong, str(wrong))
for p in SANDBOXES:
    got = difficulty_for("hub:" + p)[0]
    check("%-12s is peaceful" % p, got == "peaceful", got or "")

hard = sum(1 for p in POCKETS if difficulty_for("hub:" + p)[0] == "hard")
print("   %d of %d pockets hard, %d normal, %d sandboxes peaceful"
      % (hard, len(POCKETS), len(POCKETS) - hard, len(SANDBOXES)))

# real dimensions must inherit, never silently land on the default
orphans = []
for d in sorted(real_dims):
    parent = pocket_of(d)
    if parent is None:
        continue
    got, how = difficulty_for(d)
    pgot = difficulty_for(parent)[0]
    if got != pgot:
        orphans.append((d, got, parent, pgot))
check("every real dimension matches its pocket", not orphans, str(orphans[:3]))
inherited = sum(1 for d in real_dims if difficulty_for(d)[1] == "inherited")
print("   %d dimensions: %d explicit, %d inherited"
      % (len(real_dims), len(real_dims) - inherited, inherited))

# ---------------------------------------------------------------- 2. deny list vs quests
print("\n2. no crafting denial blocks something a quest needs")
rp = os.path.join(MC, "config", "pocketrules.json")
rules = json.load(io.open(rp, encoding="utf-8")).get("denyByDimension") or {}


def matches(pattern, text):
    """A deny pattern against raw chapter text. '*' alone matches nothing here on purpose:
    the hub is a creative lobby with no quests of its own."""
    if pattern == "*":
        return False
    stem = pattern[:-1] if pattern.endswith("*") else pattern
    stem = stem.rstrip(":")
    return stem and stem in text


total_pat = 0
collisions = []
for pocket in POCKETS:
    pats = rules.get("hub:" + pocket) or []
    total_pat += len(pats)
    if not pats:
        continue
    files = sorted(glob.glob(os.path.join(CHAPTERS, pocket + "_*.snbt")))
    text = ""
    for f in files:
        text += io.open(f, encoding="utf-8", errors="replace").read()
    hit = [p for p in pats if matches(p, text)]
    print("   %-12s %3d patterns, %2d chapters -> %s"
          % (pocket, len(pats), len(files),
             "CLASH: " + ", ".join(hit[:5]) if hit else "no quest references any denial"))
    for p in hit:
        collisions.append((pocket, p))

check("no denied pattern appears in its own pocket's quests", not collisions,
      str(collisions[:4]))
print("   %d deny patterns across %d pockets" % (total_pat, len(POCKETS)))

# the three new ones, specifically
print("\n3. the Ex Deorum denial, specifically")
for pocket in ("survival", "lostcities", "gauntlet", "oneblock", "horror"):
    pats = rules.get("hub:" + pocket) or []
    has = any("exdeorum" in p for p in pats)
    check("%-12s denies exdeorum" % pocket, has)
for pocket in ("skyblock", "caveblock", "oceanblock", "onechunk", "netherbound"):
    pats = rules.get("hub:" + pocket) or []
    has = any("exdeorum" in p for p in pats)
    check("%-12s still ALLOWS exdeorum (it owns it)" % pocket, not has)

print("\n%s" % ("ALL CHECKS PASSED" if not failures else "FAILURES: " + ", ".join(failures)))
sys.exit(1 if failures else 0)
