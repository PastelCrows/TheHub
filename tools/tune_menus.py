# -*- coding: utf-8 -*-
"""Point the loading and splash screens at the brand, and draw the two bar textures they want.

THESE SCHEMAS WERE READ, NOT GUESSED. Both mods write their own config on first launch and both
surprised me:

  SimpleSplashScreen writes `config/simplesplashscreen.json5` - JSON5, not the `.json` an
  earlier guess assumed - with integer colours and a `textures` block of filenames relative to
  `config/simplesplashscreen/`. Its progress bar enum is Vanilla|BossBar|Custom|Logo|Background|
  Hidden; the `SpinningCircle` that Kewz's older CustomSplashScreen uses does not exist here.

  DrippyLoadingScreen writes `config/drippyloadingscreen/options.txt` in its own `T:key = 'v';`
  format and wants absolute-from-instance paths like `/config/fancymenu/assets/...`.

The first launch also said exactly what was missing, in the log:

    Failed to load texture: minecraft:progressbar.png
    Failed to load texture: minecraft:progressbar_background.png
    Failed to load texture: minecraft:mojangstudios

- so the bar textures are drawn here rather than left to 404. The Mojang logo is switched off
instead of replaced; the splash is our own art and a second logo on top of it is clutter.

RUN WITH THE GAME CLOSED. Both files are written by their mods at runtime and a running game
will overwrite anything put here - the same trap as every other config in this pack.
"""
import io
import json
import os
import re
import sys

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
SPLASH = os.path.join(MC, "config", "simplesplashscreen")
FM_ASSETS = os.path.join(MC, "config", "fancymenu", "assets")
DRIPPY = os.path.join(MC, "config", "drippyloadingscreen", "options.txt")

VOID = (10, 7, 15)
PURPLE = (36, 20, 55)
GOLD_DIM = (132, 102, 32)
GOLD = (198, 160, 42)
GOLD_BRIGHT = (242, 205, 122)


def rgb_int(c):
    return (c[0] << 16) | (c[1] << 8) | c[2]


def bar_progress(w=400, h=40):
    """The filled part: gold, brighter along its upper edge like lit metal."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.45:
            c = tuple(int(GOLD_BRIGHT[i] + (GOLD[i] - GOLD_BRIGHT[i]) * (t / 0.45))
                      for i in range(3))
        else:
            c = tuple(int(GOLD[i] + (GOLD_DIM[i] - GOLD[i]) * ((t - 0.45) / 0.55))
                      for i in range(3))
        d.line([(0, y), (w, y)], fill=c + (255,))
    d.rectangle([0, 0, w - 1, h - 1], outline=GOLD_BRIGHT + (170,), width=1)
    return img


def bar_background(w=400, h=40):
    """The empty slot: a dark recess with a gold hairline, so the bar reads as set into stone."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(VOID[i] + (PURPLE[i] - VOID[i]) * t) for i in range(3))
        d.line([(0, y), (w, y)], fill=c + (255,))
    d.rectangle([0, 0, w - 1, h - 1], outline=GOLD_DIM + (200,), width=2)
    return img


def write_splash_config():
    path = os.path.join(MC, "config", "simplesplashscreen.json5")
    if not os.path.exists(path):
        print("SKIP  simplesplashscreen.json5 does not exist yet - launch the game once")
        return False
    raw = io.open(path, encoding="utf-8").read()
    # it is JSON5 with // comments; strip them to read, then rewrite whole
    stripped = re.sub(r"^\s*//.*$", "", raw, flags=re.M)
    cfg = json.loads(stripped)

    cfg["backgroundImage"] = True
    cfg["logoStyle"] = "Hidden"
    cfg["progressBarType"] = "Custom"
    cfg["customProgressBarMode"] = "Linear"
    cfg["customProgressBarBackground"] = True
    cfg["backgroundColor"] = rgb_int(VOID)
    cfg["progressBarColor"] = rgb_int(GOLD)
    cfg["progressFrameColor"] = rgb_int(GOLD_DIM)
    cfg["textures"]["BackgroundTexture"] = "background.png"
    cfg["textures"]["CustomBarTexture"] = "progressbar.png"
    cfg["textures"]["CustomBarBackgroundTexture"] = "progressbar_background.png"

    io.open(path, "w", encoding="utf-8", newline="\n").write(
        json.dumps(cfg, indent=2) + "\n")
    print("OK    simplesplashscreen.json5  background on, logo hidden, custom gold bar")
    return True


def write_drippy_config():
    if not os.path.exists(DRIPPY):
        print("SKIP  drippyloadingscreen/options.txt does not exist yet - launch the game once")
        return False
    raw = io.open(DRIPPY, encoding="utf-8", newline="").read()

    wanted = {
        "early_loading_background_texture_path": "/config/fancymenu/assets/hub_loading.png",
        "early_loading_logo_texture_path": "/config/fancymenu/assets/hub_wordmark.png",
        "early_loading_bar_progress_texture_path":
            "/config/fancymenu/assets/hub_bar_progress.png",
        "early_loading_bar_background_texture_path":
            "/config/fancymenu/assets/hub_bar_background.png",
    }
    changed = 0
    for key, value in wanted.items():
        pattern = re.compile(r"(S:" + re.escape(key) + r"\s*=\s*')[^']*(';)")
        raw, n = pattern.subn(lambda m: m.group(1) + value + m.group(2), raw)
        changed += n
        if n == 0:
            print("      WARNING: key not found, Drippy may have renamed it: " + key)
    # the wordmark is 1600x440; keep its aspect so it is not squashed
    raw = re.sub(r"(I:early_loading_logo_width\s*=\s*')[^']*(';)", r"\g<1>640\g<2>", raw)
    raw = re.sub(r"(I:early_loading_logo_height\s*=\s*')[^']*(';)", r"\g<1>176\g<2>", raw)
    io.open(DRIPPY, "w", encoding="utf-8", newline="").write(raw)
    print("OK    drippyloadingscreen/options.txt  %d paths pointed at the brand" % changed)
    return changed == len(wanted)


def main():
    running = os.popen('tasklist /FI "IMAGENAME eq javaw.exe" 2>NUL').read()
    if "javaw.exe" in running:
        print("REFUSING: Minecraft is running. Both of these files are rewritten by their mods")
        print("at runtime, so anything written now would be silently reverted.")
        return 1

    for folder in (SPLASH, FM_ASSETS):
        os.makedirs(folder, exist_ok=True)

    bar_progress().save(os.path.join(SPLASH, "progressbar.png"))
    bar_background().save(os.path.join(SPLASH, "progressbar_background.png"))
    bar_progress().save(os.path.join(FM_ASSETS, "hub_bar_progress.png"))
    bar_background().save(os.path.join(FM_ASSETS, "hub_bar_background.png"))
    print("OK    4 bar textures written (400x40, gold on a dark recess)")

    ok_splash = write_splash_config()
    ok_drippy = write_drippy_config()

    print("")
    print("The first launch logged exactly the files that were missing:")
    print("    Failed to load texture: minecraft:progressbar.png")
    print("    Failed to load texture: minecraft:progressbar_background.png")
    print("Those are the two this writes. Re-run after any launch that resets them.")
    return 0 if (ok_splash and ok_drippy) else 1


if __name__ == "__main__":
    raise SystemExit(main())
