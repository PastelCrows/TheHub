# -*- coding: utf-8 -*-
"""Stop Ex Deorum's "Void" world type being offered in packs where it breaks the premise.

WHY. Netherbound was reported as giving "the classic void start on top of a tree". Its own
world preset is correct - verified on a clean server, which generated
`minecraft:overworld type=minecraft:the_nether settings=minecraft:nether`, so the nether swap
works. The world that was actually played tells the real story: its level.dat says

    overworld generator = exdeorum:void

The world was created with Ex Deorum's VOID world type instead of Default. Ex Deorum ships

    data/minecraft/tags/worldgen/world_preset/normal.json  ->  ["exdeorum:void_world"]

and that tag is what fills the world-type cycle button on the create-world screen. So every pack
carrying Ex Deorum offers "Void" as a one-click way to generate the wrong world.

In NONE of these packs is it the right choice. Netherbound needs its nether swap; Skyblock,
Caveblock, Oceanblock and One Chunk need SkyblockBuilder to place their island, which a raw
exdeorum void start skips entirely; The Hub needs its own dimensions. Picking it silently
produces a world with no premise and no starting kit - which is exactly what happened.

HOW. A tag override written into each instance's `kubejs/data`, using NeoForge's `remove` key:

    {"replace": false, "values": [], "remove": ["exdeorum:void_world"]}

`remove` was confirmed supported before being relied on - Farmer's Delight and Supplementaries
both ship tag files using it. kubejs/data is used rather than `datapacks/` because
`minecraft/datapacks/` is NOT loaded in these instances: no globalpacks mod is installed, and
neither `netherbound_worldgen` nor `hub_worldgen` has ever appeared in any log. KubeJS does load
`kubejs/data`, which is where every live datapack file in these packs actually lives.

This removes an option from a menu. It cannot affect an existing world.

    python hide_void_worldtype.py            # report
    python hide_void_worldtype.py --apply    # write the overrides
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")
REL = os.path.join("kubejs", "data", "minecraft", "tags", "worldgen", "world_preset")
FILE = "normal.json"
DROP = "exdeorum:void_world"


def targets():
    out = []
    if not os.path.isdir(PRISM):
        return out
    for inst in sorted(os.listdir(PRISM)):
        mods = os.path.join(PRISM, inst, "minecraft", "mods")
        if not os.path.isdir(mods):
            continue
        jars = os.listdir(mods)
        has_exd = any("exdeorum" in j.lower() for j in jars)
        has_kjs = any(j.lower().startswith("kubejs") for j in jars)
        if has_exd and has_kjs:
            out.append(inst)
    return out


def main():
    apply_it = "--apply" in sys.argv
    insts = targets()
    if not insts:
        print("no instance has both Ex Deorum and KubeJS - nothing to do")
        return 0

    print("instances offering Ex Deorum's Void world type: %d" % len(insts))
    wrote = 0
    for inst in insts:
        d = os.path.join(PRISM, inst, "minecraft", REL)
        f = os.path.join(d, FILE)
        existing = None
        if os.path.exists(f):
            try:
                existing = json.loads(io.open(f, encoding="utf-8").read())
            except Exception:
                existing = None
        already = bool(existing and DROP in (existing.get("remove") or []))
        print("   %-24s %s" % (inst, "already overridden" if already else "needs override"))
        if already or not apply_it:
            continue
        os.makedirs(d, exist_ok=True)
        doc = {
            "_note": ("Drops Ex Deorum's void world type from the create-world screen. In this "
                      "pack Default is the only correct choice; a raw void start skips the "
                      "pack's own world preset and starting island."),
            "replace": False,
            "values": [],
            "remove": [DROP],
        }
        io.open(f, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=2) + "\n")
        wrote += 1

    if not apply_it:
        print("")
        print("report only. re-run with --apply to write the overrides.")
        return 0

    print("")
    print("wrote %d override(s)" % wrote)
    # read back rather than trusting the writes
    bad = 0
    for inst in insts:
        f = os.path.join(PRISM, inst, "minecraft", REL, FILE)
        try:
            d = json.loads(io.open(f, encoding="utf-8").read())
            if DROP not in (d.get("remove") or []):
                bad += 1
                print("   VERIFY FAILED: %s" % inst)
        except Exception as e:
            bad += 1
            print("   VERIFY FAILED: %s (%s)" % (inst, e))
    print("verified: %d/%d" % (len(insts) - bad, len(insts)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
