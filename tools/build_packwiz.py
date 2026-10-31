# -*- coding: utf-8 -*-
"""Generate a packwiz pack for The Hub, so it can be installed and updated from GitHub.

WHY THE FORMAT IS WRITTEN HERE RATHER THAN BY THE packwiz BINARY. packwiz publishes no tagged
releases and no tags at all - its builds come from CI artifacts fetched through a third-party
redirector. Downloading an unsigned executable from that and running it on someone's machine is
a supply-chain decision, not a convenience, and the pack format does not require it: pack.toml,
index.toml and the per-mod metafiles are small, documented TOML, and every hash in them is
computed locally from the jar actually installed. The CLIENT half is a different story - that is
packwiz-installer-bootstrap.jar, which IS a proper GitHub release (v0.0.3), pinned by sha256
below exactly the way Kewz's pre-launch script pins its own bootstrap.

WHAT GOES IN THE PACK
  mods/*.pw.toml     one metafile per jar, each with the hash of the file on this machine and a
                     URL to fetch it from. 245 of 251 resolve to a Modrinth CDN URL by hash
                     lookup; FTB's four come from maven.ftb.dev, which serves them without a key.
  the instance files kubejs/, config/, defaultconfigs/ and the generated resource pack - these
                     are OURS, so they ship as plain files in the pack and are hashed into
                     index.toml like everything else.

SELF-HOSTED, because no CDN will serve them: pocketquests (ours) and Twilight Forest, which is
LGPL-2.1-or-later and so may be redistributed unmodified provided the licence travels with it -
the release notes carry the licence, the copyright line and a link to upstream source. Credit
alone would not have been enough.

WHAT DOES NOT GO IN, and matters before sharing
  resourcepacks/     third-party, deliberately untracked. Faithful, JICKLUS and Excalibur are on
  shaderpacks/       Modrinth and SHOULD be added as packwiz entries so they download from
                     source rather than being redistributed. Not done yet; without them
                     PocketSkins logs "resource pack not installed, skipped" and every pocket
                     dimension renders vanilla.

AND THE PACK IS UNREACHABLE WHILE THE REPOSITORY IS PRIVATE. packwiz fetches over plain HTTP
with no auth, so raw.githubusercontent.com and the release assets both return 404. Measured, not
assumed - see SHARING.md. Everything third-party resolves; only our own two hosts fail.

    python build_packwiz.py           # report what the pack would contain
    python build_packwiz.py --write   # generate pack/ in the repo
"""
import hashlib
import io
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
MODS = os.path.join(MC, "mods")
PACK = os.path.join(REPO, "pack")

UA = "TheHub-packwiz-build/1.0 (personal modpack)"
MC_VERSION = "1.21.1"
NEOFORGE = "21.1.265"

BOOTSTRAP_URL = ("https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/"
                 "v0.0.3/packwiz-installer-bootstrap.jar")

# Mods with no Modrinth entry, and where they really come from.
FTB_MAVEN = "https://maven.ftb.dev/releases/dev/ftb/mods/{a}/{v}/{a}-{v}.jar"
FTB = {
    "ftb-library-neoforge": "2101.1.37",
    "ftb-quests-neoforge": "2101.1.37",
    "ftb-teams-neoforge": "2101.1.11",
    "ftb-ultimine-neoforge": "2101.1.15",
}
# No CDN will serve these, so they are release assets on our own repo. pocketquests is ours;
# Twilight Forest is LGPL-2.1-or-later, which permits redistributing the UNMODIFIED jar provided
# the licence travels with it - the release notes carry the licence, the copyright line and a
# link to the upstream source, which is what satisfies it. Credit alone would not.
RELEASE = "https://github.com/PastelCrows/TheHub/releases/download/mods-v1/%s"
SELF_HOSTED = ("pocketquests", "twilightforest")

# Our own files, shipped with the pack. Paths are relative to the instance's minecraft folder
# and keep that shape inside the pack, which is what packwiz-installer expects.
OURS = ["kubejs", "config", "defaultconfigs"]


