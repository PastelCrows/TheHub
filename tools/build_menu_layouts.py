# -*- coding: utf-8 -*-
"""Author FancyMenu's title-screen layout directly, instead of clicking it together in-game.

FancyMenu layouts are plain text with a documented-by-example structure: a `layout-meta` block,
`customization` blocks for screen-wide actions, one `menu_background` block, and an `element`
block per thing on screen. The key sets below were read out of a WORKING layout -
Kewz's Cobblemon `cobbleverse_main.txt` - rather than invented, because an unknown key is
silently ignored and the result looks like the file did not load at all.

Only constructs observed working are used here: `menu_background` with an image, and `element`
blocks of `element_type = image`. Text is deliberately NOT a FancyMenu `text` element - the
wordmark is rendered to a PNG by build_brand_assets.py, which buys real letterspacing, a gold
gradient fill and a drop shadow that Minecraft's bitmap font cannot do, and keeps this file to
the one element type whose serialization is confirmed.

The design: the hall itself as the backdrop - twelve gothic arches, ELEVEN lit and one sealed,
the same split as the real lobby (One Block and Horror have been live for a long time) - with the wordmark set high so the vanilla button column lands in the
clear middle band and the arcade reads along the bottom. Deep purple and warm gold throughout,
per the user's stated sensibility.

IDENTIFIERS. FancyMenu keys elements by a `<uuid>-<millis>` instance identifier and expects each
element's loading-requirement container to be declared alongside it. They are generated here and
written consistently; regenerating the file regenerates them, which is harmless because nothing
else refers to them.

    python build_menu_layouts.py            # write to tools/_brand/ for inspection
    python build_menu_layouts.py --apply    # install into the instance
"""
import io
import os
import sys
import time
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_brand")
MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
ASSETS = "[source:local]/config/fancymenu/assets"

NOW = int(time.time() * 1000)


def ident():
    return "%s-%d" % (uuid.uuid4(), NOW)


def image_element(source, anchor, x, y, w, h, opacity="1.0"):
    """One image element, with the full key set FancyMenu writes for its own.

    Every key here appears in the reference layout. Omitting keys it expects is the failure mode
    that looks like nothing happened, so the set is kept complete rather than minimal.
    """
    eid = ident()
    rid = ident()
    return """
element {
  source = %s
  repeat_texture = false
  nine_slice_texture = false
  nine_slice_texture_border_x = 5
  nine_slice_texture_border_y = 5
  image_tint = #FFFFFF
  restart_animated_on_menu_load = false
  element_type = image
  instance_identifier = %s
  appearance_delay = no_delay
  appearance_delay_seconds = 1.0
  fade_in_v2 = no_fading
  fade_in_speed = 1.0
  fade_out = no_fading
  fade_out_speed = 1.0
  base_opacity = %s
  auto_sizing = false
  auto_sizing_base_screen_width = 1920
  auto_sizing_base_screen_height = 1080
  sticky_anchor = false
  anchor_point = %s
  x = %d
  y = %d
  width = %d
  height = %d
  stretch_x = false
  stretch_y = false
  stay_on_screen = true
  element_loading_requirement_container_identifier = %s
  [loading_requirement_container_meta:%s] = [groups:][instances:]
  enable_parallax = false
  parallax_intensity_v2 = 0.5
  invert_parallax = false
  animated_offset_x = 0
  animated_offset_y = 0
  load_once_per_session = false
  in_editor_color = #FFC800FF
  layer_hidden_in_editor = false
  rotation_degrees = 0.0
  advanced_rotation_mode = false
  vertical_tilt_degrees = 0.0
  advanced_vertical_tilt_mode = false
  horizontal_tilt_degrees = 0.0
  advanced_horizontal_tilt_mode = false
}
""" % (source, eid, opacity, anchor, x, y, w, h, rid, rid)


def title_layout():
    rid = ident()
    bid = ident()

    # The wordmark is 1600x440 (3.64:1). At 640 wide it clears the vanilla button column
    # entirely and still reads at 1280x720, the smallest window worth designing for.
    wm_w, wm_h = 640, 176

    return """type = fancymenu_layout

layout-meta {
  identifier = title_screen
  render_custom_elements_behind_vanilla = true
  last_edited_time = %d
  is_enabled = true
  randommode = false
  randomgroup = 1
  randomonlyfirsttime = false
  layout_index = 0
  [loading_requirement_container_meta:%s] = [groups:][instances:]
}

customization {
  action = autoscale
  basewidth = 1920
  baseheight = 1080
}

menu_background {
  image_path = %s/hub_title_background.png
  slide = false
  repeat_texture = false
  parallax = false
  parallax_intensity = 0.02
  invert_parallax = false
  restart_animated_on_menu_load = false
  instance_identifier = %s
  background_type = image
}

customization {
  action = backgroundoptions
  keepaspectratio = true
}
%s""" % (NOW, rid, ASSETS, bid,
         image_element(ASSETS + "/hub_wordmark.png", "top-centered",
                       -(wm_w // 2), 54, wm_w, wm_h))


def main():
    apply = "--apply" in sys.argv
    os.makedirs(OUT, exist_ok=True)

    files = {"hub_title.txt": title_layout()}

    for name, body in files.items():
        path = os.path.join(OUT, name)
        io.open(path, "w", encoding="utf-8", newline="\n").write(body)
        print("wrote  %-22s %d lines" % (name, body.count(chr(10)) + 1))

    if not apply:
        print("")
        print("Re-run with --apply to install into config/fancymenu/customization/.")
        return 0

    dest = os.path.join(MC, "config", "fancymenu", "customization")
    os.makedirs(dest, exist_ok=True)
    for name, body in files.items():
        io.open(os.path.join(dest, name), "w", encoding="utf-8", newline="\n").write(body)
        print("installed " + name + "  ->  <instance>/config/fancymenu/customization/")

    missing = [n for n in ("hub_title_background.png", "hub_wordmark.png")
               if not os.path.exists(os.path.join(MC, "config", "fancymenu", "assets", n))]
    if missing:
        print("")
        print("MISSING ASSETS - the layout will load but render nothing: " + ", ".join(missing))
        print("Run build_brand_assets.py --apply first.")
        return 1
    print("")
    print("Assets present. FancyMenu reads this on launch; its in-game editor can then be used")
    print("to nudge anything without touching this file - but re-running this script overwrites")
    print("what the editor saved, so pick one source of truth once the design settles.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
