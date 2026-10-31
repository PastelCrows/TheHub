# -*- coding: utf-8 -*-
"""Generate the textures, models, blockstates and lang for the portal blocks.

PocketPortal registers one block per destination. Without these files every one of them is a
nameless magenta-and-black cube, which is the most visible possible way to ship something broken.

THE COLOURS ARE NOT NEW. Each portal takes the colour of the light block in its arch, from the
same table build_hub_room_v6.py uses and the same one the title screen is painted from - so the
skyblock portal is sea-lantern pale, netherbound's burns shroomlight orange, horror's is soul
lantern blue. Walk up to an arch and the portal in it matches the lamp above it.

They are tempered toward the brand gold exactly as the title art is, for the same reason: twelve
saturated portals in one hall would read as a toybox rather than as deep purple and warm gold.

THE TEXTURE is generated rather than drawn: a dark core with brighter filaments swirling out of
it, built from a polar function so it tiles tolerably and reads at 16x16. Portals in Minecraft
are animated, and these are not - an .mcmeta animation would need a vertical strip of frames and
is worth doing later; a still portal is not broken, it is just calm.

    python build_portal_assets.py            # write into mod-src/res, report
    python build_portal_assets.py --check     # verify every registered block has its files
"""
import io
import json
import math
import os
import random
import re
import sys

from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(os.path.dirname(HERE), "mod-src", "res", "assets", "pocketquests")
JAVA = os.path.join(os.path.dirname(HERE), "mod-src", "src", "pocketquests", "PocketPortal.java")

GOLD = (198, 160, 42)
TEMPER = 0.55

# destination -> (display name, light colour from its arch)
PORTALS = {
    "hub":         ("Hub Portal",            (198, 160,  42)),   # the hall itself
    "skyblock":    ("Skyblock Portal",       (142, 178, 186)),   # sea lantern
    "survival":    ("Survival Portal",       (236, 184, 112)),   # lantern
    "caveblock":   ("Caveblock Portal",      (242, 205, 122)),   # glowstone
    "netherbound": ("Netherbound Portal",    (232, 146,  78)),   # shroomlight
    "oceanblock":  ("Oceanblock Portal",     (142, 178, 186)),   # sea lantern
    "lostcities":  ("Lost Cities Portal",    (214, 122,  72)),   # redstone lamp
    "onechunk":    ("One Chunk Portal",      (242, 205, 122)),   # glowstone
    "gauntlet":    ("Gauntlet Portal",       (246, 208, 108)),   # gold block
    "redstone":    ("Redstone Land Portal",  (214, 122,  72)),   # redstone lamp
    "oneblock":    ("One Block Portal",      (238, 200, 126)),   # ochre froglight
    "horror":      ("Horror Portal",         (118, 196, 206)),   # soul lantern
}


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def texture(colour, size=16, seed=0):
    """A portal face: dark core, brighter filaments, tinted to this destination."""
    rnd = random.Random(seed)
    light = lerp(colour, GOLD, TEMPER)
    deep = lerp(light, (6, 4, 10), 0.86)
    img = Image.new("RGBA", (size, size))
    px = img.load()
    phase = rnd.random() * math.tau
    for y in range(size):
        for x in range(size):
            dx = (x - size / 2 + 0.5) / (size / 2)
            dy = (y - size / 2 + 0.5) / (size / 2)
            r = math.sqrt(dx * dx + dy * dy)
            a = math.atan2(dy, dx)
            # filaments: a swirl that tightens toward the middle
            v = math.sin(a * 3 + r * 7.5 + phase) * 0.5 + 0.5
            v *= max(0.0, 1.0 - abs(r - 0.55) * 1.7)
            v += (1.0 - min(1.0, r * 1.25)) * 0.35
            v += rnd.random() * 0.07
            v = max(0.0, min(1.0, v))
            px[x, y] = lerp(deep, light, v) + (255,)
    return img


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, indent=2) + chr(10))


def registered_destinations():
    """Read the destinations out of the Java, so the two cannot drift apart."""
    src = io.open(JAVA, encoding="utf-8").read()
    return re.findall(r'DESTINATIONS\.put\("([a-z]+)"', src)


def main():
    check = "--check" in sys.argv
    declared = registered_destinations()
    missing_decl = [d for d in declared if d not in PORTALS]
    extra_decl = [d for d in PORTALS if d not in declared]
    if missing_decl or extra_decl:
        print("MISMATCH between PocketPortal.java and this script:")
        if missing_decl:
            print("   registered but has no assets here: " + ", ".join(missing_decl))
        if extra_decl:
            print("   assets here but not registered   : " + ", ".join(extra_decl))
        return 1
    print("%d destinations, matching PocketPortal.java" % len(declared))

    wanted = []
    for i, dest in enumerate(declared):
        name, colour = PORTALS[dest]
        block = "portal_" + dest
        wanted += [
            os.path.join(RES, "textures", "block", block + ".png"),
            os.path.join(RES, "blockstates", block + ".json"),
            os.path.join(RES, "models", "block", block + ".json"),
            os.path.join(RES, "models", "item", block + ".json"),
        ]
        if check:
            continue

        tex = os.path.join(RES, "textures", "block", block + ".png")
        os.makedirs(os.path.dirname(tex), exist_ok=True)
        texture(colour, seed=i * 7 + 1).save(tex)

        write_json(os.path.join(RES, "blockstates", block + ".json"),
                   {"variants": {"": {"model": "pocketquests:block/" + block}}})
        write_json(os.path.join(RES, "models", "block", block + ".json"),
                   {"parent": "minecraft:block/cube_all",
                    # NeoForge reads this: without it the portal is an opaque cube.
                    "render_type": "minecraft:translucent",
                    "textures": {"all": "pocketquests:block/" + block}})
        write_json(os.path.join(RES, "models", "item", block + ".json"),
                   {"parent": "pocketquests:block/" + block})

    lang = {}
    for dest in declared:
        lang["block.pocketquests.portal_" + dest] = PORTALS[dest][0]
    lang_path = os.path.join(RES, "lang", "en_us.json")
    if not check:
        write_json(lang_path, lang)
    wanted.append(lang_path)

    absent = [p for p in wanted if not os.path.exists(p)]
    if absent:
        print("")
        print("MISSING %d file(s):" % len(absent))
        for p in absent[:12]:
            print("   " + os.path.relpath(p, os.path.dirname(HERE)))
        return 1

    print("%d files present under mod-src/res/assets/pocketquests" % len(wanted))
    print("blockstates, block + item models, 16x16 textures, and %d lang entries" % len(lang))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
