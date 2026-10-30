# -*- coding: utf-8 -*-
"""Validate a Prism FABRIC instance's mod set.

Written because the NeoForge validator never looked at the Fabric packs, and a real crash slipped
through as a result: Zoomify is a Kotlin mod, its entrypoint declares `"adapter": "kotlin"`, and
Fabric Language Kotlin was not installed. Fabric Loader dies with

    Could not find adapter 'kotlin' (mod zoomify!)

before writing anything to latest.log, so the game log just stopped after the mod list and looked
like a mystery hang.

Checks:
  1. duplicate mod ids
  2. `depends` satisfied, including ids supplied via another mod's `provides`
  3. **every entrypoint language adapter is actually provided by some mod** - the check that
     would have caught the Zoomify crash
  4. nested jars (fabric.mod.json "jars") counted as provided

Version ranges are checked loosely on purpose: Fabric uses semver predicates (">=1.2.0 <2",
"~1.2", "^1.2") and a half-correct parser would produce confident false alarms. Presence is
verified strictly; version text is reported, not enforced.
"""
import json
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def read_fmj(z, name="fabric.mod.json"):
    try:
        raw = z.read(name).decode("utf-8", "replace")
    except KeyError:
        return None
    # some mods ship fabric.mod.json with trailing commas or comments; be forgiving
    try:
        return json.loads(raw)
    except Exception:
        try:
            import re
            cleaned = re.sub(r"//[^\n]*", "", raw)
            cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
            return json.loads(cleaned)
        except Exception:
            return None


def scan(path, provided, adapters, requires, entry_adapters, label, tmp, depth=0):
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return
    try:
        fmj = read_fmj(z)
        if fmj:
            mid = fmj.get("id")
            ver = str(fmj.get("version", "0"))
            if mid and mid not in provided:
                provided[mid] = (ver, label, depth > 0)
            for p in fmj.get("provides", []) or []:
                if p not in provided:
                    provided[p] = (ver, label + " (provides)", depth > 0)

            for a in (fmj.get("languageAdapters") or {}):
                adapters.setdefault(a, []).append(mid or label)

            for k, v in (fmj.get("depends") or {}).items():
                requires.append((mid or label, k, v))

            eps = fmj.get("entrypoints") or {}
            for kind, lst in eps.items():
                for e in (lst or []):
                    if isinstance(e, dict) and e.get("adapter"):
                        entry_adapters.setdefault(e["adapter"], set()).add(mid or label)

            # nested jars
            if depth < 3:
                for j in fmj.get("jars", []) or []:
                    inner = j.get("file") if isinstance(j, dict) else None
                    if not inner:
                        continue
                    try:
                        data = z.read(inner)
                    except KeyError:
                        continue
                    out = os.path.join(tmp, "%d_%s" % (depth, os.path.basename(inner)))
                    with open(out, "wb") as f:
                        f.write(data)
                    scan(out, provided, adapters, requires, entry_adapters,
                         "%s > %s" % (label, os.path.basename(inner)), tmp, depth + 1)
    finally:
        z.close()


def main():
    inst = sys.argv[1]
    mods_dir = os.path.join(inst, "minecraft", "mods")
    if not os.path.isdir(mods_dir):
        print("no mods dir: %s" % inst)
        return
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fabricjars")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)

    jars = sorted(f for f in os.listdir(mods_dir) if f.endswith(".jar"))
    provided, adapters, requires, entry_adapters = {}, {}, [], {}
    top = {}
    for j in jars:
        before = set(provided)
        scan(os.path.join(mods_dir, j), provided, adapters, requires, entry_adapters, j, tmp)
        for mid in provided:
            if mid not in before and not provided[mid][2]:
                top.setdefault(mid, []).append(j)

    dupes = [(m, v) for m, v in top.items() if len(v) > 1]

    # The loader always supplies these. mixinextras in particular is bundled INSIDE
    # fabric-loader rather than shipped as a mod jar, so scanning mods/ alone reports it
    # missing - a false alarm that would train you to ignore this tool.
    for builtin in ("minecraft", "java", "fabricloader", "fabric-loader", "mixinextras"):
        provided.setdefault(builtin, ("builtin", "<loader>", False))
    adapters.setdefault("default", ["<loader>"])

    print("\n%s" % os.path.basename(inst))
    print("   jars              : %d" % len(jars))
    print("   mods provided     : %d  (%d nested)"
          % (len(provided), sum(1 for v in provided.values() if v[2])))
    print("   duplicate mod ids : %d %s" % (len(dupes), dupes[:3] if dupes else ""))

    missing = []
    for owner, dep, rng in requires:
        if dep in provided:
            continue
        if dep.startswith("fabric-") and "fabric-api" in provided:
            continue          # fabric-api supplies its modules
        missing.append((owner, dep, rng))

    print("   missing depends   : %d" % len(missing))
    for o, d, r in missing[:14]:
        print("        %-28s needs %-34s %s" % (o, d, r))

    bad_adapters = []
    for ad, users in entry_adapters.items():
        if ad not in adapters:
            bad_adapters.append((ad, sorted(users)))
    print("   missing language adapters : %d   <-- the Zoomify class of crash" % len(bad_adapters))
    for ad, users in bad_adapters:
        print("        adapter '%s' required by %s  -- NOT PROVIDED" % (ad, ", ".join(users)))
    if entry_adapters:
        print("   adapters in use   : %s" % ", ".join(sorted(entry_adapters)))
    print("   adapters provided : %s" % ", ".join(sorted(adapters)))

    ok = not dupes and not missing and not bad_adapters
    print("\n   %s" % ("VALIDATION PASSED" if ok else "PROBLEMS FOUND"))


if __name__ == "__main__":
    main()
