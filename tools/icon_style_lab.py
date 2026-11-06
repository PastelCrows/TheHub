# -*- coding: utf-8 -*-
"""Render the same icons in several art styles, side by side, to choose a direction.

WHY A LAB AND NOT JUST A REDRAW. The note was "more HD somehow? more depth? something here is
not quite good enough" plus "maybe we play with a few different art styles". That is a direction
question, and guessing at it costs sixteen redraws per guess. So this renders a few
representative subjects across four treatments on one sheet, and the pick drives the real
generator.

THE FOUR TREATMENTS

  flat    what is installed now - one outline weight, solid fills, no shading. The baseline.
  depth   the same drawing with a cast shadow, a vertical light-to-dark gradient in each fill,
          and a soft inner shadow under the outline. Same silhouette, far less papery.
  iso     the subject rebuilt as isometric solids with lit/side/shadow faces. Reads as an
          object with volume rather than a picture of one.
  lux     no black outline at all. Rich gradients, a soft contact shadow, a highlight sweep.
          The modern app-icon look - most "HD", least Minecrafty.

Rendered at 512 rather than 256: the installed set is 256 and the curves show it.

LEGIBILITY. Each tile is also written out at 32px in the bottom strip of the sheet, because the
instance list is where these actually get read, and a design that only works large is not a
design that works.

    python icon_style_lab.py                 # all four styles, three subjects
    python icon_style_lab.py --subject hub
"""
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageChops
except ImportError:
    print("Pillow is required: python -m pip install pillow")
    raise SystemExit(1)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_icons")

SS = 3
SIZE = 512
W = SIZE * SS
INK = (0x22, 0x1E, 0x2B, 255)
STROKE = int(W * 0.020)


# ------------------------------------------------------------------ colour

def rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(c, to, t):
    r, g, b = rgb(c) if isinstance(c, str) else c[:3]
    return tuple(int(round(a + (x - a) * t)) for a, x in zip((r, g, b), to))


def lighter(c, t=0.3):
    return mix(c, (255, 255, 255), t)


def darker(c, t=0.3):
    return mix(c, (0, 0, 0), t)


# ------------------------------------------------------------------ effects

def gradient(size, top, bottom):
    """A vertical linear gradient image."""
    w, h = size
    g = Image.new("RGB", (1, h))
    px = g.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = mix(top, bottom, t)
    return g.resize((w, h), Image.BILINEAR)


def shape_layer():
    return Image.new("RGBA", (W, W), (0, 0, 0, 0))


def fill_shape(mask_img, top, bottom=None):
    """Paint a gradient (or solid) through a shape's alpha mask."""
    if bottom is None:
        bottom = top
    grad = gradient((W, W), top, bottom).convert("RGBA")
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask_img.split()[3])
    return out


