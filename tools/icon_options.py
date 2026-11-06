# -*- coding: utf-8 -*-
"""Render candidate subjects for the icons whose subject is still undecided.

FOUR PACKS HAVE NO OBVIOUS SUBJECT and were asked about directly: Netherbound, Horror, the three
Creative packs, and The Hub. Describing options in prose is useless for a drawing, so this
renders them.

Everything here is drawn in the `depth` treatment from icon_style_lab, because that is the one
that keeps the bold silhouette while adding shading, and it still reads in the 32px strip. If
the treatment changes later, these subjects move across unchanged - subjects and style are kept
separate on purpose.

"WHAT VISIBLY DENOTES CREATIVE MODE" is the hard one, and worth saying plainly: Minecraft has no
official creative icon. What people actually recognise is one of four things - the inventory
full of everything, flight, instant building, or infinite supply. One candidate is drawn for
each, so the question becomes a pick rather than a guess.

    python icon_options.py                  # every undecided pack
    python icon_options.py --pack nether
"""
import importlib.util
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_icons")
_spec = importlib.util.spec_from_file_location("lab", os.path.join(HERE, "icon_style_lab.py"))
lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab)

W = lab.W
shape = lab.shape_layer
light = lab.lighter
dark = lab.darker


def L(fn):
    """Build one mask layer from a draw callback."""
    img = shape()
    fn(ImageDraw.Draw(img))
    return img


# ---------------------------------------------------------------- NETHERBOUND

def nether_ghast(p):
    _rock, fire = p
    body = L(lambda d: d.rounded_rectangle([W * .24, W * .20, W * .76, W * .66],
                                           radius=W * .13, fill=(255,) * 4))
    tent = L(lambda d: [d.rounded_rectangle(
        [W * (.29 + i * .115), W * .62, W * (.335 + i * .115), W * .84],
        radius=W * .022, fill=(255,) * 4) for i in range(4)])
    eyes = L(lambda d: [d.rounded_rectangle(
        [W * (.355 + i * .19), W * .36, W * (.445 + i * .19), W * .44],
        radius=W * .012, fill=(255,) * 4) for i in range(2)])
    mouth = L(lambda d: d.rounded_rectangle([W * .40, W * .50, W * .60, W * .56],
                                            radius=W * .012, fill=(255,) * 4))
    return [(body, "#E8E4DE"), (tent, "#D6D0C8"), (eyes, "#2A2430"), (mouth, "#2A2430")]


def nether_wither_skull(p):
    _rock, _fire = p
    skull = L(lambda d: d.rounded_rectangle([W * .24, W * .22, W * .76, W * .70],
                                            radius=W * .09, fill=(255,) * 4))
    jaw = L(lambda d: d.rounded_rectangle([W * .32, W * .66, W * .68, W * .80],
                                          radius=W * .035, fill=(255,) * 4))
    eyes = L(lambda d: [d.rounded_rectangle(
        [W * (.335 + i * .20), W * .36, W * (.455 + i * .20), W * .47],
        radius=W * .02, fill=(255,) * 4) for i in range(2)])
    return [(skull, "#4A4A48"), (jaw, "#3C3C3A"), (eyes, "#F2642E")]


def nether_portal(p):
    rock, _fire = p
    frame = L(lambda d: d.rounded_rectangle([W * .20, W * .14, W * .80, W * .86],
                                            radius=W * .05, fill=(255,) * 4))
    inner = L(lambda d: d.rounded_rectangle([W * .31, W * .25, W * .69, W * .75],
                                            radius=W * .03, fill=(255,) * 4))
    swirl = L(lambda d: d.ellipse([W * .38, W * .36, W * .62, W * .64], fill=(255,) * 4))
    return [(frame, "#3A3340"), (inner, "#7B3FD4"), (swirl, "#B98BF0")]