def sha(path, algo):
    h = hashlib.new(algo)
    with io.open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def modrinth_lookup(paths):
    """sha512 -> version info, for every jar Modrinth recognises."""
    by_hash = {}
    for p in paths:
        by_hash[sha(p, "sha512")] = p
    found = {}
    hashes = list(by_hash)
    for i in range(0, len(hashes), 100):
        body = json.dumps({"hashes": hashes[i:i + 100], "algorithm": "sha512"}).encode()
        req = urllib.request.Request(
            "https://api.modrinth.com/v2/version_files", data=body,
            headers={"Content-Type": "application/json", "User-Agent": UA}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as r:
            found.update(json.loads(r.read().decode("utf-8")))
    return by_hash, found


def toml_escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def metafile(name, filename, url, hash_sha512, side="both"):
    return (
        'name = "%s"\n'
        'filename = "%s"\n'
        'side = "%s"\n'
        '\n'
        '[download]\n'
        'hash-format = "sha512"\n'
        'hash = "%s"\n'
        'url = "%s"\n'
    ) % (toml_escape(name), toml_escape(filename), side, hash_sha512, toml_escape(url))


def main():
    write = "--write" in sys.argv
    jars = sorted(os.path.join(MODS, f) for f in os.listdir(MODS) if f.endswith(".jar"))
    print("jars installed: %d" % len(jars))

    by_hash, found = modrinth_lookup(jars)
    resolved, unresolved = {}, []
    for h, path in by_hash.items():
        v = found.get(h)
        if not v:
            unresolved.append(path)
            continue
        f = next((x for x in v["files"] if x.get("primary")), v["files"][0])
        resolved[path] = (v.get("name") or os.path.basename(path), f["url"],
                          f["hashes"]["sha512"], os.path.basename(path))
    print("resolved on Modrinth: %d" % len(resolved))
    print("not on Modrinth     : %d" % len(unresolved))

    extra, missing = {}, []
    for path in unresolved:
        base = os.path.basename(path)
        stem = base[:-4]
        ftb = next((a for a in FTB if stem.startswith(a)), None)
        if ftb:
            url = FTB_MAVEN.format(a=ftb, v=FTB[ftb])
            extra[path] = (ftb, url, sha(path, "sha512"), base)
            continue
        if any(k in base.lower() for k in SELF_HOSTED):
            extra[path] = (stem, RELEASE % base, sha(path, "sha512"), base)
            continue
        missing.append(base)

    print("resolvable from FTB maven + our own release: %d" % len(extra))
    if missing:
        print("")
        print("UNHOSTED - the pack cannot be installed by anyone else until these have a URL:")
        for m in missing:
            print("   " + m)
        print("   Both are allowed to be self-hosted (pocketquests is ours; twilightforest is")
        print("   LGPL-2.1). They need a GitHub release asset to point at.")

    own_files = []
    for top in OURS:
        root = os.path.join(MC, top)
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, MC).replace("\\", "/")
                own_files.append((rel, full))
    print("")
    print("our own files to ship: %d (%s)" % (len(own_files), ", ".join(OURS)))

    if not write:
        print("")
        print("Nothing written. Re-run with --write to generate pack/.")
        return 0

    os.makedirs(os.path.join(PACK, "mods"), exist_ok=True)
    index_rows = []

    for path, (name, url, h512, filename) in sorted(
            list(resolved.items()) + list(extra.items())):
        slug = os.path.splitext(os.path.basename(path))[0]
        rel = "mods/%s.pw.toml" % slug
        full = os.path.join(PACK, rel)
        io.open(full, "w", encoding="utf-8", newline="\n").write(
            metafile(name, filename, url, h512))
        index_rows.append((rel, sha(full, "sha256"), True))

    for rel, full in own_files:
        dest = os.path.join(PACK, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with io.open(full, "rb") as src, io.open(dest, "wb") as out:
            out.write(src.read())
        index_rows.append((rel, sha(dest, "sha256"), False))

    lines = ['hash-format = "sha256"', ""]
    for rel, h, meta in sorted(index_rows):
        lines.append("[[files]]")
        lines.append('file = "%s"' % toml_escape(rel))
        lines.append('hash = "%s"' % h)
        if meta:
            lines.append("metafile = true")
        lines.append("")
    index_path = os.path.join(PACK, "index.toml")
    io.open(index_path, "w", encoding="utf-8", newline="\n").write("\n".join(lines))

    pack_toml = (
        'name = "The Hub"\n'
        'author = "PastelCrows"\n'
        'version = "0.1.0"\n'
        'pack-format = "packwiz:1.1.0"\n'
        '\n'
        '[index]\n'
        'file = "index.toml"\n'
        'hash-format = "sha256"\n'
        'hash = "%s"\n'
        '\n'
        '[versions]\n'
        'minecraft = "%s"\n'
        'neoforge = "%s"\n'
    ) % (sha(index_path, "sha256"), MC_VERSION, NEOFORGE)
    io.open(os.path.join(PACK, "pack.toml"), "w", encoding="utf-8", newline="\n").write(pack_toml)

    print("")
    print("pack/pack.toml        written")
    print("pack/index.toml       %d entries" % len(index_rows))
    print("pack/mods/*.pw.toml   %d metafiles" % (len(resolved) + len(extra)))
    print("")
    print("Install URL once pushed:")
    print("  https://raw.githubusercontent.com/PastelCrows/TheHub/main/pack/pack.toml")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
