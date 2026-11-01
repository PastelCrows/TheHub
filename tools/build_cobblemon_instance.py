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

# FTB publish to their own maven, never to Modrinth - the same finding as the packwiz
# build. The quest bridge needs these, so they are fetched directly.
# Version pins. Only where "newest" is actively WRONG, with the reason recorded - an unexplained
# pin is a landmine for whoever updates this next.
#
#   gravelmon: every build from Alpha.10 onward is 1.4 MB and contains ZERO species JSONs - the
#   content was moved out of the jar mid-alpha and is not published anywhere on Modrinth as a
#   separate pack. Alpha.8 is 92 MB and carries 9,593 species/form definitions. Checked by
#   downloading each build and counting, not by reading release notes.
PINS = {"gravelmon": "4.0.0-Alpha.8"}

FTB_MAVEN = "https://maven.ftb.dev/releases/dev/ftb/mods/{a}/{v}/{a}-{v}.jar"
FTB = {"ftb-library-neoforge": "2101.1.37",
       "ftb-quests-neoforge": "2101.1.37",
       "ftb-teams-neoforge": "2101.1.11"}

# slug -> why it is here. Chosen from the parity audit, not from taste.
MODS = {
    # ---- core ----------------------------------------------------------------
    "cobblemon":                       "the mod itself",

    # ---- species: the content layer, ~900 species beyond base Cobblemon ------
    "gravelmon":                       "331 species - the biggest fakemon pack he runs",
    "gravels-extended-battles":        "142 species, forms and battle extensions",
    "spaceworldmons":                  "94 species - the Gold/Silver beta designs",
    "lively-mons":                     "73 species",
    "lasers-fakemon-pack":             "70 species",
    "silents-minemons":                "25 species",
    "hiddenmons-cobblemon":            "species not yet in official Cobblemon",
    "missingmons-cobblemon":           "textures, models and spawns for the gaps",

    # ---- trainers and gyms: the backbone of a region ------------------------
    "rctapi":                          "Radical Cobblemon Trainers API - trainer/battle engine",
    "rctmod":                          "1500+ trainers from the real games",
    "more-radical-trainers":           "Scarlet/Violet trainers on top of RCT",
    "rad-gyms":                        "roguelike gyms built on the RCT API",

    # ---- quests: the layer The Hub already speaks -----------------------------
    "cobblemon-quests":                "FTB Quests <-> Cobblemon bridge. The Hub runs FTB Quests.",

    # ---- legendaries and their structures ------------------------------------
    "legendary-monuments":             "special spawning for legendaries and mythicals",
    "cobblemon-legendary-structures":  "Legends Untold - legendaries AND their structures",
    "cobblemon-myths-and-legends-sidemod": "myths and legends side mod",

    # ---- progression systems --------------------------------------------------
    "cobbreeding":                     "breeding",
    "simpletms-tms-and-trs-for-cobblemon": "TMs and TRs - he runs SimpleTMs too",
    "cobbledollars":                   "money and merchants - he runs this",
    "cobbleloots":                     "loot balls",
    "cobblemon-capture-xp":            "team XP on capture",
    "cobblemon-playerxp":              "player XP from battles",
    "cobblemon-unchained":             "naturally spawning hidden abilities",
    "cobblemon-alpha-project":         "naturally spawning alphas",
    "cobblemarks-plus":                "marks",
    "only-bottle-caps":                "bottle caps for IV training",
    "cobblemon-box-link":              "box link from the main games",
    "cobblemon-safepastures":          "pastures that are actually safe",

    # ---- mechanics already chosen in the first build --------------------------
    "cobblemon-mega-showdown":         "mega, Z-moves, tera, dyna",
    "navas-zamega":                    "the Legends ZA megas",
    "cobblemon-novalidation":          "fixes form-change moveset breakage",
    "cobblemonraiddens":               "raids",
    "cobblemon-battle-extras":         "battle UI - he runs a CUSTOM build of this",
    "cobblemon-badgebox":              "badges and gyms",
    "cobblemon-pasture-loot-neoforged": "a literal NeoForge port of his pasture mod",
    "legendary-fishing-cobblemon":     "fishing",
    "cobblemon-mount-mastery":         "riding - he runs a CUSTOM build of this",
    "cobblemon-size-variations":       "size variance",
    "cobblemon-fight-or-flight-reborn": "wild Pokemon react to you",
    "cobblemon-trials-edition":        "replaces spawners and trial spawners",

    # ---- interface and information -------------------------------------------
    "cobblemon-pokedex":               "Cobbledex",
    "cobbledex-rei-emi-jei":           "Pokedex data inside JEI",
    "cobblemon-pokenav":               "PokeNav - he runs CobbleNav",
    "more-cobblemon-tweaks":           "client QoL - he runs a CUSTOM build of this",
    "cobblepedia":                     "in-game Pokepedia via Patchouli",
    "catch-rate-display":              "live catch rate",
    "catch-indicator":                 "whether a mon is catchable",
    "cobblemon-counter":               "KO and capture counters",
    "cobblemon-spawn-notification":    "tells you about important spawns",
    "cobblemon-wiki-gui":              "per-species info",

    # ---- decoration and flavour ----------------------------------------------
    "cobblefurnies":                   "Pokemon-themed furniture",
    "cobble-caf-forms":                "Cafe Remix outfits",
    "cobblemon-armory":                "Pokemon as weapons and armour",

    # ---- glue -----------------------------------------------------------------
    "cobblemon-integrations":          "cross-mod integrations",
    "cobblemon-tim-core":              "shared library for several of the above",

    # Dropped after validation named them as REAL conflicts:
    #   allthemons                   declares itself incompatible with mega_showdown; Mega Showdown wins - 13M downloads, and he runs it
    #   cobblemon-cobblestats        Battle Extras declares it incompatible; Battle Extras wins, he runs a custom build of it
    #   cobblemon-move-inspector     same - Battle Extras supersedes it and refuses to coexist
    #   cobblemon-ride-on            requires cobblemon [1.7,) and we are on 1.8.4; Mount Mastery covers riding anyway

    # NOTE: FTB Quests/Library/Teams are NOT on Modrinth - they publish to
    # maven.ftb.dev. They are fetched separately; see FTB_MAVEN below.

    # Libraries. REQUIRED, not chosen - found by validating each build.
    "architectury-api":                "required by several of the above",
    "kotlin-for-forge":                "required by the Cobbledex JEI bridge",
    "geckolib":                        "required by raid dens",
    "accessories":                     "required by mega showdown",
    "owo-lib":                         "required by accessories",
    "patchouli":                       "required by Cobblepedia",
    "chipped":                         "required by Legendary Monuments",
    "lithostitched":                   "required by Legendary Monuments",
    "resourceful-lib":                 "required by Chipped",
    "athena-ctm":                      "required by Chipped (slug is athena-ctm, not athena)",
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
    want = PINS.get(slug)
    if want:
        v = next((x for x in versions if x.get("version_number") == want), None)
        if not v:
            return None, "pinned version %s not found" % want
    else:
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

    for art, ver in FTB.items():
        fn = "%s-%s.jar" % (art, ver)
        dest = os.path.join(mods_dir, fn)
        if os.path.exists(dest):
            continue
        url = FTB_MAVEN.format(a=art, v=ver)
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url, headers=UA), timeout=180) as r:
                io.open(dest, "wb").write(r.read())
            added += 1
            print("  downloaded %-50s %6d KB  (FTB maven)"
                  % (fn[:50], os.path.getsize(dest) // 1024))
        except Exception as ex:
            print("  FAILED (FTB maven) " + fn + ": " + str(ex))

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
