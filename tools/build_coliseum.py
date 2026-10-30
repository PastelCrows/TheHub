# -*- coding: utf-8 -*-
"""The Coliseum, for the gauntlet pocket dimension.

The gauntlet is run-based: craft a Gate Pearl, drop it somewhere with room, survive every wave.
Until now "somewhere with room" meant whatever clearing you could find in amplified terrain,
which is a poor stage for the one thing the pocket dimension is about. This is a purpose-built
arena for it.

Design decisions:

  - An OCTAGON, not a circle. A true circle in a structure file means either jagged stepping or
    an enormous palette of stairs and slabs; an octagon reads as classical architecture, tiles
    cleanly, and keeps every wall axis-aligned so cover actually works as cover.

  - Cover inside the arena, because "terrain to fight on and hide behind" was the ask: four
    raised platforms reachable by steps, eight broken pillars, and two low walls. All of it is
    off-centre so the middle stays clear for a gateway - Gateways to Eternity spawns waves in a
    radius around the pearl, and blocking that spawn area breaks the wave rather than making it
    interesting.

  - Three tiers of seating rising outside the arena wall. Purely architectural, but it is what
    makes the thing read as a coliseum from outside rather than as a walled pit.

  - Four entrance tunnels on the cardinal axes, cut through the wall and the seating, so you can
    always get out of the arena in a straight line.

  - A staging alcove on the north side with a crafting table and chests - the quest book's first
    chapter is literally called "Between Runs", and this is where that happens.

It is placed onto a FLATTENED PAD rather than into the terrain: hub_setup.js clears air above and
fills stone below before placing it. That keeps the gauntlet's amplified terrain (and therefore
the scouting chapter) while giving the arena a deliberate, level stage.
"""
import io
import os
import sys

import nbt
from nbt import Int

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances\The Hub\minecraft"
D = os.path.join(MC, "kubejs", "data", "hub")

R_FLOOR = 20          # arena floor radius (octagon)
WALL_H = 6            # arena wall height above the floor
TIERS = 3             # rings of seating
TIER_W = 4            # depth of each tier
TIER_RISE = 2         # height gained per tier

SAND = "minecraft:smooth_sandstone"
FLOOR_A = "minecraft:sand"
FLOOR_B = "minecraft:suspicious_sand"
WALL = "minecraft:polished_blackstone_bricks"
WALL_TRIM = "minecraft:chiseled_polished_blackstone"
SEAT = "minecraft:smooth_stone"
SEAT_TRIM = "minecraft:stone_bricks"
PILLAR = "minecraft:polished_blackstone"
GOLD = "minecraft:gilded_blackstone"
LIGHT = "minecraft:redstone_lamp"
LANTERN = "minecraft:lantern"


def in_octagon(dx, dz, r):
    """Octagon = square clipped by the two diagonals. Cheap, and axis-aligned where it matters."""
    return abs(dx) <= r and abs(dz) <= r and abs(dx) + abs(dz) <= int(r * 1.45)


class Build:
    def __init__(self):
        self.cells = {}

    def set(self, x, y, z, name):
        self.cells[(x, y, z)] = name

    def emit(self):
        xs = [p[0] for p in self.cells]
        ys = [p[1] for p in self.cells]
        zs = [p[2] for p in self.cells]
        ox, oy, oz = min(xs), min(ys), min(zs)
        palette, pidx, blocks = [], {}, []
        for (x, y, z), name in sorted(self.cells.items()):
            if name not in pidx:
                pidx[name] = len(palette)
                palette.append({"Name": name})
            blocks.append({"pos": [Int(x - ox), Int(y - oy), Int(z - oz)],
                           "state": Int(pidx[name])})
        return ({"size": [Int(max(xs) - ox + 1), Int(max(ys) - oy + 1), Int(max(zs) - oz + 1)],
                 "entities": [], "blocks": blocks, "palette": palette,
                 "DataVersion": Int(2730)},
                (ox, oy, oz))


b = Build()
R_OUT = R_FLOOR + 2 + TIERS * TIER_W            # outermost extent
OX = OZ = R_OUT                                  # template-local offset, nothing negative

