# -*- coding: utf-8 -*-
"""What is in Kewz's pack, available on NeoForge, and NOT yet in ours.

The honest way to close a gap is to list it, not to keep thinking of mods. This resolves every
jar in his pack and every jar in ours to a Modrinth project, then prints the difference filtered
to things that actually publish for NeoForge 1.21.1 - i.e. the work that is genuinely available
and simply has not been done yet.

Read-only against his instance.

    python cobblemon_gap.py              # the list
    python cobblemon_gap.py --slugs      # just slugs, ready to paste into the build tool
"""
import hashlib
import io
import json
import os
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")
HIS = os.path.join(PRISM, "Kewz's Cobblemon", "minecraft", "mods")
OURS = os.path.join(PRISM, "Cobblemon NeoForge", "minecraft", "mods")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_parity")
UA = {"User-Agent": "TheHub-gap/1.0 (personal modpack planning)"}


def sha512(path):
    h = hashlib.new("sha512")
    with io.open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def resolve(folder):
    """jar name -> project_id, for every jar Modrinth recognises."""
    by_hash = {}
    for n in sorted(os.listdir(folder)):
        if n.endswith(".jar"):
            by_hash[sha512(os.path.join(folder, n))] = n
    found = {}
    hs = list(by_hash)
    for i in range(0, len(hs), 100):
        body = json.dumps({"hashes": hs[i:i + 100], "algorithm": "sha512"}).encode()
        req = urllib.request.Request("https://api.modrinth.com/v2/version_files", data=body,
                                     headers=dict(UA, **{"Content-Type": "application/json"}),
                                     method="POST")
        with urllib.request.urlopen(req, timeout=90) as r:
            found.update(json.loads(r.read().decode()))
    return {by_hash[h]: v["project_id"] for h, v in found.items()}, by_hash


def projects(ids):
    out = {}
    ids = sorted(set(ids))
    for i in range(0, len(ids), 100):
        url = ("https://api.modrinth.com/v2/projects?ids="
               + urllib.parse.quote(json.dumps(ids[i:i + 100])))
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
            for pr in json.loads(r.read().decode()):
                out[pr["id"]] = pr
    return out


def main():
    slugs_only = "--slugs" in sys.argv
    his, _ = resolve(HIS)
    ours, _ = resolve(OURS)
    print("his jars resolved: %d   ours: %d" % (len(his), len(ours)))

    missing_ids = set(his.values()) - set(ours.values())
    meta = projects(missing_ids)
    print("projects he has that we do not: %d" % len(missing_ids))

    avail, unavail = [], []
    for pid in missing_ids:
        pr = meta.get(pid)
        if not pr:
            continue
        ok = "neoforge" in pr.get("loaders", []) and "1.21.1" in pr.get("game_versions", [])
        row = (pr.get("downloads", 0), pr["slug"], pr.get("title", "")[:34],
               (pr.get("description") or "")[:56])
        (avail if ok else unavail).append(row)

    avail.sort(reverse=True)
    unavail.sort(reverse=True)

    if slugs_only:
        for _dl, slug, _t, _d in avail:
            print(slug)
        return 0

    print("")
    print("=" * 96)
    print("AVAILABLE ON NEOFORGE 1.21.1 AND MISSING FROM OURS: %d" % len(avail))
    print("=" * 96)
    for dl, slug, title, desc in avail:
        print("%9d  %-36s %-32s %s" % (dl, slug[:36], title, desc))

    print("")
    print("=" * 96)
    print("NOT ON NEOFORGE - needs an equivalent or goes without: %d" % len(unavail))
    print("=" * 96)
    for dl, slug, title, desc in unavail[:40]:
        print("%9d  %-36s %-32s %s" % (dl, slug[:36], title, desc))
    if len(unavail) > 40:
        print("   ... and %d more" % (len(unavail) - 40))

    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "gap_available.txt"), "w", encoding="utf-8",
            newline="\n").write("\n".join(s for _d, s, _t, _x in avail) + "\n")
    print("")
    print("slugs written to tools/_parity/gap_available.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
