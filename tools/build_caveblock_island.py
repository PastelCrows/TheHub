# -*- coding: utf-8 -*-
"""Rebuild Caveblock's starting island as what it is documented to be: a pocket in solid rock.

WHY. Two things were reported about Caveblock: "no ores spawning anywhere", and having to dig a
chamber by hand and wait a long time before anything else was possible. Investigating both
produced one real answer and one real bug.

ORES ARE BY DESIGN. Caveblock's overworld is a void (SkyblockBuilder `isCustom: true`), and its
ores come from Ex Deorum sieving, exactly like Skyblock. Verified in the instance: Ex Deorum 3.12
with 846 sieve recipes and a `recipe/ores` set, and PocketQuests' Ex Deorum gate is Hub-only so
nothing is denied in the standalone. BALANCE.md already says Caveblock "owns Ex Deorum
legitimately". Nothing to fix there.

THE PROGRESSION GATE, traced through the recipes:

    sapling -> tree -> leaves -> crook -> silkworm -> infested_leaves -> crook -> string
            -> string_mesh -> sieve dirt/gravel -> ore pieces

There are ZERO meshless sieve recipes, and the entry `string_mesh` needs `c:strings`, so until a
tree exists nothing can be sieved at all. In a void world with no spiders, the tree is the single
gate in front of the entire pack.

THE BUG. The old template was 15x7x15 holding 755 air and only 152 stone - a hollow shell in the
void, which is the opposite of "a carved pocket in solid rock" as README describes it. Worse, it
is too tight for the tree it gates everything on: of its 225 columns, the tallest clear run was 6
in only 44 of them, and an oak wants 5-6 clear above the sapling. Hence digging a chamber by
hand. And because the shell is thin, digging mostly reaches void rather than more stone.

WHAT THIS BUILDS. A solid stone cube with a carved chamber inside it:

  * 19x19x19 of stone, so mining outward yields more stone rather than void - and stone is
    itself the resource chain here (hammer -> cobble -> gravel -> sand, all siftable)
  * a 9x9x9 chamber carved in the middle: 8 clear blocks above the floor, comfortably enough
    for an oak, which removes the hand-digging entirely
  * the floor given a dirt patch for the sapling, the chest where it was, torches on the walls
  * the chest contents carried over EXACTLY from the old template, so the starting kit is
    unchanged and this stays a terrain fix rather than a balance change

The old file is kept as cavern.nbt.preshape, next to it, in keeping with the other tools here.

    python build_caveblock_island.py            # report
    python build_caveblock_island.py --apply    # write the new template
"""
import importlib.util
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("nbt", os.path.join(HERE, "nbt.py"))
nbt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nbt)

TEMPLATE = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Caveblock\minecraft\config"
    r"\skyblockbuilder\templates\islands\cavern.nbt")

SIZE = 19            # outer stone cube
CHAMBER = 9          # carved interior, odd so it centres


def load_old():
    root = nbt.load(TEMPLATE)
    pal = [p.get("Name") for p in root.get("palette", [])]
    chest = None
    for b in root.get("blocks", []):
        if pal[b["state"]] == "minecraft:chest":
            chest = b.get("nbt")
            break
    return root, pal, chest


def build(chest_nbt):
    """A solid cube with a carved chamber, a dirt patch, torches and the original chest."""
    names = ["minecraft:stone", "minecraft:air", "minecraft:dirt",
             "minecraft:torch", "minecraft:chest"]
    idx = {n: i for i, n in enumerate(names)}
    palette = [{"Name": n} for n in names]

    lo = (SIZE - CHAMBER) // 2
    hi = lo + CHAMBER - 1
    floor = lo                      # y of the chamber floor

    blocks = []
    for x in range(SIZE):
        for y in range(SIZE):
            for z in range(SIZE):
                inside = lo <= x <= hi and lo <= y <= hi and lo <= z <= hi
                blocks.append({"pos": [nbt.Int(x), nbt.Int(y), nbt.Int(z)],
                               "state": nbt.Int(idx["minecraft:air" if inside
                                                     else "minecraft:stone"])})

    def put(x, y, z, name, extra=None):
        for b in blocks:
            p = b["pos"]
            if int(p[0]) == x and int(p[1]) == y and int(p[2]) == z:
                b["state"] = nbt.Int(idx[name])
                if extra is not None:
                    b["nbt"] = extra
                else:
                    b.pop("nbt", None)
                return

    centre = SIZE // 2
    # A 3x3 dirt patch in the chamber floor for the sapling - the one thing everything waits on.
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            put(centre + dx, floor, centre + dz, "minecraft:dirt")
    # Chest in a corner of the chamber, on the floor, carrying the original contents verbatim.
    put(lo + 1, floor + 1, lo + 1, "minecraft:chest", chest_nbt)
    # Torches on the chamber floor corners, clear of the sapling.
    for cx, cz in ((lo + 1, hi - 1), (hi - 1, lo + 1), (hi - 1, hi - 1)):
        put(cx, floor + 1, cz, "minecraft:torch")

    return {
        "size": [nbt.Int(SIZE), nbt.Int(SIZE), nbt.Int(SIZE)],
        "palette": palette,
        "blocks": blocks,
        "entities": [],
        "DataVersion": nbt.Int(3955),      # 1.21.1
    }


def main():
    apply_it = "--apply" in sys.argv
    if not os.path.exists(TEMPLATE):
        print("template not found: " + TEMPLATE)
        return 1

    old, pal, chest = load_old()
    ox, oy, oz = [int(v) for v in old["size"]]
    air_old = sum(1 for b in old["blocks"] if pal[b["state"]] == "minecraft:air")
    stone_old = sum(1 for b in old["blocks"] if pal[b["state"]] == "minecraft:stone")
    print("OLD  %dx%dx%d   %d blocks listed   stone=%d air=%d"
          % (ox, oy, oz, len(old["blocks"]), stone_old, air_old))
    if chest is None:
        print("no chest found in the old template - refusing to build without the starting kit")
        return 1
    items = chest.get("Items") or []
    print("     chest carried over: %d stacks" % len(items))
    for it in items:
        print("       %-30s x%s" % (it.get("id"), it.get("count", it.get("Count"))))

    new = build(chest)
    stone_new = sum(1 for b in new["blocks"] if int(b["state"]) == 0)
    air_new = sum(1 for b in new["blocks"] if int(b["state"]) == 1)
    print("")
    print("NEW  %dx%dx%d   %d blocks   stone=%d air=%d   chamber=%d^3, %d clear above the floor"
          % (SIZE, SIZE, SIZE, len(new["blocks"]), stone_new, air_new,
             CHAMBER, CHAMBER - 1))

    if not apply_it:
        print("")
        print("report only. re-run with --apply to write it (keeps cavern.nbt.preshape).")
        return 0

    backup = TEMPLATE + ".preshape"
    if not os.path.exists(backup):
        shutil.copy2(TEMPLATE, backup)
    nbt.save(TEMPLATE, new)

    # read it back rather than trusting the write
    check = nbt.load(TEMPLATE)
    cpal = [p.get("Name") for p in check.get("palette", [])]
    cchest = [b for b in check["blocks"] if cpal[b["state"]] == "minecraft:chest"]
    citems = (cchest[0].get("nbt") or {}).get("Items") if cchest else None
    print("")
    print("written. verified: size=%s blocks=%d chest=%d stacks=%s"
          % ([int(v) for v in check["size"]], len(check["blocks"]),
             len(cchest), len(citems) if citems else 0))
    print("backup: cavern.nbt.preshape")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
