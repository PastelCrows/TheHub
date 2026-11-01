# -*- coding: utf-8 -*-
"""Render The Hub's brand assets: title screen, loading screen, splash screen.

THE BRIEF, from the user's own stated sensibility: deep purple, warm gold, gothic/elegant,
old-school D&D-era high fantasy. Not neon, not flat-modern - illuminated manuscript.

The pack is already built out of that palette, so the art is drawn from the thing itself rather
than imposed on it. The title screen IS the lobby: a twelve-bay gothic arcade.

ELEVEN LIVE, ONE SEALED. Not nine. One Block and Horror were sealed early on and have both been
live for a long time; the authority is the `LIVE` set in build_hub_room_v6.py, whose own
docstring was stale until 2026-10-31.

EACH ARCH IS ITS OWN DOOR. build_hub_room_v6.py gives every arch a frame material and a light
block, and those are carried into the art: skyblock's sea lantern is pale and cool, netherbound's
shroomlight burns orange, horror's soul lantern is a cold blue, the gauntlet's gold block is the
brightest thing in the hall. The colours are tempered toward the brand so eleven different lights
still read as one deep-purple-and-gold room, but the identity of each door is really there. The
sealed bay is crying obsidian with a deepslate cross-brace and no light at all, so "shut" reads
at a glance instead of being a faint ghost nobody can see.

TYPOGRAPHY. Palatino Linotype, checked against C:\\Windows\\Fonts rather than assumed - there is
no blackletter installed, and it is the closest thing here to the Souvenir and Friz Quadrata the
old AD&D books were set in. The wordmark renders to a PNG rather than a FancyMenu text element,
which buys real letterspacing, a gold gradient fill and a drop shadow the bitmap font cannot do.

THE ARCH. Two-centred and equilateral. For an opening of width w springing at y, the head runs
from x = w - sqrt(w^2 - dy^2) to x = sqrt(w^2 - dy^2), meeting at a point at dy = w*sqrt(3)/2.
The springing line sits a head's height DOWN FROM THE TOP of the mask - putting it at the bottom
renders twelve floating arrowheads and nothing else.

    python build_brand_assets.py            # render into tools/_brand/ for review
    python build_brand_assets.py --apply    # also install into the instance
"""
import io
import math
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_brand")
MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")

W_OUT, H_OUT = 2560, 1440
SS = 2

VOID        = (10, 7, 15)
PURPLE_DEEP = (24, 14, 37)
PURPLE_LIT  = (82, 48, 122)
STONE_LIT   = (46, 33, 60)
GOLD_DIM    = (132, 102, 32)
GOLD        = (198, 160, 42)
GOLD_BRIGHT = (242, 205, 122)
IVORY       = (237, 227, 207)

# The twelve bays in the order build_hub_room_v6.py lays them out, with the light each arch
# actually contains. None means sealed.
BAYS = [
    ("skyblock",    (142, 178, 186)),   # sea lantern
    ("survival",    (236, 184, 112)),   # lantern
    ("caveblock",   (242, 205, 122)),   # glowstone
    ("netherbound", (232, 146,  78)),   # shroomlight
    ("oceanblock",  (142, 178, 186)),   # sea lantern
    ("lostcities",  (214, 122,  72)),   # redstone lamp
    ("onechunk",    (242, 205, 122)),   # glowstone
    ("gauntlet",    (246, 208, 108)),   # gold block
    ("redstone",    (214, 122,  72)),   # redstone lamp
    ("oneblock",    (238, 200, 126)),   # ochre froglight
    ("horror",      (118, 196, 206)),   # soul lantern
    ("reserved",    None),              # sealed: crying obsidian, no light
]

FONT_DIR = r"C:\Windows\Fonts"
FACE_BOLD = os.path.join(FONT_DIR, "palab.ttf")
FACE_ITAL = os.path.join(FONT_DIR, "palai.ttf")

FLOOR_T = 0.930

