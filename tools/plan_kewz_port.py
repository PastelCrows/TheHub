# -*- coding: utf-8 -*-
"""The work plan: what reproducing each of Kewz's recompiles on NeoForge actually costs.

READ-ONLY on his instance.

Uses tools/_parity/upstream_map.txt (resolve_kewz_upstream.py) and the jars cached in
tools/_parity/upstream/, diffs each of his recompiles against the release it was built from, and
buckets the result by cost. The point is to replace "58 custom jars" - which reads as 58 porting
jobs - with an ordered plan, because the buckets are wildly different sizes of work:

    PLUMBING     only fabric.mod.json / mixin refmaps changed. Fabric loader bookkeeping. The
                 NeoForge build of the same mod already IS the fix - nothing to reproduce.
    DATA         only data/** changed -> a datapack. Loader-agnostic, same as the 27 datapacks.
    ASSETS       only assets/** changed -> a resource pack. Also loader-agnostic.
    DATA+ASSETS  both -> datapack + resource pack.
    CODE         .class files changed or added -> a real port: read his bytecode, reimplement
                 against NeoForge.

THE CLASS COUNT IS NOT AN EDIT SIZE, AND MUST NOT BE READ AS ONE. Recompiling a mod rewrites
every .class file's CRC - different compiler, different constant-pool ordering - so a one-line
source change in a big mod shows up as "every class differs". dreamdisplays reports 6519 and
fancymenu 1353; neither is a 6519-class or 1353-class edit, they are whole-jar rebuilds. The
count measures JAR SIZE, not work. What it does separate reliably is the other direction: a jar
where only 1-6 classes differ was patched surgically rather than rebuilt, and those are the ones
whose change can actually be read straight out of the diff. His filename tags are the better
guide to intent (perf1, memo1, nogc1, sheetfix1), and they are listed by audit_kewz_custom.py.

Anything unresolved is reported as unresolved rather than folded into a bucket.

    python plan_kewz_port.py
    python plan_kewz_port.py --classes   # also list the changed class names per CODE jar
"""
import io
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_parity")
CACHE = os.path.join(OUT, "upstream")
MAP = os.path.join(OUT, "upstream_map.txt")

PLUMBING_NAMES = ("fabric.mod.json", "quilt.mod.json", "META-INF/MANIFEST.MF",
                  "refmap", "architectury.common.json", "META-INF/services")


def entries(path):
    try:
        with zipfile.ZipFile(path) as z:
            return {i.filename: i.CRC for i in z.infolist()
                    if not i.filename.endswith("/")}
    except Exception:
        return {}


def classify(changed):
    code, data, assets, plumb = [], [], [], []
    for e in changed:
        if any(p in e for p in PLUMBING_NAMES):
            plumb.append(e)
        elif e.endswith(".class"):
            code.append(e)
        elif e.endswith(".mixins.json") or "mixins.json" in e:
            code.append(e)
        elif e.startswith("data/"):
            data.append(e)
        elif e.startswith("assets/"):
            assets.append(e)
        else:
            plumb.append(e)
    if code:
        return "CODE", code
    if data and assets:
        return "DATA+ASSETS", data + assets
    if data:
        return "DATA", data
    if assets:
        return "ASSETS", assets
    if plumb:
        return "PLUMBING", plumb
    return "NO-OP", []


def main():
    show_classes = "--classes" in sys.argv
    if not os.path.exists(MAP):
        print("run: python resolve_kewz_upstream.py --download   first")
        return 1

    pairs = []
    for line in io.open(MAP, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) == 4:
            pairs.append((parts[0], parts[3]))

    customs = sorted(f for f in os.listdir(KEWZ)
                     if f.endswith(".jar") and "+kewz" in f.lower())
    own = sorted(f for f in os.listdir(KEWZ)
                 if f.endswith(".jar") and f.startswith("kewz-"))
    mapped = {n: up for n, up in pairs}

    groups, unresolved = {}, []
    for name in customs:
        up = mapped.get(name)
        upath = os.path.join(CACHE, up) if up else None
        if not upath or not os.path.exists(upath):
            unresolved.append(name)
            continue
        his, theirs = entries(os.path.join(KEWZ, name)), entries(upath)
        if not his or not theirs:
            unresolved.append(name)
            continue
        changed = sorted(set(k for k in set(his) & set(theirs) if his[k] != theirs[k])
                         | (set(his) - set(theirs)))
        g, items = classify(changed)
        groups.setdefault(g, []).append((name, items, len(changed)))

    order = ["PLUMBING", "DATA", "ASSETS", "DATA+ASSETS", "NO-OP", "CODE"]
    blurb = {
        "PLUMBING":    "NOTHING TO DO - only Fabric loader bookkeeping changed",
        "DATA":        "a datapack. loader-agnostic, no compiling.",
        "ASSETS":      "a resource pack. loader-agnostic, no compiling.",
        "DATA+ASSETS": "a datapack + a resource pack. no compiling.",
        "NO-OP":       "no differing entries found",
        "CODE":        "a real port: read his bytecode, reimplement on NeoForge",
    }

    print("REPRODUCING KEWZ'S CUSTOM WORK - COST PLAN")
    print("=" * 100)
    print("his recompiles: %d      his own original mods: %d" % (len(customs), len(own)))

    free = work = 0
    for g in order:
        items = groups.get(g)
        if not items:
            continue
        print("")
        print("### %-12s %2d jars   %s" % (g, len(items), blurb[g]))
        if g == "CODE":
            print("    NOTE: a recompile rewrites EVERY class's CRC, so the count below is jar")
            print("    size, not edit size. Only the small counts (1-6) indicate a surgical patch.")
        print("-" * 100)
        for name, files, n in sorted(items, key=lambda r: -r[2]):
            if g == "CODE":
                ncls = len([f for f in files if f.endswith(".class")])
                nmix = len([f for f in files if "mixins.json" in f])
                print("   %-64s %3d classes  %d mixin cfg" % (name[:64], ncls, nmix))
                if show_classes:
                    for f in files[:6]:
                        if f.endswith(".class"):
                            print("        " + f[:88])
            else:
                print("   %-64s %3d files" % (name[:64], n))
        if g == "CODE":
            work += len(items)
        else:
            free += len(items)

    print("")
    print("=" * 100)
    print("  reproducible with NO compiling : %3d recompiles" % free)
    print("  needs a real code port         : %3d recompiles" % work)
    print("  could not resolve upstream     : %3d recompiles" % len(unresolved))
    print("  his own original mods          : %3d  (write from scratch, nothing to diff)" % len(own))
    print("=" * 100)
    if unresolved:
        print("")
        print("Unresolved (CurseForge-only or renamed upstream file) - inspect by hand:")
        for u in unresolved:
            print("   " + u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
