# -*- coding: utf-8 -*-
"""Reproduce the four recompiles that REMOVE content, by repackaging our NeoForge jars.

READ-ONLY on his instance. Writes into mod-ports/ in this repo, and optionally into our instance.

WHY THESE FOUR NEED A DIFFERENT METHOD. A datapack overrides a file inside a mod jar; it cannot
delete one. Four of his no-compile recompiles are mostly deletions - that is what his `strip1`,
`nomodel1` and `newonly1` tags mean:

    SpaceworldMons        242 removals  (strip1, nophm1)
    silents-minemons       29 removals  (nomodel1)
    cobblemon-journey-mounts 31 removals (strip1, geofix2)
    cobblemon-horizon-mons   26 removals (newonly1)

Deleting a species or a model is how he resolves collisions between overlapping fakemon packs:
two packs shipping the same Pokemon, or a pack shipping a model that a better one also provides.
That cannot be expressed as data, so the jar itself has to change - which is exactly why he
recompiles instead of writing a datapack.

WHAT THIS DOES. His edit is read as a path-level diff against the upstream FABRIC release he
built from, then the same removals and overrides are applied to OUR NeoForge jar of that mod.
Only `data/**` and `assets/**` paths are touched - never a class, never a mixin config, never
the mod metadata - so the result is the NeoForge mod with his content decisions applied, not a
cross-loader frankenstein.

WHAT IT REFUSES TO DO. A path he removed that does not exist in the NeoForge jar is reported and
skipped rather than ignored silently: the two builds can ship different paths, and a removal
list that quietly matches nothing would look like success while changing nothing. Same for an
override whose target is absent.

Outputs carry a `+hub` suffix so a repackaged jar is never mistaken for an upstream release.

    python repack_kewz_mods.py              # report what it would change
    python repack_kewz_mods.py --apply      # write jars into mod-ports/
    python repack_kewz_mods.py --install    # also swap them into the instance
"""
import io
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")
KEWZ = os.path.join(PRISM, "Kewz's Cobblemon", "minecraft", "mods")
OURMODS = os.path.join(PRISM, "Cobblemon NeoForge", "minecraft", "mods")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "_parity", "upstream")
MAP = os.path.join(HERE, "_parity", "upstream_map.txt")
PORTS = os.path.join(REPO, "mod-ports")

# his jar  ->  the modId of our NeoForge jar to repackage
TARGETS = {
    "SpaceworldMons-4.0-1.21.1+kewz.dex1.nophm1.strip1.held2.jar": "spaceworldmons",
    "silents-minemons-4.4.2+kewz.nomodel1.flowerpot1.jar":         "silentsminemons",
    "cobblemon-journey-mounts-1.7.2+kewz.1.8.geofix2.strip1.jar":   "mr_cobblemon_journeymounts",
    "cobblemon-horizon-mons-1.0.2+kewz.newonly1.jar":               "mr_cobblemon_horizonmons",
}


def entries(path):
    with zipfile.ZipFile(path) as z:
        return {i.filename: i.CRC for i in z.infolist() if not i.filename.endswith("/")}


def modids_of(path):
    import re
    out = set()
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return out
    for t in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if t in z.namelist():
            out |= set(re.findall(r'modId\s*=\s*"([^"]+)"',
                                  z.read(t).decode("utf-8", "replace")))
            break
    if "fabric.mod.json" in z.namelist():
        import json
        try:
            raw = re.sub(r",\s*([}\]])", r"\1",
                         z.read("fabric.mod.json").decode("utf-8", "replace"))
            d = json.loads(raw)
            if d.get("id"):
                out.add(d["id"])
        except Exception:
            pass
    return out


def our_jar_for(modid):
    for f in sorted(os.listdir(OURMODS)):
        if f.endswith(".jar") and modid in modids_of(os.path.join(OURMODS, f)):
            return f
    # Some content jars declare no modId at all - silents-minemons ships only data and assets
    # with no neoforge.mods.toml, so there is nothing to match on. Fall back to the filename
    # stem, which for a data-only pack is the only identity it has.
    stem = modid.replace("_", "").replace("-", "")
    for f in sorted(os.listdir(OURMODS)):
        if not f.endswith(".jar"):
            continue
        norm = f.lower().replace("_", "").replace("-", "")
        if norm.startswith(stem[:12]):
            return f
    return None