# How far each arch's own light is pulled toward the brand's gold before it is drawn. The first
# attempt used the raw block colours and the hall came out a rainbow - eleven saturated slabs
# that read as a colour chart, not as deep purple and warm gold. At 0.55 the identities survive
# (sea lantern still cool, shroomlight still orange, soul lantern still blue) but they all sit
# inside one palette.
TEMPER = 0.55


def tempered(c):
    return lerp(c, GOLD, TEMPER)


def font(path, size):
    if not os.path.exists(path):
        raise SystemExit("font not found: " + path)
    return ImageFont.truetype(path, size)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def ramp(size, stops):
    w, h = size
    col = Image.new("RGB", (1, h))
    px = col.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = stops[-1][1]
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                c = lerp(c0, c1, (t - t0) / max(1e-6, t1 - t0))
                break
        px[0, y] = c
    return col.resize((w, h), Image.BILINEAR)


def glow(size, centre, rx, ry, colour, strength):
    w, h = size
    q = 4
    g = Image.new("L", (w // q, h // q), 0)
    d = ImageDraw.Draw(g)
    cx, cy = centre[0] // q, centre[1] // q
    for i in range(14, 0, -1):
        t = i / 14.0
        d.ellipse([cx - rx * t / q, cy - ry * t / q, cx + rx * t / q, cy + ry * t / q],
                  fill=int(255 * (1 - t) ** 2.2 * strength))
    g = g.resize((w, h), Image.BILINEAR).filter(ImageFilter.GaussianBlur(max(6, rx // 10)))
    out = Image.new("RGB", (w, h), colour)
    out.putalpha(g)
    return out


def arch_mask(w, h):
    head = w * math.sqrt(3) / 2.0
    spring = int(round(head))
    m = Image.new("L", (w, h), 0)
    px = m.load()
    for y in range(h):
        if y >= spring:
            x0, x1 = 0, w
        else:
            dy = spring - y
            if dy >= head:
                continue
            k = math.sqrt(max(0.0, w * w - dy * dy))
            x0, x1 = int(round(w - k)), int(round(k))
        for x in range(max(0, x0), min(w, x1)):
            px[x, y] = 255
    return m, spring


def outline_of(mask, width):
    """A band just inside the mask edge - the archivolt moulding around each opening."""
    eroded = mask.filter(ImageFilter.MinFilter(width * 2 + 1))
    return ImageChops.subtract(mask, eroded)


def ashlar(size, rows=20):
    """Faint coursed stonework, so the wall reads as masonry and not a flat field."""
    w, h = size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    course = max(8, h // rows)
    block = course * 3
    for i, y in enumerate(range(0, h, course)):
        d.line([(0, y), (w, y)], fill=24, width=max(1, course // 22))
        offset = (block // 2) if (i % 2) else 0
        for x in range(-block, w + block, block):
            d.line([(x + offset, y), (x + offset, y + course)],
                   fill=18, width=max(1, course // 26))
    return layer.filter(ImageFilter.GaussianBlur(0.6))


def tracery(d, x, y, w, head, colour, weight):
    """A circle over two lancets in the arch head - the cheapest gothic tell there is."""
    cx = x + w // 2
    r = int(w * 0.16)
    cy = y + int(head * 0.40)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=weight)
    d.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], outline=colour, width=weight)
    lw = int(w * 0.26)
    for side in (-1, 1):
        ix = cx + side * int(w * 0.19) - lw // 2
        iy = cy + int(r * 1.05)
        d.arc([ix, iy, ix + lw, iy + lw], 180, 360, fill=colour, width=weight)
        d.line([(ix, iy + lw // 2), (ix, y + head)], fill=colour, width=weight)
        d.line([(ix + lw, iy + lw // 2), (ix + lw, y + head)], fill=colour, width=weight)


def build_hall(w, h):
    floor_y = int(h * FLOOR_T)

    base = ramp((w, h), [(0.0, VOID), (0.30, PURPLE_DEEP), (0.72, (36, 20, 55)),
                         (1.0, (20, 11, 31))]).convert("RGB")
    base.paste(Image.new("RGB", (w, h), STONE_LIT), (0, 0), ashlar((w, h)))

    total = len(BAYS)
    aw = int(w * 0.0515)
    head = int(aw * math.sqrt(3) / 2.0)
    shaft = int(h * 0.205)
    ah = head + shaft
    pier = int(w * 0.0150)
    span = total * aw + (total - 1) * pier
    x0 = (w - span) // 2
    y0 = floor_y - ah

    lights = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    reflect = Image.new("RGB", (w, h), (0, 0, 0))
    weight = max(2, w // 900)
    d = ImageDraw.Draw(base)

    for i in range(total + 1):
        px = x0 - pier + i * (aw + pier)
        face = ramp((pier, ah + head // 2),
                    [(0.0, (26, 18, 38)), (0.5, STONE_LIT), (1.0, (22, 15, 33))])
        base.paste(face, (px, y0 - head // 2))
        cap_y = y0 + head
        d.rectangle([px - weight, cap_y - weight * 3, px + pier + weight, cap_y], fill=GOLD_DIM)
        d.rectangle([px - weight, floor_y - weight * 4, px + pier + weight, floor_y],
                    fill=(58, 42, 74))

    for i, (name, light) in enumerate(BAYS):
        x = x0 + i * (aw + pier)
        m, _ = arch_mask(aw, ah)

        if light is None:
            fill = ramp((aw, ah), [(0.0, (30, 18, 46)), (0.40, (52, 31, 78)),
                                   (0.80, (44, 26, 66)), (1.0, (26, 15, 40))])
        else:
            t = tempered(light)
            fill = ramp((aw, ah), [(0.0, lerp(t, VOID, 0.94)),
                                   (0.62, lerp(t, VOID, 0.86)),
                                   (0.88, lerp(t, VOID, 0.52)),
                                   (1.0, lerp(t, VOID, 0.16))])
        base.paste(fill, (x, y0), m)
        base.paste(Image.new("RGB", (aw, ah), GOLD if light else PURPLE_LIT),
                   (x, y0), outline_of(m, weight))

        # Tracery and braces go on their own layer and are pasted THROUGH the arch mask. Drawn
        # straight onto the wall they ran past the opening - the sealed bay's cross-brace stuck
        # out into the pier either side of it.
        detail = Image.new("RGB", (aw, ah), (0, 0, 0))
        dm = Image.new("L", (aw, ah), 0)
        dd, dmd = ImageDraw.Draw(detail), ImageDraw.Draw(dm)
        for drw, col in ((dd, GOLD_DIM if light else (92, 58, 132)), (dmd, 255)):
            tracery(drw, 0, 0, aw, head, col, max(1, weight - 1))
        if light is None:
            for a, b in (((0, head), (aw, ah - weight)), ((aw, head), (0, ah - weight))):
                dd.line([a, b], fill=(48, 40, 56), width=weight * 4)
                dmd.line([a, b], fill=255, width=weight * 4)
                dd.line([a, b], fill=(92, 80, 104), width=weight)
                dmd.line([a, b], fill=255, width=weight)
        dm = ImageChops.multiply(dm, m)
        base.paste(detail, (x, y0), dm)

        if light is None:
            continue

        lights = Image.alpha_composite(
            lights, glow((w, h), (x + aw // 2, floor_y - int(shaft * 0.10)),
                         int(aw * 1.5), int(ah * 0.42), tempered(light), 0.30))
        reflect.paste(ramp((aw, int(h * 0.050)),
                           [(0.0, lerp(tempered(light), VOID, 0.72)), (1.0, VOID)]),
                      (x, floor_y))

    scene = Image.alpha_composite(base.convert("RGBA"), lights).convert("RGB")

    fd = ImageDraw.Draw(scene)
    fd.rectangle([0, floor_y, w, h], fill=(11, 7, 16))
    scene = ImageChops.add(scene, reflect.filter(ImageFilter.GaussianBlur(w // 320)))
    ImageDraw.Draw(scene, "RGBA").line([(0, floor_y), (w, floor_y)],
                                       fill=GOLD_DIM + (120,), width=weight)

    return Image.alpha_composite(
        scene.convert("RGBA"),
        glow((w, h), (w // 2, floor_y - int(h * 0.02)), int(w * 0.46), int(h * 0.05),
             (196, 150, 90), 0.30)).convert("RGB")


def filigree(d, box, colour, weight):
    x0, y0, x1, y1 = box
    d.rectangle([x0, y0, x1, y1], outline=colour, width=weight)
    inset = weight * 5
    d.rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset],
                outline=colour, width=max(1, weight // 2))
    s = weight * 9
    for (cx, cy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        d.polygon([(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)], fill=colour)


def gold_text(size, text, face, px, tracking=0.0, grad=(GOLD_BRIGHT, GOLD_DIM)):
    f = font(face, px)
    w, h = size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = (w - total) / 2
    bbox = f.getbbox(text)
    y = (h - (bbox[3] - bbox[1])) / 2 - bbox[1]
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=f, fill=255)
        x += cw + tracking
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(ramp((w, h), [(0.0, grad[0]), (1.0, grad[1])]), (0, 0), mask)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow.paste(Image.new("RGB", (w, h), (0, 0, 0)), (0, 0), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(px // 14))
    shadow.putalpha(shadow.getchannel("A").point(lambda v: int(v * 0.8)))
    return Image.alpha_composite(shadow, out)


def title_background():
    W, H = W_OUT * SS, H_OUT * SS
    scene = build_hall(W, H)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.22, -H * 0.40, W * 1.22, H * 1.30], fill=255)
    scene = Image.composite(scene, Image.new("RGB", (W, H), (0, 0, 0)),
                            vig.filter(ImageFilter.GaussianBlur(W // 11)))
    filigree(ImageDraw.Draw(scene),
             (int(W * 0.020), int(H * 0.030), int(W * 0.980), int(H * 0.970)),
             GOLD_DIM, max(2, W // 1100))
    return scene.resize((W_OUT, H_OUT), Image.LANCZOS)


def wordmark(w=1600, h=440):
    W, H = w * SS, h * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.alpha_composite(gold_text((W, int(H * 0.62)), "THE HUB", FACE_BOLD,
                                  int(H * 0.40), tracking=int(H * 0.055)), (0, 0))
    d = ImageDraw.Draw(img)
    ry = int(H * 0.66)
    half = int(W * 0.30)
    d.line([(W // 2 - half, ry), (W // 2 + half, ry)], fill=GOLD_DIM + (255,), width=SS)
    s = int(H * 0.030)
    d.polygon([(W // 2, ry - s), (W // 2 + s, ry), (W // 2, ry + s), (W // 2 - s, ry)],
              fill=GOLD + (255,))
    img.alpha_composite(gold_text((W, int(H * 0.26)), "ELEVEN WORLDS, ONE HALL", FACE_ITAL,
                                  int(H * 0.095), tracking=int(H * 0.030),
                                  grad=(IVORY, GOLD_DIM)), (0, int(H * 0.70)))
    return img.resize((w, h), Image.LANCZOS)


def quiet_backdrop(framed=True):
    """Loading and splash: the same hall, further off and out of focus."""
    W, H = W_OUT * SS, H_OUT * SS
    scene = build_hall(W, H).filter(ImageFilter.GaussianBlur(W // 220))
    scene = Image.blend(scene, Image.new("RGB", (W, H), VOID), 0.30)
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.18, -H * 0.30, W * 1.18, H * 1.25], fill=255)
    scene = Image.composite(scene, Image.new("RGB", (W, H), (0, 0, 0)),
                            vig.filter(ImageFilter.GaussianBlur(W // 9)))
    if framed:
        filigree(ImageDraw.Draw(scene),
                 (int(W * 0.028), int(H * 0.042), int(W * 0.972), int(H * 0.958)),
                 GOLD_DIM, max(2, W // 1100))
    return scene.resize((W_OUT, H_OUT), Image.LANCZOS)


def icon(size=256):
    """The pack's mark: one lit arch. The hall reduced to the smallest thing still recognisable.

    Sized for Prism's instance list and for a window icon, so it has to survive being drawn at
    32px - which is why it is a single arch rather than twelve, and why the gold is the brightest
    thing in it. Prism scans %APPDATA%/PrismLauncher/icons for PNGs and offers whatever it finds
    in the icon picker.
    """
    S = size * SS
    img = ramp((S, S), [(0.0, (18, 11, 28)), (0.55, PURPLE_DEEP), (1.0, (12, 7, 18))]).convert("RGB")

    aw = int(S * 0.44)
    head = int(aw * math.sqrt(3) / 2.0)
    ah = head + int(S * 0.34)
    x = (S - aw) // 2
    y = int(S * 0.80) - ah

    m, _ = arch_mask(aw, ah)
    fill = ramp((aw, ah), [(0.0, (16, 10, 24)), (0.50, (34, 22, 34)),
                           (0.84, (120, 86, 36)), (1.0, GOLD_BRIGHT)])
    img.paste(fill, (x, y), m)
    weight = max(2, S // 110)
    img.paste(Image.new("RGB", (aw, ah), GOLD), (x, y), outline_of(m, weight))

    img = Image.alpha_composite(
        img.convert("RGBA"),
        glow((S, S), (S // 2, int(S * 0.74)), int(aw * 1.5), int(ah * 0.6),
             GOLD, 0.55)).convert("RGB")

    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, int(S * 0.80), S, S], fill=(10, 6, 15, 255))
    d.line([(0, int(S * 0.80)), (S, int(S * 0.80))], fill=GOLD_DIM + (140,), width=weight)
    filigree(ImageDraw.Draw(img), (weight * 2, weight * 2, S - weight * 2, S - weight * 2),
             GOLD_DIM, weight)
    return img.resize((size, size), Image.LANCZOS)


def main():
    apply = "--apply" in sys.argv
    os.makedirs(OUT, exist_ok=True)

    live = sum(1 for _, c in BAYS if c)
    print("hall: %d bays, %d live, %d sealed" % (len(BAYS), live, len(BAYS) - live))
    print("")

    pieces = {
        "hub_title_background.png": title_background,
        "hub_wordmark.png":         wordmark,
        "hub_loading.png":          lambda: quiet_backdrop(True),
        "hub_splash.png":           lambda: quiet_backdrop(False),
        "hub_icon.png":             lambda: icon(256),
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
        ("hub_title_background.png", os.path.join(MC, "config", "fancymenu", "assets"), None),
        ("hub_wordmark.png",         os.path.join(MC, "config", "fancymenu", "assets"), None),
        ("hub_loading.png",          os.path.join(MC, "config", "fancymenu", "assets"), None),
        ("hub_splash.png",           os.path.join(MC, "config", "simplesplashscreen"),
         "background.png"),
        # Prism scans this folder and offers whatever it finds in the instance icon picker.
        ("hub_icon.png", os.path.expandvars(r"%APPDATA%\PrismLauncher\icons"), "thehub.png"),
    ]
    print("")
    for name, dest, rename in targets:
        os.makedirs(dest, exist_ok=True)
        out_name = rename or name
        with io.open(made[name], "rb") as src, io.open(os.path.join(dest, out_name), "wb") as f:
            f.write(src.read())
        print("installed %-26s -> %s" % (out_name, dest.replace(MC, "<instance>")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
