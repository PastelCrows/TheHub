# -*- coding: utf-8 -*-
"""Download resource packs for testing, then MEASURE what they actually are.

A pack's name is marketing, not a fact. "128x" in a title says nothing about whether the
textures really are 128x, how much of the game they cover, or whether the pack is a demo with
most of its files missing - and all three matter a great deal in a 247-mod pack, where every
texture the pack does not supply falls back to 16x and sits next to one that did.

So each download is verified by opening it and looking:

  resolution  read from block/stone.png, which every vanilla-style pack ships, rather than
              from the title.
  coverage    the share of ALL 1617 vanilla block and item textures in the 1.21.1 client jar
              that the pack actually supplies.

              The first version of this sampled twenty common block textures instead, and that
              was not a shortcut, it was a wrong answer: it reported Majestica at 100% when the
              real figure over the whole set is 68.8%, and a pack choice was made on the back of
              that. Twenty famous textures are exactly the ones every pack does first. Anything
              short of ~85% means vanilla 16x showing through right beside retextured blocks.

  extra       textures the pack ships that do NOT exist in 1.21.1, i.e. it was authored for a
              newer version. Harmless on its own - high extra WITH high coverage is fine, and
              judging a pack by pack_format alone is how Ashen got wrongly called the risky one
              at 98.9% coverage.
  pack_format the declared format number, flagged when it does not match 1.21.1 (34).

Nothing is installed unless the zip opens and contains a pack.mcmeta, so a truncated download
cannot land in the resourcepacks folder looking usable.
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from PIL import Image
except ImportError:
    Image = None

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
DEST = os.path.join(MC, "resourcepacks")
UA = "hub-pack-setup/1.0 (personal modpack)"

PACK_FORMAT_1_21_1 = 34

WANT = [
    ("Faithful 64x - Release 6.zip",
     "https://cdn.modrinth.com/data/r4GILswZ/versions/BauEG3pq/"
     "Faithful%2064x%20-%20Release%206.zip",
     "the 64x step up from the Faithful 32x already installed"),
    ("Default HD 128x Demo 1.8.2.7.zip",
     "https://cdn.modrinth.com/data/orfTV6nk/versions/rErHu3BE/"
     "Default%20HD%20128x%20Demo%201.8.2.7.zip",
     "vanilla art at 128x - isolates resolution from style. DEMO, so expect gaps"),
    ("Flows HD (1.21) Full.zip",
     "https://cdn.modrinth.com/data/mcD4qf3J/versions/6f9SdIvb/"
     "Flows%20HD%20%281.21%29%20Full.zip",
     "a complete classic HD pack, for a fair high-res comparison"),
]

CLIENT_JAR = os.path.expandvars(
    "%APPDATA%/PrismLauncher/libraries/com/mojang/minecraft/1.21.1"
    "/minecraft-1.21.1-client.jar")
TEXROOT = "assets/minecraft/textures/"
_vanilla = None


def vanilla_textures():
    """Every block and item texture in the 1.21.1 client jar - the real denominator."""
    global _vanilla
    if _vanilla is None:
        z = zipfile.ZipFile(CLIENT_JAR)
        try:
            _vanilla = {n for n in z.namelist()
                        if n.startswith(TEXROOT) and n.endswith(".png")
                        and n[len(TEXROOT):].split("/")[0] in ("block", "item")}
        finally:
            z.close()
    return _vanilla


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def inspect(path):
    """Return (ok, resolution, coverage, pack_format, note)."""
    try:
        z = zipfile.ZipFile(path)
    except Exception as ex:
        return False, None, None, None, "not a valid zip: %s" % ex
    try:
        names = set(z.namelist())
        if "pack.mcmeta" not in names:
            return False, None, None, None, "no pack.mcmeta"

        fmt = None
        try:
            meta = json.loads(z.read("pack.mcmeta").decode("utf-8-sig"))
            fmt = meta.get("pack", {}).get("pack_format")
        except Exception:
            pass

        base = TEXROOT + "block/"
        van = vanilla_textures()
        mine = {n for n in names if n.startswith(TEXROOT) and n.endswith(".png")
                and n[len(TEXROOT):].split("/")[0] in ("block", "item")}
        coverage = len(van & mine) / float(len(van)) if van else None
        extra = len(mine - van)

        res = None
        if Image is not None:
            for probe in ("stone", "dirt", "cobblestone"):
                key = base + probe + ".png"
                if key in names:
                    try:
                        img = Image.open(io.BytesIO(z.read(key)))
                        res = img.size[0]
                        break
                    except Exception:
                        continue
        total_block = sum(1 for n in names if n.startswith(base) and n.endswith(".png"))
        return True, res, coverage, fmt, "%d block tex, %d for a newer MC" % (total_block, extra)
    finally:
        z.close()


def main():
    if not os.path.isdir(DEST):
        print("resourcepacks folder not found: %s" % DEST)
        return 1
    if Image is None:
        print("note: Pillow missing, resolution will not be measured\n")

    results = []
    for name, url, why in WANT:
        final = os.path.join(DEST, name)
        if os.path.exists(final):
            print("already present : %s" % name)
        else:
            tmp = final + ".part"
            print("downloading     : %s" % name)
            try:
                n = fetch(url, tmp)
            except Exception as ex:
                print("   FAILED: %s" % ex)
                if os.path.exists(tmp):
                    os.remove(tmp)
                continue
            ok = inspect(tmp)[0]
            if not ok:
                print("   rejected, not a usable pack; not installed")
                os.remove(tmp)
                continue
            os.replace(tmp, final)
            print("   %.1f MB installed" % (n / 1048576.0))
        results.append((name, why, final))

    print("\nMEASURED  (name is marketing; this is what is actually in the zip)")
    print("%-38s %6s %9s %7s  %s" % ("pack", "res", "coverage", "format", "contents"))
    print("   coverage is against all %d vanilla 1.21.1 block+item textures"
          % len(vanilla_textures()))
    print("-" * 94)
    # include the packs already installed so the comparison is complete
    existing = sorted(f for f in os.listdir(DEST) if f.endswith(".zip"))
    for f in existing:
        ok, res, cov, fmt, note = inspect(os.path.join(DEST, f))
        if not ok:
            print("%-38s  %s" % (f[:38], note))
            continue
        flag = ""
        if cov is not None and cov < 0.85:
            flag = "  <- GAPS, vanilla 16x shows through"
        elif fmt != PACK_FORMAT_1_21_1:
            flag = "  <- format != 34 (cosmetic warning only)"
        print("%-38s %5s %8s %7s  %s%s"
              % (f[:38], ("%dx" % res) if res else "?",
                 "%.0f%%" % (cov * 100) if cov is not None else "?",
                 fmt, note, flag))

    print("\nNOTE ON HIGH RESOLUTION IN THIS PACK")
    print("   These packs retexture VANILLA. The hub loads 247 mods whose thousands of blocks")
    print("   are untouched, so at 64x and above the modded blocks stay 16x right next to a")
    print("   retextured vanilla one - the mismatch gets more obvious the higher you go.")
    print("   Resolution also multiplies atlas and VRAM cost, and the atlas is rebuilt on every")
    print("   pack switch, so it directly lengthens the pause PocketSkins has to take.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
