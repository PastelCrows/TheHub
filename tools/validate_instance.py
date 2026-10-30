# -*- coding: utf-8 -*-
"""Validate a Prism NeoForge instance's mod set.

Checks, ordered by how much grief each has caused on this project:
  1. duplicate modIds (two jars providing one mod => hard crash)
  2. required dependencies present, with the versionRange EVALUATED
  3. incompatible / breaks declarations EVALUATED, not merely printed
  4. JarJar nested mods counted as provided

Three bugs this file has already had, each of which produced a confident wrong answer:
  - it scanned META-INF/jars/ for nested jars. That is FABRIC's path; NeoForge uses
    META-INF/jarjar/. Create JarJars flywheel and ponder, so six mods read as "missing
    required" while the game was demonstrably running them.
  - parse_toml emitted (modId, version) only when `version` came AFTER `modId` inside a
    [[mods]] block, so a toml written the other way round provided no mod at all.
  - it treated a dependency with no `type` as required, ignoring the older
    `mandatory = false` spelling.

Hence the self-tests below: a validator that passes everything is worse than no validator.
"""
import os
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NESTED_DIRS = ("META-INF/jarjar/", "META-INF/jars/")   # neoforge first, fabric fallback


def vtuple(v):
    """Every integer group in the version, in order.

    Not `split(".")` and not truncated at the first `-`: Big Reactors declares zerocore as
    `[1.21.1-2.4.9,1.21.1-2.5.0)` and is shipping 1.21.1-2.4.9, so dropping everything after
    the dash collapsed the whole range to [1.21.1,1.21.1) and reported a false mismatch.
    """
    nums = re.findall(r"\d+", str(v))
    out = [int(n) for n in nums[:6]]
    return tuple(out + [0] * 6)[:6]


def _single(ver, rng):
    rng = rng.strip()
    if not rng:
        return True
    if rng[0] not in "[(":
        return vtuple(ver) >= vtuple(rng)
    lo_inc = rng[0] == "["
    hi_inc = rng[-1] == "]"
    lo, _, hi = rng[1:-1].partition(",")
    lo, hi = lo.strip(), hi.strip()      # ranges are often written "[1.21.1, 1.22)"
    v = vtuple(ver)
    if lo and (v < vtuple(lo) or (v == vtuple(lo) and not lo_inc)):
        return False
    if hi and (v > vtuple(hi) or (v == vtuple(hi) and not hi_inc)):
        return False
    return True


def in_range(ver, rng):
    rng = (rng or "").strip()
    if not rng:
        return True
    parts = re.findall(r"[\[(][^\])]*[\])]", rng)
    if not parts:
        parts = [rng]
    for part in parts:
        if _single(ver, part):
            return True
    return False


assert in_range("1.21.1", "[1.21,1.21.2)")
assert not in_range("1.21.2", "[1.21,1.21.2)")
assert in_range("21.1.265", "[21.0.78-beta,)")
assert not in_range("1.2.8", "[1.2.9,)")
assert in_range("1.1.25", "[1.1.17,1.2.0)")
assert not in_range("1.2.0", "[1.1.17,1.2.0)")
assert in_range("5.0.0", "5.0.0")
assert not in_range("4.9.0", "5.0.0")
assert in_range("1.0.82", "[1.0.82,)")
assert in_range("1.21.1", "[1.21.1]")
assert not in_range("1.21.0", "[1.21.1]")
# whitespace inside the range, as many tomls write it
assert in_range("1.21.1", "[1.21.1, 1.22)")
assert in_range("6.6.3", "[6.6.3, 6.7)")
assert not in_range("6.7.0", "[6.6.3, 6.7)")
# qualifier versions, where the meaningful digits sit after the dash
assert in_range("1.21.1-2.4.9", "[1.21.1-2.4.9,1.21.1-2.5.0)")
assert not in_range("1.21.1-2.5.1", "[1.21.1-2.4.9,1.21.1-2.5.0)")
print("range evaluator self-test passed")


def parse_toml(text, jarver=None):
    """-> (mods [(id, ver)], deps [(owner, id, type, range, side)]). Block-scoped, order-free."""
    mods = []
    deps = []
    state = {"kind": None, "owner": None, "blk": {}}

    def flush():
        kind = state["kind"]
        blk = state["blk"]
        if kind == "mod" and blk.get("modId"):
            v = blk.get("version", "0")
            if "${" in v:
                v = jarver or "0"
            mods.append((blk["modId"], v))
        elif kind == "dep" and blk.get("modId"):
            typ = blk.get("type")
            if typ is None:
                mandatory = blk.get("mandatory", "true").lower() == "true"
                typ = "required" if mandatory else "optional"
            deps.append((state["owner"], blk["modId"], typ.lower(),
                         blk.get("versionRange", ""), blk.get("side", "BOTH")))

    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if line.startswith("["):
            flush()
            state["blk"] = {}
            m = re.match(r'\[\[dependencies\.?"?([^\]"]*)"?\]\]', line)
            if m:
                state["kind"] = "dep"
                state["owner"] = m.group(1)
            elif re.match(r"\[\[mods\]\]", line):
                state["kind"] = "mod"
            else:
                state["kind"] = None
            continue
        m = re.match(r'(\w+)\s*=\s*"([^"]*)"', line)
        if m is None:
            m = re.match(r"(\w+)\s*=\s*(\S+)", line)
        if m and state["kind"]:
            state["blk"][m.group(1)] = m.group(2).strip('"')
    flush()
    return mods, deps


