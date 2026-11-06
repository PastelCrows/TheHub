# -*- coding: utf-8 -*-
"""Render a themed icon for every Prism instance.

WHAT THE BRIEF ACTUALLY WAS. The reference supplied was Kewz's Cobblemon icon, and the first
attempt here missed the point by copying its GEOMETRY - a rounded hexagon holding two
interlocking isometric arms around a centre nut - and recolouring it sixteen times. That shape
is a pokeball rendered in blocks. It is a Cobblemon icon. It means nothing on Lost Cities.

What was wanted is the LOOK: that clean. Flat shapes, one bold near-black outline, a tight
palette, a silhouette that still reads at 32px. The SUBJECT of each icon should be its pack.

So: one shared house style, sixteen different drawings.

  * a rounded-square container, not a hexagon - the hexagon is Kewz's mark, and reusing it would
    make our packs look like forks of his
  * INK and STROKE are the single outline colour and weight everything uses, which is what makes
    them read as a set without any of them repeating a shape
  * each pack gets its own small draw function, named for it
  * two or three flat colours each, no gradients

Supersampled 4x then LANCZOS down: flat art with diagonal edges aliases badly at icon sizes.

    python build_instance_icons.py                 # render to tools/_icons
    python build_instance_icons.py --sheet         # also write a contact sheet
    python build_instance_icons.py --install       # copy to Prism and set iconKey
    python build_instance_icons.py --only "The Hub"
"""
import io
import math
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow is required: python -m pip install pillow")
    raise SystemExit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_icons")
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
ICONS = os.path.join(PRISM, "icons")
INSTANCES = os.path.join(PRISM, "instances")

SS = 4
SIZE = 256
W = SIZE * SS
INK = "#221E2B"
STROKE = int(W * 0.022)


# ---------------------------------------------------------------- helpers

def mix(c, to, t):
    c = c.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % tuple(int(round(a + (x - a) * t)) for a, x in zip((r, g, b), to))


def lighter(c, t=0.28):
    return mix(c, (255, 255, 255), t)


def darker(c, t=0.30):
    return mix(c, (0, 0, 0), t)


def poly(d, pts, fill=None, outline=True, width=None):
    if fill:
        d.polygon(pts, fill=fill)
    if outline:
        d.line(list(pts) + [pts[0], pts[1]], fill=INK,
               width=width or STROKE, joint="curve")


def disc(d, cx, cy, r, fill, outline=True):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill,
              outline=INK if outline else None, width=STROKE if outline else 0)


def box(d, x0, y0, x1, y1, fill, r=None, outline=True):
    r = int(r if r is not None else W * 0.02)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill,
                        outline=INK if outline else None, width=STROKE if outline else 0)


def cube(d, cx, cy, s, colour, h=None):
    """A flat isometric cube, positioned by the centre of its top face."""
    h = h or s * 0.85
    hw, hh = s, s * 0.56
    poly(d, [(cx - hw, cy), (cx, cy + hh), (cx, cy + hh + h), (cx - hw, cy + h)],
         darker(colour, 0.34), True)
    poly(d, [(cx + hw, cy), (cx, cy + hh), (cx, cy + hh + h), (cx + hw, cy + h)],
         darker(colour, 0.14), True)
    poly(d, [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)],
         lighter(colour, 0.22), True)


def container(d, bg):
    m = W * 0.055
    d.rounded_rectangle([m, m, W - m, W - m], radius=int(W * 0.26), fill=bg,
                        outline=INK, width=int(STROKE * 1.9))


def arch_path(cx, base, half, rise):
    """A pointed-ish arch outline, used by more than one icon."""
    pts = [(cx - half, base)]
    for k in range(33):
        t = k / 32.0
        pts.append((cx - half + 2 * half * t, base - rise * math.sin(math.pi * t)))
    pts.append((cx + half, base))
    return pts


# ---------------------------------------------------------------- per-pack art
# Few shapes, large. Anything fiddly turns to mush at 32px, which is the size that matters in
# the instance list.