# ---------------------------------------------------------------- arena floor
for dx in range(-R_FLOOR, R_FLOOR + 1):
    for dz in range(-R_FLOOR, R_FLOOR + 1):
        if not in_octagon(dx, dz, R_FLOOR):
            continue
        # a little variation so 1200 blocks of flat sand does not read as a texture bug
        block = FLOOR_B if (dx * 7 + dz * 11) % 29 == 0 else FLOOR_A
        b.set(OX + dx, 0, OZ + dz, block)
        b.set(OX + dx, -1, OZ + dz, SAND)        # one course beneath, so digging shows masonry

# centre marker: where the Gate Pearl goes. Deliberately flat and open.
for dx in range(-2, 3):
    for dz in range(-2, 3):
        if abs(dx) + abs(dz) <= 2:
            b.set(OX + dx, 0, OZ + dz, GOLD)

# ---------------------------------------------------------------- arena wall
wall_r = R_FLOOR + 1
ENTRANCE_HALF = 3
for dx in range(-wall_r, wall_r + 1):
    for dz in range(-wall_r, wall_r + 1):
        if not in_octagon(dx, dz, wall_r):
            continue
        if in_octagon(dx, dz, R_FLOOR):
            continue                              # interior, already floor
        # leave the four cardinal entrances open
        if abs(dz) <= ENTRANCE_HALF and dx > 0:
            continue
        if abs(dz) <= ENTRANCE_HALF and dx < 0:
            continue
        if abs(dx) <= ENTRANCE_HALF and dz > 0:
            continue
        if abs(dx) <= ENTRANCE_HALF and dz < 0:
            continue
        for dy in range(0, WALL_H):
            b.set(OX + dx, dy, OZ + dz, WALL if dy < WALL_H - 1 else WALL_TRIM)

# ---------------------------------------------------------------- seating tiers
for t in range(TIERS):
    inner = R_FLOOR + 2 + t * TIER_W
    outer = inner + TIER_W - 1
    base_y = WALL_H - 2 + t * TIER_RISE
    for dx in range(-outer, outer + 1):
        for dz in range(-outer, outer + 1):
            if not in_octagon(dx, dz, outer) or in_octagon(dx, dz, inner - 1):
                continue
            if abs(dz) <= ENTRANCE_HALF and abs(dx) > R_FLOOR:
                continue                          # keep the entrance tunnels clear
            if abs(dx) <= ENTRANCE_HALF and abs(dz) > R_FLOOR:
                continue
            for dy in range(base_y - 1, base_y + 1):
                b.set(OX + dx, dy, OZ + dz, SEAT if dy == base_y else SEAT_TRIM)
    # a lamp on the step edge every eighth block, so the tiers are lit at night
    for dx in range(-outer, outer + 1, 8):
        for dz in (-outer, outer):
            if in_octagon(dx, dz, outer):
                b.set(OX + dx, base_y + 1, OZ + dz, LANTERN)
    for dz in range(-outer, outer + 1, 8):
        for dx in (-outer, outer):
            if in_octagon(dx, dz, outer):
                b.set(OX + dx, base_y + 1, OZ + dz, LANTERN)

# ---------------------------------------------------------------- cover inside the arena
# Four raised platforms, off-centre, each with a step up. Something to hold and to shoot from.
for sx, sz in ((-11, -11), (11, -11), (-11, 11), (11, 11)):
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if abs(dx) + abs(dz) <= 4:
                b.set(OX + sx + dx, 1, OZ + sz + dz, PILLAR)
                b.set(OX + sx + dx, 2, OZ + sz + dz, SEAT)
    b.set(OX + sx, 3, OZ + sz, LIGHT)
    # a step so the platform is reachable without jumping twice
    for dz in range(-1, 2):
        b.set(OX + sx + (4 if sx < 0 else -4), 1, OZ + sz + dz, SEAT_TRIM)

# Eight broken pillars - partial cover you can break line of sight behind.
for px, pz, hgt in ((-17, 0, 5), (17, 0, 4), (0, -17, 5), (0, 17, 4),
                    (-7, -15, 3), (7, 15, 3), (15, -7, 3), (-15, 7, 3)):
    for dy in range(1, hgt + 1):
        b.set(OX + px, dy, OZ + pz, PILLAR)
    b.set(OX + px, hgt + 1, OZ + pz, WALL_TRIM)

# Two low walls, long enough to actually hide behind.
for dz in range(-5, 6):
    b.set(OX - 6, 1, OZ + dz, WALL)
    b.set(OX - 6, 2, OZ + dz, WALL_TRIM)
for dx in range(-5, 6):
    b.set(OX + dx, 1, OZ + 6, WALL)
    b.set(OX + dx, 2, OZ + 6, WALL_TRIM)

