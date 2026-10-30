# -*- coding: utf-8 -*-
"""Pin per-shaderpack options that should never be left to the pack's own default.

Right now that means one thing: MOTION BLUR OFF, everywhere.

Why a script rather than six hand-written files: every pack spells the option differently, and
five of the six already default to off, so "disable motion blur" is really "find this pack's name
for it and pin it". Getting the name wrong writes a key Iris ignores, which looks identical to
having fixed it. So each name below was read out of the pack itself, and the script re-checks that
the option still exists before writing it.

    pack                        option                default    on by default?
    Nostalgia                   motionblurToggle      defined    YES  <- the one that hurt
    BSL                         MOTION_BLUR           //define   no
    MakeUp UltraFast            MOTION_BLUR           //define   no
    Complementary Reimagined    MOTION_BLUR_EFFECT    -1         no
    Complementary Unbound       MOTION_BLUR_EFFECT    -1         no
    Spooklementary              MOTION_BLUR_EFFECT    -1         no

Nostalgia is survival's shader, which is where it was reported. The Complementary family gates on
`#if MOTION_BLUR_EFFECT == 1`, so -1 is off; BSL and MakeUp ship the #define commented out. The
five are pinned anyway: a profile can turn them on (Nostalgia's own profile.Medium lists
motionblurToggle), and a pinned value says what the pack is meant to look like instead of relying
on a default that an update is free to change.

Iris keeps per-pack settings next to the pack as `<pack file name>.txt` and rewrites that file
whenever the in-game shader options are touched, so run this with the game CLOSED.
"""
import io
import os
import re
import sys
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PACKS = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft\shaderpacks")

# pack file name -> {option: value}
SETTINGS = {
    "Nostalgia_v5.1.zip":                 {"motionblurToggle": "false"},
    "BSL_v10.1.8.zip":                    {"MOTION_BLUR": "false"},
    "MakeUp-UltraFast-9.6.zip":           {"MOTION_BLUR": "false"},
    "ComplementaryReimagined_r5.9.3.zip": {"MOTION_BLUR_EFFECT": "-1"},
    "ComplementaryUnbound_r5.9.3.zip":    {"MOTION_BLUR_EFFECT": "-1"},
    "Spooklementary_v2.0.4.zip":          {"MOTION_BLUR_EFFECT": "-1"},
}


def option_exists(pack_path, option):
    """Is this option actually declared in the pack? Guards against a silently ignored key."""
    pat = re.compile(r"(?m)^\s*(?://\s*)?#define\s+" + re.escape(option) + r"\b")
    with zipfile.ZipFile(pack_path) as z:
        for name in z.namelist():
            if not name.endswith((".glsl", ".properties", ".vsh", ".fsh")):
                continue
            try:
                text = z.read(name).decode("utf-8", "replace")
            except Exception:
                continue
            if pat.search(text):
                return True
    return False


def read_existing(path):
    """Keep every setting already in the file; only the ones named here are overwritten."""
    values = {}
    if not os.path.exists(path):
        return values
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def main():
    if not os.path.isdir(PACKS):
        print("shaderpacks directory not found: " + PACKS)
        return 1

    failures = []
    for pack, wanted in sorted(SETTINGS.items()):
        pack_path = os.path.join(PACKS, pack)
        if not os.path.exists(pack_path):
            print("MISSING  " + pack + "  (not installed - skipped)")
            continue

        for option in wanted:
            if not option_exists(pack_path, option):
                failures.append(pack + ": no such option '" + option + "'")

        settings_path = pack_path + ".txt"
        values = read_existing(settings_path)
        before = dict(values)
        values.update(wanted)

        body = ["#" + time.strftime("%a %b %d %H:%M:%S %Z %Y")]
        for key in sorted(values):
            body.append(key + "=" + values[key])
        io.open(settings_path, "w", encoding="utf-8", newline="\n").write(
            chr(10).join(body) + chr(10))

        changed = [k for k in wanted if before.get(k) != wanted[k]]
        state = "set " + ", ".join(k + "=" + wanted[k] for k in sorted(changed)) \
            if changed else "already correct"
        print("OK       " + pack.ljust(36) + state)

    if failures:
        print("")
        for f in failures:
            print("FAIL     " + f)
        print("")
        print("An option name that does not exist is written anyway and then ignored by Iris,")
        print("which is indistinguishable from having fixed the setting. Re-read the pack.")
        return 1

    print("")
    print("Motion blur pinned off in " + str(len(SETTINGS)) + " shaderpacks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