def art_hub(d, p):
    """A lit gothic doorway. The first version drew a narrow arch over a dark one and read as a
    capital A - the legs converged and the opening vanished. Wide opening, visible piers, a
    floor line and a keystone fix it: the silhouette now says doorway at any size."""
    dark, gold = p
    base = W * 0.78
    # piers
    box(d, W * 0.22, W * 0.40, W * 0.34, base, gold, r=W * 0.015)
    box(d, W * 0.66, W * 0.40, W * 0.78, base, gold, r=W * 0.015)
    # arch band over the opening
    band = arch_path(W * 0.5, W * 0.42, W * 0.28, W * 0.26)
    poly(d, band, gold, True)
    # the opening itself, lit
    inner = arch_path(W * 0.5, base, W * 0.155, W * 0.30)
    poly(d, inner, dark, True)
    glow = arch_path(W * 0.5, base - W * 0.02, W * 0.105, W * 0.21)
    poly(d, glow, lighter(gold, 0.35), True)
    # keystone and floor
    box(d, W * 0.455, W * 0.115, W * 0.545, W * 0.20, lighter(gold, 0.3), r=W * 0.012)
    d.line([(W * 0.17, base), (W * 0.83, base)], fill=INK, width=int(STROKE * 1.7))


def art_cobblemon(d, p):
    """A pokeball - the one pack where the reference's own subject is the right answer."""
    red, white = p
    cx = cy = W * 0.5
    r = W * 0.30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=white)
    d.pieslice([cx - r, cy - r, cx + r, cy + r], 180, 360, fill=red)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=INK, width=int(STROKE * 1.3))
    d.rectangle([cx - r, cy - STROKE, cx + r, cy + STROKE], fill=INK)
    disc(d, cx, cy, r * 0.32, white)
    disc(d, cx, cy, r * 0.15, lighter(red, 0.15))


def art_skyblock(d, p):
    """A floating island. The tree was a disc on a stick - a two-tier canopy reads as a tree."""
    sky, grass = p
    cx, y = W * 0.5, W * 0.62
    poly(d, [(cx - W * 0.25, y), (cx + W * 0.25, y), (cx + W * 0.13, y + W * 0.15),
             (cx + W * 0.05, y + W * 0.21), (cx - W * 0.06, y + W * 0.17)],
         "#8A5A33", True)
    box(d, cx - W * 0.26, y - W * 0.075, cx + W * 0.26, y + W * 0.015, grass, r=W * 0.025)
    box(d, cx - W * 0.028, y - W * 0.19, cx + W * 0.028, y - W * 0.05, "#7A5230")
    poly(d, [(cx, y - W * 0.36), (cx + W * 0.15, y - W * 0.20), (cx - W * 0.15, y - W * 0.20)],
         darker(grass, 0.18), True)
    poly(d, [(cx, y - W * 0.28), (cx + W * 0.175, y - W * 0.13),
             (cx - W * 0.175, y - W * 0.13)], lighter(grass, 0.12), True)


def art_caveblock(d, p):
    """A cave mouth with a torch and ore in the rock. The first version was a grey square with a
    dark triangle in it - the ore dots and a bigger torch give it something to be about."""
    stone, flame = p
    box(d, W * 0.16, W * 0.19, W * 0.84, W * 0.81, stone, r=W * 0.05)
    cx, base = W * 0.5, W * 0.76
    poly(d, arch_path(cx, base, W * 0.20, W * 0.34), darker(stone, 0.70), True)
    for ox, oy in ((0.265, 0.33), (0.715, 0.38), (0.255, 0.63)):
        disc(d, W * ox, W * oy, W * 0.040, flame)
    box(d, cx + W * 0.105, base - W * 0.21, cx + W * 0.145, base - W * 0.02, "#7A5230")
    disc(d, cx + W * 0.125, base - W * 0.255, W * 0.058, flame)
    d.line([(W * 0.17, base), (W * 0.83, base)], fill=INK, width=int(STROKE * 1.5))


