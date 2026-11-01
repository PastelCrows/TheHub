# -*- coding: utf-8 -*-
"""Resolve the recompiles that filename matching could not, using what the jar says about itself.

READ-ONLY on his instance.

WHY A THIRD ATTEMPT. Resolution has now failed twice for the same reason: both earlier tools
guessed the project from the FILENAME. Filenames are the least reliable thing about a mod - the
author picks them freely, renames them between releases, and Kewz appends his own tags. 24 jars
came back unresolved, which risked being read as "24 mods that cannot be sourced" when it only
ever meant "my query was wrong".

Every jar states its own identity, so ask it instead:

    fabric.mod.json  ->  id, name, version        e.g. vsbattleintro / "Cobblemon: Stylish Battles"

That immediately explains some earlier failures. `cobblemon-stylish-battles-1.0.0.jar` has modId
`vsbattleintro`; no amount of filename tokenising finds that. `Cobblemon AFP 1.9.2...jar` is
really `cobblemon_alatia`, "Cobblemon Alatia's Fakemon Pack" - the filename is an abbreviation.

Four lookups per jar, cheapest first:
    1. Modrinth project by modId used as a slug           (slugs often equal the modId)
    2. Modrinth search on the DECLARED DISPLAY NAME       (a real title, not a mangled stem)
    3. Modrinth search on the modId with separators split
    4. match a version by its version_number containing the jar's declared upstream version,
       rather than requiring the filename to match

A mod genuinely absent from Modrinth is reported as absent WITH its modId and name, so it can be
looked for on CurseForge or GitHub by hand. "Not on Modrinth" is a real answer; "my search
failed" is not.

    python resolve_kewz_upstream2.py              # resolve and report
    python resolve_kewz_upstream2.py --download   # also fetch what it finds
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_parity")
CACHE = os.path.join(OUT, "upstream")
UA = {"User-Agent": "TheHub-upstream-resolver/2.0 (personal modpack planning)"}


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode())


def identity(path):
    """(modId, displayName, declaredVersion) straight out of the jar."""
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return None
    try:
        if "fabric.mod.json" in z.namelist():
            raw = z.read("fabric.mod.json").decode("utf-8", "replace")
            raw = re.sub(r",\s*([}\]])", r"\1", raw)
            d = json.loads(raw)
            return d.get("id"), d.get("name"), d.get("version")
        for t in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
            if t in z.namelist():
                s = z.read(t).decode("utf-8", "replace")
                g = lambda k: (re.search(k + r'\s*=\s*"([^"]+)"', s) or [None, None])[1]
                return g("modId"), g("displayName"), g("version")
    except Exception:
        pass
    return None


def upstream_version(declared, filename):
    """The upstream version, with Kewz's tags removed."""
    v = declared or ""
    v = re.sub(r"\+kewz[.\w-]*", "", v)
    v = re.sub(r"[-.]kewz[.\w-]*", "", v)
    if not re.search(r"\d", v):
        m = re.search(r"(\d+[\w.]*?)(?:\+kewz|-kewz|\.jar)", filename)
        v = m.group(1) if m else v
    return v.strip("+-. ")


def numeric_core(v):
    """Leading dotted-number run, e.g. '1.9.2-1.21.1-fabric' -> '1.9.2'."""
    m = re.match(r"v?(\d+(?:\.\d+)*)", v or "")
    return m.group(1) if m else ""


def try_project(pid):
    try:
        return get("https://api.modrinth.com/v2/project/%s" % urllib.parse.quote(pid))
    except Exception:
        return None


def search(query, limit=6):
    try:
        url = ("https://api.modrinth.com/v2/search?query=" + urllib.parse.quote(query)
               + "&limit=%d" % limit)
        return [h["project_id"] for h in get(url).get("hits", [])]
    except Exception:
        return []


def versions_of(pid):
    try:
        return get("https://api.modrinth.com/v2/project/%s/version" % pid, timeout=90)
    except Exception:
        return []


TARGET_MC = "1.21.1"


