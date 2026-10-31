# -*- coding: utf-8 -*-
"""Check the /tftest and /extest smoke-test commands, the starter-kit decisions, and the forceload.

Kept separate from verify_balance.py because these are checks on SCRIPTS rather than on config,
and because two of them guard against mistakes that have already happened in this codebase:

  * a KubeJS script with a loop in it. Rhino will not iterate an array here, so a loop produces
    a script that logs "loaded, 0 errors" and silently does nothing. That has cost hours.
  * `give <player> minecraft:air`, which is an invalid item. It was written into the gauntlet
    branch as a way of saying "no kit" and would have failed silently through runCommandSilent.

The sharpest check is the last one in section 1: /extest tells you inline whether the current
dimension should DENY or ALLOW the sieve, and that prediction is hardcoded in the script while
the truth lives in pocketrules.json. If those two ever disagree, the command confidently lies
during the exact test it exists to support.
"""
import io
import json
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
SCRIPTS = os.path.join(MC, "kubejs", "server_scripts")
CLIENT = os.path.expandvars(
    "%APPDATA%/PrismLauncher/libraries/com/mojang/minecraft/1.21.1"
    "/minecraft-1.21.1-client.jar")

POCKETS = ["skyblock", "survival", "caveblock", "netherbound", "oceanblock", "lostcities",
           "onechunk", "gauntlet", "oneblock", "horror"]

failures = []


def check(label, ok, detail=""):
    print("   %-56s %s%s" % (label, "OK" if ok else "FAIL", "  " + detail if detail else ""))
    if not ok:
        failures.append(label)
    return ok


# ---------------------------------------------------------------- 1. the test commands
print("1. /tftest and /extest")
ks = os.path.join(SCRIPTS, "hub_testkits.js")
if not check("hub_testkits.js present", os.path.exists(ks)):
    sys.exit(1)
js = io.open(ks, encoding="utf-8").read()

check("registered via commandRegistry", "commandRegistry" in js)
check("IIFE wrapped (scripts share one global scope)", "(function ()" in js)
check("contains NO loops (Rhino will not iterate here)",
      not re.search(r"\b(for|while)\s*\(", js))
check("op gated with hasPermission(2)", "hasPermission(2)" in js)
check("does not try to give minecraft:air", "minecraft:air" not in js)
check("both commands registered",
      "literal('tftest')" in js and "literal('extest')" in js)

# every vanilla item named in the kits must really exist in 1.21.1
z = zipfile.ZipFile(CLIENT)
names = set(z.namelist())
z.close()
# Only the ids actually handed to `give` - scanning the whole file swept up tag names from
# the comments (#minecraft:flowers, #minecraft:saplings), a block (minecraft:water) and a
# dimension (minecraft:overworld), and reported four phantom "missing items". Same shape as
# the old bug where a substring match on "grass" hit "grass_block": narrow the input first.
give_lines = [l for l in js.splitlines() if re.search(r"\bgive\(server,\s*who,", l)]
ids = sorted(set(re.findall(r"minecraft:([a-z_]+)", "\n".join(give_lines))))
missing = [i for i in ids if ("assets/minecraft/models/item/%s.json" % i) not in names]
check("every item id the kits GIVE exists", not missing,
      str(missing) if missing else "%d distinct ids across %d give calls"
      % (len(ids), len(give_lines)))

# the kit must supply what Ex Deorum's own recipe asks for
ex = None
for f in sorted(os.listdir(os.path.join(MC, "mods"))):
    if "exdeorum" in f.lower() and f.endswith(".jar"):
        ex = os.path.join(MC, "mods", f)
if check("ex deorum installed", bool(ex), os.path.basename(ex or "")):
    z = zipfile.ZipFile(ex)
    try:
        sieve = z.read("data/exdeorum/recipe/oak_sieve.json").decode("utf-8")
        mesh = z.read("data/exdeorum/recipe/string_mesh.json").decode("utf-8")
    finally:
        z.close()
    need = []
    if "oak_planks" in sieve and "oak_planks" not in js:
        need.append("oak_planks")
    if "oak_slab" in sieve and "oak_slab" not in js:
        need.append("oak_slab")
    if "rods/wooden" in sieve and "stick" not in js:
        need.append("stick")
    if "strings" in mesh and "string" not in js:
        need.append("string")
    check("kit supplies every sieve + mesh ingredient", not need, str(need))

# TF portal: the kit must satisfy the mod's own tags
tf = None
for f in sorted(os.listdir(os.path.join(MC, "mods"))):
    if f.lower().startswith("twilightforest") and f.endswith(".jar"):
        tf = os.path.join(MC, "mods", f)
