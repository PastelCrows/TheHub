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
#
#   matthiesen-core: the move tutor and poke power both declare [1.3.0,2.0.0),
#   and the newest build is 2.0.0 - outside the range by one patch. Pinned to the
#   last 1.x so they load at all.
#   gravels-extended-battles: Gravelmon 4.0.0-Alpha.8 does not declare a RANGE for this,
#   it pins one exact version id - MMwKsJoI = 2.0.0-Alpha.15. Resolving it to "newest"
#   instead installed Alpha.37, and that HUNG THE GAME: from 2.0.0-Alpha.16 onward GEB
#   downloads species on demand and asks the client for a selection code at startup.
#   The prompt blocks mod construction forever under javaw, which has no stdin - the
#   JVM thread dump put modloading-worker-0 in ProcessSelectionPrompt.next() while the
#   render thread sat in ModLoader.waitForFuture. Alpha.15 carries 0 ondemand classes
#   and 0 prompt classes; Alpha.37 carries 139 and 13. Verified by reading both jars.
#   This is also why Gravelmon Alpha.10+ is 1.4 MB instead of 92 MB - same redesign.
#   cameraoverhaul: every 1.21.1 neoforge build from 2.0.2 up declares cloth_config
#   ">=16.0.0", and cloth-config does not publish 16 for 1.21.1 at all - it stops at
#   15.0.140. That is an upstream packaging bug, and it would refuse to load. 2.0.0 covers
#   mc 1.20.6-1.21.1 and asks for cloth ">=14.0.0", which 15.0.140 satisfies. All nine
#   builds were checked by reading their tomls.
PINS = {"gravelmon": "4.0.0-Alpha.8", "matthiesen-core": "1.3.5",
        "gravels-extended-battles": "2.0.0-Alpha.15",
        "cameraoverhaul": "2.0.0-neoforge+mc.1.20.6-1.21.1"}

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


    # ---- the gap, found by diffing his pack against ours ---------------------
    # cobblemon_gap.py resolved both packs to Modrinth projects and listed what he has, we lack,
    # and NeoForge publishes. Only 16 were Cobblemon-specific - the rest of his 370 is a general
    # survival layer The Hub already carries.
    "cobblemon-rustling-spots":        "dynamic world-driven rustling spots",
    "rs-teamrocket-addon":             "Jessie and James interrupt rustling spots",
    "wild-battle-api":                 "shared wild-battle AI, needed by several addons",
    "cobblemon-move-tutor":            "a move tutor NPC",
    "cobblemon-minigames":             "Game Corner arcade and casino",
    "cobblemon-failskins":             "character cosmetics - he runs this",
    "cobblemon-shiny-cookie":          "shiny cookies",
    "cobblemon-smartphone":            "the smartphone he runs a Pokedex app on",
    "aios-extra-structures":           "more Cobblemon structures - region building material",
    "msd-ores":                        "ores for crafting Mega Showdown items",
    "pokemon-fly-transitions":         "Pokemon-style Fly transitions",
    "lootrmon":                        "Lootr + Cobblemon gilded chest compatibility",
    "lootr":                           "per-player loot - every player gets their own chest",
    "cobblemon-poke-power":            "Pokemon as a power source for tech mods",
    "torchmaster":                     "spawn control blocks - he uses these to shape spawns",
    "cobblemon-torchmaster-fix":       "makes Torchmaster actually stop Cobblemon spawns",
    "oracle-index":                    "client-side in-game documentation",


    # ---- the foundation layer -------------------------------------------------
    # Kewz's pack is a full survival pack with Pokemon on top, and the gap analysis showed 192 of
    # the 255 projects separating us were exactly this. ETF and EMF are not optional niceties
    # here: emissive and custom entity textures/models are what make Pokemon look right, and BOTH
    # COBBLEVERSE and the official Cobblemon NeoForge pack ship them.
    "sodium":                          "renderer",
    "sodium-extra":                    "the options Sodium leaves out",
    "reeses-sodium-options":           "a usable Sodium options screen",
    "iris":                            "shaders",
    "lithium":                         "game logic optimisation",
    "ferrite-core":                    "memory",
    "modernfix":                       "startup, memory, the lot",
    "immediatelyfast":                 "immediate-mode rendering",
    "entityculling":                   "async path-traced culling - matters with many Pokemon",
    "moreculling":                     "more culling",
    "badoptimizations":                "non-render optimisations",
    "clumps":                          "clumps XP orbs - battles drop a lot",
    "entitytexturefeatures":           "ETF - emissive and random entity textures",
    "entity-model-features":           "EMF - custom entity models; both packs ship these",
    # continuity is a FABRIC mod - it asks for connector and fabric_api, which is not a
    # thing on pure NeoForge. Fusion is the NeoForge connected-textures mod, and The Hub
    # already runs it.
    "fusion-connected-textures":       "connected textures, the NeoForge one",
    "not-enough-animations":           "first-person animations in third person",
    "just-zoom":                       "zoom - zoomify is Fabric-only; The Hub uses this one",
    "jade":                            "what am I looking at",
    "jei":                             "recipes - the Cobbledex bridge needs it",
    "appleskin":                       "food HUD",
    "xaeros-minimap":                  "minimap",
    "xaeros-world-map":                "world map - essential for eleven regions",
    "mouse-tweaks":                    "inventory handling",
    "controlling":                     "searchable keybinds",
    "shulkerboxtooltip":               "see inside shulkers",
    "enchantment-descriptions":        "what enchantments do",
    "sound-physics-remastered":        "sound occlusion and reverb",
    "spark":                           "profiler - this pack will need it",

    # survival, storage and building - the layer he actually plays
    "sophisticated-backpacks":         "the backpacks, and NeoForge-NATIVE here; he runs a port",
    "sophisticated-storage":           "matching storage, also native",
    "toms-storage":                    "simple vanilla-style storage",
    "waystones":                       "fast travel - eleven regions need it",
    "lootr":                           "per-player loot chests",
    "comforts":                        "sleeping bags and hammocks",
    "handcrafted":                     "furniture for building towns",
    "supplementaries":                 "building blocks and utilities",
    "farmers-delight":                 "cooking",
    "oritech":                         "the tech mod he added and liked",
    "visual-workbench":                "items stay in the crafting table",

    # NOTE: FTB Quests/Library/Teams are NOT on Modrinth - they publish to
    # maven.ftb.dev. They are fetched separately; see FTB_MAVEN below.

    # Libraries. REQUIRED, not chosen - found by validating each build.
    "architectury-api":                "required by several of the above",
    "kotlin-for-forge":                "required by the Cobbledex JEI bridge",
    "geckolib":                        "required by raid dens",
    "accessories":                     "required by mega showdown",
    "owo-lib":                         "required by accessories",
    "searchables":                     "required by Controlling",
    "puzzles-lib":                     "required by Visual Workbench",
    "bookshelf-lib":                   "required by Enchantment Descriptions",
    "prickle":                         "required by Enchantment Descriptions",
    "konkrete":                        "required by Just Zoom",
    "sophisticated-core":              "required by the backpacks and storage",
    "moonlight":                       "required by Supplementaries",
    "balm":                            "required by Waystones",
    "matthiesen-core":                 "required by the move tutor and poke power",
    "patchouli":                       "required by Cobblepedia",
    "chipped":                         "required by Legendary Monuments",
    "lithostitched":                   "required by Legendary Monuments",
    "resourceful-lib":                 "required by Chipped",
    "athena-ctm":                      "required by Chipped (slug is athena-ctm, not athena)",

    # ---- HIS PACK IS NOT A POKEMON PACK, IT IS A PACK WITH POKEMON IN IT -------
    # The gap was 237 jars, and it got dismissed here twice as "client/perf/QoL" - which was
    # both inaccurate and the wrong way to think about it. tools/cobblemon_gap.py measured 158
    # projects he runs that publish for NeoForge 1.21.1 and we did not have, and that list is
    # the pack's whole character: nineteen [Let's Do] mods of villages, restaurants and farms,
    # Terrablender and Biolith for worldgen, Serene Seasons, Enhanced Celestials, a building
    # palette, a camera layer and an audio layer. The region work does not substitute for any
    # of this - Terrablender and Biolith are what the region work is BUILT ON.
    # ---- towns, food and farms - the [Let's Do] suite, which is how a region stops looking
    # like vanilla and starts looking like a Pokemon town
    "lets-do-vinery":                      "",
    "lets-do-meadow":                      "",
    "lets-do-beachparty":                  "",
    # Curios is NOT optional here, whatever the tomls say. [Let's Do] Beachparty's neoforge
    # main class hard-references top.theillusivec4.curios.api...ICurioItem in its constructor
    # (the beach hat), and its toml declares only neoforge, minecraft and architectury - no
    # curios entry at all, required OR optional. So mod construction died with a
    # NoClassDefFoundError, which aborted the whole parallel task, which left registries frozen
    # before cobblenav had registered its items - and THAT is what surfaced as the crash report.
    # No static validator can catch this: the declaration is simply wrong. Only launching finds
    # it. Eleven other mods here guard their curios integration properly; this one does not.
    # Curios and Accessories coexist by design - Accessories ships accessories_compat_layer for
    # exactly this - and nothing in the set declares curios incompatible.
    "curios":                              "hard-referenced by beachparty, undeclared",
    "lets-do-farm-charm":                  "",
    "lets-do-herbalbrews":                 "",
    "lets-do-furniture":                   "",
    "lets-do-hearth-timber":               "",
    "lets-do-lilis-pottery":               "",
    "lets-do-alpine-whispers":             "",
    "lets-do-addon-corn-expansion":        "",
    "lets-do-lilis-lucky-lures":           "",
    "lets-do-candlelight-farmcharm-compat": "",
    "lets-do-bakery-farmcharm-compat":     "",
    "lets-do-brewery-farmcharm-compat":    "",
    "lets-do-addon-compat":                "",
    "lets-do-emi-compat":                  "",
    "seasonal-lets-do":                    "",
    "apple-wood-rebarked":                 "",
    "chefs-delight":                       "",

    # ---- worldgen and biome control - load-bearing for eleven regions, not flavour
    "terrablender":                        "",
    "biolith":                             "",
    "biome-replacer":                      "",
    "streams-reflowing":                   "",
    "the-roads-more-travelled":            "",
    "bathymetry":                          "",
    "head-in-the-clouds":                  "",
    "smooth-skies":                        "",
    "dawn-of-time":                        "",
    "immersive-gateways":                  "",
    "huge-structure-blocks":               "",
    "cubes-without-borders":               "",

    # ---- seasons, weather and sky
    "serene-seasons":                      "",
    "serene-seasons-gen-fix":              "",
    "enhanced-celestials-2-core":          "",
    "enhanced-celestials-2-default-lunar-events": "",
    "enhanced-celestials-2-shader-support": "",
    "immersive-weather-renewed":           "",
    "immersivethunder":                    "",
    "betterdays":                          "",

    # ---- building palette - the blocks a hand-authored region is actually built out of
    "rechiseled":                          "",
    "carved-wood":                         "",
    "diagonal-fences":                     "",
    "diagonal-walls":                      "",
    "diagonal-windows":                    "",
    "furnies":                             "",
    "immersive-paintings":                 "",
    "better-beds":                         "",
    "reconnectible-chains":                "",
    "fast-item-frames":                    "",
    "chiseled-bookshelf-visualizer":       "",
    "lmps":                                "",
    "selectivebounds":                     "",

    # ---- camera, movement and feel - much of what makes his pack read as polished.
    # Do A Barrel Roll and its addon Rolling Down In The Deep are NOT here: every one of
    # DABR's four neoforge builds for 1.21.1 declares fabric_api as a mandatory dependency
    # with no version range, which means it expects Sinytra Connector. Checked all four
    # tomls, not just the newest. Not viable on plain NeoForge.
    "shoulder-surfing-reloaded":           "",
    "cameraoverhaul":                      "",
    "ok-zoomer":                           "",
    "playeranimator":                      "",
    "hang-glider":                         "",
    "dive-in":                             "",
    "bridging-mod":                        "",
    "smooth-swapping":                     "",
    "radial-hot-bar":                      "",
    "clavis":                              "",
    "brb":                                 "",

    # ---- the audio layer
    "sound":                               "",
    "extrasoundsforge":                    "",
    "esf":                                 "",
    "soundsbegone":                        "",
    "extreme_sound_muffler":               "",
    "immersive-melodies":                  "",
    "melody":                              "",
    "music-notification":                  "",
    "chimes":                              "",

    # ---- interface. EMI is what he runs, not JEI, and five of his addons only speak EMI.
    # His own EMI is an unpublished fabric SNAPSHOT, which is why the hash lookup missed it;
    # EMI itself publishes 1.1.24 for neoforge/1.21.1, checked directly. JEI stays as well:
    # the two coexist, and dropping it would break anything here that declares it required.
    "emi":                                 "recipe viewer - what his five emi_* addons need",
    # ---- interface addons and polish
    "emi-loot":                            "",
    "emi-enchanting":                      "",
    "emi-ores":                            "",
    "reliable-emi":                        "",
    "notenoughrecipebook":                 "",
    "trashslot":                           "",
    "immersive-ui":                        "",
    "immersive-hotbar":                    "",
    "obscure-tooltips":                    "",
    "whats-that-slot":                     "",
    "map-tooltip":                         "",
    "effecttimerplus":                     "",
    "fancy-toasts":                        "",
    "detail-armor-bar-reconstructed":      "",
    "eclipseui":                          "required by detail-armor-bar",
    "inventory-particles":                 "",
    "loot-journal":                        "",
    "screenshot-viewer":                   "",
    "screenshot-to-clipboard":             "",
    "highlight":                           "",
    "blur-plus":                           "",
    "better-f1-reborn":                    "",
    "countereds-smooth-f5":                "",
    "resourcify":                          "",
    "craftpresence":                       "",
    "ping-wheel":                          "",
    "what-are-they-up-to":                 "",
    "satisfying-buttons":                  "",
    "emojiful":                            "",
    "interactic-renewed":                  "",
    "discord-chat-connect":                "",

    # ---- performance and stability
    "scalablelux":                         "",
    "ixeris":                              "",
    "smooth-boot":                         "",
    "framepacer":                          "",
    "packforge":                           "",
    "notenoughcrashes":                    "",
    "neruina":                             "",
    "packet-fixer":                        "",
    "fast-ip-ping":                        "",
    "log-begone":                          "",
    "modelfix":                            "",
    "map-distance-fix":                    "",
    "asyncparticles":                      "",
    "vescompatcomp":                       "",
    "fragmentum":                          "",
    "voxy-server-side":                    "",
    "data-anchor":                         "",
    "chunk-loaders":                       "",
    "tiny-takeover-backport":              "",

    # ---- config and resource-pack infrastructure
    "cloth-config":                        "",
    "yacl":                                "",
    "forge-config-api-port":               "",
    "fzzy-config":                         "",
    "supermartijn642s-config-lib":         "",
    "default-options":                     "",
    "globalpacks":                         "",
    "resource-pack-overrides":             "",
    "respackopts":                         "",
    "configurable":                        "",
    "iris-shader-folder":                  "",
    "modefite-item-definition-backport":   "",
    "puzzle":                              "",

    # ---- libraries the above pull in
    "iceberg":                             "",
    "coroutil":                            "",
    "midnightlib":                         "",
    "glitchcore":                          "",
    "mru":                                 "",
    "supermartijn642s-core-lib":           "",
    "particle-core":                       "",
    "prism-lib":                           "",
    "shatterbyte-lib":                     "",
    "libjf":                               "",
    "corgilib":                            "",
    "unilib":                              "",
    "platform":                            "",
    "gnetum":                              "",
    "toadlib":                             "",
    "mossylib":                            "",
    "eveningstarlib":                      "",
    "tlib":                                "",
    "effectual":                           "",
    "fwa":                                 "",

    # ---- THE GAP THE HASH METHOD COULD NOT SEE ---------------------------------
    # cobblemon_gap.py resolves his jars by sha512, so all 74 of his CUSTOM builds hash-match
    # nothing and were simply absent from the comparison. Any mod he runs ONLY as a +kewz
    # recompile was therefore never counted as missing from ours - and 57 of them were. The
    # earlier claim of "3 installable projects short" was true only of his unmodified jars.
    # Measured properly by comparing modIds instead of hashes: 41 third-party mods we lacked
    # (the other 16 are his own originals), of which these publish for NeoForge 1.21.1.
    # Slugs rarely equal modIds - fightorflight lives at cobblemon-fight-or-flight-reborn -
    # so each was resolved by display name and the full slug read back from the API.
    "cobblemon-alatias-fakemon-pack":      "fakemon species pack he runs - we had none of it",
    "kazeran-eeveelutions":                "eeveelution species pack",
    "cobblemon-horizon-mons":              "species pack",
    "cobblemon-journey-mounts":            "rideable mounts for gen1-9",
    "perfectpartners":                     "companion/partner Pokemon system",
    "cobblemon-battle-tower":              "battle tower progression",
    "cobblebase":                          "base-building for Cobblemon",
    "cobblemon-emi-compat":                "Pokemon data inside EMI",
    "extra-move-anims-cobblemon":          "move animations",
    "ftb-quests-cobblemon-entity":         "FTB Quests tasks that target Pokemon - the quest bridge",
    "lets-do-bloomingnature":              "16 biomes - the single biggest biome source in HIS pack",
    "grassier-grass":                      "denser grass",
    "dreamdisplays":                       "display screens",
    "fancymenu":                           "menu customisation - The Hub already uses it",
    "packed-packs":                        "resource-pack profiles",
    "put-a-plug-in-it":                    "PAPI",
    "reactive-music":                      "context-aware music",
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
