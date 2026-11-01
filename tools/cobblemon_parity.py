# -*- coding: utf-8 -*-
"""How close can a NeoForge pack get to Kewz's Cobblemon pack?

READ-ONLY ANALYSIS. Kewz's instance is his; this reads file hashes and writes nothing to it,
which is the standing rule for that folder.

THE QUESTION. The plan was always to fold his pack in as the twelfth arch, and it was never
possible: his is Fabric, The Hub is NeoForge. So the real question is what a from-scratch
NeoForge build of the same idea would be missing, and that is answerable with numbers instead
of impressions.

METHOD. Every jar in his mods folder is hashed and looked up on Modrinth by sha512, which
identifies the exact file rather than guessing from the filename. Each resolved project is then
asked whether it publishes for NeoForge at all, and whether it covers 1.21.1. Three outcomes:

  AVAILABLE      the project lists neoforge and 1.21.1 - a direct swap
  NO NEOFORGE    Fabric-only upstream - needs an equivalent, or the feature is lost
  UNRESOLVED     not on Modrinth under that hash. For this pack that is mostly Kewz's OWN
                 recompiles - every jar with +kewz in the name is a custom build - plus
                 CurseForge-only mods. These are the expensive column: a custom build is not
                 something you can go and download.

A project listing neoforge AND 1.21.1 does not strictly prove a neoforge build exists FOR
1.21.1, only that both appear somewhere in its history. That is the right resolution for a
first pass; the mods that matter get checked individually afterwards.
"""
import hashlib
import io
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_parity")
UA = "TheHub-parity-audit/1.0 (personal modpack planning)"
TARGET_MC = "1.21.1"


def sha512(path):
    h = hashlib.sha512()
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def post(url, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    if not os.path.isdir(KEWZ):
        print("Kewz instance not found at " + KEWZ)
        return 1
    os.makedirs(OUT, exist_ok=True)

    jars = sorted(f for f in os.listdir(KEWZ) if f.endswith(".jar"))
    print("jars in Kewz's pack: %d" % len(jars))
    custom = [f for f in jars if "+kewz" in f.lower()]
    print("  of which are his own recompiles (+kewz): %d" % len(custom))
    print("")

    by_hash = {}
    for name in jars:
        by_hash[sha512(os.path.join(KEWZ, name))] = name

    found = {}
    hashes = list(by_hash)
    for i in range(0, len(hashes), 100):
        found.update(post("https://api.modrinth.com/v2/version_files",
                          {"hashes": hashes[i:i + 100], "algorithm": "sha512"}))
        print("  looked up %d/%d" % (min(i + 100, len(hashes)), len(hashes)))

    resolved, unresolved = {}, []
    for h, name in by_hash.items():
        v = found.get(h)
        if v:
            resolved[name] = v["project_id"]
        else:
            unresolved.append(name)

    ids = sorted(set(resolved.values()))
    print("")
    print("resolved to %d distinct Modrinth projects" % len(ids))

    projects = {}
    for i in range(0, len(ids), 100):
        batch = ids[i:i + 100]
        data = get("https://api.modrinth.com/v2/projects?ids=" +
                   urllib.parse.quote(json.dumps(batch)))
        for pr in data:
            projects[pr["id"]] = pr

    available, no_neoforge = [], []
    for name, pid in sorted(resolved.items()):
        pr = projects.get(pid)
        if not pr:
            unresolved.append(name)
            continue
        loaders = pr.get("loaders", [])
        versions = pr.get("game_versions", [])
        row = (pr.get("title") or pr.get("slug"), name, pr.get("slug"))
        if "neoforge" in loaders and TARGET_MC in versions:
            available.append(row)
        else:
            no_neoforge.append(row + (",".join(sorted(loaders)) or "none",))

    total = len(jars)
    print("")
    print("=" * 74)
    print("  AVAILABLE on NeoForge + %s : %4d   (%.0f%% of the pack)"
          % (TARGET_MC, len(available), 100.0 * len(available) / total))
    print("  NO NeoForge build            : %4d" % len(no_neoforge))
    print("  UNRESOLVED (custom / CF-only): %4d" % len(unresolved))
    print("=" * 74)

    io.open(os.path.join(OUT, "available.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join("%-44s %s" % (t, s) for t, _f, s in sorted(available)) + "\n")
    io.open(os.path.join(OUT, "no_neoforge.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join("%-44s %-34s loaders: %s" % (t, s, l)
                  for t, _f, s, l in sorted(no_neoforge)) + "\n")
    io.open(os.path.join(OUT, "unresolved.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(sorted(unresolved)) + "\n")

    print("")
    print("FABRIC-ONLY, the features that would be lost or need an equivalent:")
    for t, _f, s, l in sorted(no_neoforge)[:30]:
        print("   %-42s %s" % (t[:42], l))
    if len(no_neoforge) > 30:
        print("   ... and %d more, see tools/_parity/no_neoforge.txt" % (len(no_neoforge) - 30))

    print("")
    print("Full lists written to tools/_parity/")
    return 0


if __name__ == "__main__":
    import urllib.parse
    raise SystemExit(main())
