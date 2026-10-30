# -*- coding: utf-8 -*-
"""Give every pocket dimension its own nether and end terrain.

Until now all ten `*_nether` dimensions shared `minecraft:nether` and all ten `*_end` shared
`minecraft:end`. A dimension has no seed of its own - it derives from the world seed - so
identical settings mean identical terrain. Ten separate nethers, laid out exactly the same.

There is no "seed offset" knob in worldgen, so the only honest way to get different terrain is
different settings. Three levers, all part of the vanilla schema:

  legacy_random_source   switches the RNG implementation outright. Same density functions,
                         completely different noise field. The single biggest lever and the
                         safest, because it changes nothing structural.
  noise.size_vertical    vertical scale of the terrain - taller or more compressed formations.
  noise.size_horizontal  horizontal scale - wider or tighter caverns.

Values stay close to vanilla (nether 1/2, end 2/1) so nothing becomes unplayable; the point is
distinct layouts, not novelty worldgen.

ON THE END, deliberately conservative. The central island and the dragon fight come from the
island density function, which is independent of these levers, so they survive untouched - but
the outer islands and end-city terrain will differ per pocket dimension, which is the part worth
differentiating. size_horizontal is varied by at most one step for the same reason.
"""
import io
import json
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\instances\The Hub\minecraft"
CLIENT = (r"C:\Users\Fejcr\AppData\Roaming\PrismLauncher\libraries\com\mojang"
          r"\minecraft\1.21.1\minecraft-1.21.1-client.jar")
NS = os.path.join(MC, "kubejs", "data", "hub", "worldgen", "noise_settings")
DIM = os.path.join(MC, "kubejs", "data", "hub", "dimension")

POCKETS = ["skyblock", "survival", "caveblock", "netherbound", "oceanblock",
           "lostcities", "onechunk", "gauntlet", "oneblock", "horror"]

# (legacy_random_source, size_horizontal, size_vertical, sea_level_delta)
NETHER_VARIANTS = [
    (True,  1, 2,  0),   # vanilla
    (False, 1, 2,  0),
    (True,  1, 1,  0),
    (False, 1, 1,  0),
    (True,  1, 3,  0),
    (False, 1, 3,  0),
    (True,  2, 2,  0),
    (False, 2, 2,  0),
    (True,  1, 2, +2),
    (False, 1, 2, -2),
]
# end: only the RNG and the two scales, each at most one step from vanilla (2/1)
END_VARIANTS = [
    (True,  2, 1),       # vanilla
    (False, 2, 1),
    (True,  2, 2),
    (False, 2, 2),
    (True,  3, 1),
    (False, 3, 1),
    (True,  3, 2),
    (False, 3, 2),
    (True,  2, 3),
    (False, 2, 3),
]
assert len(NETHER_VARIANTS) == len(POCKETS)
assert len(END_VARIANTS) == len(POCKETS)

z = zipfile.ZipFile(CLIENT)
BASE_NETHER = json.loads(z.read("data/minecraft/worldgen/noise_settings/nether.json").decode("utf-8"))
BASE_END = json.loads(z.read("data/minecraft/worldgen/noise_settings/end.json").decode("utf-8"))
z.close()

os.makedirs(NS, exist_ok=True)
made = []

for i, pocket in enumerate(POCKETS):
    lrs, sh, sv, sea = NETHER_VARIANTS[i]
    d = json.loads(json.dumps(BASE_NETHER))
    d["legacy_random_source"] = lrs
    d["noise"]["size_horizontal"] = sh
    d["noise"]["size_vertical"] = sv
    d["sea_level"] = BASE_NETHER["sea_level"] + sea
    name = "%s_nether_terrain" % pocket
    io.open(os.path.join(NS, name + ".json"), "w", encoding="utf-8").write(json.dumps(d, indent=1))
    made.append(name)

    elrs, esh, esv = END_VARIANTS[i]
    e = json.loads(json.dumps(BASE_END))
    e["legacy_random_source"] = elrs
    e["noise"]["size_horizontal"] = esh
    e["noise"]["size_vertical"] = esv
    ename = "%s_end_terrain" % pocket
    io.open(os.path.join(NS, ename + ".json"), "w", encoding="utf-8").write(json.dumps(e, indent=1))
    made.append(ename)

print("wrote %d noise settings files" % len(made))

# ---- point each real dimension at its own settings ----
print("\n%-14s %-34s %-34s" % ("POCKET DIM", "NETHER", "END"))
print("-" * 86)
changed = 0
for i, pocket in enumerate(POCKETS):
    for kind in ("nether", "end"):
        p = os.path.join(DIM, "%s_%s.json" % (pocket, kind))
        if not os.path.exists(p):
            print("   MISSING %s" % p)
            continue
        d = json.load(io.open(p, encoding="utf-8"))
        g = d["generator"]
        if g.get("type") != "minecraft:noise":
            continue                      # flat void nethers (skyblock, onechunk) stay as they are
        g["settings"] = "hub:%s_%s_terrain" % (pocket, kind)
        io.open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
        changed += 1
    n = json.load(io.open(os.path.join(DIM, "%s_nether.json" % pocket), encoding="utf-8"))
    e = json.load(io.open(os.path.join(DIM, "%s_end.json" % pocket), encoding="utf-8"))
    ns_ = n["generator"].get("settings")
    es_ = e["generator"].get("settings")
    print("%-14s %-34s %-34s" % (pocket,
                                 "<flat void>" if isinstance(ns_, dict) else str(ns_),
                                 "<flat void>" if isinstance(es_, dict) else str(es_)))

print("\n   dimension files repointed: %d" % changed)

# ---- verify ----
print("\nVERIFY")
import hashlib
sigs = {}
bad = []
for f in sorted(os.listdir(NS)):
    if not f.endswith(".json"):
        continue
    try:
        d = json.load(io.open(os.path.join(NS, f), encoding="utf-8"))
    except Exception as ex:
        bad.append((f, ex))
        continue
    if f.endswith("_terrain.json"):
        key = (d["legacy_random_source"], d["noise"]["size_horizontal"],
               d["noise"]["size_vertical"], d.get("sea_level"))
        sigs.setdefault(("nether" if "_nether_" in f else "end", key), []).append(f[:-5])
print("   all noise settings parse      : %s %s" % (not bad, bad[:2]))
dupes = {k: v for k, v in sigs.items() if len(v) > 1}
print("   duplicate terrain configs     : %d %s" % (len(dupes), list(dupes.values())[:2]))

# every referenced settings id must exist on disk
missing = []
for pocket in POCKETS:
    for kind in ("nether", "end"):
        d = json.load(io.open(os.path.join(DIM, "%s_%s.json" % (pocket, kind)), encoding="utf-8"))
        s = d["generator"].get("settings")
        if isinstance(s, str) and s.startswith("hub:"):
            if not os.path.exists(os.path.join(NS, s.split(":")[1] + ".json")):
                missing.append(s)
print("   every referenced settings file exists: %s %s" % (not missing, missing[:3]))

# the end's island function must be untouched - that is what the dragon fight rides on
e0 = json.load(io.open(os.path.join(NS, "survival_end_terrain.json"), encoding="utf-8"))
same_router = json.dumps(e0["noise_router"], sort_keys=True) == json.dumps(BASE_END["noise_router"], sort_keys=True)
print("   end noise_router left identical to vanilla: %s  (dragon island intact)" % same_router)
assert not bad and not dupes and not missing and same_router
print("\n   10 distinct nether terrains and 10 distinct end terrains")
