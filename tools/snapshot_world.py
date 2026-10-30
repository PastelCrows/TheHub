# -*- coding: utf-8 -*-
"""Snapshot a seeded hub world, then create new ones by copying it instead of generating them.

THE PROBLEM THIS SOLVES. Creating a fresh hub world is not cheap. On first load the pack has to
place the lobby room, seed eleven pocket dimensions (each a forceload, a structure place and an
unpin, sequenced across ticks), place the Coliseum and the texture showcase, and generate spawn
chunks in every one of them. That is the slow part of "new world", and it is identical every
time - so doing it once and copying the result is strictly better than doing it again.

A snapshot taken AFTER seeding also carries the world's persistentData flags (hubRoomVersion6,
hubWorldSeeded, hubExtrasVersion2), so the new world skips re-seeding rather than redoing it.
That is the whole trick, and it is also the one thing to watch: if a build_* tool changes a
structure, the flag has to be bumped for the change to land. Those flags are deliberately
version-named for exactly this reason - `hubExtrasVersion2` re-places even inside an old
snapshot, where a flag called `hubExtras` would have been skipped forever.

Snapshots live in <instance>/world-snapshots/, outside saves/, so Minecraft never lists them as
playable worlds.

    python snapshot_world.py list
    python snapshot_world.py save "New World (2)" pristine
    python snapshot_world.py new pristine "Test 3"

Refuses to touch anything while the game is running - the region files are open, and a copy
taken mid-write is a corrupt world that looks fine until it does not.
"""
import os
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

INST = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub")
SAVES = os.path.join(INST, "minecraft", "saves")
SNAPS = os.path.join(INST, "world-snapshots")


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq javaw.exe"],
                             capture_output=True, text=True, errors="replace").stdout
        return "javaw.exe" in out
    except Exception:
        return False


def measure(path):
    files = 0
    size = 0
    for root, _d, fs in os.walk(path):
        for f in fs:
            files += 1
            try:
                size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return files, size


def human(n):
    return "%.1f MB" % (n / 1048576.0)


def do_list():
    print("WORLDS  (%s)" % SAVES)
    if os.path.isdir(SAVES):
        for d in sorted(os.listdir(SAVES)):
            p = os.path.join(SAVES, d)
            if os.path.isdir(p):
                f, s = measure(p)
                print("   %-30s %4d files  %10s" % (d, f, human(s)))
    print("\nSNAPSHOTS  (%s)" % SNAPS)
    if not os.path.isdir(SNAPS) or not os.listdir(SNAPS):
        print("   none yet")
        return
    for d in sorted(os.listdir(SNAPS)):
        p = os.path.join(SNAPS, d)
        if os.path.isdir(p):
            f, s = measure(p)
            seeded = os.path.exists(os.path.join(p, "level.dat"))
            print("   %-30s %4d files  %10s  %s"
                  % (d, f, human(s), "" if seeded else "NO level.dat - unusable"))


def copy_verified(src, dst, label):
    if os.path.exists(dst):
        print("   refusing: %s already exists" % dst)
        return 1
    sf, ss = measure(src)
    print("   copying %d files, %s" % (sf, human(ss)))
    shutil.copytree(src, dst)
    df, ds = measure(dst)
    print("\nVERIFY")
    print("   %-40s %s" % ("file count matches", "OK" if df == sf else "FAIL %d vs %d" % (df, sf)))
    print("   %-40s %s" % ("byte count matches", "OK" if ds == ss else "FAIL"))
    have_level = os.path.exists(os.path.join(dst, "level.dat"))
    print("   %-40s %s" % ("level.dat present", "OK" if have_level else "FAIL"))
    ok = df == sf and ds == ss and have_level
    print("\n   %s -> %s  %s" % (label, dst, "OK" if ok else "PROBLEM"))
    return 0 if ok else 1


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] == "list":
        do_list()
        return 0

    if game_running():
        print("REFUSING: Minecraft is running.\n")
        print("   Region files are open; a copy taken mid-write is a corrupt world that looks")
        print("   fine until it does not. Close the game first.")
        return 2

    if argv[0] == "save":
        if len(argv) < 2:
            print("usage: snapshot_world.py save <world> [snapshot-name]")
            return 2
        world = argv[1]
        name = argv[2] if len(argv) > 2 else "pristine"
        src = os.path.join(SAVES, world)
        if not os.path.isdir(src):
            print("no such world: %s" % src)
            return 2
        os.makedirs(SNAPS, exist_ok=True)
        return copy_verified(src, os.path.join(SNAPS, name), "snapshot")

    if argv[0] == "new":
        if len(argv) < 3:
            print("usage: snapshot_world.py new <snapshot-name> <new world name>")
            return 2
        src = os.path.join(SNAPS, argv[1])
        if not os.path.isdir(src):
            print("no such snapshot: %s" % src)
            return 2
        return copy_verified(src, os.path.join(SAVES, argv[2]), "new world")

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
