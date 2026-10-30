# -*- coding: utf-8 -*-
"""Run every check in one go, and be explicit about what these checks CANNOT tell you.

WHAT THEY COVER
  validate_instance    dependency graph: duplicate modIds, missing requirements, version ranges
  check_incompatible   declared incompatibilities between mods
  verify_worlds        portal mixins bind; the region-offset round trip is a true inverse
  verify_skins         every pack/shader name resolves; inheritance; the 1:1 pairing
  verify_effects       the ambience gate binds and decides correctly
  verify_balance       difficulty map, and no recipe denial collides with a quest
  verify_testkits      /tftest and /extest, the starter-kit decisions, the forceload
  tune_settings        the client settings are still what was set
  tune_shaders         motion blur is pinned off in every shaderpack
  fix_advancements     no mod ships a pre-1.20.2 placed_block advancement unrepaired

WHAT THEY DO NOT COVER, and this is the important part: **none of this runs the game.** Every
check here is static analysis of jars and configs, or the mod's own logic executed outside
Minecraft. In particular every mixin that patches another mod carries `require = 0`, which means
a descriptor that no longer matches fails SILENTLY - these checks confirm the descriptor exists
in the target jar today, not that Mixin bound it at runtime.

So a green run here means "nothing is obviously wrong before launch". It does not mean tested.
The log lines to look for after an actual launch are listed at the end of this output.
"""
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub")

CHECKS = [
    ("validate_instance", ["validate_instance.py", HUB], "VALIDATION PASSED"),
    ("check_incompatible", ["check_incompatible.py", HUB], "CLEAN"),
    ("verify_worlds", ["verify_worlds.py"], "ALL CHECKS PASSED"),
    ("verify_skins", ["verify_skins.py"], "ALL CHECKS PASSED"),
    ("verify_effects", ["verify_effects.py"], "ALL CHECKS PASSED"),
    ("verify_balance", ["verify_balance.py"], "ALL CHECKS PASSED"),
    ("verify_testkits", ["verify_testkits.py"], "ALL CHECKS PASSED"),
    ("tune_settings", ["tune_settings.py"], "ALL CHECKS PASSED"),
    ("tune_shaders", ["tune_shaders.py"], "Motion blur pinned off"),
    ("fix_advancements", ["fix_advancements.py"], "override"),
]

# What to grep for in logs/latest.log after the first real launch. Each of these is a line the
# mod prints itself, so its ABSENCE is the signal that a gate silently did not load.
EXPECTED_LOG_LINES = [
    ("[pocketquests] ambience:", "PocketEffects read pocketeffects.json"),
    ("[pocketquests] serversidehorror:", "the 23 effect switches were found by reflection"),
    ("[pocketquests] modded dimensions:", "PocketWorlds read pocketdims.json"),
    ("[pocketquests] difficulty:", "PocketDifficulty read pocketdifficulty.json"),
    ("[pocketquests] skins:", "PocketSkins read pocketskins.json"),
    ("[pocketquests] crafting gate:", "which of the two crafting mixins is live - see FastBenchMixin"),
    ("[pocketquests] crafting rules:", "PocketRules read pocketrules.json"),
    ("Mixin apply", "look for FAILED/ERROR near pocketquests mixins"),
]


def main():
    results = []
    for name, argv, needle in CHECKS:
        r = subprocess.run([sys.executable] + [os.path.join(HERE, argv[0])] + argv[1:],
                           capture_output=True, text=True, errors="replace", cwd=HERE)
        out = (r.stdout or "") + (r.stderr or "")
        ok = needle in out and "FAILURES" not in out and "PROBLEMS FOUND" not in out
        results.append((name, ok, r.returncode, out))
        print("  %-20s %s" % (name, "PASS" if ok else "FAIL"))

    bad = [r for r in results if not r[1]]
    if bad:
        print("\n%d FAILED - output follows\n" % len(bad))
        for name, _ok, _rc, out in bad:
            print("=" * 78)
            print("### %s" % name)
            print("\n".join(out.splitlines()[-25:]))

    print("\n" + "=" * 78)
    print("STATIC ONLY. None of the above launched the game.")
    print("After the next real launch, grep logs/latest.log for these - a MISSING line means")
    print("that gate did not load, and every cross-mod mixin here fails silently by design:\n")
    for needle, why in EXPECTED_LOG_LINES:
        print("    %-42s %s" % (needle, why))

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