def cast_shadow(mask_img, offset, blur, opacity=110):
    sh = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    a = mask_img.split()[3].point(lambda v: min(255, v) and opacity)
    sh.putalpha(a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    moved = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    moved.paste(sh, offset)
    return moved


def inner_shadow(mask_img, blur, opacity=90):
    """Darken just inside a shape's edge - what sells thickness."""
    alpha = mask_img.split()[3]
    shrunk = alpha.filter(ImageFilter.GaussianBlur(blur))
    rim = ImageChops.subtract(alpha, shrunk)
    lay = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    lay.putalpha(rim.point(lambda v: int(v * opacity / 255)))
    return lay


def outline(mask_img, width, colour=INK):
    """A stroke that follows any shape, however it was built."""
    a = mask_img.split()[3]
    grown = a.filter(ImageFilter.MaxFilter(3))
    for _ in range(max(0, width // 2 - 1)):
        grown = grown.filter(ImageFilter.MaxFilter(3))
    ring = ImageChops.subtract(grown, a)
    lay = Image.new("RGBA", (W, W), colour[:3] + (0,))
    lay.putalpha(ring)
    return lay


# ------------------------------------------------------------------ subjects
# Each returns a list of (mask_layer, base_colour) painted back-to-front. Building subjects as
# MASKS rather than as finished pixels is what lets one drawing be re-rendered in every style.

def subject_hub(pal):
    """A gothic archway: two columns, a POINTED arch, a lit opening.

    The round arch read as a barn. Gothic means the two sides meet at a point, so the opening is
    built from two circular arcs struck from opposite springing points - which is how a real
    pointed arch is set out - rather than from a sine bump.
    """
    dark, gold = pal
    layers = []

    def pointed(cx, base, halfw, rise, steps=40):
        """Two arcs meeting at an apex, closed down the sides to the base."""
        apex = (cx, base - rise)
        left = [(cx - halfw, base)]
        for k in range(steps + 1):
            t = k / steps
            left.append((cx - halfw + halfw * t,
                         base - rise * math.sin(math.pi * 0.5 * t) ** 0.72))
        right = []
        for k in range(steps + 1):
            t = k / steps
            right.append((cx + halfw - halfw * t,
                          base - rise * math.sin(math.pi * 0.5 * t) ** 0.72))
        return left + [apex] + list(reversed(right)) + [(cx + halfw, base)]

    body = shape_layer()
    d = ImageDraw.Draw(body)
    base = W * 0.80
    d.rounded_rectangle([W * 0.17, W * 0.42, W * 0.31, base], radius=W * 0.012, fill=(255,) * 4)
    d.rounded_rectangle([W * 0.69, W * 0.42, W * 0.83, base], radius=W * 0.012, fill=(255,) * 4)
    d.polygon(pointed(W * 0.5, W * 0.50, W * 0.33, W * 0.34), fill=(255,) * 4)
    d.rectangle([W * 0.17, W * 0.46, W * 0.83, W * 0.54], fill=(255,) * 4)
    layers.append((body, gold))

    hole = shape_layer()
    ImageDraw.Draw(hole).polygon(pointed(W * 0.5, base, W * 0.175, W * 0.40), fill=(255,) * 4)
    layers.append((hole, dark))

    glow = shape_layer()
    ImageDraw.Draw(glow).polygon(
        pointed(W * 0.5, base - W * 0.015, W * 0.115, W * 0.28), fill=(255,) * 4)
    layers.append((glow, lighter(gold, 0.5)))
    return layers


def subject_flame(pal):
    """A flame, drawn from explicit control points.

    The first attempt generated the outline from a cosine-modulated radius and produced an oval.
    A flame is not a perturbed circle: it is a wide round base that narrows and then LEANS, with
    a lick peeled off one side. Those are specific points, so they are written as points.
    """
    rock, fire = pal
    layers = []

    def teardrop(cx, top, halfw, bottom, lean):
        pts = [(cx + lean, top)]
        for k in range(1, 25):                       # right side, tip down to the belly
            t = k / 24.0
            pts.append((cx + lean * (1 - t) + halfw * math.sin(math.pi * t * 0.5) ** 0.75,
                        top + (bottom - top) * t ** 0.78))
        for k in range(25):                          # round the base
            t = k / 24.0
            ang = math.pi * t
            pts.append((cx + halfw * math.cos(ang), bottom + halfw * 0.42 * math.sin(ang)))
        for k in range(1, 25):                       # left side back up to the tip
            t = 1 - k / 24.0
            pts.append((cx + lean * (1 - t) - halfw * math.sin(math.pi * t * 0.5) ** 0.75,
                        top + (bottom - top) * t ** 0.78))
        return pts

    o = shape_layer()
    ImageDraw.Draw(o).polygon(
        teardrop(W * 0.47, W * 0.14, W * 0.235, W * 0.66, W * 0.07), fill=(255,) * 4)
    layers.append((o, fire))

    # the lick: a second, smaller tongue leaning the other way
    lick = shape_layer()
    ImageDraw.Draw(lick).polygon(
        teardrop(W * 0.615, W * 0.30, W * 0.085, W * 0.58, -W * 0.03), fill=(255,) * 4)
    layers.append((lick, lighter(fire, 0.30)))

    i = shape_layer()
    ImageDraw.Draw(i).polygon(
        teardrop(W * 0.465, W * 0.40, W * 0.105, W * 0.655, W * 0.02), fill=(255,) * 4)
    layers.append((i, lighter(fire, 0.62)))
    return layers


def subject_island(pal):
    sky, grass = pal
    layers = []
    rock = shape_layer()
    d = ImageDraw.Draw(rock)
    d.polygon([(W * 0.25, W * 0.60), (W * 0.75, W * 0.60), (W * 0.62, W * 0.76),
               (W * 0.54, W * 0.84), (W * 0.42, W * 0.78)], fill=(255,) * 4)
    layers.append((rock, "#8A5A33"))

    cap = shape_layer()
    ImageDraw.Draw(cap).rounded_rectangle(
        [W * 0.235, W * 0.525, W * 0.765, W * 0.615], radius=W * 0.025, fill=(255,) * 4)
    layers.append((cap, grass))

    trunk = shape_layer()
    ImageDraw.Draw(trunk).rounded_rectangle(
        [W * 0.47, W * 0.33, W * 0.53, W * 0.55], radius=W * 0.01, fill=(255,) * 4)
    layers.append((trunk, "#7A5230"))

    can = shape_layer()
    d2 = ImageDraw.Draw(can)
    d2.ellipse([W * 0.33, W * 0.17, W * 0.67, W * 0.40], fill=(255,) * 4)
    d2.ellipse([W * 0.27, W * 0.25, W * 0.52, W * 0.43], fill=(255,) * 4)
    d2.ellipse([W * 0.48, W * 0.25, W * 0.73, W * 0.43], fill=(255,) * 4)
    layers.append((can, lighter(grass, 0.10)))
    return layers


SUBJECTS = {
    "hub": (subject_hub, ("#2E2142", "#F2B33D"), "#6E49C6"),
    "flame": (subject_flame, ("#5A2A24", "#F2642E"), "#2E1C20"),
    "island": (subject_island, ("#5BC8F5", "#7FC24A"), "#DCF2FA"),
}


# ------------------------------------------------------------------ styles

def container(bg, rounded=True, style="flat"):
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = W * 0.05
    r = int(W * 0.26)
    if style == "lux":
        base = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        mask = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        ImageDraw.Draw(mask).rounded_rectangle([m, m, W - m, W - m], radius=r, fill=(255,) * 4)
        base = fill_shape(mask, lighter(bg, 0.22), darker(bg, 0.22))
        return base
    d.rounded_rectangle([m, m, W - m, W - m], radius=r, fill=rgb(bg) + (255,),
                        outline=INK, width=int(STROKE * 1.9))
    return img


def compose(subject_fn, pal, bg, style):
    img = container(bg, style=style)

    for mask, colour in subject_fn(pal):
        col = rgb(colour) if isinstance(colour, str) else colour

        if style == "flat":
            lay = fill_shape(mask, col, col)
            img.alpha_composite(lay)
            img.alpha_composite(outline(mask, STROKE))

        elif style == "depth":
            img.alpha_composite(cast_shadow(mask, (int(W * 0.012), int(W * 0.018)),
                                            W * 0.012, 90))
            img.alpha_composite(fill_shape(mask, lighter(col, 0.30), darker(col, 0.16)))
            img.alpha_composite(inner_shadow(mask, W * 0.012, 95))
            img.alpha_composite(outline(mask, STROKE))

        elif style == "iso":
            # Extrude by stepping the mask down-right, then outline the UNION once. Outlining
            # the extruded copy AND the face separately drew two parallel lines through every
            # form and read as a misprint rather than as depth.
            dx, dy = int(W * 0.020), int(W * 0.032)
            union = mask.copy()
            steps = 7
            for k in range(1, steps + 1):
                shifted = Image.new("RGBA", (W, W), (0, 0, 0, 0))
                shifted.paste(mask, (dx * k // steps, dy * k // steps))
                union.alpha_composite(shifted)
            side = fill_shape(union, darker(col, 0.40), darker(col, 0.55))
            img.alpha_composite(side)
            img.alpha_composite(fill_shape(mask, lighter(col, 0.28), col))
            img.alpha_composite(outline(union, STROKE))

        elif style == "lux":
            img.alpha_composite(cast_shadow(mask, (0, int(W * 0.022)), W * 0.030, 120))
            img.alpha_composite(fill_shape(mask, lighter(col, 0.42), darker(col, 0.24)))
            hi = inner_shadow(mask, W * 0.010, 70)
            img.alpha_composite(hi)

    return img.resize((SIZE, SIZE), Image.LANCZOS)


STYLES = ["flat", "depth", "iso", "lux"]


def main():
    want = None
    if "--subject" in sys.argv:
        i = sys.argv.index("--subject")
        if i + 1 < len(sys.argv):
            want = sys.argv[i + 1]
    subs = [k for k in SUBJECTS if (want is None or k == want)]
    os.makedirs(OUT, exist_ok=True)

    cell = 256
    cols = len(STYLES)
    rows = len(subs)
    sheet = Image.new("RGBA", (cell * cols, cell * rows + 90), (250, 250, 252, 255))
    d = ImageDraw.Draw(sheet)

    for r, sname in enumerate(subs):
        fn, pal, bg = SUBJECTS[sname]
        for c, style in enumerate(STYLES):
            im = compose(fn, pal, bg, style).resize((cell, cell), Image.LANCZOS)
            sheet.paste(im, (c * cell, r * cell), im)
            im.save(os.path.join(OUT, "lab_%s_%s.png" % (sname, style)))

    # the 32px strip: the size that actually decides whether a design works
    y = cell * rows + 12
    for c, style in enumerate(STYLES):
        d.text((c * cell + 10, y), style, fill=(40, 36, 50))
        for r, sname in enumerate(subs):
            fn, pal, bg = SUBJECTS[sname]
            tiny = compose(fn, pal, bg, style).resize((32, 32), Image.LANCZOS)
            sheet.paste(tiny, (c * cell + 10 + r * 40, y + 26), tiny)

    sheet.save(os.path.join(OUT, "_stylelab.png"))
    print("styles : %s" % ", ".join(STYLES))
    print("subjects: %s" % ", ".join(subs))
    print("sheet  : tools/_icons/_stylelab.png  (bottom strip is each one at 32px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
