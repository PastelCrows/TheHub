# -*- coding: utf-8 -*-
"""Apply the client settings changes that this specific machine actually benefits from.

Everything here is chosen against measured hardware, not a generic "optimise Minecraft" list:

    CPU   Ryzen 7 2700 (Zen+, 2018) - 8c/16t but weak single-thread, and Minecraft's server
          thread is single-threaded. This is the TPS ceiling, so SERVER-side savings are worth
          more here than anywhere else.
    RAM   32 GB with a fixed 10 GB heap. Comfortable; no change warranted.
    GPU   RTX 3050 with 4 GB of VRAM - the real constraint, and it just took on 64x textures
          plus a shaderpack in every pocket dimension. VRAM savings are worth real money here.

WHAT IS CHANGED, and why each one is safe:

  simulationDistance 10 -> 8   The single biggest server-tick lever. Ticking chunks scale with
                               the square of the distance, so 10 -> 8 is about a third fewer
                               chunks ticking entities, block entities and random ticks. No
                               visual change at all - render distance stays at 12.
  mipmapLevels 4 -> 2          Texture memory, on a 4 GB card now running 64x vanilla textures
                               next to 247 mods' worth of 16x. Mip level 4 keeps a full chain of
                               downscales resident; 2 keeps enough to stop distant shimmer.
  entityShadows true -> false  The vanilla blob shadow under every entity. With a shaderpack
                               enabled in every dimension the shader draws real shadows anyway,
                               so this is close to visually free.

WHAT IS DELIBERATELY LEFT ALONE - these are real levers with real costs, and they are the
user's call rather than a silent edit:

  EntityCulling safeMode       false moves entity-data extraction off the render thread onto the
                               async culling thread (measured in CullTask: `if (!safeMode)
                               extractEntityData(...)` there, and the opposite on the client
                               tick). A genuine FPS win, but it can race with the entity list
                               and the mod author defaults it ON for that reason.
  graphicsMode Fancy -> Fast   A solid win, but it visibly changes clouds, leaves and water -
                               and matters much less with shaders on.
  Sodium leaves_quality FAST   Makes leaves opaque, fewer faces. Visual change, and Leaves Be
                               Gone plus MoreCulling already cover much of this ground.
  Faithful 64x -> 32x          The lever to pull FIRST if VRAM stutter shows up, since it quarters
                               the vanilla atlas. Not pre-emptively, though - 64x was the point.

Refuses to run while the game is open: Minecraft rewrites options.txt on exit and would undo the
edit, exactly as NeoForge does with its configs.
"""
import io
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
OPTIONS = os.path.join(MC, "options.txt")

CHANGES = {
    "simulationDistance": ("8", "a third fewer chunks ticking; no visual change"),
    "mipmapLevels": ("2", "texture memory on a 4 GB card running 64x"),
    "entityShadows": ("false", "shaders draw real shadows; the vanilla blob is redundant"),
}


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq javaw.exe"],
                             capture_output=True, text=True, errors="replace").stdout
        return "javaw.exe" in out
    except Exception:
        return False


def read_options():
    vals = {}
    for line in io.open(OPTIONS, encoding="utf-8"):
        if ":" in line:
            k, v = line.split(":", 1)
            vals[k.strip()] = v.rstrip("\n")
    return vals


def main():
    if not os.path.exists(OPTIONS):
        print("options.txt not found: %s" % OPTIONS)
        return 1
    if game_running() and "--force" not in sys.argv:
        print("REFUSING TO WRITE: Minecraft is running.\n")
        print("   It rewrites options.txt on exit and would undo this. Close it and re-run.")
        return 2

    before = read_options()
    print("BEFORE")
    for k in CHANGES:
        print("   %-22s %s" % (k, before.get(k, "<unset>")))

    lines = io.open(OPTIONS, encoding="utf-8").read().splitlines(True)
    out, touched = [], {}
    for line in lines:
        if ":" in line:
            k = line.split(":", 1)[0].strip()
            if k in CHANGES:
                want = CHANGES[k][0]
                if before.get(k) != want:
                    line = "%s:%s\n" % (k, want)
                    touched[k] = want
        out.append(line)

    # anything not already present gets appended rather than silently skipped
    for k, (want, _why) in CHANGES.items():
        if k not in before:
            out.append("%s:%s\n" % (k, want))
            touched[k] = want

    if not touched:
        print("\n   already applied; nothing to do")
    else:
        if not os.path.exists(OPTIONS + ".prehubtune"):
            shutil.copy2(OPTIONS, OPTIONS + ".prehubtune")
        io.open(OPTIONS, "w", encoding="utf-8", newline="").write("".join(out))
        print("\nAPPLIED")
        for k, v in touched.items():
            print("   %-22s -> %-8s %s" % (k, v, CHANGES[k][1]))

    # ---------------------------------------------------------------- verify
    print("\nVERIFY")
    after = read_options()
    ok = True
    for k, (want, _why) in CHANGES.items():
        got = after.get(k)
        good = got == want
        print("   %-22s %-8s %s" % (k, got, "OK" if good else "FAIL (wanted %s)" % want))
        ok = ok and good

    # the settings we must NOT have disturbed
    for k, expect in (("renderDistance", before.get("renderDistance")),
                      ("entityDistanceScaling", before.get("entityDistanceScaling")),
                      ("particles", before.get("particles"))):
        same = after.get(k) == expect
        print("   %-22s %-8s unchanged=%s" % (k, after.get(k), same))
        ok = ok and same

    print("   backup exists                  %s" % os.path.exists(OPTIONS + ".prehubtune"))
    print("\n   %s" % ("ALL CHECKS PASSED" if ok else "PROBLEMS FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