def art_oceanblock(d, p):
    """A palm on a scrap of sand, with the waterline behind. The earlier curling wave read as a
    blue hill - a horizon plus an island is unambiguous."""
    water, sand = p
    box(d, W * 0.16, W * 0.19, W * 0.84, W * 0.81, lighter(water, 0.62), r=W * 0.05)
    y = W * 0.60
    d.rectangle([W * 0.17, y, W * 0.83, W * 0.80], fill=water)
    d.line([(W * 0.17, y), (W * 0.83, y)], fill=INK, width=int(STROKE))
    island = [(W * 0.28, W * 0.70)]
    for k in range(25):
        t = k / 24.0
        island.append((W * 0.28 + W * 0.44 * t, W * 0.70 - W * 0.10 * math.sin(math.pi * t)))
    island.append((W * 0.72, W * 0.70))
    poly(d, island, sand, True)
    box(d, W * 0.485, W * 0.40, W * 0.525, W * 0.655, "#7A5230")
    for dx, dy in ((-0.115, -0.03), (0.115, -0.03), (0.0, -0.075)):
        disc(d, W * (0.505 + dx), W * (0.40 + dy), W * 0.072, darker(water, 0.15))


def art_onechunk(d, p):
    """Exactly one chunk of ground, cut out and standing alone."""
    grass, dirt = p
    cx, cy = W * 0.5, W * 0.40
    s, h = W * 0.235, W * 0.28
    hh = s * 0.56
    poly(d, [(cx - s, cy), (cx, cy + hh), (cx, cy + hh + h), (cx - s, cy + h)], dirt, True)
    poly(d, [(cx + s, cy), (cx, cy + hh), (cx, cy + hh + h), (cx + s, cy + h)],
         darker(dirt, 0.24), True)
    poly(d, [(cx, cy - hh), (cx + s, cy), (cx, cy + hh), (cx - s, cy)], grass, True)


def art_oneblock(d, p):
    """One block, and the cycle that keeps handing you another."""
    magic, grow = p
    cx, cy = W * 0.5, W * 0.57
    r = W * 0.245
    d.arc([cx - r, cy - r - W * 0.05, cx + r, cy + r - W * 0.05], 205, 455,
          fill=grow, width=int(STROKE * 1.7))
    tx, ty = cx + r * 0.76, cy - r * 0.58
    poly(d, [(tx + W * 0.055, ty + W * 0.005), (tx - W * 0.03, ty - W * 0.055),
             (tx - W * 0.015, ty + W * 0.055)], grow, True)
    cube(d, cx, cy, W * 0.155, magic, h=W * 0.14)


def art_netherbound(d, p):
    """A flame. Nested rectangles were meant to be a portal and read as a picture frame; a
    flame is one silhouette, says nether instantly, and survives being shrunk."""
    rock, fire = p
    cx = W * 0.5
    outer = [(cx, W * 0.16)]
    for k in range(33):
        t = k / 32.0
        ang = math.pi * t
        outer.append((cx + W * 0.26 * math.sin(ang),
                      W * 0.16 + W * 0.62 * t + W * 0.05 * math.sin(ang * 2)))
    for k in range(33):
        t = k / 32.0
        ang = math.pi * t
        outer.append((cx - W * 0.26 * math.sin(math.pi - ang),
                      W * 0.78 - W * 0.62 * t - W * 0.05 * math.sin((math.pi - ang) * 2)))
    poly(d, outer, fire, True)
    inner = [(cx, W * 0.40)]
    for k in range(33):
        t = k / 32.0
        ang = math.pi * t
        inner.append((cx + W * 0.135 * math.sin(ang), W * 0.40 + W * 0.36 * t))
    for k in range(33):
        t = k / 32.0
        ang = math.pi * t
        inner.append((cx - W * 0.135 * math.sin(math.pi - ang), W * 0.76 - W * 0.36 * t))
    poly(d, inner, lighter(fire, 0.5), True)
    d.line([(W * 0.22, W * 0.80), (W * 0.78, W * 0.80)], fill=rock, width=int(STROKE * 2.2))


