# -*- coding: utf-8 -*-
"""Find the upstream release each of Kewz's recompiles was built from, properly this time.

READ-ONLY on his instance.

WHY A SECOND TOOL. audit_kewz_custom.py --diff could only resolve 19 of 55 recompiles, and that
was a tool limitation rather than a fact about his pack. It searched Modrinth with a stem produced
by a regex that mangled the name: `voxy-0.2.19-beta+1.21.1-fabric+kewz.nogc1.jar` became a query
that matched nothing. 36 jars came back "upstream not found", which then became 36 jars classified
as "inspect by hand" - a misleading answer to the question "how much work is this".

HOW THIS ONE WORKS. Every custom filename is upstream-name + upstream-version + `+kewz.`tags, so
the base filename is recoverable exactly by deleting the tag section:

    cobblemon-battle-extras-fabric-1.13.45+kewz.1.8.stage3.cd181.jar
    -> cobblemon-battle-extras-fabric-1.13.45.jar

Then, rather than guessing a search query, each candidate project's FULL version list is scanned
for a file whose name matches that base - exactly first, then by normalised comparison that
ignores loader words and separators, because authors rename files between releases. The project
is found by trying progressively shorter prefixes of the name, which is what a person would do.

Writes tools/_parity/upstream_map.txt so the diff step can use it.

    python resolve_kewz_upstream.py              # resolve and report
    python resolve_kewz_upstream.py --download   # also fetch the matched jars for diffing
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

KEWZ = os.path.expandvars(
    r"%APPDATA%\PrismLauncher\instances\Kewz's Cobblemon\minecraft\mods")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_parity")
CACHE = os.path.join(OUT, "upstream")
UA = {"User-Agent": "TheHub-upstream-resolver/1.0 (personal modpack planning)"}

LOADER_WORDS = ("fabric", "neoforge", "forge", "quilt")


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode())


def base_of(name):
    """Strip the +kewz tag section, recovering the upstream filename."""
    n = re.sub(r"\+kewz\.[A-Za-z0-9._+-]+(?=\.jar$)", "", name)
    n = re.sub(r"\+kewz(?=\.jar$)", "", n)
    n = re.sub(r"\.kewz\.[A-Za-z0-9._+-]+(?=\.jar$)", "", n)
    return n


def norm(s):
    """Lowercase, drop loader words, keep only alphanumerics - for fuzzy filename equality."""
    s = s.lower()
    if s.endswith(".jar"):
        s = s[:-4]
    for w in LOADER_WORDS:
        s = s.replace(w, "")
    return re.sub(r"[^a-z0-9]", "", s)


def name_tokens(base):
    """The project-name part, as progressively shorter candidate queries."""
    stem = base[:-4] if base.endswith(".jar") else base
    # cut at the first token that starts with a digit (the version)
    parts = re.split(r"[-_+ ]", stem)
    words = []
    for p in parts:
        if re.match(r"^v?\d", p):
            break
        if p.lower() in LOADER_WORDS:
            continue
        if p:
            words.append(p)
    if not words:
        words = [parts[0]] if parts else [stem]
    out = []
    for k in range(len(words), 0, -1):
        out.append(" ".join(words[:k]))
    return out


def search_projects(query, limit=5):
    url = ("https://api.modrinth.com/v2/search?query=" + urllib.parse.quote(query)
           + "&limit=%d&facets=" % limit
           + urllib.parse.quote('[["versions:1.21.1"]]'))
    try:
        return [h["project_id"] for h in get(url).get("hits", [])]
    except Exception:
        return []


def versions_of(pid):
    try:
        return get("https://api.modrinth.com/v2/project/%s/version" % pid, timeout=90)
    except Exception:
        return []


def find_upstream(name):
    """-> (project_id, version_number, filename, url) or None."""
    base = base_of(name)
    target_exact = base.lower()
    target_norm = norm(base)
    tried = set()
    for q in name_tokens(base):
        for pid in search_projects(q):
            if pid in tried:
                continue
            tried.add(pid)
            for v in versions_of(pid):
                for f in v.get("files", []):
                    fn = f["filename"]
                    if fn.lower() == target_exact or norm(fn) == target_norm:
                        return pid, v["version_number"], fn, f["url"]
    return None


def main():
    download = "--download" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    if download:
        os.makedirs(CACHE, exist_ok=True)

    customs = sorted(f for f in os.listdir(KEWZ)
                     if f.endswith(".jar") and "kewz" in f.lower())
    print("custom jars to resolve: %d" % len(customs))
    print("")

    found, missing = [], []
    for name in customs:
        hit = find_upstream(name)
        if hit:
            pid, ver, fn, url = hit
            found.append((name, pid, ver, fn, url))
            print("  OK   %-58s -> %s" % (name[:58], fn[:46]))
            if download:
                dest = os.path.join(CACHE, fn)
                if not os.path.exists(dest):
                    try:
                        with urllib.request.urlopen(
                                urllib.request.Request(url, headers=UA), timeout=300) as r:
                            io.open(dest, "wb").write(r.read())
                    except Exception as e:
                        print("        download failed: %s" % e)
        else:
            missing.append(name)
            print("  --   %-58s    no upstream match" % name[:58])

    io.open(os.path.join(OUT, "upstream_map.txt"), "w", encoding="utf-8",
            newline="\n").write("\n".join(
                "%s\t%s\t%s\t%s" % (n, p, v, f) for n, p, v, f, _u in found) + "\n")

    print("")
    print("=" * 92)
    print("  resolved   : %3d" % len(found))
    print("  unresolved : %3d" % len(missing))
    print("=" * 92)
    if missing:
        print("")
        print("Unresolved - these are CurseForge-only, unpublished, or his own originals:")
        for m in missing:
            print("   " + m)
    print("")
    print("map written to tools/_parity/upstream_map.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