# ---------------------------------------------------------------- staging alcove (north)
AZ = -(R_FLOOR + 1)
for dx in range(-4, 5):
    for dz in range(-3, 1):
        b.set(OX + dx, 0, OZ + AZ + dz - 1, "minecraft:polished_blackstone")
for dx in range(-4, 5):
    for dy in range(1, 5):
        b.set(OX + dx, dy, OZ + AZ - 5, WALL)
for dz in range(-4, 1):
    for dy in range(1, 5):
        b.set(OX - 5, dy, OZ + AZ + dz - 1, WALL)
        b.set(OX + 5, dy, OZ + AZ + dz - 1, WALL)
for dx in range(-5, 6):
    b.set(OX + dx, 5, OZ + AZ - 5, WALL_TRIM)
b.set(OX - 2, 1, OZ + AZ - 3, "minecraft:crafting_table")
b.set(OX, 1, OZ + AZ - 3, "minecraft:chest")
b.set(OX + 2, 1, OZ + AZ - 3, "minecraft:chest")
b.set(OX - 4, 2, OZ + AZ - 4, LANTERN)
b.set(OX + 4, 2, OZ + AZ - 4, LANTERN)

root, origin = b.emit()
os.makedirs(os.path.join(D, "structure"), exist_ok=True)
p = os.path.join(D, "structure", "coliseum.nbt")
n = nbt.save(p, root)
chk = nbt.load(p)
assert chk["size"] == root["size"] and len(chk["blocks"]) == len(root["blocks"])

sx, sy, sz = (int(v) for v in root["size"])
print("coliseum.nbt  size=%dx%dx%d  blocks=%d  palette=%d  %.1f KB"
      % (sx, sy, sz, len(root["blocks"]), len(root["palette"]), n / 1024.0))

# the template's local origin is (min x, min y, min z); arena floor sits at local y = 1 - oy
oy = origin[1]
floor_local_y = 0 - oy
print("\n   template-local arena floor y : %d" % floor_local_y)
print("   outermost radius             : %d blocks" % R_OUT)

# Place so the arena floor lands on y=64, and work out where to drop the player.
PLACE_Y = 64 - floor_local_y
print("\n   to put the arena floor at y 64, place corner y = %d" % PLACE_Y)
CORNER = (-(sx // 2), PLACE_Y, -(sz // 2))
print("   suggested place corner       : %s" % (CORNER,))

# arrival: just inside the south entrance, on the floor, facing the centre
cells = {}
pal = [str(e["Name"]) for e in root["palette"]]
for bl in root["blocks"]:
    q = bl["pos"]
    cells[(CORNER[0] + int(q[0]), CORNER[1] + int(q[1]), CORNER[2] + int(q[2]))] = pal[int(bl["state"])]
PASS = {"air", "cave_air", "void_air", "lantern", "torch"}


def standable(x, y, z):
    below = cells.get((x, y - 1, z), "minecraft:air").split(":")[-1]
    feet = cells.get((x, y, z), "minecraft:air").split(":")[-1]
    head = cells.get((x, y + 1, z), "minecraft:air").split(":")[-1]
    return feet in PASS and head in PASS and below not in PASS


cand = None
for z in range(R_FLOOR - 1, 0, -1):
    if standable(0, 65, z):
        cand = (0, 65, z)
        break
print("\n   arrival cell (on the floor, inside the south entrance): %s" % (cand,))
if cand:
    x, y, z = cand
    print("      below=%s" % cells.get((x, y - 1, z)))
    print("      feet =%s" % cells.get((x, y, z), "minecraft:air"))

# centre must be CLEAR so a gateway can spawn its waves
centre_clear = all(standable(dx, 65, dz) for dx in range(-2, 3) for dz in range(-2, 3)
                   if abs(dx) + abs(dz) <= 2)
print("\n   centre 5x5 standable and clear of cover: %s" % centre_clear)
assert centre_clear, "the gateway spawn area is obstructed"
assert cand, "no standable arrival cell found"

io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "coliseum_place.txt"),
        "w", encoding="utf-8").write("%d %d %d\n%d %d %d\n%d\n"
                                     % (CORNER[0], CORNER[1], CORNER[2],
                                        cand[0], cand[1], cand[2], R_OUT))
print("\nwrote coliseum_place.txt (corner, arrival, radius)")
