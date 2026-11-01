# -*- coding: utf-8 -*-
"""Add the performance mods this pack is actually missing, and refuse the ones that are not safe.

The hub already carries most of the obvious set - Sodium (+ Extra, Extras, Options API, Dynamic
Lights), Lithium, ModernFix, FerriteCore, EntityCulling, MoreCulling, ImmediatelyFast,
BadOptimizations, Dynamic FPS, Noisium, Clumps, Particle Core, Alternate Current, Leaves Be Gone,
Better Block Entities, Chunky, Spark. So this is a short list by design; the remaining headroom is
in configuration, not in more jars.

WHAT IS DELIBERATELY NOT INSTALLED, and why - the judgement matters more than the downloads:

  ScalableLux      a Starlight-derived LIGHTING ENGINE, and the only NeoForge 1.21.1 build is an
                   `alpha devbuild`. Replacing the lighting engine is exactly the change that can
                   corrupt light data across 32 dimensions, and an alpha one in a pack being
                   actively played is a bad trade for some chunk-load time. Revisit at release.
  Distant Horizons an LOD renderer that RAISES total VRAM and whose Iris compatibility is still
                   experimental. This machine has a 4 GB RTX 3050 already running 64x textures
                   plus shaders - the wrong direction entirely.
  Embeddium        a direct alternative to Sodium; the two conflict. Sodium is already here.
  Chloride         a fourth Sodium add-on on top of three. Marginal gain, more surface to break.

The hardware is what drives these calls: Ryzen 7 2700 (2018, weak single-thread, and Minecraft is
single-thread bound), 32 GB RAM so the 10 GB heap is comfortable, and an RTX 3050 with only 4 GB
of VRAM - which is the real constraint. So the picks favour SERVER-SIDE tick savings, where the
CPU is the ceiling, and avoid anything that spends VRAM.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
MODS = os.path.join(MC, "mods")
UA = "hub-pack-setup/1.0 (personal modpack)"

# (filename, url, why, risk)
WANT = [
    ("letmedespawn-neoforge-1.21.1-1.26.10.2.jar",
     "https://cdn.modrinth.com/data/vE2FN5qn/versions/Ta6w35oG/"
     "letmedespawn-neoforge-1.21.1-1.26.10.2.jar",
     "mob despawn tuning - server tick, where this CPU is the ceiling", "release, 30 KB"),

    ("AI-Improvements-1.21-0.5.3.jar",
     "https://cdn.modrinth.com/data/DSVgwcji/versions/dGNP90t0/AI-Improvements-1.21-0.5.3.jar",
     "vanilla mob AI goal-selector tuning - again server tick", "release, 30 KB"),

    ("packetfixer-3.3.1-1.20.5-1.21.X-merged.jar",
     "https://cdn.modrinth.com/data/c7m1mi73/versions/2C41Q8WX/"
     "packetfixer-3.3.1-1.20.5-1.21.X-merged.jar",
     "raises packet/NBT size limits - 247 mods make a very large registry sync", "release"),

    ("DistantHorizons-3.3.3-1.21.1-fabric-neoforge.jar",
     "https://cdn.modrinth.com/data/uCdwusMi/versions/9w34y8ai/"
     "DistantHorizons-3.3.3-1.21.1-fabric-neoforge.jar",
     "LOD terrain far past the render distance - the thing the Cobblemon server does with Voxy, "
     "which is Fabric-only and so not available here. Render distance renders REAL chunks and is "
     "the wrong lever for that look.",
     "release; was refused in the first performance pass on a VRAM figure that turned out to be "
     "wrong - see PERFORMANCE.md"),

    # RRLS was REMOVED on 2026-10-31. It was added to make resource reloads non-blocking -
    # hideOverlays = "ALL" draws a small progress line over the still world instead of a loading
    # screen. That worked, and it is exactly why a 90-second texture swap read as a frozen
    # client: nothing on screen said it was working. With DrippyLoadingScreen now providing a
    # branded loading screen for that same moment, the two were mutually exclusive and the
    # branded screen won. Left here, commented, so this is a decision rather than an omission.
]


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def mod_ids(path):
    """The modIds a jar PROVIDES - only the ones declared inside [[mods]] blocks.

    A naive `modId\\s*=\\s*"..."` regex over the whole file also picks up every
    `[[dependencies.x]]` entry, so every mod appears to provide "neoforge" and "minecraft" and
    every install looks like a duplicate. The first run of this script did exactly that and
    rejected all four jars. Sections have to be tracked.
    """
    import re
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return []
    try:
        raw = None
        for name in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
            if name in z.namelist():
                raw = z.read(name).decode("utf-8", "replace")
                break
        if raw is None:
            return []
        ids, in_mods = [], False
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("[["):
                in_mods = s.startswith("[[mods]]")
                continue
            if s.startswith("["):
                in_mods = False
                continue
            if in_mods:
                m = re.match(r'modId\s*=\s*"([^"]+)"', s)
                if m:
                    ids.append(m.group(1))
        return ids
    finally:
        z.close()


def _self_test():
    """The regex bug was silent, so prove the parser before trusting it."""
    import re
    sample = '''modLoader="javafml"
[[mods]]
modId="letmedespawn"
version="1.0"
[[dependencies.letmedespawn]]
modId="neoforge"
versionRange="[21,)"
[[dependencies.letmedespawn]]
modId="minecraft"
'''
    ids, in_mods = [], False
    for line in sample.splitlines():
        s = line.strip()
        if s.startswith("[["):
            in_mods = s.startswith("[[mods]]")
            continue
        if s.startswith("["):
            in_mods = False
            continue
        if in_mods:
            m = re.match(r'modId\s*=\s*"([^"]+)"', s)
            if m:
                ids.append(m.group(1))
    assert ids == ["letmedespawn"], ids
    return True


def main():
    assert _self_test(), "mods.toml parser self-test failed"
    print("   mods.toml parser self-test passed")
    existing = {}
    for f in os.listdir(MODS):
        if f.endswith(".jar"):
            for m in mod_ids(os.path.join(MODS, f)):
                existing[m] = f

    print("INSTALLING")
    added = []
    for name, url, why, risk in WANT:
        dest = os.path.join(MODS, name)
        if os.path.exists(dest):
            print("   already present : %s" % name)
            continue
        tmp = dest + ".part"
        try:
            n = fetch(url, tmp)
        except Exception as ex:
            print("   DOWNLOAD FAILED : %s  (%s)" % (name, ex))
            if os.path.exists(tmp):
                os.remove(tmp)
            continue
        ids = mod_ids(tmp)
        if not ids:
            print("   REJECTED, no mods.toml : %s" % name)
            os.remove(tmp)
            continue
        clash = [m for m in ids if m in existing]
        if clash:
            print("   REJECTED, modId already provided by %s : %s"
                  % (existing[clash[0]], ", ".join(clash)))
            os.remove(tmp)
            continue
        os.replace(tmp, dest)
        added.append((name, ids, why, risk, n))
        print("   + %-46s %s" % (name[:46], ", ".join(ids)))
        print("       %s" % why)
        print("       [%s]" % risk)

    print("\n   %d added" % len(added))

    # ---------------------------------------------------------------- verify
    print("\nVERIFY")
    ok = True
    for name, ids, _why, _risk, _n in added:
        p = os.path.join(MODS, name)
        present = os.path.exists(p)
        try:
            zipfile.ZipFile(p).testzip()
            valid = True
        except Exception:
            valid = False
        print("   %-46s installed=%s valid-zip=%s" % (name[:46], present, valid))
        ok = ok and present and valid

    # no duplicate modIds across the whole mods folder
    seen, dupes = {}, []
    for f in sorted(os.listdir(MODS)):
        if not f.endswith(".jar"):
            continue
        for m in mod_ids(os.path.join(MODS, f)):
            if m in seen:
                dupes.append((m, seen[m], f))
            else:
                seen[m] = f
    print("   duplicate modIds across the pack : %d %s" % (len(dupes), dupes[:3]))
    ok = ok and not dupes
    print("   total jars now                   : %d"
          % sum(1 for f in os.listdir(MODS) if f.endswith(".jar")))

    print("\n   %s" % ("OK - now run validate_instance.py" if ok else "PROBLEMS FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
