# -*- coding: utf-8 -*-
"""Render The Hub's brand assets: title screen, loading screen, splash screen.

THE BRIEF, from the user's own stated sensibility: deep purple, warm gold, gothic/elegant,
old-school D&D-era high fantasy. Not neon, not flat-modern - illuminated manuscript.

The convenient part is that the pack is already built out of that palette, so the art is drawn
from the thing itself rather than imposed on it. The lobby is polished blackstone and deepslate
brick lit by glowstone, and its hall is TWELVE ARCHES, nine of them live and three sealed in
crying obsidian. Crying obsidian is purple; glowstone is warm gold. So the title screen is that
hall: twelve arches, nine lit from within, three cold and sealed. Anyone who has stood in the
lobby will recognise it, and the 9/3 split is real information rather than decoration - see
tools/build_hub_room_v5.py, which emits the arch coordinates.

TYPOGRAPHY. Palatino Linotype, because it is the closest thing on this machine to the Souvenir
and Friz Quadrata that the old AD&D books were set in - a humanist serif with calligraphic
bones. Checked against C:\\Windows\\Fonts rather than assumed; there is no blackletter installed
and Times/Georgia would read as a word processor rather than a rulebook.

WHY RENDER THE TEXT INTO THE IMAGE rather than use FancyMenu's `text` element: the serialization
keys for `image` elements were read out of a known-good layout file and are safe to author by
hand, and rendering type here means real letterspacing, a gold gradient fill and a drop shadow,
none of which Minecraft's bitmap font can do. The layout stays to constructs that have been
observed working.

Everything is drawn at 2x and downsampled, because arches are arcs and arcs alias badly.

    python build_brand_assets.py            # render into tools/_brand/ for review
    python build_brand_assets.py --apply    # also install into the instance
"""
import io
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_brand")
MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")

# ----------------------------------------------------------------- palette
# Deep purple and warm gold. The purples are taken toward blackstone rather than toward magenta;
# the golds are antique (glowstone lit through dust), not lemon.
VOID        = (11, 7, 16)        # near-black, violet-biased - the ground everything sits on
PURPLE_DEEP = (26, 15, 40)
PURPLE_MID  = (45, 24, 70)
PURPLE_LIT  = (74, 42, 112)      # crying obsidian, catching light
GOLD_DIM    = (138, 107, 32)
GOLD        = (201, 162, 39)
GOLD_BRIGHT = (242, 205, 122)
IVORY       = (237, 227, 207)    # parchment, for text that must stay readable

FONT_DIR = r"C:\Windows\Fonts"
FACE_BOLD = os.path.join(FONT_DIR, "palab.ttf")      # Palatino Linotype Bold
FACE_ITAL = os.path.join(FONT_DIR, "palai.ttf")      # Palatino Linotype Italic

SS = 2  # supersample factor


