# -*- coding: utf-8 -*-
"""Install the presentation layer: the three screens a player sees before gameplay.

The target is what Kewz's Cobblemon pack does, rebuilt for NeoForge. His is Fabric, so not one of
his jars transfers. These are the NeoForge equivalents, each confirmed against Modrinth's API for
1.21.1 rather than assumed:

    FancyMenu           3.9.14 (2026-09-28)  title screen, pause menu, multiplayer screen
    Melody              1.0.10               FancyMenu's audio library - REQUIRED by 3.9.x
    DrippyLoadingScreen 3.1.5  (2026-08-01)  the world-loading screen, same editor as FancyMenu
    SimpleSplashScreen  1.21-1.3.2           the Mojang-logo stage before any of that

Three different screens, and it is worth keeping them apart: SimpleSplashScreen is the very first
stage (the Mojang logo), Drippy is the loading screen you watch while a world opens, FancyMenu is
everything you can click.

Melody is the easy one to miss. FancyMenu 3.9.14 declares Konkrete [1.9.4,) and Melody [1.0.6,)
as REQUIRED; Konkrete was already installed as a NeoForge build at 1.9.9, Melody was not there at
all, and a missing FancyMenu dependency is the kind of thing that takes the loader down without a
useful message.

Drippy was not found by searching. FancyMenu's own neoforge.mods.toml lists it as an optional
dependency, which is a far better signal than a search result - it is by the same author and uses
the same layout editor. Its three required dependencies are exactly the three mods above.

SimpleSplashScreen is the weak link, and worth saying out loud: it is the only NeoForge option for
the Mojang-logo stage, its one 1.21.1 build is from June 2024, and it needs Cloth Config (already
installed). Marked `release` and declares 1.21.1 explicitly, but unmaintained. Dropping it costs
only that first stage; the other two are independent of it.

KNOWN TENSION, not resolved here: RRLS is installed with hideOverlays = "ALL" so that resource
reloads happen behind the world instead of behind a loading screen - that is a deliberate
performance choice and it is what makes the 90-second texture swap non-blocking. Drippy customises
the screen RRLS is hiding. Expect to pick one: a branded loading screen, or reloads that do not
stop the game. Try it and decide which is worth more.

Nothing here is CONFIGURED by this script. FancyMenu and Drippy layouts are built with their
in-game editors and saved to config/fancymenu/customization/*.txt; SimpleSplashScreen reads images
and colours from its own config folder. This only puts the jars in place so that work can start.

Run with --apply to actually write. Without it, this prints what it would do.
"""
import io
import os
import re
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
MODS = os.path.join(MC, "mods")
UA = "hub-pack-setup/1.0 (personal modpack)"

# (filename, url, why, risk)
WANT = [
    ("fancymenu_neoforge_3.9.14_MC_1.21.1.jar",
     "https://cdn.modrinth.com/data/Wq5SjeWM/versions/P9dDosz2/"
     "fancymenu_neoforge_3.9.14_MC_1.21.1.jar",
     "the title screen, pause menu and multiplayer screen - built in its own in-game editor",
     "release, current (2026-09-28)"),

    ("melody_neoforge_1.0.10_MC_1.21.jar",
     "https://cdn.modrinth.com/data/CVT4pFB2/versions/efcdRVZP/"
     "melody_neoforge_1.0.10_MC_1.21.jar",
     "REQUIRED by FancyMenu 3.9.x - its audio library, no dependencies of its own",
     "release"),

    ("drippyloadingscreen_neoforge_3.1.5_MC_1.21.1.jar",
     "https://cdn.modrinth.com/data/v3CYg2V9/versions/MVgsDsSB/"
     "drippyloadingscreen_neoforge_3.1.5_MC_1.21.1.jar",
     "the WORLD-LOADING screen, with the same layout editor as FancyMenu - found as an optional "
     "dependency declared by FancyMenu itself, which is a better signal than a search result",
     "release, current (2026-08-01); requires FancyMenu + Konkrete + Melody, all now present"),

    ("SimpleSplashScreen-NeoForge-1.21-1.3.2.jar",
     "https://cdn.modrinth.com/data/4uhcFYch/versions/yjWMWufp/"
     "SimpleSplashScreen-NeoForge-1.21-1.3.2.jar",
     "the Mojang-logo stage: background image, colours, progress bar style",
     "release, but a 2024 build and the only NeoForge option - see the module docstring"),
]


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    with io.open(path, "wb") as f:
        f.write(data)
    return len(data)


# The duplicate check reuses add_performance_mods.mod_ids rather than reimplementing it. The
# reimplementation here was wrong within an hour: it split sections on a regex anchored with
# `\s*$`, and neoforge.mods.toml writes `[[mods]] #mandatory` with a trailing comment, so the
# split never matched and FancyMenu and Melody both reported providing NOTHING. One parser, one
# place, already carrying its own note about the last time this went wrong.
from add_performance_mods import mod_ids  # noqa: E402


def _self_test():
    """The duplicate check has been wrong before; prove the parser on a real installed jar."""
    checks = [("pocketquests-1.15.0.jar", "pocketquests"),
              # written as `[[mods]] #mandatory`; the trailing comment is what broke the first
              # parser, so it is the one that has to stay in the self-test
              ("fancymenu_neoforge_3.9.14_MC_1.21.1.jar", "fancymenu")]
    done = []
    for name, want in checks:
        path = os.path.join(MODS, name)
        if not os.path.exists(path):
            continue
        ids = list(mod_ids(path))
        assert want in ids, "mod_ids self-test failed on %s: got %r" % (name, ids)
        done.append(name)
    if not done:
        return "mod_ids self-test skipped (no sample jar installed yet)"
    return "mod_ids parser verified against " + " and ".join(done)


def main():
    apply = "--apply" in sys.argv
    print(_self_test())
    print("")

    if not os.path.isdir(MODS):
        print("mods folder not found: " + MODS)
        return 1

    existing = {}
    for name in os.listdir(MODS):
        if name.endswith(".jar"):
            for mid in mod_ids(os.path.join(MODS, name)):
                existing[mid] = name

    rc = 0
    for name, url, why, risk in WANT:
        dest = os.path.join(MODS, name)
        if os.path.exists(dest):
            print("PRESENT  " + name)
            continue
        print(("WOULD ADD" if not apply else "ADDING  ") + " " + name)
        print("         why  : " + why)
        print("         risk : " + risk)
        if not apply:
            continue
        tmp = dest + ".part"
        try:
            size = fetch(url, tmp)
        except Exception as ex:
            print("         FAILED: " + str(ex))
            rc = 1
            continue
        ids = mod_ids(tmp)
        clash = {m: existing[m] for m in ids if m in existing}
        if clash:
            os.remove(tmp)
            print("         REFUSED: already provided by " + ", ".join(
                "%s (%s)" % (m, f) for m, f in sorted(clash.items())))
            rc = 1
            continue
        os.replace(tmp, dest)
        for m in ids:
            existing[m] = name
        print("         ok   : %d KB, provides %s" % (size // 1024, ", ".join(sorted(ids))))

    print("")
    print("Now run validate_instance.py - it is what checks the dependency RANGES, which is the")
    print("question this script does not answer (Konkrete 1.9.9 is installed; FancyMenu 3.9.14")
    print("has to be happy with that exact version).")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