def nether_lava(p):
    rock, fire = p
    block = L(lambda d: d.rounded_rectangle([W * .18, W * .34, W * .82, W * .82],
                                            radius=W * .04, fill=(255,) * 4))
    pool = L(lambda d: d.rounded_rectangle([W * .18, W * .34, W * .82, W * .50],
                                           radius=W * .035, fill=(255,) * 4))
    drip = L(lambda d: [d.rounded_rectangle(
        [W * (.30 + i * .19), W * .46, W * (.37 + i * .19), W * (.60 + i * .05)],
        radius=W * .032, fill=(255,) * 4) for i in range(3)])
    return [(block, "#6E3630"), (pool, fire), (drip, light(fire, .25))]


# ---------------------------------------------------------------- HORROR

def horror_eye(p):
    dusk, blood = p
    lid = L(lambda d: d.ellipse([W * .16, W * .33, W * .84, W * .67], fill=(255,) * 4))
    iris = L(lambda d: d.ellipse([W * .40, W * .36, W * .60, W * .64], fill=(255,) * 4))
    pup = L(lambda d: d.ellipse([W * .465, W * .43, W * .535, W * .57], fill=(255,) * 4))
    return [(lid, light(dusk, .68)), (iris, blood), (pup, "#201A28")]


def horror_enderman_eyes(p):
    dusk, _blood = p
    head = L(lambda d: d.rounded_rectangle([W * .28, W * .22, W * .72, W * .78],
                                           radius=W * .05, fill=(255,) * 4))
    eyes = L(lambda d: [d.rounded_rectangle(
        [W * (.315 + i * .21), W * .42, W * (.475 + i * .21), W * .50],
        radius=W * .015, fill=(255,) * 4) for i in range(2)])
    return [(head, dark(dusk, .55)), (eyes, "#D8A6F5")]


def horror_doorway(p):
    dusk, blood = p
    door = L(lambda d: d.rounded_rectangle([W * .26, W * .16, W * .74, W * .84],
                                           radius=W * .04, fill=(255,) * 4))
    gap = L(lambda d: d.polygon([(W * .44, W * .16), (W * .60, W * .16),
                                 (W * .56, W * .84), (W * .40, W * .84)], fill=(255,) * 4))
    fig = L(lambda d: (d.ellipse([W * .455, W * .34, W * .545, W * .44], fill=(255,) * 4),
                       d.rounded_rectangle([W * .445, W * .43, W * .555, W * .72],
                                           radius=W * .02, fill=(255,) * 4)))
    return [(door, dark(dusk, .25)), (gap, "#E8D9B0"), (fig, "#1C1722")]


def horror_candle(p):
    dusk, blood = p
    stick = L(lambda d: d.rounded_rectangle([W * .44, W * .38, W * .56, W * .74],
                                            radius=W * .02, fill=(255,) * 4))
    base = L(lambda d: d.rounded_rectangle([W * .34, W * .72, W * .66, W * .82],
                                           radius=W * .025, fill=(255,) * 4))
    fl = L(lambda d: d.polygon([(W * .50, W * .20), (W * .575, W * .33),
                                (W * .50, W * .40), (W * .425, W * .33)], fill=(255,) * 4))
    return [(stick, "#E2DACB"), (base, dark(dusk, .3)), (fl, "#F2B33D")]


# ---------------------------------------------------------------- CREATIVE
# Four things people actually recognise as creative mode, one candidate each.

def creative_palette(p):
    """The inventory full of everything - a swatch grid."""
    a, b = p
    cols = ["#E8564C", "#F2B33D", "#7FC24A", "#3D8FD6", "#9B6BE8", "#3FC9A5",
            "#E8832E", "#D8D4DC", "#5BC8F5"]
    plate = L(lambda d: d.rounded_rectangle([W * .17, W * .17, W * .83, W * .83],
                                            radius=W * .06, fill=(255,) * 4))
    out = [(plate, "#F7F5F8")]
    for i, c in enumerate(cols):
        gx, gy = i % 3, i // 3
        out.append((L(lambda d, gx=gx, gy=gy: d.rounded_rectangle(
            [W * (.245 + gx * .18), W * (.245 + gy * .18),
             W * (.385 + gx * .18), W * (.385 + gy * .18)],
            radius=W * .018, fill=(255,) * 4)), c))
    return out