def font(path, size):
    if not os.path.exists(path):
        raise SystemExit("font not found: " + path)
    return ImageFont.truetype(path, size)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def vertical_gradient(size, top, bottom, stops=None):
    """A vertical gradient. `stops` is an optional list of (t, colour) for a multi-stop ramp."""
    w, h = size
    img = Image.new("RGB", (1, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if stops:
            c = stops[0][1]
            for i in range(len(stops) - 1):
                t0, c0 = stops[i]
                t1, c1 = stops[i + 1]
                if t0 <= t <= t1:
                    c = lerp(c0, c1, (t - t0) / max(1e-6, t1 - t0))
                    break
            else:
                c = stops[-1][1]
        else:
            c = lerp(top, bottom, t)
        px[0, y] = c
    return img.resize((w, h), Image.BILINEAR)


def radial_glow(size, centre, radius, colour, strength=1.0):
    """An additive soft glow, returned as an RGB image to be screened over the base."""
    w, h = size
    small = max(8, int(radius / 8))
    g = Image.new("L", (w // 4, h // 4), 0)
    d = ImageDraw.Draw(g)
    cx, cy = centre[0] // 4, centre[1] // 4
    r = radius // 4
    for i in range(12, 0, -1):
        t = i / 12.0
        d.ellipse([cx - r * t, cy - r * t * 0.72, cx + r * t, cy + r * t * 0.72],
                  fill=int(255 * (1 - t) ** 2 * strength))
    g = g.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(small))
    out = Image.new("RGB", (w, h), colour)
    out.putalpha(g)
    return out


def arch_mask(w, h):
    """A two-centred (equilateral) gothic arch, built by scanline rather than by pieslice.

    The pieslice version of this drew a notch instead of a point, because the arcs were being
    bounded by boxes that did not correspond to the two springing centres. The geometry is not
    actually fiddly once written down: for an opening of width w springing at y = spring, the
    left arc is centred at (w, spring) with radius w and the right arc at (0, spring), also
    radius w. At a height dy above the springing line the opening runs from

        x_left  = w - sqrt(w^2 - dy^2)        to        x_right = sqrt(w^2 - dy^2)

    which is the full width at dy = 0 and meets at a point at dy = w*sqrt(3)/2. That apex height
    is what makes it equilateral, and it is why the head is always 0.866 of the opening width.
    """
    head = w * math.sqrt(3) / 2.0
    # The springing line sits a HEAD'S HEIGHT DOWN FROM THE TOP, not at the bottom of the mask.
    # Putting it at h-1 meant every row below it was outside the loop's reach, so the shafts were
    # never filled and the hall rendered as twelve floating arrowheads.
    spring = int(round(head))
    m = Image.new("L", (w, h), 0)
    px = m.load()
    top = 0
    for y in range(h):
        if y >= spring:
            x0, x1 = 0, w                      # the shaft, full width
        else:
            dy = spring - y
            if dy >= head:
                continue                       # above the apex
            k = math.sqrt(max(0.0, w * w - dy * dy))
            x0 = int(round(w - k))
            x1 = int(round(k))
        for x in range(max(0, x0), min(w, x1)):
            px[x, y] = 255
    return m, top


FLOOR_T = 0.935   # where the hall floor meets the arches; both must agree


def draw_arcade(base):
    """The hall: twelve arches, nine lit from within, three sealed in crying obsidian.

    The lobby really is twelve arches with three sealed, so the split is carried over exactly
    rather than chosen for composition. See tools/build_hub_room_v5.py for the real coordinates.
    """
    w, h = base.size
    FLOOR_Y = int(h * FLOOR_T)
    total = 12
    sealed_at = {2, 6, 9}

    aw = int(w * 0.050)
    head = int(aw * math.sqrt(3) / 2.0)
    shaft = int(h * 0.255)
    ah = head + shaft
    gap = int(w * 0.0135)
    span = total * aw + (total - 1) * gap
    x0 = (w - span) // 2
    base_y = FLOOR_Y
    y0 = base_y - ah

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    for i in range(total):
        x = x0 + i * (aw + gap)
        m, _ = arch_mask(aw, ah)
        sealed = i in sealed_at

        if sealed:
            # crying obsidian: cold purple, no light behind it
            fill = vertical_gradient((aw, ah), (36, 20, 56), (18, 10, 28),
                                     stops=[(0.0, (30, 17, 47)), (0.6, (42, 24, 66)),
                                            (1.0, (16, 9, 25))])
        else:
            # an opening, not a panel: dark at the head, light pooling at the threshold
            fill = vertical_gradient((aw, ah), VOID, GOLD,
                                     stops=[(0.0, (14, 9, 20)), (0.55, (26, 17, 28)),
                                            (0.82, (96, 68, 28)), (1.0, GOLD_BRIGHT)])
        base.paste(fill, (x, y0), m)

        if not sealed:
            g = radial_glow((w, h), (x + aw // 2, base_y - int(shaft * 0.25)),
                            int(aw * 2.1), GOLD, strength=0.42)
            glow = Image.alpha_composite(glow, g)

        edge = Image.new("RGB", (aw, ah), GOLD_DIM if not sealed else PURPLE_LIT)
        outline = m.filter(ImageFilter.FIND_EDGES).point(lambda v: min(255, v * 4))
        base.paste(edge, (x, y0), outline)

    out = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")
    return out


def filigree(d, box, colour, weight=3):
    """A restrained gold frame: double rule with corner diamonds. Gothic, not Baroque."""
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], outline=colour, width=weight)
    inset = weight * 5
    d.rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                outline=colour, width=max(1, weight // 2))
    s = weight * 9
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=colour)


def gold_text(size, text, face, px, tracking=0.0, grad=(GOLD_BRIGHT, GOLD_DIM)):
    """Text filled with a vertical gold gradient, with a soft shadow beneath it."""
    f = font(face, px)
    w, h = size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    # manual letterspacing - PIL has no tracking
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = (w - total) / 2
    bbox = f.getbbox(text)
    y = (h - (bbox[3] - bbox[1])) / 2 - bbox[1]
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=f, fill=255)
        x += cw + tracking
    fill = vertical_gradient((w, h), grad[0], grad[1])
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(fill, (0, 0), mask)

    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.paste(Image.new("RGB", (w, h), (0, 0, 0)), (0, 0), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(px // 14))
    shadow.putalpha(shadow.getchannel("A").point(lambda v: int(v * 0.75)))
    return Image.alpha_composite(shadow, out)


# ----------------------------------------------------------------- the pieces
def title_background(w=1920, h=1080):
    W, H = w * SS, h * SS
    base = vertical_gradient((W, H), VOID, PURPLE_DEEP,
                             stops=[(0.0, VOID), (0.42, PURPLE_DEEP),
                                    (0.78, PURPLE_MID), (1.0, (16, 9, 24))]).convert("RGB")

    # a cold wash from above, so the hall is lit only by its own arches
    base = Image.blend(base, Image.new("RGB", (W, H), PURPLE_LIT), 0.06)

    # The floor goes down FIRST. Drawn after the arcade it painted over the arch shafts, which
    # left twelve floating heads and no hall.
    d = ImageDraw.Draw(base, "RGBA")
    d.rectangle([0, int(H * FLOOR_T), W, H], fill=(8, 5, 12, 255))

    base = draw_arcade(base)

    d = ImageDraw.Draw(base, "RGBA")
    d.line([(0, int(H * FLOOR_T)), (W, int(H * FLOOR_T))], fill=GOLD_DIM + (110,), width=SS)

    # vignette
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-W * 0.25, -H * 0.35, W * 1.25, H * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(W // 12))
    dark = Image.new("RGB", (W, H), (0, 0, 0))
    base = Image.composite(base, dark, vig)

    d = ImageDraw.Draw(base)
    filigree(d, (int(W * 0.022), int(H * 0.034), int(W * 0.978), int(H * 0.966)),
             GOLD_DIM, weight=2 * SS)

    return base.resize((w, h), Image.LANCZOS)


def wordmark(w=1200, h=340):
    W, H = w * SS, h * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    t = gold_text((W, int(H * 0.62)), "THE HUB", FACE_BOLD, int(H * 0.40),
                  tracking=int(H * 0.055))
    img.alpha_composite(t, (0, 0))

    d = ImageDraw.Draw(img)
    ry = int(H * 0.66)
    half = int(W * 0.30)
    d.line([(W // 2 - half, ry), (W // 2 + half, ry)], fill=GOLD_DIM + (255,), width=SS)
    s = int(H * 0.030)
    d.polygon([(W // 2, ry - s), (W // 2 + s, ry), (W // 2, ry + s), (W // 2 - s, ry)],
              fill=GOLD + (255,))

    sub = gold_text((W, int(H * 0.26)), "ELEVEN WORLDS, ONE HALL", FACE_ITAL, int(H * 0.095),
                    tracking=int(H * 0.030), grad=(IVORY, GOLD_DIM))
    img.alpha_composite(sub, (0, int(H * 0.70)))

    return img.resize((w, h), Image.LANCZOS)


def plain_backdrop(w, h, with_frame=True):
    """The quieter sibling used behind loading and splash - same world, less event."""
    W, H = w * SS, h * SS
    base = vertical_gradient((W, H), VOID, PURPLE_MID,
                             stops=[(0.0, VOID), (0.55, PURPLE_DEEP),
                                    (1.0, (22, 12, 34))]).convert("RGB")
    g = radial_glow((W, H), (W // 2, int(H * 0.52)), int(W * 0.42), GOLD, strength=0.30)
    base = Image.alpha_composite(base.convert("RGBA"), g).convert("RGB")

    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.2, -H * 0.3, W * 1.2, H * 1.3], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(W // 10))
    base = Image.composite(base, Image.new("RGB", (W, H), (0, 0, 0)), vig)

    if with_frame:
        filigree(ImageDraw.Draw(base),
                 (int(W * 0.03), int(H * 0.045), int(W * 0.97), int(H * 0.955)),
                 GOLD_DIM, weight=2 * SS)
    return base.resize((w, h), Image.LANCZOS)


def main():
    apply = "--apply" in sys.argv
    os.makedirs(OUT, exist_ok=True)

    pieces = {
        "hub_title_background.png": lambda: title_background(),
        "hub_wordmark.png":         lambda: wordmark(),
        "hub_loading.png":          lambda: plain_backdrop(1920, 1080),
        "hub_splash.png":           lambda: plain_backdrop(1920, 1080, with_frame=False),
    }
    made = {}
    for name, fn in pieces.items():
        img = fn()
        path = os.path.join(OUT, name)
        img.save(path)
        made[name] = path
        print("rendered  %-28s %dx%d  %d KB"
              % (name, img.size[0], img.size[1], os.path.getsize(path) // 1024))

    if not apply:
        print("")
        print("Review them in tools/_brand, then re-run with --apply to install.")
        return 0

    targets = [
        ("hub_title_background.png", os.path.join(MC, "config", "fancymenu", "assets")),
        ("hub_wordmark.png",         os.path.join(MC, "config", "fancymenu", "assets")),
        ("hub_loading.png",          os.path.join(MC, "config", "fancymenu", "assets")),
        ("hub_splash.png",           os.path.join(MC, "config", "simplesplashscreen")),
    ]
    print("")
    for name, dest in targets:
        os.makedirs(dest, exist_ok=True)
        with io.open(made[name], "rb") as src, io.open(os.path.join(dest, name), "wb") as dst:
            dst.write(src.read())
        print("installed " + name + "  ->  " + dest.replace(MC, "<instance>"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
