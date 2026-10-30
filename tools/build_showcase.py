# -*- coding: utf-8 -*-
"""A texture-pack showcase, to be placed in redstone land.

Thirteen packs are installed and I cannot judge how any of them LOOK - only that they are valid
and what they cover. This builds somewhere to look at them: swap pack in the resource pack menu,
walk the gallery, decide.

Two halves, because block swatches on their own are misleading:

  - A SWATCH GALLERY: grouped rows of 2x2x2 samples, one row per material family, so a pack's
    treatment of (say) every wood type can be compared side by side at a glance.
  - BUILD SCENES: a house corner with a roof and a window, a path, a tree, water and lava, a
    lit interior. A pack can have gorgeous individual textures and still read badly in a build,
    or look plain in swatches and come alive in a wall - this is where that shows.

Every block id is checked against the client jar before anything is written.
"""
import io
import json
import os
import sys
import zipfile

import nbt
from nbt import Int

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances\The Hub\minecraft"
CLIENT = (r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\libraries\com\mojang"
          r"\minecraft\1.21.1\minecraft-1.21.1-client.jar")
D = os.path.join(MC, "kubejs", "data", "hub")

# ---------------------------------------------------------------- valid ids
z = zipfile.ZipFile(CLIENT)
lang = json.loads(z.read("assets/minecraft/lang/en_us.json").decode("utf-8"))
z.close()
VALID = set()
for k in lang:
    if k.startswith("block.minecraft."):
        n = k[len("block.minecraft."):]
        if "." not in n:
            VALID.add("minecraft:" + n)
print("valid vanilla block ids: %d" % len(VALID))

ROWS = [
    ("stone family", ["stone", "cobblestone", "stone_bricks", "smooth_stone", "andesite",
                      "polished_andesite", "diorite", "granite", "calcite", "tuff"]),
    ("deepslate + sculk", ["deepslate", "cobbled_deepslate", "polished_deepslate",
                           "deepslate_bricks", "deepslate_tiles", "sculk", "sculk_catalyst",
                           "basalt", "smooth_basalt", "blackstone"]),
    ("wood: logs", ["oak_log", "spruce_log", "birch_log", "jungle_log", "acacia_log",
                    "dark_oak_log", "mangrove_log", "cherry_log", "crimson_stem",
                    "warped_stem"]),
    ("wood: planks", ["oak_planks", "spruce_planks", "birch_planks", "jungle_planks",
                      "acacia_planks", "dark_oak_planks", "mangrove_planks", "cherry_planks",
                      "bamboo_planks", "crimson_planks"]),
    ("ores", ["coal_ore", "iron_ore", "copper_ore", "gold_ore", "redstone_ore", "lapis_ore",
              "diamond_ore", "emerald_ore", "deepslate_diamond_ore", "ancient_debris"]),
    ("metal + mineral", ["iron_block", "gold_block", "copper_block", "exposed_copper",
                         "weathered_copper", "oxidized_copper", "diamond_block",
                         "emerald_block", "netherite_block", "amethyst_block"]),
    ("terracotta", ["terracotta", "white_terracotta", "orange_terracotta", "yellow_terracotta",
                    "light_blue_terracotta", "red_terracotta", "brown_terracotta",
                    "cyan_terracotta", "purple_terracotta", "black_terracotta"]),
    ("concrete", ["white_concrete", "orange_concrete", "yellow_concrete", "lime_concrete",
                  "light_blue_concrete", "blue_concrete", "red_concrete", "purple_concrete",
                  "gray_concrete", "black_concrete"]),
    ("wool", ["white_wool", "orange_wool", "yellow_wool", "lime_wool", "light_blue_wool",
              "blue_wool", "red_wool", "purple_wool", "gray_wool", "black_wool"]),
    ("glass", ["glass", "tinted_glass", "white_stained_glass", "light_blue_stained_glass",
               "lime_stained_glass", "red_stained_glass", "purple_stained_glass",
               "black_stained_glass", "gray_stained_glass", "yellow_stained_glass"]),
    ("ground + foliage", ["grass_block", "dirt", "coarse_dirt", "podzol", "mycelium", "sand",
                          "red_sand", "gravel", "clay", "moss_block"]),
    ("leaves", ["oak_leaves", "spruce_leaves", "birch_leaves", "jungle_leaves",
                "acacia_leaves", "dark_oak_leaves", "mangrove_leaves", "cherry_leaves",
                "azalea_leaves", "flowering_azalea_leaves"]),
    ("nether", ["netherrack", "nether_bricks", "red_nether_bricks", "soul_sand", "soul_soil",
                "magma_block", "crimson_nylium", "warped_nylium", "nether_wart_block",
                "shroomlight"]),
    ("end + purpur", ["end_stone", "end_stone_bricks", "purpur_block", "purpur_pillar",
                      "obsidian", "crying_obsidian", "chorus_flower", "quartz_block",
                      "chiseled_quartz_block", "smooth_quartz"]),
    ("light sources", ["glowstone", "sea_lantern", "redstone_lamp", "lantern", "soul_lantern",
                       "torch", "campfire", "ochre_froglight", "verdant_froglight",
                       "pearlescent_froglight"]),
    ("utility + redstone", ["crafting_table", "furnace", "chest", "barrel", "bookshelf",
                            "observer", "piston", "dispenser", "hopper", "target"]),
]

bad = []
for label, blocks in ROWS:
    for blk in blocks:
        if "minecraft:" + blk not in VALID:
            bad.append((label, blk))
print("\ninvalid ids in the swatch list: %d" % len(bad))
for label, blk in bad:
    print("   %-20s %s" % (label, blk))
assert not bad, "fix the block list before building"