def upstream_map():
    m = {}
    if os.path.exists(MAP):
        for line in io.open(MAP, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 4:
                m[p[0]] = p[3]
    return m


def main():
    apply_it = "--apply" in sys.argv or "--install" in sys.argv
    install = "--install" in sys.argv
    mp = upstream_map()
    if apply_it:
        os.makedirs(PORTS, exist_ok=True)

    for hisjar, modid in sorted(TARGETS.items()):
        print("=" * 100)
        up = mp.get(hisjar)
        if not up or not os.path.exists(os.path.join(CACHE, up)):
            print("%-60s  upstream not cached - skipped" % hisjar[:60])
            continue
        ourjar = our_jar_for(modid)
        if not ourjar:
            print("%-60s  modId '%s' not installed here - skipped" % (hisjar[:60], modid))
            continue

        his = entries(os.path.join(KEWZ, hisjar))
        theirs = entries(os.path.join(CACHE, up))
        ours = entries(os.path.join(OURMODS, ourjar))

        removed = sorted(set(theirs) - set(his))
        changed = sorted(k for k in set(his) & set(theirs) if his[k] != theirs[k])
        added = sorted(set(his) - set(theirs))

        def content_only(paths):
            return [p for p in paths
                    if (p.startswith("data/") or p.startswith("assets/"))
                    and not p.endswith(".class")]

        removed, changed, added = (content_only(removed), content_only(changed),
                                   content_only(added))

        rm_hit = [p for p in removed if p in ours]
        rm_miss = [p for p in removed if p not in ours]
        ch_hit = [p for p in changed if p in ours]
        ch_miss = [p for p in changed if p not in ours]

        print("his jar  : %s" % hisjar)
        print("our jar  : %s" % ourjar)
        print("  removals : %4d of %4d found in our jar" % (len(rm_hit), len(removed)))
        print("  overrides: %4d of %4d found in our jar" % (len(ch_hit), len(changed)))
        print("  additions: %4d (new content, no target needed)" % len(added))
        if rm_miss:
            print("  SKIPPED %d removals - path absent from the NeoForge build:" % len(rm_miss))
            for p in rm_miss[:4]:
                print("      " + p[:88])
        if ch_miss:
            print("  SKIPPED %d overrides - path absent from the NeoForge build:" % len(ch_miss))
            for p in ch_miss[:4]:
                print("      " + p[:88])

        if not apply_it:
            continue
        if not rm_hit and not ch_hit and not added:
            print("  nothing applicable - not written")
            continue

        stem = ourjar[:-4]
        outname = "%s+hub.jar" % stem
        outpath = os.path.join(PORTS, outname)
        zh = zipfile.ZipFile(os.path.join(KEWZ, hisjar))
        drop = set(rm_hit)
        with zipfile.ZipFile(os.path.join(OURMODS, ourjar)) as zin, \
                zipfile.ZipFile(outpath, "w", zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                if info.filename.endswith("/") or info.filename in drop:
                    continue
                data = zin.read(info.filename)
                if info.filename in ch_hit:
                    data = zh.read(info.filename)
                zout.writestr(info.filename, data)
            for p in added:
                try:
                    zout.writestr(p, zh.read(p))
                except Exception:
                    pass
        print("  written: mod-ports/%s  (%.1f MB)"
              % (outname, os.path.getsize(outpath) / 1048576.0))

        if install:
            shutil.copy2(outpath, os.path.join(OURMODS, outname))
            os.remove(os.path.join(OURMODS, ourjar))
            print("  installed, replaced %s" % ourjar)

    print("=" * 100)
    if not apply_it:
        print("report only. --apply writes to mod-ports/, --install also swaps them in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