def pick_version(vers, want, want_core, loader):
    """Best version matching the declared number AND the same build target.

    The build target is not optional. A byte-diff only means anything against the same loader
    and the same Minecraft version: compare a fabric jar to the neoforge build of the same
    release and every class differs, which reads as "he rewrote the mod" when he changed nothing.
    An unconstrained match produced exactly that - catchindicator-fabric paired with
    catchindicator-NEOFORGE, and grassiergrass +mc1.21.1 paired with +mc26.3. Both would have
    been scored as huge code ports. So filter first, then rank.
    """
    ok = [v for v in vers
          if (not loader or loader in [l.lower() for l in v.get("loaders", [])])
          and TARGET_MC in v.get("game_versions", [])]
    if not ok:
        return None
    for v in ok:                                     # exact
        if v["version_number"] == want:
            return v
    for v in ok:                                     # declared inside the version string
        if want and want in v["version_number"]:
            return v
    for v in ok:                                     # numeric core equal
        if want_core and numeric_core(v["version_number"]) == want_core:
            return v
    for v in ok:                                     # numeric core appears
        if want_core and want_core in v["version_number"]:
            return v
    return None


def resolve(name):
    path = os.path.join(KEWZ, name)
    ident = identity(path)
    if not ident:
        return None, ("?", "?", "?")
    mid, disp, dver = ident
    want = upstream_version(dver, name)
    core = numeric_core(want)
    low = name.lower()
    loader = ("fabric" if "fabric" in low else
              "neoforge" if "neoforge" in low else
              "forge" if "forge" in low else "fabric")

    candidates = []
    if mid:
        pr = try_project(mid)
        if pr:
            candidates.append(pr["id"])
    for q in filter(None, [disp, (mid or "").replace("_", " ").replace("-", " ")]):
        for pid in search(q):
            if pid not in candidates:
                candidates.append(pid)

    for pid in candidates[:8]:
        vers = versions_of(pid)
        if not vers:
            continue
        v = pick_version(vers, want, core, loader)
        if v and v.get("files"):
            f = v["files"][0]
            return (pid, v["version_number"], f["filename"], f["url"]), (mid, disp, want)
    return None, (mid, disp, want)


def main():
    download = "--download" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    if download:
        os.makedirs(CACHE, exist_ok=True)

    prev = set()
    mp = os.path.join(OUT, "upstream_map.txt")
    if os.path.exists(mp):
        for line in io.open(mp, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 4:
                prev.add(p[0])

    customs = sorted(f for f in os.listdir(KEWZ)
                     if f.endswith(".jar") and "+kewz" in f.lower())
    todo = [f for f in customs if f not in prev]
    print("recompiles: %d    already resolved: %d    to try: %d"
          % (len(customs), len(prev), len(todo)))
    print("")

    new, still = [], []
    for name in todo:
        hit, (mid, disp, want) = resolve(name)
        if hit:
            pid, ver, fn, url = hit
            new.append((name, pid, ver, fn, url))
            print("  OK   %-56s  %s -> %s" % (name[:56], mid or "?", fn[:40]))
            if download:
                dest = os.path.join(CACHE, fn)
                if not os.path.exists(dest):
                    try:
                        with urllib.request.urlopen(
                                urllib.request.Request(url, headers=UA), timeout=300) as r:
                            io.open(dest, "wb").write(r.read())
                    except Exception as e:
                        print("        download failed: %s" % e)
        else:
            still.append((name, mid, disp, want))
            print("  --   %-56s  modId=%s  name=%s  v=%s"
                  % (name[:56], mid, (disp or "?")[:26], want))

    if new:
        with io.open(mp, "a", encoding="utf-8", newline="\n") as fh:
            for n, p, v, f, _u in new:
                fh.write("%s\t%s\t%s\t%s\n" % (n, p, v, f))

    print("")
    print("=" * 100)
    print("  newly resolved : %3d" % len(new))
    print("  still absent   : %3d" % len(still))
    print("=" * 100)
    if still:
        print("")
        print("NOT ON MODRINTH - look on CurseForge/GitHub by modId:")
        for n, mid, disp, want in still:
            print("   %-30s %-32s v%s" % (mid, (disp or "?")[:32], want))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
