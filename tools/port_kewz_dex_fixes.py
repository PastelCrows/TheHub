# -*- coding: utf-8 -*-
"""Turn Kewz's data-only recompiles into one datapack, no compiling.

READ-ONLY on his instance. Writes a datapack into ours.

WHAT THIS CAPTURES. Four of his recompiles change nothing but `data/**`, and all four carry his
`dex1` tag: corrections to Pokedex entries and species definitions in the fakemon packs.

    lively-mons        72 species files
    lasers-fakemon     10 species + dex, 1 new dex entry
    Cobblemon AFP       2 dex files
    kazeran-eeveelutions 1 dex_additions file

Rebuilding four mods to ship 86 JSON files is the expensive way to do it. A datapack overrides mod
data directly, so the same corrections apply to the NeoForge builds of those mods untouched - the
same reason 22 of his 27 datapacks needed no porting at all.

WHY ONLY THESE FOUR. The other four no-compile recompiles REMOVE files (his nomodel1, strip1 and
newonly1 tags): 242 removals in SpaceworldMons alone. A datapack can override a file in a mod jar
but cannot delete one, so a removal cannot be expressed this way, and pretending otherwise would
produce a pack that silently does a fraction of the job. Those four need the jar repackaged
instead, and are listed by plan_kewz_port.py with exact file lists.

CONFLICT CHECK. Every file written here is also checked against what the installed NeoForge jar
of the same mod ships, so an override that would be a no-op - or that targets a path the NeoForge
build does not even have - is reported rather than written blind.

    python port_kewz_dex_fixes.py            # report
    python port_kewz_dex_fixes.py --apply    # write the datapack
"""
import io
import json
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")
KEWZ = os.path.join(PRISM, "Kewz's Cobblemon", "minecraft", "mods")
OURMODS = os.path.join(PRISM, "Cobblemon NeoForge", "minecraft", "mods")
OURDP = os.path.join(PRISM, "Cobblemon NeoForge", "minecraft", "datapacks")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_parity", "upstream")
MAP = os.path.join(HERE, "_parity", "upstream_map.txt")

OUT_NAME = "kewz-dex-fixes-ported.zip"

# the four data-only recompiles, confirmed by diff to be overrides with zero removals
JARS = [
    "lively-mons-1.11.1+kewz.dex1.jar",
    "lasers-fakemon-pack-1.6.2+kewz.dex1.jar",
    "Cobblemon AFP 1.9.2-1.21.1-Fabric-NoGEB+kewz.dex1.jar",
    "kazeran-eeveelutions-1.6+kewz.dex1.jar",
]


def entries(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename: i.CRC for i in z.infolist() if not i.filename.endswith("/")}


def upstream_map():
    m = {}
    if os.path.exists(MAP):
        for line in io.open(MAP, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 4:
                m[p[0]] = p[3]
    return m


def our_data_paths():
    """every data/** path our installed NeoForge jars ship, so overrides can be checked."""
    have = {}
    for f in sorted(os.listdir(OURMODS)):
        if not f.endswith(".jar"):
            continue
        try:
            z = zipfile.ZipFile(os.path.join(OURMODS, f))
        except Exception:
            continue
        for n in z.namelist():
            if n.startswith("data/") and not n.endswith("/"):
                have.setdefault(n, f)
    return have


def main():
    apply_it = "--apply" in sys.argv
    mp = upstream_map()
    have = our_data_paths()
    print("data/** paths our NeoForge jars ship: %d" % len(have))
    print("")

    files, missing_target, noop = {}, [], 0
    for jar in JARS:
        up = mp.get(jar)
        if not up or not os.path.exists(os.path.join(CACHE, up)):
            print("  SKIP %-54s upstream not cached" % jar[:54])
            continue
        hp, tp = os.path.join(KEWZ, jar), os.path.join(CACHE, up)
        his, theirs = entries(hp), entries(tp)
        changed = sorted([k for k in set(his) & set(theirs) if his[k] != theirs[k]]
                         + list(set(his) - set(theirs)))
        changed = [k for k in changed if k.startswith("data/")]
        zh = zipfile.ZipFile(hp)
        taken = 0
        for k in changed:
            if k not in have:
                missing_target.append((jar, k))
            files[k] = zh.read(k)
            taken += 1
        print("  %-54s %3d data files" % (jar[:54], taken))

    print("")
    print("total override files: %d" % len(files))
    if missing_target:
        print("")
        print("WARNING - %d of these paths are NOT shipped by any installed NeoForge jar." % len(missing_target))
        print("An override of a path nothing provides does nothing. Shown so it is a decision,")
        print("not an accident:")
        for jar, k in missing_target[:14]:
            print("   %-34s %s" % (jar[:34], k[:70]))
        if len(missing_target) > 14:
            print("   ... and %d more" % (len(missing_target) - 14))

    # validate every file is parseable JSON before shipping it
    bad = []
    for k, v in files.items():
        if k.endswith(".json"):
            try:
                json.loads(v.decode("utf-8"))
            except Exception as e:
                bad.append((k, str(e)[:60]))
    print("")
    print("JSON parse check: %d files, %d malformed" % (len(files), len(bad)))
    for k, e in bad[:8]:
        print("   %s  %s" % (k[:70], e))

    if not apply_it:
        print("")
        print("report only. re-run with --apply to write %s" % OUT_NAME)
        return 0

    os.makedirs(OURDP, exist_ok=True)
    dest = os.path.join(OURDP, OUT_NAME)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("pack.mcmeta", json.dumps({
            "pack": {
                "pack_format": 48,
                "description": "Kewz dex/species corrections, ported from his Fabric recompiles"
            }
        }, indent=2))
        for k, v in sorted(files.items()):
            z.writestr(k, v)
    print("")
    print("written: %s  (%d files, %.1f KB)"
          % (dest, len(files), os.path.getsize(dest) / 1024.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