def art_lostcities(d, p):
    """A ruined skyline. Plain bars read as a bar chart - windows make them buildings, and one
    broken top makes them ruins."""
    concrete, moss = p
    base = W * 0.78
    towers = ((0.19, 0.42, 0.135), (0.345, 0.26, 0.145), (0.515, 0.47, 0.13),
              (0.665, 0.34, 0.145))
    for x, top, wdt in towers:
        box(d, W * x, W * top, W * (x + wdt), base, concrete, r=W * 0.01)
        rows = int((base - W * top) / (W * 0.075))
        for ry in range(rows - 1):
            for cxo in (0.030, 0.075):
                if cxo + 0.030 > wdt:
                    continue
                wx = W * (x + cxo)
                wy = W * top + W * 0.045 + ry * W * 0.075
                d.rectangle([wx, wy, wx + W * 0.030, wy + W * 0.040],
                            fill=darker(concrete, 0.55))
    # one tower sheared off, and moss creeping over two of them
    poly(d, [(W * 0.345, W * 0.26), (W * 0.49, W * 0.26), (W * 0.49, W * 0.315),
             (W * 0.42, W * 0.285), (W * 0.345, W * 0.33)], moss, True)
    box(d, W * 0.665, W * 0.34, W * 0.81, W * 0.395, moss, r=W * 0.01)
    d.line([(W * 0.15, base), (W * 0.85, base)], fill=INK, width=int(STROKE * 1.6))


def art_survival(d, p):
    """A sword. Two crossed lines read as an X and nothing else, so this draws one unmistakable
    blade instead: tapered point, crossguard, grip, pommel."""
    grass, wood = p
    cx = W * 0.5
    poly(d, [(cx, W * 0.17), (cx + W * 0.075, W * 0.30), (cx + W * 0.075, W * 0.56),
             (cx - W * 0.075, W * 0.56), (cx - W * 0.075, W * 0.30)],
         lighter(grass, 0.45), True)
    box(d, W * 0.285, W * 0.555, W * 0.715, W * 0.635, grass, r=W * 0.018)
    box(d, cx - W * 0.045, W * 0.635, cx + W * 0.045, W * 0.775, wood, r=W * 0.015)
    disc(d, cx, W * 0.80, W * 0.058, lighter(wood, 0.3))


def art_gauntlet(d, p):
    """A shield with a blade across it. The row of arches read as teeth at icon size; a shield
    is one bold silhouette and says combat immediately."""
    blood, brass = p
    cx = W * 0.5
    top, bot = W * 0.21, W * 0.82
    shield = [(cx - W * 0.26, top), (cx + W * 0.26, top), (cx + W * 0.26, W * 0.50)]
    for k in range(25):
        t = k / 24.0
        shield.append((cx + W * 0.26 * (1 - t), W * 0.50 + (bot - W * 0.50) * math.sin(t * math.pi / 2)))
    for k in range(25):
        t = k / 24.0
        shield.append((cx - W * 0.26 * t, bot - (bot - W * 0.50) * math.sin(t * math.pi / 2)))
    poly(d, shield, brass, True)
    d.line([(cx, top + W * 0.04), (cx, bot - W * 0.06)], fill=blood, width=int(STROKE * 2.2))
    d.line([(cx - W * 0.17, W * 0.40), (cx + W * 0.17, W * 0.40)], fill=blood,
           width=int(STROKE * 2.2))


def art_horror(d, p):
    """One eye, open in the dark."""
    dusk, blood = p
    box(d, W * 0.16, W * 0.19, W * 0.84, W * 0.81, darker(dusk, 0.6), r=W * 0.05)
    cx, cy = W * 0.5, W * 0.5
    lid = []
    for k in range(33):
        t = k / 32.0
        lid.append((cx - W * 0.24 + W * 0.48 * t, cy - W * 0.16 * math.sin(math.pi * t)))
    for k in range(33):
        t = k / 32.0
        lid.append((cx + W * 0.24 - W * 0.48 * t, cy + W * 0.16 * math.sin(math.pi * t)))
    poly(d, lid, lighter(dusk, 0.65), True)
    disc(d, cx, cy, W * 0.098, blood)
    disc(d, cx, cy, W * 0.042, INK, outline=False)