# parser self-tests: the exact shapes that broke it before
_m, _d = parse_toml('[[mods]]\nversion = "1.2.3"\nmodId = "x"\n')
assert _m == [("x", "1.2.3")], _m                       # version BEFORE modId
_m, _d = parse_toml('[[mods]]\nmodId="y"\nversion="${file.jarVersion}"\n', jarver="9.9")
assert _m == [("y", "9.9")], _m                         # placeholder version
_m, _d = parse_toml('[[dependencies.a]]\nmodId="b"\nmandatory=false\n')
assert _d[0][2] == "optional", _d                       # old `mandatory` spelling
_m, _d = parse_toml('[[dependencies."a"]]\nmodId="b"\ntype="required"\n')
assert _d[0][2] == "required" and _d[0][0] == "a", _d    # quoted owner
print("toml parser self-test passed")


def jar_version(z):
    try:
        mf = z.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        m = re.search(r"Implementation-Version:\s*(\S+)", mf)
        return m.group(1) if m else None
    except Exception:
        return None


def read_toml(z):
    for cand in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        try:
            return z.read(cand).decode("utf-8", "replace")
        except KeyError:
            pass
    return None


def scan(path, provided, alldeps, label, tmp, depth=0):
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return
    try:
        text = read_toml(z)
        if text:
            mods, deps = parse_toml(text, jar_version(z))
            for mid, ver in mods:
                if mid not in provided:
                    provided[mid] = (ver, label, depth > 0)
            alldeps.extend(deps)
        if depth < 3:
            for n in z.namelist():
                if n.endswith(".jar") and any(n.startswith(d) for d in NESTED_DIRS):
                    out = os.path.join(tmp, "%d_%s" % (depth, os.path.basename(n)))
                    with open(out, "wb") as f:
                        f.write(z.read(n))
                    scan(out, provided, alldeps,
                         "%s > %s" % (label, os.path.basename(n)), tmp, depth + 1)
    finally:
        z.close()


def main():
    inst = sys.argv[1]
    mc_ver = sys.argv[2] if len(sys.argv) > 2 else "1.21.1"
    neo_ver = sys.argv[3] if len(sys.argv) > 3 else "21.1.265"
    mods_dir = os.path.join(inst, "minecraft", "mods")
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_jarjar")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)

    jars = sorted(f for f in os.listdir(mods_dir) if f.endswith(".jar"))
    provided = {}
    alldeps = []
    for j in jars:
        scan(os.path.join(mods_dir, j), provided, alldeps, j, tmp)

    # genuine top-level duplicates: one modId declared by two different jars
    dupes = []
    seen = {}
    for j in jars:
        try:
            z = zipfile.ZipFile(os.path.join(mods_dir, j))
        except Exception:
            continue
        text = read_toml(z)
        jv = jar_version(z)
        z.close()
        if not text:
            continue
        for mid, _v in parse_toml(text, jv)[0]:
            if mid in seen and seen[mid] != j:
                dupes.append((mid, seen[mid], j))
            seen[mid] = j

    provided.setdefault("minecraft", (mc_ver, "<game>", False))
    provided.setdefault("neoforge", (neo_ver, "<loader>", False))

    print("\n%s" % os.path.basename(inst))
    print("   jars              : %d" % len(jars))
    print("   mods provided     : %d  (%d via JarJar)"
          % (len(provided), sum(1 for v in provided.values() if v[2])))
    print("   duplicate modIds  : %d %s" % (len(dupes), dupes[:4] if dupes else ""))

    missing = []
    badver = []
    conflicts = []
    loose = []            # sloppy minecraft/neoforge ranges - warn, never fail
    for owner, mid, typ, rng, side in alldeps:
        if side.upper() == "SERVER":
            continue
        have = provided.get(mid)
        if typ in ("incompatible", "breaks", "discouraged"):
            if have and in_range(have[0], rng):
                conflicts.append((owner, typ, mid, rng, have[0]))
            continue
        if typ != "required" or mid == "forge":
            continue
        if not have:
            missing.append((owner, mid, rng))
        elif not in_range(have[0], rng):
            # Plenty of mods declare an over-tight game range (e.g. cucumber says
            # [1.21,1.21.1) while shipping a 1.21.1 build). NeoForge does not block on these
            # and the packs demonstrably run, so they are noise here, not findings.
            if mid in ("minecraft", "neoforge"):
                loose.append((owner, mid, rng, have[0]))
            else:
                badver.append((owner, mid, rng, have[0]))

    print("   missing required  : %d" % len(missing))
    for o, m, r in missing[:12]:
        print("        %-26s needs %-24s %s" % (o, m, r))
    print("   version mismatches: %d" % len(badver))
    for o, m, r, h in badver[:12]:
        print("        {:<26} needs {:<24} range {:<18} have {}".format(o, m, r, h))
    print("   REAL conflicts    : %d" % len(conflicts))
    for o, t, m, r, h in conflicts[:12]:
        print("        {:<26} {:<12} {:<20} range {:<14} installed {}".format(o, t, m, r, h))
    print("   loose game ranges : %d  (warning only - over-tight mc/neoforge declarations)"
          % len(loose))

    ok = not dupes and not missing and not badver and not conflicts
    print("\n   %s" % ("VALIDATION PASSED" if ok else "PROBLEMS FOUND"))
    return ok


if __name__ == "__main__":
    main()
