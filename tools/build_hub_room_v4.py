# -*- coding: utf-8 -*-
"""The hub, v4 - rebuilt as a proper hall, sized for ten pocket dimensions.

Terminology used throughout (and in the generated comments):
  the hub            - the master dimension, hub:hub. Never called a pocket dimension.
  pocket dimension   - one per gamemode/modpack, hub:<name>.
  real dimensions    - nether / overworld / end, always named by the pocket dimension they sit
                       inside: "the skyblock nether", hub:skyblock_nether.

What changed from v3:
  - Ten arches instead of eight, five per wall, so One Block and Horror have somewhere to go.
    The two unwired ones are built SEALED (crying obsidian behind a frame) rather than left as
    holes, so the hall reads as finished with two doors not yet opened.
  - A real room instead of a slab: a raised central dais, a lantern-lit colonnade between the
    arches, overhead beams, a bordered floor with a centre aisle, and a recessed back panel
    behind every arch so each one reads as an alcove in its pocket dimension's material.
  - Arch coordinates are emitted from here and written into hub_portals.js by the same script,
    so the geometry and the travel detection cannot drift apart. v3 relied on me keeping two
    files in sync by hand.

The portal blocks now have an item form (see hub_blocks.js), so this layout can be remodelled
by hand in creative afterwards - middle-click a portal to grab it.
"""
import io
import os
import re
import sys

import nbt
from nbt import Int

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances\The Hub\minecraft"
D = os.path.join(MC, "kubejs", "data", "hub")

#        pocket dim      frame material                     back panel                       light
THEME = [
    ("skyblock",    "minecraft:quartz_bricks",        "minecraft:smooth_quartz",        "minecraft:sea_lantern"),
    ("survival",    "minecraft:stripped_oak_wood",    "minecraft:oak_planks",           "minecraft:lantern"),
    ("caveblock",   "minecraft:polished_deepslate",   "minecraft:deepslate_bricks",     "minecraft:glowstone"),
    ("netherbound", "minecraft:red_nether_bricks",    "minecraft:nether_bricks",        "minecraft:shroomlight"),
    ("oceanblock",  "minecraft:prismarine_bricks",    "minecraft:dark_prismarine",      "minecraft:sea_lantern"),
    ("lostcities",  "minecraft:cracked_stone_bricks", "minecraft:stone_bricks",         "minecraft:redstone_lamp"),
    ("onechunk",    "minecraft:moss_block",           "minecraft:mossy_stone_bricks",   "minecraft:glowstone"),
    ("gauntlet",    "minecraft:gilded_blackstone",    "minecraft:polished_blackstone",  "minecraft:gold_block"),
    # not yet wired - no pocket dimension exists for these two, so they are sealed
    ("oneblock",    "minecraft:copper_block",         "minecraft:cut_copper",           "minecraft:ochre_froglight"),
    ("horror",      "minecraft:blackstone",           "minecraft:polished_basalt",      "minecraft:soul_lantern"),
]
LIVE = {"skyblock", "survival", "caveblock", "netherbound", "oceanblock",
        "lostcities", "onechunk", "gauntlet"}

HALF_X, HALF_Z = 26, 14
WALL_Z = 12
XS = [-20, -10, 0, 10, 20]          # five arches per wall
PILLARS = [-25, -15, -5, 5, 15, 25]
PLACE = (-HALF_X, 64, -HALF_Z)


class Build:
    def __init__(self):
        self.cells = {}

    def set(self, x, y, z, name, props=None):
        self.cells[(x, y, z)] = (name, tuple(sorted((props or {}).items())))

    def emit(self):
        xs = [p[0] for p in self.cells]
        ys = [p[1] for p in self.cells]
        zs = [p[2] for p in self.cells]
        ox, oy, oz = min(xs), min(ys), min(zs)
        palette, pidx, blocks = [], {}, []
        for (x, y, z), (name, props) in sorted(self.cells.items()):
            key = (name, props)
            if key not in pidx:
                e = {"Name": name}
                if props:
                    e["Properties"] = {k: v for k, v in props}
                pidx[key] = len(palette)
                palette.append(e)
            blocks.append({"pos": [Int(x - ox), Int(y - oy), Int(z - oz)],
                           "state": Int(pidx[key])})
        return {"size": [Int(max(xs) - ox + 1), Int(max(ys) - oy + 1), Int(max(zs) - oz + 1)],
                "entities": [], "blocks": blocks, "palette": palette,
                "DataVersion": Int(2730)}


b = Build()
OX, OZ = HALF_X, HALF_Z     # template-local offset so nothing is negative

FLOOR = "minecraft:polished_deepslate"
RIM = "minecraft:polished_blackstone"
AISLE = "minecraft:chiseled_polished_blackstone"
DAIS = "minecraft:polished_deepslate_bricks"
PILLAR = "minecraft:polished_blackstone"
BEAM = "minecraft:polished_blackstone_bricks"

