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


# Minecraft versions embedded INSIDE a mod version are the last big source of false
# mismatches. Two real shapes from this pack:
#
#   moonlight            have "1.21.1-3.7.2"  needs "[1.21-2.29.33,)"   -> mc is a PREFIX
#   forgeconfigapiport   have "21.1.6"        needs ">=v21.1.6-1.21.1-NeoForge"  -> a SUFFIX
#
# Both failed, and both were satisfied: 3.7.2 > 2.29.33, and 21.1.6 == 21.1.6. Comparing every
# integer group in order cannot see that, because it lines the mc digits up against the mod's.
# So strip the game version and loader name from both sides before comparing. The longest mc
# form goes first (1.21.1 before 1.21), and nothing is stripped if no digits would survive -
# that keeps `minecraft` and `neoforge` comparing as themselves.
MC_FORMS = ("1.21.1", "1.21")
LOADER_WORDS = ("neoforge", "forge", "fabric", "quilt")


def strip_game(v):
    """Remove an embedded Minecraft version and loader name, leaving the mod's own version.

    Only a DASH-DELIMITED component is removed. Stripping by plain substring looked right and
    was wrong: "1.21" is a substring of the bare game version "1.21.1", so a substring strip
    turned minecraft's own version into ".1" and broke every mc range in the suite. The
    self-test below caught it, which is the whole reason that suite exists.
    """
    out = str(v).lower()
    for w in LOADER_WORDS:
        out = re.sub(r"[-+_.]?" + w, "", out)
    for form in MC_FORMS:
        f = re.escape(form)
        cut = re.sub(r"(?:^|(?<=-))" + f + r"(?=-|$)", "", out)
        if cut != out and re.search(r"\d", cut):
            out = cut
    out = out.strip("-+_.")
    return out if re.search(r"\d", out) else str(v)


def vtuple(v):
    """Every integer group in the version, in order.

    Not `split(".")` and not truncated at the first `-`: Big Reactors declares zerocore as
    `[1.21.1-2.4.9,1.21.1-2.5.0)` and is shipping 1.21.1-2.4.9, so dropping everything after
    the dash collapsed the whole range to [1.21.1,1.21.1) and reported a false mismatch.
    """
    nums = re.findall(r"\d+", strip_game(v))
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
# the mc-version-inside-the-mod-version cases, both seen in the Cobblemon pack
assert in_range("1.21.1-3.7.2", "[1.21-2.29.33,)")          # mc as a prefix on both sides
assert not in_range("1.21.1-2.1.0", "[1.21-2.29.33,)")
assert in_range("21.1.6", ">=v21.1.6-1.21.1-NeoForge")      # mc+loader as a suffix on the range
assert not in_range("21.1.5", ">=v21.1.6-1.21.1-NeoForge")
assert in_range("1.21.1", "[1.21,1.21.2)")                  # bare mc versions still compare
assert vtuple("1.21.1") == (1, 21, 1, 0, 0, 0)              # nothing stripped to nothing
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
                # Keep the HIGHEST version, not the first one scanned. A modId can be provided
                # both standalone and nested in someone's META-INF/jarjar, and NeoForge resolves
                # that by version, not by scan order. First-seen-wins reported this pack as
                # having YACL 3.6.6 (nested inside fragmentum) when 3.8.2 was sitting in mods/,
                # and then failed three mods that were actually satisfied. A validator that
                # invents failures gets ignored, which is the same as having none.
                old = provided.get(mid)
                if old is None or vtuple(ver) > vtuple(old[0]):
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
