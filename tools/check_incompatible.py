# -*- coding: utf-8 -*-
"""Report mod incompatibilities that will ACTUALLY block loading.

The check validate.py was missing. But a declaration alone means nothing: an `incompatible`
block carries a versionRange, and it only bites when the installed version falls inside it.
Reporting raw declarations produces a wall of false positives on packs that demonstrably
run - the same mistake as reading Fabric `breaks` entries without evaluating their predicates.

So this parses the Maven range and compares the installed version against it.
"""
import os, re, sys, zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
B = r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances"


def vkey(v):
    """Loose version -> comparable tuple. Trailing build metadata is ignored."""
    v = re.split(r"[+\-]", str(v).strip())[0]
    parts = []
    for chunk in re.split(r"[._]", v):
        parts.append(int(chunk) if chunk.isdigit() else 0)
    return tuple(parts + [0] * (6 - len(parts)))[:6]


def in_range(ver, rng):
    """Maven range: [a,b] inclusive, (a,b) exclusive, [a,) open, empty/absent = any."""
    if not rng or not rng.strip():
        return True
    rng = rng.strip()
    if not rng[0] in "[(":
        # a bare version in NeoForge means ">= that version"
        return vkey(ver) >= vkey(rng)
    lo_inc, hi_inc = rng[0] == "[", rng[-1] == "]"
    inner = rng[1:-1]
    if "," not in inner:                      # [1.2] = exactly 1.2
        return vkey(ver) == vkey(inner)
    lo, hi = inner.split(",", 1)
    k = vkey(ver)
    if lo.strip():
        if k < vkey(lo) or (not lo_inc and k == vkey(lo)):
            return False
    if hi.strip():
        if k > vkey(hi) or (not hi_inc and k == vkey(hi)):
            return False
    return True


def scan(mods_dir):
    present, decls = {}, []
    for fn in sorted(os.listdir(mods_dir)):
        if not fn.endswith(".jar"):
            continue
        try:
            z = zipfile.ZipFile(os.path.join(mods_dir, fn))
            t = z.read("META-INF/neoforge.mods.toml").decode("utf-8", "replace")
        except Exception:
            continue
        owners = []
        for b in re.split(r"\[\[mods\]\]", t)[1:]:
            m = re.search(r'modId\s*=\s*"([^"]+)"', b)
            v = re.search(r'version\s*=\s*"([^"]+)"', b)
            if m:
                owners.append(m.group(1))
                present[m.group(1)] = (v.group(1) if v else "0", fn)
        owner = owners[0] if owners else fn
        for blk in re.findall(r'\[\[dependencies\.[^\]]+\]\](.*?)(?=\[\[|\Z)', t, re.S):
            mid = re.search(r'modId\s*=\s*"([^"]+)"', blk)
            typ = re.search(r'type\s*=\s*"([^"]+)"', blk)
            rng = re.search(r'versionRange\s*=\s*"([^"]*)"', blk)
            rsn = re.search(r'reason\s*=\s*"([^"]*)"', blk)
            if mid and typ and typ.group(1).lower() in ("incompatible", "discouraged"):
                decls.append((owner, mid.group(1), typ.group(1).lower(),
                              rng.group(1) if rng else "",
                              (rsn.group(1) if rsn else "")[:58]))
    return present, decls


def report(name, mods_dir):
    present, decls = scan(mods_dir)
    hard, soft, inert = [], [], 0
    for owner, target, typ, rng, reason in decls:
        if target not in present:
            continue
        ver = present[target][0]
        if not in_range(ver, rng):
            inert += 1
            continue
        (hard if typ == "incompatible" else soft).append((owner, target, ver, rng, reason))
    n = len([f for f in os.listdir(mods_dir) if f.endswith(".jar")])
    print("   %-14s %3d jars  %-11s  (%d declarations ruled out by version range)" % (
        name, n, "CLEAN" if not hard else "%d BLOCKING" % len(hard), inert))
    for owner, target, ver, rng, reason in hard:
        print("        BLOCKING %-15s refuses %-14s present=%-14s range=%s %s" % (
            owner, target, ver, rng or "any", reason))
    for owner, target, ver, rng, reason in soft:
        print("        warns    %-15s dislikes %-13s present=%s" % (owner, target, ver))
    return len(hard)


def resolve_mods_dir(path):
    """Accept either an instance directory or a mods directory.

    The CLI path used to hand sys.argv[1] straight to report() as the mods dir, while the
    no-argument path below correctly appends minecraft/mods. Given an instance directory it
    therefore listed instance.cfg and mmc-pack.json, found zero jars, and printed CLEAN - a
    false pass indistinguishable from a real one. Never report clean on an empty scan.
    """
    path = path.rstrip("\\/")
    if os.path.basename(path).lower() == "mods" and os.path.isdir(path):
        return path
    for candidate in (os.path.join(path, "minecraft", "mods"), os.path.join(path, "mods")):
        if os.path.isdir(candidate):
            return candidate
    return None


if len(sys.argv) > 1:
    _md = resolve_mods_dir(sys.argv[1])
    if _md is None:
        print("no mods directory found under %s" % sys.argv[1])
        sys.exit(2)
    _jars = len([f for f in os.listdir(_md) if f.endswith(".jar")])
    if _jars == 0:
        print("REFUSING to report: %s contains no jars" % _md)
        sys.exit(2)
    sys.exit(1 if report(os.path.basename(sys.argv[1].rstrip("\\/")), _md) else 0)

total = 0
for inst in ("Skyblock", "Survival", "Caveblock", "Netherbound", "Oceanblock",
             "Lost Cities", "One Chunk", "The Gauntlet", "The Hub"):
    md = os.path.join(B, inst, "minecraft", "mods")
    if os.path.isdir(md):
        total += report(inst, md)
print("\nRESULT: %s" % ("all instances clean" if total == 0
                        else "%d blocking incompatibilities remain" % total))
