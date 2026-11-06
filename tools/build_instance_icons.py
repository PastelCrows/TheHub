# -*- coding: utf-8 -*-
"""Render a matching icon for every Prism instance.

THE STYLE is taken from Kewz's Cobblemon icon, supplied as the reference: a rounded HEXAGON with
a thick near-black outline, flat ISOMETRIC blocks inside it, a tight palette where each block
face is lit / mid / shadow, and a small hexagonal nut at the centre. The point is a SET - every
instance instantly reads as part of the same collection - so the geometry is identical
throughout and only the palette and the arm shape change per pack.

WHY GENERATED RATHER THAN DRAWN. Seventeen icons by hand would drift; generated ones cannot. It
also means a repaint is a palette edit rather than seventeen redraws, and a new instance gets an
icon that already matches.

ISOMETRIC PROJECTION. A unit cube at integer grid (gx, gy, gz):

    sx = (gx - gy) * HALF_W
    sy = (gx + gy) * HALF_H - gz * CUBE_H

drawn as three faces - top rhombus, left face, right face - in the lit / mid / shadow tints of
one colour. Painter's order is by (gx + gy + gz) so nearer cubes overwrite farther ones.

EVERYTHING IS SUPERSAMPLED 4x and downsampled with LANCZOS, because the diagonals in an
isometric cube alias badly at icon sizes otherwise.

    python build_instance_icons.py                 # render to tools/_icons
    python build_instance_icons.py --install       # also copy to Prism and set iconKey
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

SS = 4                      # supersample factor
SIZE = 256                  # final icon edge
OUTLINE = "#241F2E"         # the near-black of the reference
INNER_BG = "#FFFFFF"

HALF_W = 21                 # iso cube half width  (pre-supersample units)
HALF_H = 12                 # iso cube half height
CUBE_H = 18                 # vertical rise of one cube
EDGE = 3                    # dark edge between cubes, so blocks stay separable


def shades(hex_colour):
    """lit / mid / shadow for one base colour, as the reference does per face."""
    base = hex_colour.lstrip("#")
    r, g, b = (int(base[i:i + 2], 16) for i in (0, 2, 4))

    def mix(t, to):
        return tuple(int(round(c + (x - c) * t)) for c, x in zip((r, g, b), to))

    return {
        "top": mix(0.22, (255, 255, 255)),
        "left": (r, g, b),
        "right": mix(0.34, (0, 0, 0)),
    }


# Two interlocking L-shaped arms around a centre nut - the reference's own arrangement.
# Cells are (gx, gy, gz). ARM_A reads up-and-right, ARM_B mirrors it down-and-left.
# Height matters: with both arms on z=0 the cells read as one flat plate rather than two
# shapes. Arm A is raised a level so the pair interlocks the way the reference's does - each is
# an L that wraps half way round the centre, and together they pinwheel about the nut.
ARM_A = [(-1, -1, 1), (0, -1, 1), (1, -1, 1), (1, 0, 1)]
ARM_B = [(1, 1, 0), (0, 1, 0), (-1, 1, 0), (-1, 0, 0)]

# Per-instance palettes. Deep purple + warm gold is the stated house style and belongs to The
# Hub; everything else is chosen to read as that pack at a glance while staying in the same
# flat two-colour register.
PALETTES = {
    "The Hub":               ("#8B5CF6", "#F2B33D"),   # deep purple + warm gold - house brand
    "Cobblemon NeoForge":    ("#E8584E", "#F5F3F7"),   # pokeball red + white
    "Skyblock":              ("#5BC8F5", "#9BE08A"),   # sky + grass
    "Caveblock":             ("#8C8FA3", "#D9A441"),   # stone + torchlight
    "Oceanblock":            ("#2FB6C4", "#F2DFA8"),   # water + sand
    "One Chunk":             ("#7FC24A", "#A9743F"),   # grass + dirt
    "One Block":             ("#B07CE8", "#6EE7A0"),   # magic + growth
    "Netherbound":           ("#C94B3F", "#4FC3D9"),   # netherrack + soul fire
    "Lost Cities":           ("#9AA3AD", "#4E8C63"),   # concrete + overgrowth
    "Survival":              ("#6BA94A", "#8A5A33"),   # grass + wood
    "The Gauntlet":          ("#C8403F", "#C9A227"),   # blood + brass
    "Horror":                ("#6B5A82", "#C0392B"),   # dusk + blood, both lifted
    #   clear of the outline: the first pair sat 34 luminance from #241F2E and the
    #   darker block read as a hole punched in the icon rather than as a block.
    "Creative Forge":        ("#E08A3C", "#6E7A8A"),   # forge orange + steel
    "Creative Modern":       ("#4FA8E0", "#E6E9ED"),   # glass + white
    "Creative Maximum":      ("#9B6BE8", "#45C9A5"),   # violet + teal
    "Knock-off Hermitcraft": ("#4FBF7A", "#E8C84A"),   # hermit green + gold
}
DEFAULT_PALETTE = ("#7D7F8C", "#C9C6D6")


def hexagon(cx, cy, r):
    """Flat-top hexagon: flat top and bottom edges, points at left and right."""
    pts = []
    for i in range(6):
        a = math.radians(60 * i)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rounded_poly(draw, pts, radius, fill):
    """A polygon with genuinely rounded corners.

    The obvious version - draw the polygon, then a disc at every vertex - is wrong, and looked
    it: the discs bulge past the edges and the hexagon came out as a six-atom molecule. The
    right way is to stroke the outline with a round-jointed line of width 2*radius, which grows
    the shape outward by exactly radius with arcs at the corners, and fill the body behind it.
    Callers therefore pass an INSET polygon so the result lands on the intended size.
    """
    draw.polygon(pts, fill=fill)
    # pts[0] AND pts[1]: the closing joint is only rounded if the path continues through it,
    # otherwise a wedge is left missing at that vertex - which is what the second render showed.
    draw.line(list(pts) + [pts[0], pts[1]], fill=fill, width=int(radius * 2), joint="curve")


def cube(draw, cx, cy, gx, gy, gz, colour):
    sx = cx + (gx - gy) * HALF_W * SS
    sy = cy + (gx + gy) * HALF_H * SS - gz * CUBE_H * SS
    hw, hh, ch = HALF_W * SS, HALF_H * SS, CUBE_H * SS
    s = shades(colour)
    e = EDGE * SS
    # Dark silhouette first, then the faces inset into it. Without this, two cubes of the same
    # colour sitting side by side merge into one unreadable slab - which is exactly what the
    # first render did.
    draw.polygon([(sx, sy - hh - e), (sx + hw + e, sy), (sx + hw + e, sy + ch),
                  (sx, sy + hh + ch + e), (sx - hw - e, sy + ch), (sx - hw - e, sy)],
                 fill=OUTLINE)
    k = e * 0.9
    draw.polygon([(sx, sy - hh + k), (sx + hw - k, sy), (sx, sy + hh - k), (sx - hw + k, sy)],
                 fill=s["top"])
    draw.polygon([(sx - hw + k, sy + k), (sx - k, sy + hh), (sx - k, sy + hh + ch - k),
                  (sx - hw + k, sy + ch - k)], fill=s["left"])
    draw.polygon([(sx + hw - k, sy + k), (sx + k, sy + hh), (sx + k, sy + hh + ch - k),
                  (sx + hw - k, sy + ch - k)], fill=s["right"])


def nut(draw, cx, cy, colour):
    """The small centre hexagon - a bolt head seen from above."""
    r = int(HALF_W * SS * 0.78)
    s = shades(colour)
    outer = hexagon(cx, cy, r)
    draw.polygon(outer, fill=OUTLINE)
    draw.polygon(hexagon(cx, cy, int(r * 0.80)), fill=s["top"])
    draw.polygon(hexagon(cx, cy, int(r * 0.44)), fill=OUTLINE)


def render(colour_a, colour_b):
    w = SIZE * SS
    img = Image.new("RGBA", (w, w), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = w / 2.0

    r_out = w * 0.46
    rounding = w * 0.070
    rounded_poly(d, hexagon(cx, cy, r_out - rounding), rounding, OUTLINE)
    inner_r = r_out - w * 0.115
    rounded_poly(d, hexagon(cx, cy, inner_r - rounding * 0.8), rounding * 0.8, INNER_BG)

    order = [(c, colour_a) for c in ARM_A] + [(c, colour_b) for c in ARM_B]
    order.sort(key=lambda t: (t[0][0] + t[0][1] + t[0][2]))

    # Centre the arrangement by its real drawn extent rather than by eye. An isometric stack is
    # not symmetric about its grid origin - raising one arm shifts the silhouette upward - so a
    # hand-tuned offset only ever centres one particular arm shape. Measuring it keeps every
    # future arrangement centred for free.
    hw, hh, ch = HALF_W * SS, HALF_H * SS, CUBE_H * SS
    xs, ys = [], []
    for (gx, gy, gz), _c in order:
        sx = (gx - gy) * hw
        sy = (gx + gy) * hh - gz * ch
        xs += [sx - hw, sx + hw]
        ys += [sy - hh, sy + hh + ch]
    bx = cx - (min(xs) + max(xs)) / 2.0
    by = cy - (min(ys) + max(ys)) / 2.0

    for (gx, gy, gz), col in order:
        cube(d, bx, by, gx, gy, gz, col)
    nut(d, bx, by - ch * 0.5, colour_b)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


def instances():
    if not os.path.isdir(INSTANCES):
        return []
    out = []
    for n in sorted(os.listdir(INSTANCES)):
        if os.path.isfile(os.path.join(INSTANCES, n, "instance.cfg")):
            out.append(n)
    return out


def safe_key(name):
    return "hub_" + re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()


def set_icon_key(inst, key):
    cfg = os.path.join(INSTANCES, inst, "instance.cfg")
    lines = io.open(cfg, encoding="utf-8").read().split("\n")
    done = False
    for i, l in enumerate(lines):
        if l.startswith("iconKey="):
            lines[i] = "iconKey=" + key
            done = True
            break
    if not done:
        for i, l in enumerate(lines):
            if l.startswith("[General]"):
                lines.insert(i + 1, "iconKey=" + key)
                done = True
                break
    io.open(cfg, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
    return done


def main():
    install = "--install" in sys.argv
    only = None
    if "--only" in sys.argv:
        i = sys.argv.index("--only")
        if i + 1 < len(sys.argv):
            only = sys.argv[i + 1]

    os.makedirs(OUT, exist_ok=True)
    names = instances()
    # Kewz's pack keeps its own icon. It is his, it is the reference this whole set was drawn
    # from, and restyling it would make his instance harder to pick out rather than easier.
    names = [n for n in names if n != "Kewz's Cobblemon"]
    if only:
        names = [n for n in names if n == only] or [only]
    if not names:
        print("no instances found")
        return 1

    # Prism rewrites instance.cfg while a game is running, so refuse to touch it then.
    if install:
        import subprocess
        try:
            tl = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
            if "javaw.exe" in tl or "prismlauncher.exe" in tl:
                print("Prism or a game is running - close both before --install, "
                      "or instance.cfg edits get overwritten.")
                return 1
        except Exception:
            pass

    print("%-24s %-20s %s" % ("instance", "palette", "file"))
    print("-" * 74)
    for name in names:
        a, b = PALETTES.get(name, DEFAULT_PALETTE)
        img = render(a, b)
        key = safe_key(name)
        path = os.path.join(OUT, key + ".png")
        img.save(path)
        print("%-24s %-20s %s" % (name[:24], "%s / %s" % (a, b), os.path.basename(path)))
        if install:
            os.makedirs(ICONS, exist_ok=True)
            img.save(os.path.join(ICONS, key + ".png"))
            set_icon_key(name, key)

    print("")
    if install:
        print("installed to %s and iconKey set on %d instance(s)" % (ICONS, len(names)))
    else:
        print("rendered to %s  (use --install to apply)" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
