# -*- coding: utf-8 -*-
"""Download shaderpacks for the per-pocket-dimension skins, and verify each is really a shaderpack.

A shaderpack zip and a shaderpack ADDON zip look identical from the outside, and a few popular
packs are addons: they ship only overrides and need the base pack present to do anything. Dropping
one in shaderpacks/ gives either an Iris load error or, worse, a pack that selects but renders
wrong. Spooklementary is 0.5 MB against Nostalgia's 1.8 MB, which is exactly the shape that
deserves checking rather than assuming.

So each download is opened and counted:

  program files   .fsh / .vsh / .glsl under shaders/. A complete pack has dozens; a handful means
                  an addon that overrides a few programs and expects a base pack.
  properties      shaders.properties and/or block.properties, which a standalone pack ships to
                  declare its options and block mappings.

Performance tier comes from Modrinth's own category tags rather than from a guess, because the
whole point of the exercise is shaders that do not cost much: BSL is tagged `low`, Nostalgia
`medium`, MakeUp Ultra Fast `potato`. Anything untagged is treated as unknown and noted.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
DEST = os.path.join(MC, "shaderpacks")
UA = "hub-pack-setup/1.0 (personal modpack)"

# (filename, url, modrinth perf tag, what it is paired with)
WANT = [
    ("Nostalgia_v5.1.zip",
     "https://cdn.modrinth.com/data/xEItlMn3/versions/fzxeGgx7/Nostalgia_v5.1.zip",
     "medium", "JICKLUS - warm, vanilla-like fantasy"),
    ("Spooklementary_v2.0.4.zip",
     "https://cdn.modrinth.com/data/6uJCfiCH/versions/rcr90eRP/Spooklementary_v2.0.4.zip",
     "untagged", "horror-desaturated - purpose-built horror atmosphere"),
    ("MakeUp-UltraFast-9.6.zip",
     "https://cdn.modrinth.com/data/izsIPI7a/versions/t4YRxQug/MakeUp-UltraFast-9.6.zip",
     "potato", "redstone land - FPS first, for large contraptions"),
]

SHADER_EXT = (".fsh", ".vsh", ".glsl", ".gsh", ".csh")


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def inspect(path):
    """(ok, programs, has_properties, note)"""
    try:
        z = zipfile.ZipFile(path)
    except Exception as ex:
        return False, 0, False, "not a valid zip: %s" % ex
    try:
        names = z.namelist()
        programs = sum(1 for n in names if n.lower().endswith(SHADER_EXT))
        props = any(n.lower().endswith(("shaders.properties", "block.properties"))
                    for n in names)
        has_dir = any("shaders/" in n for n in names)
        if not has_dir:
            return False, programs, props, "no shaders/ directory - not a shaderpack"
        kind = "standalone" if programs >= 20 else "LOOKS LIKE AN ADDON"
        return True, programs, props, kind
    finally:
        z.close()


def main():
    if not os.path.isdir(DEST):
        print("shaderpacks folder not found: %s" % DEST)
        return 1

    for name, url, _perf, _why in WANT:
        final = os.path.join(DEST, name)
        if os.path.exists(final):
            print("already present : %s" % name)
            continue
        tmp = final + ".part"
        print("downloading     : %s" % name)
        try:
            n = fetch(url, tmp)
        except Exception as ex:
            print("   FAILED: %s" % ex)
            if os.path.exists(tmp):
                os.remove(tmp)
            continue
        ok = inspect(tmp)[0]
        if not ok:
            print("   rejected, not a shaderpack; not installed")
            os.remove(tmp)
            continue
        os.replace(tmp, final)
        print("   %.1f MB installed" % (n / 1048576.0))

    print("\nVERIFIED  (an addon needs its base pack and must not be used alone)")
    print("%-34s %9s %6s %-22s %s" % ("shaderpack", "programs", "props", "kind", "perf"))
    print("-" * 94)
    perf_of = {n: p for n, _u, p, _w in WANT}
    perf_of.setdefault("BSL_v10.1.8.zip", "low")
    perf_of.setdefault("ComplementaryReimagined_r5.9.3.zip", "untagged")
    perf_of.setdefault("ComplementaryUnbound_r5.9.3.zip", "untagged")

    problems = []
    for f in sorted(os.listdir(DEST)):
        if not f.endswith(".zip"):
            continue
        ok, programs, props, kind = inspect(os.path.join(DEST, f))
        if not ok:
            print("%-34s  %s" % (f[:34], kind))
            problems.append(f)
            continue
        print("%-34s %9d %6s %-22s %s"
              % (f[:34], programs, "yes" if props else "no", kind,
                 perf_of.get(f, "untagged")))
        if "ADDON" in kind:
            problems.append(f)

    if problems:
        print("\n   NEEDS ATTENTION: %s" % ", ".join(problems))
        print("   An addon pack must not be assigned in pocketskins.json on its own.")
    else:
        print("\n   every shaderpack is standalone and usable")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
