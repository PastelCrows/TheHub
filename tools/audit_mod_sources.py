# -*- coding: utf-8 -*-
"""How many of the installed jars can an automated installer fetch from Modrinth by hash?

This is the number the packwiz-vs-custom-updater decision turns on, and it was being guessed at.
Modrinth's /v2/version_files takes a list of file hashes and returns the version each one belongs
to, so an exact match means "an installer can pull this file, byte for byte, with no account, no
API key and no manual click".

Anything unmatched is NOT automatically a problem - it may be our own jar, or a library that
another mod ships inside itself - so the output separates those out rather than counting them
all as blockers.
"""
import io
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
pairs = []
for line in io.open(os.path.join(HERE, "hashes.txt"), encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    h, _, name = line.partition(" ")
    pairs.append((h.strip(), name.strip().lstrip("*")))

print("jars on disk:", len(pairs))

found = {}
CHUNK = 100
for i in range(0, len(pairs), CHUNK):
    chunk = pairs[i:i + CHUNK]
    body = json.dumps({"hashes": [h for h, _ in chunk], "algorithm": "sha1"}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.modrinth.com/v2/version_files",
        data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "TheHub-pack-audit/1.0 (local tooling)"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        found.update(json.loads(r.read().decode("utf-8")))
    print("  queried %d/%d" % (min(i + CHUNK, len(pairs)), len(pairs)))

missing = [(h, n) for h, n in pairs if h not in found]
print("")
print("on Modrinth by exact hash : %d" % (len(pairs) - len(missing)))
print("not matched               : %d" % len(missing))
print("")
if missing:
    print("NOT MATCHED")
    for h, n in sorted(missing, key=lambda x: x[1].lower()):
        print("   " + n)