def art_creative_forge(d, p):
    """An anvil with a spark. The first attempt was three stacked bars and read as furniture -
    an anvil needs the horn and the waisted profile to be recognisable."""
    orange, steel = p
    poly(d, [(W * 0.20, W * 0.40), (W * 0.76, W * 0.40), (W * 0.82, W * 0.46),
             (W * 0.70, W * 0.52), (W * 0.26, W * 0.52)], steel, True)
    poly(d, [(W * 0.38, W * 0.52), (W * 0.62, W * 0.52), (W * 0.58, W * 0.66),
             (W * 0.42, W * 0.66)], darker(steel, 0.26), True)
    box(d, W * 0.26, W * 0.66, W * 0.74, W * 0.78, steel, r=W * 0.02)
    disc(d, W * 0.33, W * 0.27, W * 0.05, orange)
    disc(d, W * 0.46, W * 0.21, W * 0.032, lighter(orange, 0.35))


def art_creative_modern(d, p):
    """A blueprint grid with one solid block placed on it."""
    blue, paper = p
    box(d, W * 0.16, W * 0.19, W * 0.84, W * 0.81, paper, r=W * 0.05)
    faint = mix(blue, (255, 255, 255), 0.62)
    for i in range(1, 4):
        v = W * (0.19 + i * 0.155)
        d.line([(v, W * 0.21), (v, W * 0.79)], fill=faint, width=int(STROKE * 0.6))
        d.line([(W * 0.18, v), (W * 0.82, v)], fill=faint, width=int(STROKE * 0.6))
    box(d, W * 0.345, W * 0.375, W * 0.655, W * 0.645, blue, r=W * 0.02)


def art_creative_maximum(d, p):
    """A heap of blocks - the pack is simply more of everything."""
    violet, teal = p
    cube(d, W * 0.355, W * 0.52, W * 0.145, violet, h=W * 0.13)
    cube(d, W * 0.645, W * 0.52, W * 0.145, teal, h=W * 0.13)
    cube(d, W * 0.5, W * 0.355, W * 0.145, lighter(violet, 0.3), h=W * 0.13)


def art_hermitcraft(d, p):
    """A chicken. The spiral shell read as a fingerprint; the instance's old Prism icon was a
    chicken and it is instantly recognisable at any size."""
    green, gold = p
    cx, cy = W * 0.52, W * 0.52
    poly(d, [(cx - W * 0.05, cy + W * 0.02), (cx - W * 0.26, cy + W * 0.17),
             (cx - W * 0.04, cy + W * 0.25), (cx + W * 0.16, cy + W * 0.14)],
         lighter(green, 0.55), True)
    disc(d, cx, cy, W * 0.175, "#FBF7F2")
    for i, dx in enumerate((-0.055, 0.0, 0.055)):
        disc(d, cx + W * dx, cy - W * (0.165 + 0.012 * (i == 1)), W * 0.042, "#C0392B")
    poly(d, [(cx + W * 0.165, cy - W * 0.01), (cx + W * 0.30, cy + W * 0.025),
             (cx + W * 0.165, cy + W * 0.06)], gold, True)
    disc(d, cx + W * 0.055, cy - W * 0.045, W * 0.026, INK, outline=False)

ART = {
    "The Hub": art_hub,
    "Cobblemon NeoForge": art_cobblemon,
    "Skyblock": art_skyblock,
    "Caveblock": art_caveblock,
    "Oceanblock": art_oceanblock,
    "One Chunk": art_onechunk,
    "One Block": art_oneblock,
    "Netherbound": art_netherbound,
    "Lost Cities": art_lostcities,
    "Survival": art_survival,
    "The Gauntlet": art_gauntlet,
    "Horror": art_horror,
    "Creative Forge": art_creative_forge,
    "Creative Modern": art_creative_modern,
    "Creative Maximum": art_creative_maximum,
    "Knock-off Hermitcraft": art_hermitcraft,
}

