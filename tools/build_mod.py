# -*- coding: utf-8 -*-
"""Compile and install a purpose-written mod for one of the instances.

TWO PROFILES, ONE CLASSPATH IMPLEMENTATION. This started as the PocketQuests build and now
also builds hubtmfilter for the Cobblemon instance. The classpath resolution is the entire
value of this script - which jars, which exact versions, read out of Prism rather than
guessed - so a second mod gets a profile here instead of a second copy of that logic.

    python build_mod.py                 # pocketquests -> The Hub
    python build_mod.py hubtmfilter     # hubtmfilter  -> Cobblemon NeoForge


Written down because the first several builds were ad hoc javac invocations reconstructed from
memory each time, and the classpath is the whole trick. Notes worth keeping:

  client-...-srg.jar   Prism keeps a fully deobfuscated Minecraft here, with official Mojang
                       names for classes AND methods. This is what makes real mixins possible
                       at all; without it you are guessing at names.
  mergetool-...-api    supplies net.neoforged.api.distmarker.Dist, which nothing else carries.
  loader-...jar        FancyModLoader, for @Mod and FMLEnvironment.
  -proc:none           the Mixin jar ships an annotation processor that wants a full Gradle
                       environment and fails the build if it is allowed to run.

VERSIONS ARE READ FROM PRISM, NOT GUESSED. The first draft of this script globbed the libraries
tree and took the last match by string sort, which is wrong in a way that looks right: it picked
datafixerupper 8.0.16 over 10.0.21 only because "8" sorts after "10", and it picked sponge-mixin
0.17.5 when the pack actually RUNS 0.16.4. So instead the instance names its components in
mmc-pack.json and Prism's meta cache lists each component's exact library coordinates - the same
list it builds the real launch classpath from. Compiling against anything else is guesswork.

The srg jar is the one exception and is still globbed: it is generated locally by Prism rather
than being a declared library, so it appears in no manifest.

Mods being PATCHED are deliberately absent from the classpath: HorrorMessagesMixin names its
target as a string via @Mixin(targets=...), so the horror mod is not needed to compile against,
and that keeps the build from breaking when that mod is updated or removed.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
LIB = os.path.join(PRISM, "libraries")
OUT = os.path.join(HERE, "_build")

# Each profile names its source tree, its instance, and the mods it compiles AGAINST. A mod we
# PATCH never belongs here: PocketQuests names its horror target as a string via
# @Mixin(targets=...) precisely so the build does not depend on that mod existing.
PROFILES = {
    "pocketquests": {
        "src": "mod-src",
        "instance": "The Hub",
        "mod_deps": ["ftb-quests-neoforge-*.jar", "ftb-library-neoforge-*.jar",
                     "architectury-*-neoforge.jar"],
        "expect": ["pocketquests/PocketEffects.class", "pocketquests/PocketQuests.class"],
    },
    "hubtmfilter": {
        "src": "mod-src-cobblemon",
        "instance": "Cobblemon NeoForge",
        # Cobblemon IS on this classpath, unlike the patched mods above, because the mixin names
        # TechnicalMachines as a real class rather than a string and the filter calls its API.
        "mod_deps": ["Cobblemon-neoforge-*.jar", "architectury-*-neoforge.jar",
                     "kotlinforforge-*.jar"],
        "expect": ["hubtmfilter/TmFilter.class", "hubtmfilter/HubTmFilter.class"],
    },
    "hubworldgenfix": {
        "src": "mod-src-cobblemon-wg",
        "instance": "Cobblemon NeoForge",
        # Pure vanilla target - no mod needs to be on the classpath for this one.
        "mod_deps": [],
        "expect": ["hubworldgenfix/PoolRepair.class", "hubworldgenfix/HubWorldgenFix.class"],
    },
    "hubchunkyfix": {
        "src": "mod-src-chunkyfix",
        "instance": "The Hub",
        # Distant Horizons is NOT on this classpath: the mixin names its target as a string via
        # @Mixin(targets=...) and ChunkyReady reaches Chunky by reflection, so neither mod has to
        # be present to compile - which also keeps the build working when either is updated.
        "mod_deps": [],
        "expect": ["hubchunkyfix/ChunkyReady.class", "hubchunkyfix/HubChunkyFix.class"],
    },
}
PROFILE = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in PROFILES else "pocketquests"
_P = PROFILES[PROFILE]
SRC = os.path.join(os.path.dirname(HERE), _P["src"])
INST = os.path.join(PRISM, "instances", _P["instance"])
HUB = os.path.join(INST, "minecraft")

# artifact ids we need on the compile classpath, resolved out of Prism's meta cache
NEEDED = {
    "datafixerupper": "datafixer",
    "brigadier":      "brigadier",
    "gson":           "gson",
    "bus":            "eventbus",
    "mergetool":      "distmarker",
    "loader":         "fml",
    "sponge-mixin":   "mixin",
    "slf4j-api":      "slf4j",
}
# The NeoForge jar itself, which carries every net.neoforged.neoforge.* event class. It is not a
# plain library coordinate (the meta cache lists it as a jarMod / launch artifact), so it is
# resolved against the NeoForge component version straight from mmc-pack.json. Leaving it out is
# what made the first build fail with "package net.neoforged.neoforge.common does not exist".
NEOFORGE_JAR = "net/neoforged/neoforge/%s/neoforge-%s-universal.jar"
MOD_DEPS = _P["mod_deps"]


def natural(v):
    """1.21.1 < 8.0.16 < 10.0.21 - the ordering string sort gets wrong."""
    return [int(p) if p.isdigit() else p for p in re.split(r"[.+\-]", v)]


def coord_to_path(coord):
    """group:artifact:version[:classifier] -> libraries/group/path/artifact/version/file.jar"""
    parts = coord.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else None
    name = "%s-%s%s.jar" % (artifact, version, "-" + classifier if classifier else "")
    return os.path.join(LIB, os.path.join(*group.split(".")), artifact, version, name)


def resolve_classpath():
    """Read the instance components, then each component's library list from the meta cache."""
    pack = json.load(io.open(os.path.join(INST, "mmc-pack.json"), encoding="utf-8"))
    components = [(c["uid"], c["version"]) for c in pack["components"]
                  if not c.get("dependencyOnly")]

    coords = []
    for uid, version in components:
        meta = os.path.join(PRISM, "meta", uid, version + ".json")
        if not os.path.exists(meta):
            print("   note: no meta for %s %s" % (uid, version))
            continue
        d = json.load(io.open(meta, encoding="utf-8"))
        for key in ("libraries", "mavenFiles", "jarMods"):
            for l in (d.get(key) or []):
                if l.get("name"):
                    coords.append(l["name"])

    # newest version per needed artifact, compared properly
    best = {}
    for c in coords:
        p = c.split(":")
        if len(p) < 3 or p[1] not in NEEDED:
            continue
        slot = NEEDED[p[1]]
        if slot not in best or natural(p[2]) > natural(best[slot].split(":")[2]):
            best[slot] = c

    cp, missing = [], []
    mc_version = dict(components).get("net.minecraft", "")
    srg = sorted(glob.glob(os.path.join(
        LIB, "net", "minecraft", "client", mc_version + "-*", "client-*-srg.jar")))
    if srg:
        cp.append(srg[-1])
        print("   %-11s %s" % ("minecraft", os.path.basename(srg[-1])))
    else:
        missing.append(("minecraft", "client-%s-*-srg.jar" % mc_version))

    nf_version = dict(components).get("net.neoforged", "")
    nf = os.path.join(LIB, NEOFORGE_JAR % (nf_version, nf_version))
    if os.path.exists(nf):
        cp.append(nf)
        print("   %-11s %s" % ("neoforge", os.path.basename(nf)))
    else:
        missing.append(("neoforge", nf))

    for slot in sorted(set(NEEDED.values())):
        coord = best.get(slot)
        if coord is None:
            missing.append((slot, "not listed by any component"))
            continue
        path = coord_to_path(coord)
        if not os.path.exists(path):
            missing.append((slot, coord + " -> " + path))
            continue
        cp.append(path)
        print("   %-11s %s" % (slot, os.path.basename(path)))

    for pat in MOD_DEPS:
        hits = sorted(glob.glob(os.path.join(HUB, "mods", pat)))
        if hits:
            cp.append(hits[-1])
            print("   %-11s %s" % ("moddep", os.path.basename(hits[-1])))
        else:
            missing.append(("moddep", pat))
    return cp, missing