def creative_infinity(p):
    """Infinite supply - the infinity loop over a block."""
    a, b = p
    blk = L(lambda d: d.rounded_rectangle([W * .32, W * .55, W * .68, W * .84],
                                          radius=W * .035, fill=(255,) * 4))
    def loop(d):
        for cx in (W * .39, W * .61):
            d.ellipse([cx - W * .135, W * .20, cx + W * .135, W * .47], fill=(255,) * 4)
    ring = L(loop)
    hole = L(lambda d: [d.ellipse([cx - W * .065, W * .27, cx + W * .065, W * .40],
                                  fill=(255,) * 4) for cx in (W * .39, W * .61)])
    return [(ring, a), (hole, "#F7F5F8"), (blk, b)]


def creative_flight(p):
    """Flight - elytra-style wings, the one creative verb with a silhouette."""
    a, b = p
    body = L(lambda d: d.rounded_rectangle([W * .455, W * .34, W * .545, W * .70],
                                           radius=W * .03, fill=(255,) * 4))
    wings = L(lambda d: (
        d.polygon([(W * .47, W * .36), (W * .14, W * .52), (W * .47, W * .62)],
                  fill=(255,) * 4),
        d.polygon([(W * .53, W * .36), (W * .86, W * .52), (W * .53, W * .62)],
                  fill=(255,) * 4)))
    return [(wings, a), (body, b)]


def creative_place(p):
    """Instant building - a block appearing under a cursor, with sparks."""
    a, b = p
    blk = L(lambda d: d.rounded_rectangle([W * .28, W * .44, W * .72, W * .80],
                                          radius=W * .04, fill=(255,) * 4))
    top = L(lambda d: d.rounded_rectangle([W * .28, W * .44, W * .72, W * .56],
                                          radius=W * .035, fill=(255,) * 4))
    spark = L(lambda d: [d.polygon(
        [(cx, cy - W * .075), (cx + W * .030, cy), (cx, cy + W * .075), (cx - W * .030, cy)],
        fill=(255,) * 4) for cx, cy in
        ((W * .28, W * .26), (W * .50, W * .18), (W * .73, W * .28))])
    return [(spark, a), (blk, dark(b, .30)), (top, b)]


# ---------------------------------------------------------------- THE HUB

def hub_nexus(p):
    """Hub and spokes: a core with portals around it. Literally what the pack is."""
    dark_, gold = p
    spokes = L(lambda d: [d.line(
        [(W * .5, W * .5),
         (W * .5 + W * .33 * math.cos(math.radians(a)),
          W * .5 + W * .33 * math.sin(math.radians(a)))],
        fill=(255,) * 4, width=int(W * .035)) for a in range(0, 360, 60)])
    nodes = L(lambda d: [d.ellipse(
        [W * .5 + W * .33 * math.cos(math.radians(a)) - W * .085,
         W * .5 + W * .33 * math.sin(math.radians(a)) - W * .085,
         W * .5 + W * .33 * math.cos(math.radians(a)) + W * .085,
         W * .5 + W * .33 * math.sin(math.radians(a)) + W * .085],
        fill=(255,) * 4) for a in range(0, 360, 60)])
    core = L(lambda d: d.ellipse([W * .35, W * .35, W * .65, W * .65], fill=(255,) * 4))
    return [(spokes, dark(gold, .35)), (nodes, gold), (core, light(gold, .35))]


def hub_portal_ring(p):
    """A ring portal: gold frame, lit interior."""
    dark_, gold = p
    ring = L(lambda d: d.ellipse([W * .16, W * .16, W * .84, W * .84], fill=(255,) * 4))
    inner = L(lambda d: d.ellipse([W * .28, W * .28, W * .72, W * .72], fill=(255,) * 4))
    swirl = L(lambda d: d.ellipse([W * .38, W * .38, W * .62, W * .62], fill=(255,) * 4))
    return [(ring, gold), (inner, dark_), (swirl, light(gold, .45))]


