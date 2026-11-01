# -*- coding: utf-8 -*-
"""Audit the custom work in Kewz's Cobblemon pack - the part that is not downloadable.

READ-ONLY. Reads his jars, writes nothing to his instance.

WHY THIS MATTERS MORE THAN THE MOD LIST. The parity audit found 224 of 370 jars swap straight to
NeoForge, which is the easy news. The hard news was 74 jars with `+kewz` in the filename: his own
recompiles. Those are the "billion little fixes and tweaks" - they exist nowhere else, and they
are what turns a pile of Cobblemon addons into a complete Pokemon experience.

This works out WHAT each one actually changes, by comparing his jar against the upstream release
it was built from. Every custom jar names its own base version:

    cobblemon-battle-extras-fabric-1.13.45+kewz.1.8.stage3.cd181.sheetfix1.jar
    ^-------- upstream project + version -------^ ^---- his change tags ----^

So the upstream file can be fetched and the two compared entry by entry, by name and CRC. That
gives a precise answer - these classes changed, these assets were added, this data file was
replaced - rather than a guess from the tag names.

WHAT THE TAGS SEEM TO MEAN is recorded as it is learned; they are his shorthand, not a standard.

    sheetfix / spec / tip    sprite sheets, species data, tooltips
    dex / pokedex            Pokedex behaviour
    keys / ui / items / fps  keybinds, interface, item handling, framerate
    skins / officialfx       cosmetics and effects
    loader### / cd### / c### pinned compatibility with a loader or Cobblemon build
    srvfix / nogc / novoxyfog server-side fixes, GC tuning, Voxy fog interaction

    python audit_kewz_custom.py            # inventory and classification only
    python audit_kewz_custom.py --diff     # also fetch upstream jars and diff them
"""
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_parity")
CACHE = os.path.join(OUT, "upstream")
UA = {"User-Agent": "TheHub-parity-audit/1.0 (personal modpack planning)"}

COBBLE = re.compile(r"cobble|pokemon|poke|dex|mega|raid|battle|badge|rct", re.I)


def tags_of(name):
    m = re.search(r"\+kewz\.([A-Za-z0-9._]+?)(?:\.jar)?$", name)
    return m.group(1).split(".") if m else []


def base_of(name):
    return re.sub(r"\+kewz\.[A-Za-z0-9._]+(?=\.jar$)", "", name)


def composition(path):
    """What KIND of jar is it: code, assets, data?"""
    out = {"class": 0, "assets": 0, "data": 0, "other": 0}
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if n.endswith("/"):
                    continue
                if n.endswith(".class"):
                    out["class"] += 1
                elif n.startswith("assets/"):
                    out["assets"] += 1
                elif n.startswith("data/"):
                    out["data"] += 1
                else:
                    out["other"] += 1
    except Exception:
        pass
    return out


def entries(path):
    """name -> CRC, for diffing two jars precisely."""
    try:
        with zipfile.ZipFile(path) as z:
            return {i.filename: i.CRC for i in z.infolist() if not i.filename.endswith("/")}
    except Exception:
        return {}


def sha512(path):
    h = hashlib.sha512()
    with io.open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def modrinth_search(query):
    url = ("https://api.modrinth.com/v2/search?query=" + urllib.parse.quote(query)
           + "&limit=1")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
            d = json.loads(r.read().decode())
        return d["hits"][0] if d.get("hits") else None
    except Exception:
        return None


def fetch_upstream(filename):
    """Try to find and download the exact upstream file this was built from."""
    os.makedirs(CACHE, exist_ok=True)
    dest = os.path.join(CACHE, filename)
    if os.path.exists(dest):
        return dest
    stem = re.sub(r"[-_]?(fabric|neoforge|forge)?[-_]?v?[\d.+]*\.jar$", "", filename, flags=re.I)
    hit = modrinth_search(stem.replace("-", " ").replace("_", " ").strip())
    if not hit:
        return None
    url = ("https://api.modrinth.com/v2/project/%s/version" % hit["project_id"])
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            versions = json.loads(r.read().decode())
    except Exception:
        return None
    for v in versions:
        for f in v.get("files", []):
            if f["filename"] == filename:
                try:
                    with urllib.request.urlopen(
                            urllib.request.Request(f["url"], headers=UA), timeout=180) as r:
                        io.open(dest, "wb").write(r.read())
                    return dest
                except Exception:
                    return None
    return None


def main():
    do_diff = "--diff" in sys.argv
    if not os.path.isdir(KEWZ):
        print("Kewz instance not found")
        return 1
    os.makedirs(OUT, exist_ok=True)

    custom = sorted(f for f in os.listdir(KEWZ)
                    if f.endswith(".jar") and "+kewz" in f.lower())
    print("custom jars: %d of %d" % (
        len(custom), len([f for f in os.listdir(KEWZ) if f.endswith(".jar")])))
    print("")

    tagcount = {}
    rows = []
    for name in custom:
        path = os.path.join(KEWZ, name)
        tg = tags_of(name)
        for t in tg:
            key = re.sub(r"\d+$", "", t) or t
            tagcount[key] = tagcount.get(key, 0) + 1
        comp = composition(path)
        rows.append((name, tg, comp, bool(COBBLE.search(name))))

    cobble = [r for r in rows if r[3]]
    print("Cobblemon-related custom jars : %d" % len(cobble))
    print("other custom jars             : %d" % (len(rows) - len(cobble)))
    print("")
    print("HIS CHANGE VOCABULARY, by how often each tag appears:")
    for t, c in sorted(tagcount.items(), key=lambda kv: -kv[1])[:22]:
        print("   %-18s %d" % (t, c))

    print("")
    print("COBBLEMON CUSTOM JARS - what kind of change each one is:")
    print("   %-54s %7s %7s %6s" % ("jar", "classes", "assets", "data"))
    for name, tg, comp, _ in sorted(cobble):
        print("   %-54s %7d %7d %6d"
              % (name[:54], comp["class"], comp["assets"], comp["data"]))

    io.open(os.path.join(OUT, "custom_jars.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join("%-70s tags=%s classes=%d assets=%d data=%d"
                  % (n, ",".join(t) or "-", c["class"], c["assets"], c["data"])
                  for n, t, c, _ in rows) + "\n")

    if not do_diff:
        print("")
        print("Run with --diff to fetch the upstream releases and diff them entry by entry.")
        return 0

    print("")
    print("DIFFING against upstream (only jars whose base file can be found):")
    found = missing = 0
    report = []
    for name, tg, comp, is_c in sorted(rows, key=lambda r: (not r[3], r[0])):
        base = base_of(name)
        up = fetch_upstream(base)
        if not up:
            missing += 1
            continue
        found += 1
        his, theirs = entries(os.path.join(KEWZ, name)), entries(up)
        added = sorted(set(his) - set(theirs))
        removed = sorted(set(theirs) - set(his))
        changed = sorted(k for k in set(his) & set(theirs) if his[k] != theirs[k])
        report.append((name, added, removed, changed))
        print("   %-50s +%-4d -%-4d ~%-4d" % (name[:50], len(added), len(removed), len(changed)))
        for k in changed[:4]:
            print("        ~ " + k[:78])

    io.open(os.path.join(OUT, "custom_diffs.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n\n".join("%s\n  added:   %s\n  removed: %s\n  changed: %s"
                    % (n, ", ".join(a[:20]) or "-", ", ".join(r[:20]) or "-",
                       ", ".join(c[:20]) or "-")
                    for n, a, r, c in report) + "\n")
    print("")
    print("upstream found for %d, not found for %d" % (found, missing))
    print("Full diffs in tools/_parity/custom_diffs.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
