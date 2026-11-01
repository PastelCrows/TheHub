# -*- coding: utf-8 -*-
"""Create a standalone NeoForge Cobblemon instance - the twelfth arch, built the way the other
eleven were: as a working instance first, folded into The Hub only once it stands alone.

WHY STANDALONE FIRST. Every pocket dimension in The Hub was a playable instance before it was a
pocket. The one that skipped that step is the one that never happened. This is that step.

WHAT IT INSTALLS. Cobblemon itself, plus a replacement for each feature Kewz's Fabric pack has
that NeoForge was assumed to be missing. The parity audit found eight of nine had an answer, and
two of them - Mount Mastery and Battle Extras - are mods he maintains as his OWN custom builds
and which exist upstream for NeoForge already.

THE LIBRARY LIST WAS NOT GUESSED. The first build installed twelve mods and validate_instance.py
immediately reported six unmet dependencies: architectury, kotlinforforge, geckolib and
accessories. Guessing a Cobblemon library set would have been exactly the kind of assumption that
gets discovered in-game instead of at build time.

RE-RUNNABLE ON PURPOSE. A first build is never complete, because the dependency set is only
discovered by validating it. Existing jars are left alone and missing ones added, so the loop is
build, validate, add, validate.

    python build_cobblemon_instance.py           # report what it would install
    python build_cobblemon_instance.py --apply   # create or top up the instance
"""
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
NAME = "Cobblemon NeoForge"
INST = os.path.join(PRISM, "instances", NAME)
MC_VERSION = "1.21.1"
NEOFORGE = "21.1.265"
LWJGL = "3.3.3"
UA = {"User-Agent": "TheHub-cobblemon-build/1.0 (personal modpack)"}

# slug -> why it is here. Chosen from the parity audit, not from taste.
MODS = {
    "cobblemon":                       "the mod itself",
    "cobblemon-pokedex":               "Cobbledex - replaces his Smartphone Pokedex App",
    "cobbledex-rei-emi-jei":           "Pokedex data in JEI, which The Hub standardises on",
    "cobblemon-badgebox":              "badges and gyms - replaces COBBLEVERSE Badges & Trophies",
    "cobblemonraiddens":               "raids - replaces his raid-icons work",
    "cobblemon-mega-showdown":         "mega evolution - replaces mega-mewtwo and megastorm",
    "cobblemon-battle-extras":         "battle UI - he runs a CUSTOM build of this one",
    "cobblemon-pasture-loot-neoforged": "a literal NeoForge port of the pasture mod he uses",
    "legendary-fishing-cobblemon":     "fishing - replaces better_cobblemon_fishing",
    "cobblemon-mount-mastery":         "riding - he runs a CUSTOM build of this one too",
    "missingmons-cobblemon":           "fills species gaps in the base dex",
    "cobblemon-size-variations":       "size variance, a visible part of his pack's feel",

    # Libraries. REQUIRED, not chosen - found by validating the first build.
    "architectury-api":                "required by size-variations, badgebox, mega showdown",
    "kotlin-for-forge":                "required by the Cobbledex JEI bridge",
    "geckolib":                        "required by raid dens",
    "accessories":                     "required by mega showdown",
    "owo-lib":                         "required by accessories - found on the SECOND validate",
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def newest(slug):
    url = ("https://api.modrinth.com/v2/project/%s/version?loaders=%s&game_versions=%s"
           % (slug, urllib.parse.quote(json.dumps(["neoforge"])),
              urllib.parse.quote(json.dumps([MC_VERSION]))))
    try:
        versions = get(url)
    except Exception as ex:
        return None, str(ex)
    if not versions:
        return None, "no neoforge build for " + MC_VERSION
    v = versions[0]
    f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
    return (v.get("version_number"), f["filename"], f["url"]), None


def write_instance_files():
    io.open(os.path.join(INST, "mmc-pack.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps({"components": [
            {"cachedName": "LWJGL 3", "cachedVersion": LWJGL, "cachedVolatile": True,
             "dependencyOnly": True, "uid": "org.lwjgl3", "version": LWJGL},
            {"cachedName": "Minecraft",
             "cachedRequires": [{"suggests": LWJGL, "uid": "org.lwjgl3"}],
             "cachedVersion": MC_VERSION, "important": True,
             "uid": "net.minecraft", "version": MC_VERSION},
            {"cachedName": "NeoForge",
             "cachedRequires": [{"equals": MC_VERSION, "uid": "net.minecraft"}],
             "cachedVersion": NEOFORGE, "uid": "net.neoforged", "version": NEOFORGE},
        ], "formatVersion": 1}, indent=4) + "\n")

    io.open(os.path.join(INST, "instance.cfg"), "w", encoding="utf-8", newline="\n").write(
        "[General]\n"
        "ConfigVersion=1.3\n"
        "InstanceType=OneSix\n"
        "name=" + NAME + "\n"
        "iconKey=default\n"
        "notes=Standalone NeoForge Cobblemon. Stands alone first; becomes The Hub's twelfth arch\n"
        "      only once it does. See COBBLEMON-PARITY.md.\n"
        "OverrideMemory=true\n"
        "MinMemAlloc=6144\n"
        "MaxMemAlloc=6144\n"
        "uuid=" + uuid.uuid4().hex + "\n")


def main():
    apply = "--apply" in sys.argv
    print("Resolving %d mods for NeoForge %s ..." % (len(MODS), MC_VERSION))
    print("")
    resolved, failed = [], []
    for slug, why in MODS.items():
        info, err = newest(slug)
        if info:
            ver, filename, url = info
            resolved.append((slug, ver, filename, url, why))
            print("  OK    %-34s %-18s %s" % (slug[:34], (ver or "")[:18], why))
        else:
            failed.append((slug, err, why))
            print("  MISS  %-34s %s" % (slug[:34], err))

    print("")
    print("resolved %d, missing %d" % (len(resolved), len(failed)))
    for slug, err, why in failed:
        print("   %-34s %s  (%s)" % (slug, err, why))

    if not apply:
        print("")
        print("Nothing written. Re-run with --apply.")
        return 0

    fresh = not os.path.exists(INST)
    mods_dir = os.path.join(INST, "minecraft", "mods")
    os.makedirs(mods_dir, exist_ok=True)
    if fresh:
        write_instance_files()
        print("")
        print("created instance at " + INST)

    print("")
    total = added = 0
    for slug, ver, filename, url, _why in resolved:
        dest = os.path.join(mods_dir, filename)
        if os.path.exists(dest):
            continue
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
            data = r.read()
        io.open(dest, "wb").write(data)
        total += len(data)
        added += 1
        print("  downloaded %-50s %6d KB" % (filename[:50], len(data) // 1024))
    if not added:
        print("  nothing new to download")

    jars = [f for f in os.listdir(mods_dir) if f.endswith(".jar")]
    print("")
    print("instance : %s" % INST)
    print("mods     : %d jars, %d added this run (%.1f MB)" % (len(jars), added,
                                                               total / 1048576.0))
    print("memory   : 6 GB - Cobblemon alone needs nowhere near The Hub's 12")
    print("")
    print("Validate it, and add whatever it names:")
    print('  python tools/validate_instance.py "%s"' % INST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