def hub_keystone(p):
    """A keystone medallion - one object, strong silhouette, no architecture to misread."""
    dark_, gold = p
    stone = L(lambda d: d.polygon(
        [(W * .5, W * .13), (W * .84, W * .33), (W * .84, W * .67),
         (W * .5, W * .87), (W * .16, W * .67), (W * .16, W * .33)], fill=(255,) * 4))
    bevel = L(lambda d: d.polygon(
        [(W * .5, W * .24), (W * .74, W * .38), (W * .74, W * .62),
         (W * .5, W * .76), (W * .26, W * .62), (W * .26, W * .38)], fill=(255,) * 4))
    eye = L(lambda d: d.ellipse([W * .42, W * .42, W * .58, W * .58], fill=(255,) * 4))
    return [(stone, gold), (bevel, dark_), (eye, light(gold, .5))]


def hub_stack(p):
    """Eleven worlds stacked: a tower of distinct slabs."""
    dark_, gold = p
    cols = ["#E8564C", "#F2B33D", "#7FC24A", "#3D8FD6", "#9B6BE8", "#3FC9A5"]
    out = []
    for i, c in enumerate(cols):
        y = W * (.22 + i * .098)
        inset = W * (.012 * abs(i - 2.5))
        out.append((L(lambda d, y=y, inset=inset: d.rounded_rectangle(
            [W * .22 + inset, y, W * .78 - inset, y + W * .082],
            radius=W * .022, fill=(255,) * 4)), c))
    return out


PACKS = {
    "nether": ("Netherbound", ("#5A2A24", "#F2642E"), "#2E1C20",
               [("ghast", nether_ghast), ("wither skull", nether_wither_skull),
                ("portal", nether_portal), ("lava block", nether_lava)]),
    "horror": ("Horror", ("#6B5A82", "#C0392B"), "#2A2334",
               [("eye (current)", horror_eye), ("enderman eyes", horror_enderman_eyes),
                ("figure in doorway", horror_doorway), ("candle", horror_candle)]),
    "creative": ("Creative (any of the three)", ("#9B6BE8", "#3FC9A5"), "#F0ECF8",
                 [("palette grid", creative_palette), ("infinity + block", creative_infinity),
                  ("flight", creative_flight), ("instant place", creative_place)]),
    "hub": ("The Hub", ("#2E2142", "#F2B33D"), "#6E49C6",
            [("nexus", hub_nexus), ("portal ring", hub_portal_ring),
             ("keystone", hub_keystone), ("world stack", hub_stack)]),
}


def main():
    want = None
    if "--pack" in sys.argv:
        i = sys.argv.index("--pack")
        if i + 1 < len(sys.argv):
            want = sys.argv[i + 1]
    keys = [k for k in PACKS if want is None or k == want]
    os.makedirs(OUT, exist_ok=True)

    cell = 230
    cols = 4
    rows = len(keys)
    sheet = Image.new("RGBA", (cell * cols, (cell + 46) * rows + 10), (250, 250, 252, 255))
    sd = ImageDraw.Draw(sheet)

    for r, key in enumerate(keys):
        title, pal, bg, cands = PACKS[key]
        y0 = r * (cell + 46)
        sd.text((8, y0 + 6), title, fill=(30, 26, 40))
        for c, (label, fn) in enumerate(cands[:cols]):
            img = lab.container(bg, style="depth")
            for mask, colour in fn(pal):
                col = lab.rgb(colour) if isinstance(colour, str) else colour
                img.alpha_composite(lab.cast_shadow(
                    mask, (int(W * .012), int(W * .018)), W * .012, 90))
                img.alpha_composite(lab.fill_shape(mask, light(col, .30), dark(col, .16)))
                img.alpha_composite(lab.inner_shadow(mask, W * .012, 95))
                img.alpha_composite(lab.outline(mask, lab.STROKE))
            small = img.resize((cell - 16, cell - 16), Image.LANCZOS)
            sheet.paste(small, (c * cell + 8, y0 + 26), small)
            sd.text((c * cell + 10, y0 + cell + 16), label, fill=(60, 55, 72))
            tiny = img.resize((32, 32), Image.LANCZOS)
            sheet.paste(tiny, (c * cell + cell - 48, y0 + cell + 8), tiny)

    sheet.save(os.path.join(OUT, "_options.png"))
    print("packs  : %s" % ", ".join(keys))
    print("sheet  : tools/_icons/_options.png   (32px version beside each label)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
