# -*- coding: utf-8 -*-
"""Classify Kewz's recompiled jars by HOW EXPENSIVE each one is to reproduce on NeoForge.

READ-ONLY on his instance.

WHY. "Recreate his custom work" sounds like 58 porting jobs. It is not. A recompile that only
edits `data/cobblemon/species/*.json` is a DATAPACK, and a datapack does not care about the
loader - that is the same finding that made 27 of his datapacks portable in an afternoon. A
recompile that only edits `assets/**` is a RESOURCE PACK. Only the ones that touch `.class`
files or mixin configs are actual porting work, and the ones that touch ONLY `fabric.mod.json`
or a mixin refmap are Fabric loader plumbing that NeoForge does not need at all.

So each jar is diffed against the upstream release it was built from, and the changed entries are
bucketed. The output is a work plan ordered by cost instead of a list of 58 identical-looking
problems.

    DATA       changed only data/**            -> ship as a datapack, no compiling
    ASSETS     changed only assets/**          -> ship as a resource pack, no compiling
    DATA+ASSETS both of the above              -> datapack + resource pack
    PLUMBING   only fabric.mod.json / refmaps  -> nothing to do, the NeoForge build is the fix
    CODE       any .class or *.mixins.json     -> real port, needs reading his bytecode
    UNKNOWN    upstream release not found      -> cannot diff; inspect by hand

Reads tools/_parity/custom_diffs.txt, which audit_kewz_custom.py --diff produces.

    python classify_kewz_recompiles.py
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
DIFFS = os.path.join(HERE, "_parity", "custom_diffs.txt")
KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")

PLUMBING = ("fabric.mod.json", "refmap", "quilt.mod.json", "META-INF/MANIFEST.MF")


def bucket(entries):
    """entries: list of changed/added/removed paths -> a cost bucket."""
    code = data = assets = plumb = False
    for e in entries:
        e = e.strip()
        if not e or e == "-":
            continue
        if any(p in e for p in PLUMBING):
            plumb = True
        elif e.endswith(".class") or e.endswith(".mixins.json") or "mixins.json" in e:
            code = True
        elif e.startswith("data/"):
            data = True
        elif e.startswith("assets/"):
            assets = True
        else:
            plumb = True
    if code:
        return "CODE"
    if data and assets:
        return "DATA+ASSETS"
    if data:
        return "DATA"
    if assets:
        return "ASSETS"
    if plumb:
        return "PLUMBING"
    return "NO-OP"


def parse():
    if not os.path.exists(DIFFS):
        print("run: python audit_kewz_custom.py --diff   first")
        return None
    text = io.open(DIFFS, encoding="utf-8").read()
    out = []
    for block in text.split("\n\n"):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        name = lines[0].strip()
        if not name.endswith(".jar"):
            continue
        ent = []
        for l in lines[1:]:
            m = re.match(r"\s*(added|removed|changed):\s*(.*)", l)
            if m:
                ent.extend(x.strip() for x in m.group(2).split(", "))
        out.append((name, ent))
    return out


def main():
    rows = parse()
    if rows is None:
        return 1

    diffed = {n for n, _ in rows}
    allcustom = sorted(f for f in os.listdir(KEWZ)
                       if f.endswith(".jar") and "+kewz" in f.lower())

    groups = {}
    for name, ent in rows:
        groups.setdefault(bucket(ent), []).append((name, ent))
    undiffed = [f for f in allcustom if f not in diffed]
    if undiffed:
        groups["UNKNOWN"] = [(f, []) for f in undiffed]

    order = ["PLUMBING", "DATA", "ASSETS", "DATA+ASSETS", "NO-OP", "CODE", "UNKNOWN"]
    cost = {
        "PLUMBING":    "nothing to do - the NeoForge build already is the fix",
        "DATA":        "datapack. no compiling.",
        "ASSETS":      "resource pack. no compiling.",
        "DATA+ASSETS": "datapack + resource pack. no compiling.",
        "NO-OP":       "no meaningful difference found",
        "CODE":        "real port - read his bytecode, reimplement",
        "UNKNOWN":     "upstream release not found; inspect by hand",
    }

    print("HIS %d RECOMPILES, BY WHAT IT WOULD ACTUALLY TAKE" % len(allcustom))
    print("=" * 98)
    free = work = 0
    for g in order:
        items = groups.get(g)
        if not items:
            continue
        print("")
        print("%-12s %3d jars   %s" % (g, len(items), cost[g]))
        print("-" * 98)
        for name, ent in sorted(items):
            shown = [e for e in ent if e and e != "-"][:2]
            tail = (" | " + "; ".join(x[:46] for x in shown)) if shown else ""
            print("   %-62s%s" % (name[:62], tail))
        if g in ("PLUMBING", "DATA", "ASSETS", "DATA+ASSETS", "NO-OP"):
            free += len(items)
        else:
            work += len(items)

    print("")
    print("=" * 98)
    print("  reproducible WITHOUT compiling : %3d" % free)
    print("  needs a real port              : %3d" % work)
    print("=" * 98)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