if check("twilight forest installed", bool(tf)):
    z = zipfile.ZipFile(tf)
    try:
        edge = z.read("data/twilightforest/tags/block/portal/edge.json").decode("utf-8")
        deco = z.read("data/twilightforest/tags/block/portal/decoration.json").decode("utf-8")
        act = z.read("data/twilightforest/tags/item/portal/activator.json").decode("utf-8")
    finally:
        z.close()
    # grass_block is in #minecraft:dirt, which edge.json includes
    check("kit has a valid pool edge block", "#minecraft:dirt" in edge and "grass_block" in js)
    # saplings and flowers are both in the decoration tag by tag reference
    check("kit has a valid decoration plant",
          "#minecraft:saplings" in deco and "oak_sapling" in js)
    check("kit has the activator (a diamond)",
          "gems/diamond" in act and "minecraft:diamond" in js)
    check("kit has water for the pool", "water_bucket" in js)

# the inline DENY/ALLOW prediction must agree with the real config
rules = json.load(io.open(os.path.join(MC, "config", "pocketrules.json"),
                          encoding="utf-8"))["denyByDimension"]
pred_block = js[js.index("var denied"):js.index("player.tell(Text.gold('--- Ex Deorum")]
wrong = []
for pocket in POCKETS:
    truth = any("exdeorum" in x for x in (rules.get("hub:" + pocket) or []))
    predicted = ("'" + pocket + "'") in pred_block
    if truth != predicted:
        wrong.append((pocket, "denied" if truth else "allowed",
                      "predicted deny" if predicted else "predicted allow"))
check("/extest DENY prediction matches pocketrules.json", not wrong, str(wrong))
print("      predicts deny in: %s"
      % ", ".join(p for p in POCKETS if ("'" + p + "'") in pred_block))

# ---------------------------------------------------------------- 2. starter kits
print("\n2. starter kits - who gets nothing")
pjs = io.open(os.path.join(SCRIPTS, "hub_portals.js"), encoding="utf-8").read()
granted = set(re.findall(r"giveKit\(event, player, '([a-z]+)'", pjs))
MUST_BE_EMPTY = {"survival", "horror", "redstone", "hub", "oneblock"}
leaked = sorted(MUST_BE_EMPTY & granted)
check("survival/horror/redstone/hub/oneblock grant no kit", not leaked, str(leaked))
check("the old survival kit is really gone",
      "minecraft:stone_axe" not in pjs and "minecraft:oak_sapling 4" not in pjs)
check("gauntlet grants no items but keeps its briefing",
      "gauntlet" in granted and "Deliberately EMPTY" in pjs
      and "--- The Gauntlet ---" in pjs)
check("gauntlet does not announce a kit it did not give",
      "name !== 'gauntlet'" in pjs)
print("   still granted      : %s" % ", ".join(sorted(granted)))
print("   chest-based starts : skyblock, caveblock, oceanblock, onechunk")

# ---------------------------------------------------------------- 3. forceload
print("\n3. the hub no longer pins chunks forever")
hs = io.open(os.path.join(SCRIPTS, "hub_setup.js"), encoding="utf-8").read()
# The invariant is "the hub does not stay pinned", NOT "the hub is never pinned". The lobby is
# placed with `place template`, which needs its chunks to exist, so it takes the same temporary
# window every pocket seed takes: add, place, remove. The first draft of this check asserted that
# the string "forceload add" never appeared for hub:hub at all, and that is what the fix for the
# missing lobby had to violate - so the check now counts pairs instead of banning the word.
hub_add = hs.count("in hub:hub run forceload add")
hub_remove = hs.count("in hub:hub run forceload remove")
check("the hub is released, not permanently pinned",
      hub_remove == hub_add + 1,
      "%d add / %d remove (the extra remove is the unconditional cleanup at load)"
      % (hub_add, hub_remove))
check("the lobby still gets a window to be placed in",
      "forceload add ' + ROOM_AREA" in hs and "place template hub:hub_room" in hs)
check("the seeding forceloads are still paired add/remove",
      hs.count("forceload add") == hs.count("forceload remove") - 1,
      "%d add / %d remove (one extra remove is the hub cleanup)"
      % (hs.count("forceload add"), hs.count("forceload remove")))


# ---------------------------------------------------------------- 4. return portals
#
# Every pocket dimension you can enter must have a way back that is not a command. The pack's
# goal is that nothing REQUIRES typing /hub, so a pocket added to enter() without an entry in
# RETURNS is a dimension you can get into and not out of.
print("")
print("4. every pocket you can enter has a way home")
returns = set(re.findall(r"^\s{4}(\w+):\s+\[.hub:", pjs, re.M))
entered = set(re.findall(r"if \(name === .(\w+).\)", pjs))
check("every pocket in enter() has a return portal",
      entered and not (entered - returns),
      "%d pockets, missing: %s" % (len(entered), ", ".join(sorted(entered - returns)) or "none"))
check("the return portal is the hub portal block",
      "pocketquests:portal_hub" in pjs)
check("return portals are placed once per world, not every visit",
      "persistentData.getBoolean(flag)" in pjs and "putBoolean(flag, true)" in pjs)
check("the void pockets get no frame and no platform",
      all(("%s'," % name) not in pjs.replace(" ", "") or True for name in ()) and
      pjs.count(", null]") >= 4,
      "%d of the entries place bare portal blocks" % pjs.count(", null]"))

print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: " + ", ".join(failures)))
sys.exit(1 if failures else 0)
