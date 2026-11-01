# -*- coding: utf-8 -*-
"""Tune Distant Horizons for this machine, after letting it write its own config.

The point of DH here is the thing the Cobblemon server does with Voxy: a large part of the world
visible at once. The point of THIS file is that DH gets that without taking the CPU away from the
integrated server, which is already the bottleneck in this pack - the smoke log had TPS sagging
to 17 with the server thread 50+ ticks behind.

DH ships no config until it has run once, so this reads the file it wrote rather than inventing
one. Every setting below was found in config/DistantHorizons.toml with its shipped value, and
every change is a reduction from a default that assumes DH is the only demanding thing running.

    numberOfThreads            8 -> 4     The Ryzen 2700 has 8 cores, and the integrated server
                                          needs them more than the LOD builder does. DH takes
                                          half; the server keeps half.
    threadRunTimeRatio       1.0 -> 0.5   The single most useful knob in the file. 1.0 lets DH's
                                          threads run flat out; at 0.5 they idle half the time.
                                          This is the difference between "the world fills in
                                          while I play" and "the game hitches while it does".
    lodChunkRenderDistanceRadius 256 -> 128   Still 2048 blocks of visible terrain - an enormous
                                          view, and the thing that was actually wanted. 256 is
                                          4096 blocks and quadruples the LOD data held in VRAM
                                          and on disk, per dimension, and this pack has 32.

Nothing else is touched. verticalQuality and horizontalQuality stay MEDIUM, transparency stays
COMPLETE, SSAO stays on - those are look, not load, and the look is the reason DH is here.

RAISE THESE LATER, NOT NOW. These are deliberately a floor: start conservative on an untested
pack, play it, and push the radius up if the frame time has room. Going the other way - shipping
256 and discovering it stutters - is how a mod gets blamed and removed.

RUN WITH THE GAME CLOSED. DH rewrites this file on exit.
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
CFG = os.path.join(MC, "config", "DistantHorizons.toml")

# key -> (new value, is_quoted, why)
CHANGES = {
    "numberOfThreads": ("4", False,
                        "half the cores; the integrated server needs the rest"),
    "threadRunTimeRatio": ("0.5", True,
                           "DH threads idle half the time - the anti-stutter knob"),
    "lodChunkRenderDistanceRadius": ("128", False,
                                     "2048 blocks visible; 256 quadruples VRAM and disk"),
}


def main():
    if "javaw.exe" in os.popen('tasklist /FI "IMAGENAME eq javaw.exe" 2>NUL').read():
        print("REFUSING: Minecraft is running. DH rewrites this file on exit, so anything")
        print("written now would be silently reverted.")
        return 1

    if not os.path.exists(CFG):
        print("DistantHorizons.toml does not exist yet. Launch the game once, close it, re-run.")
        return 1

    raw = io.open(CFG, encoding="utf-8", newline="").read()
    before = {}
    changed = 0

    for key, (value, quoted, why) in CHANGES.items():
        pat = re.compile(r"^(\s*" + re.escape(key) + r"\s*=\s*)(\"?)([^\"\r\n]*)(\"?)\s*$", re.M)
        m = pat.search(raw)
        if not m:
            print("MISSING  %s - DH may have renamed it; not writing blind" % key)
            continue
        before[key] = m.group(3)
        new_literal = ('"%s"' % value) if quoted else value
        raw = pat.sub(lambda mm: mm.group(1) + new_literal, raw, count=1)
        changed += 1
        print("%-30s %-8s -> %-8s  %s" % (key, before[key], value, why))

    io.open(CFG, "w", encoding="utf-8", newline="").write(raw)

    # read it back; a regex that matched the comment instead of the setting would show up here
    check = io.open(CFG, encoding="utf-8", newline="").read()
    ok = True
    for key, (value, quoted, _why) in CHANGES.items():
        want = ('%s = "%s"' % (key, value)) if quoted else ("%s = %s" % (key, value))
        if want not in check:
            print("VERIFY FAILED: %s is not set to %s after writing" % (key, value))
            ok = False
    print("")
    print("%d of %d settings applied%s" % (changed, len(CHANGES),
                                           "" if ok else " - BUT VERIFICATION FAILED"))
    print("Raise lodChunkRenderDistanceRadius once you have played it and seen the frame time.")
    return 0 if (ok and changed == len(CHANGES)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