# ---- floor: bordered slab with a centre aisle ----
for dx in range(-HALF_X, HALF_X + 1):
    for dz in range(-HALF_Z, HALF_Z + 1):
        edge = abs(dx) == HALF_X or abs(dz) == HALF_Z
        block = RIM if edge else FLOOR
        if not edge and dz == 0:
            block = AISLE                       # aisle running the length of the hall
        b.set(OX + dx, 0, OZ + dz, block)

# ---- central dais, raised one step ----
for dx in range(-3, 4):
    for dz in range(-3, 4):
        if abs(dx) + abs(dz) <= 4:
            b.set(OX + dx, 1, OZ + dz, DAIS)
b.set(OX, 2, OZ, "minecraft:sea_lantern")
for dx, dz in ((-3, 0), (3, 0), (0, -3), (0, 3)):
    b.set(OX + dx, 2, OZ + dz, "minecraft:lantern")

# ---- colonnade: pillars between the arches, with lights ----
for side in (-1, 1):
    cz = side * WALL_Z
    for px in PILLARS:
        for dy in range(1, 7):
            b.set(OX + px, dy, OZ + cz, PILLAR)
        b.set(OX + px, 7, OZ + cz, BEAM)
        b.set(OX + px, 5, OZ + cz + (-side), "minecraft:lantern")
    # overhead beam tying the colonnade together
    for dx in range(-HALF_X, HALF_X + 1):
        b.set(OX + dx, 7, OZ + cz, BEAM)

# ---- the ten arches ----
doors = []
for i, (name, frame, panel, light) in enumerate(THEME):
    side = -1 if i < 5 else 1
    cx = XS[i % 5]
    cz = side * WALL_Z
    live = name in LIVE

    for dy in range(1, 6):                       # columns
        b.set(OX + cx - 2, dy, OZ + cz, frame)
        b.set(OX + cx + 2, dy, OZ + cz, frame)
    for dx in range(-2, 3):                      # lintel
        b.set(OX + cx + dx, 6, OZ + cz, frame)
    b.set(OX + cx, 7, OZ + cz, light)            # keystone light above the beam line

    for dx in range(-2, 3):                      # recessed back panel -> reads as an alcove
        for dy in range(1, 6):
            b.set(OX + cx + dx, dy, OZ + cz + side, panel)

    for dx in range(-1, 2):                      # threshold
        b.set(OX + cx + dx, 0, OZ + cz, light if dx == 0 else frame)

    for dx in range(-1, 2):                      # the opening itself
        for dy in range(1, 5):
            if live:
                b.set(OX + cx + dx, dy, OZ + cz, "hub:portal_" + name)
            else:
                # sealed: no pocket dimension exists yet, so the door is visibly shut
                b.set(OX + cx + dx, dy, OZ + cz, "minecraft:crying_obsidian")
    doors.append((name, cx, cz, live))

root = b.emit()
p = os.path.join(D, "structure", "hub_room.nbt")
n = nbt.save(p, root)
chk = nbt.load(p)
assert chk["size"] == root["size"] and len(chk["blocks"]) == len(root["blocks"])
print("hub_room.nbt  size=%s  blocks=%d  palette=%d  %d bytes" % (
    "x".join(str(int(v)) for v in root["size"]), len(root["blocks"]),
    len(root["palette"]), n))

print("\n%-13s %-7s %-7s %s" % ("POCKET DIM", "X", "Z", "STATE"))
print("-" * 42)
for name, cx, cz, live in doors:
    print("%-13s %-7d %-7d %s" % (name, cx, cz, "portal" if live else "SEALED"))

live_doors = [(n_, x, z) for n_, x, z, l in doors if l]
print("\nlive arches: %d   sealed: %d" % (len(live_doors), len(doors) - len(live_doors)))

# ---- push the coordinates into hub_portals.js so the two cannot drift ----
JS = os.path.join(MC, "kubejs", "server_scripts", "hub_portals.js")
s = io.open(JS, encoding="utf-8").read()
block = []
for idx, (name, cx, cz) in enumerate(live_doors):
    kw = "if" if idx == 0 else "else if"
    block.append("      %s (near(px, %d) && near(pz, %d)) hit = '%s';" % (kw, cx, cz, name))
new_block = "\n".join(block)

start = s.index("      if (near(px,")
end = s.index("    }", start)
s = s[:start] + new_block + "\n" + s[end:]
io.open(JS, "w", encoding="utf-8").write(s)
print("\nhub_portals.js arch coordinates rewritten from this build")

# verify they now agree
got = dict((m[2], (int(m[0]), int(m[1]))) for m in
           re.findall(r"near\(px, (-?\d+)\) && near\(pz, (-?\d+)\)\) hit = '(\w+)'", s))
bad = [n_ for n_, x, z in live_doors if got.get(n_) != (x, z)]
print("   script arches        : %d" % len(got))
print("   every live arch wired: %s %s" % (not bad, bad or ""))
ys = sorted({64 + dy for dy in range(1, 5)})
print("   portal world Y range : %d..%d  (script detects 65..68)" % (min(ys), max(ys)))
assert not bad and min(ys) == 65 and max(ys) == 68
assert len(got) == 8, got
print("\nplace corner: %s" % (PLACE,))
