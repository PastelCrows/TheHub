# -*- coding: utf-8 -*-
"""Find declared exact-version dependencies that the installed set does not satisfy.

WHY THIS EXISTS. The Cobblemon pack hung twice on boot, and the cause was not a bad mod - it
was this resolver preferring "newest for neoforge/1.21.1" over a dependency that named ONE
exact version. Gravelmon 4.0.0-Alpha.8 pins Gravels Extended Battles to version id MMwKsJoI
(2.0.0-Alpha.15); it got Alpha.37, which asks the client a question on stdin during mod
construction and never comes back.

A range is a preference. A version_id is an author saying "this exact build, nothing else."
Modrinth distinguishes the two and so should we, so this checks every installed jar's declared
dependencies and reports the exact pins that are NOT met.

    python check_version_pins.py            # the unmet pins
    python check_version_pins.py --all      # every exact pin, met or not
"""
import hashlib
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODS = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Cobblemon NeoForge\minecraft\mods")
UA = {"User-Agent": "TheHub-pincheck/1.0 (personal modpack planning)"}


def sha512(path):
    h = hashlib.sha512()
    with io.open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        return json.loads(r.read().decode())


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers=dict(UA, **{"Content-Type": "application/json"}), method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def main():
    show_all = "--all" in sys.argv
    jars = sorted(f for f in os.listdir(MODS) if f.endswith(".jar"))
    by_hash = {sha512(os.path.join(MODS, n)): n for n in jars}

    # installed jar -> its own Modrinth version record (carries its dependencies)
    found = {}
    hs = list(by_hash)
    for i in range(0, len(hs), 100):
        found.update(post("https://api.modrinth.com/v2/version_files",
                          {"hashes": hs[i:i + 100], "algorithm": "sha512"}))
    print("resolved %d of %d jars on Modrinth" % (len(found), len(jars)))

    installed_version_ids = {v["id"] for v in found.values()}
    installed_projects = {v["project_id"]: by_hash[h] for h, v in found.items()}

    # every dependency that names an exact version_id
    pins = []
    for h, v in found.items():
        for d in v.get("dependencies", []):
            vid = d.get("version_id")
            if vid and d.get("dependency_type") in (None, "required"):
                pins.append((by_hash[h], d.get("project_id"), vid))

    if not pins:
        print("no exact version pins declared")
        return 0

    want = {}
    for _dep, _pid, vid in pins:
        want[vid] = None
    for vid in list(want):
        try:
            want[vid] = get("https://api.modrinth.com/v2/version/" + vid)
        except Exception:
            want[vid] = None

    names = {}
    ids = sorted({p for _d, p, _v in pins if p})
    for i in range(0, len(ids), 100):
        for pr in get("https://api.modrinth.com/v2/projects?ids="
                      + urllib.parse.quote(json.dumps(ids[i:i + 100]))):
            names[pr["id"]] = pr["slug"]

    unmet, met = [], []
    for dep_jar, pid, vid in sorted(pins):
        pinned = want.get(vid)
        slug = names.get(pid, pid or "?")
        pin_name = pinned["version_number"] if pinned else "(version %s)" % vid
        have_jar = installed_projects.get(pid)
        ok = vid in installed_version_ids
        row = (dep_jar, slug, pin_name, have_jar or "NOT INSTALLED", ok)
        (met if ok else unmet).append(row)

    print("")
    print("=" * 96)
    print("EXACT VERSION PINS NOT SATISFIED: %d" % len(unmet))
    print("=" * 96)
    for dep_jar, slug, pin_name, have, _ok in unmet:
        print("  %s" % dep_jar)
        print("      requires %-32s exactly %s" % (slug, pin_name))
        print("      installed: %s" % have)
    if not unmet:
        print("  (none)")

    if show_all:
        print("")
        print("satisfied pins: %d" % len(met))
        for dep_jar, slug, pin_name, _h, _o in met:
            print("  %-56s -> %s %s" % (dep_jar[:56], slug, pin_name))

    return 1 if unmet else 0


if __name__ == "__main__":
    raise SystemExit(main())