def version_of():
    toml = io.open(os.path.join(SRC, "res", "META-INF", "neoforge.mods.toml"),
                   encoding="utf-8").read()
    return re.search(r'version="([^"]+)"', toml).group(1)


def main():
    print("%s build  ->  %s" % (PROFILE, _P["instance"]))
    cp, missing = resolve_classpath()
    if missing:
        print("\n   MISSING classpath entries, build aborted:")
        for n, p in missing:
            print("      %-11s %s" % (n, p))
        return 1

    ver = version_of()
    classes = os.path.join(OUT, "classes")
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(classes)

    sources = []
    for root, _dirs, files in os.walk(os.path.join(SRC, "src")):
        sources += [os.path.join(root, f) for f in files if f.endswith(".java")]
    print("\n   sources   : %d" % len(sources))

    # every path goes in QUOTED: the project lives under "Custom Games" and javac splits an
    # argfile on whitespace, so an unquoted path becomes two bogus flags.
    argfile = os.path.join(OUT, "sources.txt")
    io.open(argfile, "w", encoding="utf-8").write(
        "\n".join('"%s"' % s.replace("\\", "/") for s in sources))

    cmd = ["javac", "-nowarn", "-proc:none", "-encoding", "UTF-8",
           "--release", "21", "-cp", os.pathsep.join(cp), "-d", classes, "@" + argfile]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        print("\n   COMPILE FAILED\n")
        print((r.stdout or "")[-6000:])
        print((r.stderr or "")[-6000:])
        return 1
    notes = [l for l in (r.stderr or "").splitlines() if l.strip()]
    print("   compiled  : ok%s" % ("  (%d notes)" % len(notes) if notes else ""))
    for l in notes:                  # printed, not just counted - a silent note is a wasted one
        print("      %s" % l.strip())

    jar = os.path.join(OUT, "%s-%s.jar" % (PROFILE, ver))
    with zipfile.ZipFile(jar, "w", zipfile.ZIP_DEFLATED) as z:
        n = 0
        for base in (classes, os.path.join(SRC, "res")):
            for root, _dirs, files in os.walk(base):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, base).replace("\\", "/"))
                    n += 1
    print("   jar       : %s  (%d entries, %d KB)"
          % (os.path.basename(jar), n, os.path.getsize(jar) // 1024))

    # ---- install, removing older versions so two never load at once ----
    dest = os.path.join(HUB, "mods")
    for f in os.listdir(dest):
        if f.startswith(PROFILE + "-") and f != os.path.basename(jar):
            os.remove(os.path.join(dest, f))
            print("   removed   : %s" % f)
    shutil.copy2(jar, dest)
    print("   installed : %s -> %s/mods" % (os.path.basename(jar), _P["instance"]))

    # ---- verify the INSTALLED jar contains what it claims ----
    print("\nVERIFY")
    z = zipfile.ZipFile(os.path.join(dest, os.path.basename(jar)))
    names = z.namelist()
    mx = json.loads(z.read("%s.mixins.json" % PROFILE).decode("utf-8"))
    pkg = mx["package"].replace(".", "/")
    ok = True
    for m in list(mx.get("mixins", [])) + list(mx.get("client", [])):
        present = "%s/%s.class" % (pkg, m) in names
        print("   mixin declared and present : %-22s %s" % (m, present))
        ok = ok and present
    for need in list(_P.get("expect", [])) + ["META-INF/neoforge.mods.toml"]:
        print("   %-42s %s" % (need, need in names))
        ok = ok and need in names
    toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    vok = ('version="%s"' % ver) in toml
    print("   mods.toml version matches jar name   : %s" % vok)
    z.close()
    ok = ok and vok
    print("\n   %s" % ("BUILD OK" if ok else "BUILD INCOMPLETE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