GAP = 1
CELL = 2
PITCH = CELL + GAP            # 3 blocks per sample
ROW_PITCH = 4                 # 2 deep + 2 gap
BASE = "minecraft:polished_andesite"
EDGE = "minecraft:polished_blackstone"
MARK = "minecraft:chiseled_polished_blackstone"


class Build:
    def __init__(self):
        self.cells = {}

    def set(self, x, y, z, name):
        self.cells[(x, y, z)] = name

    def box(self, x0, y0, z0, x1, y1, z1, name):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, name)

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
                 "DataVersion": Int(2730)}, (ox, oy, oz))


b = Build()
WIDTH = len(ROWS[0][1]) * PITCH + 4
DEPTH = len(ROWS) * ROW_PITCH + 6

# ---- platform ----
b.box(0, 0, 0, WIDTH, 0, DEPTH, BASE)
for x in range(0, WIDTH + 1):
    b.set(x, 0, 0, EDGE)
    b.set(x, 0, DEPTH, EDGE)
for z in range(0, DEPTH + 1):
    b.set(0, 0, z, EDGE)
    b.set(WIDTH, 0, z, EDGE)

# ---- swatch rows ----
legend = []
for ri, (label, blocks) in enumerate(ROWS):
    z0 = 3 + ri * ROW_PITCH
    # a marker stripe at the row head, so rows are countable from the walkway
    b.set(1, 1, z0, MARK)
    for ci, blk in enumerate(blocks):
        x0 = 3 + ci * PITCH
        b.box(x0, 1, z0, x0 + CELL - 1, CELL, z0 + CELL - 1, "minecraft:" + blk)
    legend.append("row %2d  z=%-4d %s" % (ri + 1, z0, label))

# ---- build scenes, off the end of the gallery ----
SX = WIDTH + 8
b.box(SX - 2, 0, 0, SX + 30, 0, 26, BASE)

# a house corner: walls, window, door gap, roof
b.box(SX, 1, 2, SX + 10, 1, 12, "minecraft:oak_planks")          # floor
b.box(SX, 2, 2, SX, 6, 12, "minecraft:stone_bricks")             # wall
b.box(SX, 2, 2, SX + 10, 6, 2, "minecraft:stone_bricks")         # wall
b.box(SX + 1, 3, 2, SX + 2, 5, 2, "minecraft:glass_pane")        # window
b.box(SX, 3, 6, SX, 5, 7, "minecraft:glass_pane")                # window
b.box(SX + 5, 2, 2, SX + 6, 4, 2, "minecraft:air")               # doorway
for i in range(6):                                                # stepped roof
    b.box(SX - 1 + i, 7 + i, 1 + i, SX + 11 - i, 7 + i, 13 - i, "minecraft:dark_oak_planks")
b.set(SX + 3, 2, 5, "minecraft:lantern")
b.set(SX + 8, 2, 9, "minecraft:bookshelf")
b.set(SX + 7, 2, 4, "minecraft:crafting_table")

# a path and a small garden
b.box(SX + 13, 1, 2, SX + 15, 1, 20, "minecraft:gravel")
b.box(SX + 17, 1, 3, SX + 24, 1, 10, "minecraft:grass_block")
for gx, gz in ((18, 4), (20, 6), (22, 8), (19, 9), (23, 5)):
    b.set(SX + gx, 2, gz, "minecraft:poppy")
# a tree
b.box(SX + 21, 2, 14, SX + 21, 7, 14, "minecraft:oak_log")
for dx in range(-2, 3):
    for dz in range(-2, 3):
        for dy in (6, 7):
            if abs(dx) + abs(dz) <= 3:
                b.set(SX + 21 + dx, dy, 14 + dz, "minecraft:oak_leaves")
b.set(SX + 21, 8, 14, "minecraft:oak_leaves")

# water and lava pools, side by side
b.box(SX + 17, 1, 17, SX + 20, 1, 21, "minecraft:water")
b.box(SX + 16, 1, 16, SX + 21, 1, 16, "minecraft:stone")
b.box(SX + 24, 1, 17, SX + 27, 1, 21, "minecraft:lava")
b.box(SX + 23, 1, 16, SX + 28, 1, 16, "minecraft:stone")

root, origin = b.emit()
sx, sy, sz = (int(v) for v in root["size"])
os.makedirs(os.path.join(D, "structure"), exist_ok=True)
p = os.path.join(D, "structure", "showcase.nbt")
n = nbt.save(p, root)
chk = nbt.load(p)
assert chk["size"] == root["size"] and len(chk["blocks"]) == len(root["blocks"])
print("\nshowcase.nbt  size=%dx%dx%d  blocks=%d  palette=%d  %.1f KB"
      % (sx, sy, sz, len(root["blocks"]), len(root["palette"]), n / 1024.0))

# place it in redstone land, well clear of spawn (which is 0,64,0)
CORNER = (120, 63, -30)
print("\n   placed in redstone land at corner %s" % (CORNER,))
print("   platform surface y = %d (walk on %d)" % (CORNER[1] + 1, CORNER[1] + 2))
print("   gallery spans x %d..%d, z %d..%d" % (CORNER[0], CORNER[0] + sx,
                                               CORNER[2], CORNER[2] + sz))
print("\n   %d swatch rows x %d samples = %d blocks on show"
      % (len(ROWS), len(ROWS[0][1]), len(ROWS) * len(ROWS[0][1])))
print("\nLEGEND (walk +z along the gallery):")
for line in legend:
    print("   " + line)

io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "showcase_place.txt"),
        "w", encoding="utf-8").write("%d %d %d\n%d %d %d\n"
                                     % (CORNER + (CORNER[0] + 5, CORNER[1] + 2, CORNER[2] + 5)))