# (two subject colours, container background)
THEME = {
    "The Hub":               (("#2E2142", "#F2B33D"), "#6E49C6"),
    "Cobblemon NeoForge":    (("#E8564C", "#F7F5F8"), "#F3E7D6"),
    "Skyblock":              (("#5BC8F5", "#7FC24A"), "#DCF2FA"),
    "Caveblock":             (("#8C8FA3", "#F0A93C"), "#E6E4EA"),
    "Oceanblock":            (("#2196B0", "#EBD9A3"), "#D6EFF2"),
    "One Chunk":             (("#7FC24A", "#A9743F"), "#EAF4DC"),
    "One Block":             (("#B07CE8", "#3FC98B"), "#F0E8FA"),
    "Netherbound":           (("#5A2A24", "#F2642E"), "#2E1C20"),
    "Lost Cities":           (("#A7AFB8", "#4E8C63"), "#E4E7EA"),
    "Survival":              (("#6BA94A", "#9A6637"), "#EDF2E2"),
    "The Gauntlet":          (("#B8342F", "#D9A93C"), "#F2E6D2"),
    "Horror":                (("#6B5A82", "#C0392B"), "#2A2334"),
    "Creative Forge":        (("#E8832E", "#8C97A3"), "#EFEAE4"),
    "Creative Modern":       (("#3D8FD6", "#FFFFFF"), "#E8EEF4"),
    "Creative Maximum":      (("#9B6BE8", "#3FC9A5"), "#F0ECF8"),
    "Knock-off Hermitcraft": (("#4FBF7A", "#E8B94A"), "#EAF6EC"),
}
DEFAULT = (("#8A8FA3", "#C9C6D6"), "#ECECEF")


def render(name):
    pal, bg = THEME.get(name, DEFAULT)
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    container(d, bg)
    fn = ART.get(name)
    if fn:
        fn(d, pal)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def instances():
    if not os.path.isdir(INSTANCES):
        return []
    return [n for n in sorted(os.listdir(INSTANCES))
            if os.path.isfile(os.path.join(INSTANCES, n, "instance.cfg"))]


def safe_key(name):
    return "hub_" + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()


def set_icon_key(inst, key):
    cfg = os.path.join(INSTANCES, inst, "instance.cfg")
    lines = io.open(cfg, encoding="utf-8").read().split("\n")
    for i, l in enumerate(lines):
        if l.startswith("iconKey="):
            lines[i] = "iconKey=" + key
            break
    else:
        for i, l in enumerate(lines):
            if l.startswith("[General]"):
                lines.insert(i + 1, "iconKey=" + key)
                break
    io.open(cfg, "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def main():
    install = "--install" in sys.argv
    sheet = "--sheet" in sys.argv
    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        if i + 1 < len(sys.argv):
            only = sys.argv[i + 1]

    os.makedirs(OUT, exist_ok=True)
    # Kewz's pack keeps its own icon: it is his, and it is the reference this set learned from.
    names = [n for n in instances() if n != "Kewz's Cobblemon"]
    if only:
        names = [n for n in names if n == only] or [only]
    if not names:
        print("no instances found")
        return 1

    if install:
        import subprocess
        try:
            tl = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
            if "javaw.exe" in tl or "prismlauncher.exe" in tl:
                print("Prism or a game is running - close both, or instance.cfg gets overwritten.")
                return 1
        except Exception:
            pass

    made = []
    for name in names:
        img = render(name)
        key = safe_key(name)
        img.save(os.path.join(OUT, key + ".png"))
        made.append((name, key, img))
        print("  %-24s %s" % (name[:24], "ok" if name in ART else "NO ART - blank container"))
        if install:
            os.makedirs(ICONS, exist_ok=True)
            img.save(os.path.join(ICONS, key + ".png"))
            set_icon_key(name, key)

    if sheet and made:
        cols = 4
        rows = (len(made) + cols - 1) // cols
        cs = Image.new("RGBA", (SIZE * cols, SIZE * rows), (255, 255, 255, 255))
        for i, (_n, _k, im) in enumerate(made):
            cs.paste(im, ((i % cols) * SIZE, (i // cols) * SIZE), im)
        cs.resize((SIZE * cols // 2, SIZE * rows // 2), Image.LANCZOS).save(
            os.path.join(OUT, "_contact.png"))
        print("\ncontact sheet: tools/_icons/_contact.png")

    print("")
    print(("installed and iconKey set on %d" % len(made)) if install
          else ("rendered %d to %s" % (len(made), OUT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
