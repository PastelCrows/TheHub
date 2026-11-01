# -*- coding: utf-8 -*-
"""Check pocketskins.json, and show which portal transits actually cost a texture reload.

Worth having as its own tool because this config gets edited by hand every time a pack is
reassigned, and both failure modes are silent:

  * a pack id that does not match an installed file is skipped with one log line, and the
    dimension quietly renders in whatever was already selected;
  * a dimension that resolves to the wrong skin reloads into textures nobody intended - which
    is exactly what used to happen walking into the horror nether.

Resolution MUST mirror PocketSkins.skinFor(): exact entry, else the entry for that dimension's
POCKET DIMENSION, else "default". A checker that modelled only exact matches would report every
inherited real dimension as broken and train you to ignore it.

The last section is the useful one. A reload only happens when the desired pack SET differs from
what is already selected, so the real cost of a layout is the number of TRANSITIONS that change
it, not the number of packs in it. Two pocket dimensions sharing a pack - or both on vanilla -
switch between each other for free. Travel goes through the hub, so hub-to-pocket is the transit
that matters, and it is paid twice per round trip.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
CFG = os.path.join(MC, "config", "pocketskins.json")

failures = []


def check(label, ok, detail=""):
    print("   %-54s %s%s" % (label, "OK" if ok else "FAIL", "  " + detail if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def main():
    if not os.path.exists(CFG):
        print("pocketskins.json not found")
        return 1

    print("1. config")
    try:
        cfg = json.load(io.open(CFG, encoding="utf-8"))
        check("parses as JSON", True)
    except Exception as ex:
        check("parses as JSON", False, str(ex))
        return 1

    allow = cfg.get("allowResourcePackSwitching")
    delay = cfg.get("switchDelayTicks")
    print("   resource pack switching : %s" % ("ON" if allow else "off"))
    print("   switchDelayTicks        : %s%s"
          % (delay, "  (%.1fs of calm after landing)" % (delay / 20.0)
             if isinstance(delay, int) else ""))
    check("switchDelayTicks is set when switching is on",
          (not allow) or isinstance(delay, int))

    installed_packs = set()
    rp = os.path.join(MC, "resourcepacks")
    if os.path.isdir(rp):
        installed_packs = {"file/" + f for f in os.listdir(rp)}
    installed_shaders = set()
    sp = os.path.join(MC, "shaderpacks")
    if os.path.isdir(sp):
        installed_shaders = set(os.listdir(sp))

    dd = os.path.join(MC, "kubejs", "data", "hub", "dimension")
    real_dims = {"hub:" + f[:-5] for f in os.listdir(dd) if f.endswith(".json")}

    by = cfg.get("byDimension") or {}
    default = cfg.get("default") or {}

    def pocket_of(dim):
        if not dim.startswith("hub:"):
            return None
        name = dim[4:]
        for suffix in ("_nether", "_end"):
            if name.endswith(suffix):
                return "hub:" + name[: -len(suffix)]
        return None

    def skin_for(dim):
        """Mirror of PocketSkins.skinFor: exact, else the pocket dimension, else default."""
        if dim in by:
            return by[dim], "explicit"
        parent = pocket_of(dim)
        if parent and parent in by:
            return by[parent], "inherited from " + parent
        return default, "default"

    def packs_of(dim):
        return tuple(skin_for(dim)[0].get("resourcePacks") or [])

    # ---------------------------------------------------------------- 2. references resolve
    print("\n2. every referenced pack and shader is installed")
    bad_packs, bad_shaders, bad_dims = [], [], []
    for dim, skin in sorted(by.items()):
        if dim not in real_dims:
            bad_dims.append(dim)
        for p in (skin.get("resourcePacks") or []):
            if p not in installed_packs:
                bad_packs.append((dim, p))
        sh = skin.get("shader")
        if sh and sh not in installed_shaders:
            bad_shaders.append((dim, sh))
    if default.get("shader") and default["shader"] not in installed_shaders:
        bad_shaders.append(("default", default["shader"]))
    for p in (default.get("resourcePacks") or []):
        if p not in installed_packs:
            bad_packs.append(("default", p))

    check("all resource pack ids resolve to installed files", not bad_packs)
    for dim, p in bad_packs:
        print("        %-22s %s  -- NOT INSTALLED" % (dim, p))
    check("all shaderpack names resolve to installed files", not bad_shaders)
    for dim, sh in bad_shaders:
        print("        %-22s %s  -- NOT INSTALLED" % (dim, sh))
    check("all configured dimensions exist", not bad_dims)
    for d in bad_dims:
        print("        %s  -- no such dimension" % d)

    # ---------------------------------------------------------------- 3. inheritance is right
    print("\n3. every real dimension keeps its pocket dimension's textures")
    wrong = []
    for d in sorted(real_dims):
        parent = pocket_of(d)
        if parent is None:
            continue
        if packs_of(d) != packs_of(parent):
            wrong.append((d, packs_of(d), parent, packs_of(parent)))
    check("no real dimension drops its pocket's pack", not wrong)
    for d, dp, parent, pp in wrong:
        print("        %-24s %s   but %s uses %s" % (d, list(dp) or "vanilla", parent,
                                                     list(pp) or "vanilla"))
    inherited = sum(1 for d in real_dims if skin_for(d)[1].startswith("inherited"))
    explicit = sum(1 for d in real_dims if skin_for(d)[1] == "explicit")
    print("   %d dimensions: %d explicit, %d inherited, %d on default"
          % (len(real_dims), explicit, inherited, len(real_dims) - explicit - inherited))

    # ---------------------------------------------------------------- 4. transition cost
    print("\n4. what each hub transit costs")
    hub_packs = packs_of("hub:hub")
    pockets = sorted(d for d in real_dims
                     if d != "hub:hub" and pocket_of(d) is None)
    free, paused = [], []
    for d in pockets:
        (free if packs_of(d) == hub_packs else paused).append(d)

    print("   the hub itself uses: %s" % (list(hub_packs) or "vanilla"))
    print("\n   FREE from the hub (same pack set, no reload):")
    for d in free:
        print("        %-22s %s" % (d, list(packs_of(d)) or "vanilla"))
    print("\n   PAUSES on entry AND again on the way back (%d of %d):" % (len(paused), len(pockets)))
    for d in paused:
        print("        %-22s %s" % (d, list(packs_of(d))))
    sets = {packs_of(d) for d in pockets + ["hub:hub"]}
    print("\n   distinct pack sets in play : %d" % len(sets))
    print("   a round trip costs 2 reloads for a paused pocket, 0 for a free one")

    # ---------------------------------------------------------------- 5. shader pairing
    print("\n5. shaders pair 1:1 with texture packs")
    #
    # The invariant: a transit either changes BOTH the pack and the shader, or neither. That is
    # what keeps the cheap transits cheap - a shader change alone would add an Iris recompile to
    # a transit that was previously free. Redstone land is a declared exception, carrying the
    # cheapest shader available because FPS while building beats atmosphere there.
    EXCEPTIONS = {"hub:redstone"}

    def shader_of(dim):
        return skin_for(dim)[0].get("shader")

    pairing = {}
    for d in sorted(real_dims):
        if pocket_of(d) is not None:
            continue                       # real dimensions inherit; judge the pocket
        pairing.setdefault(packs_of(d), set()).add((shader_of(d), d))

    broken = []
    for pack, entries in sorted(pairing.items()):
        shaders = {s for s, d in entries if d not in EXCEPTIONS}
        excepted = sorted(d for s, d in entries if d in EXCEPTIONS)
        label = (list(pack)[0].replace("file/", "") if pack else "vanilla")
        print("   %-34s -> %s%s"
              % (label[:34], ", ".join(sorted(s or "none" for s in shaders)),
                 "   (+%s excepted)" % ", ".join(excepted) if excepted else ""))
        if len(shaders) > 1:
            broken.append((label, sorted(shaders)))
    check("each texture pack maps to exactly one shader", not broken)
    for label, shaders in broken:
        print("        %s has %d shaders: %s" % (label, len(shaders), shaders))

    shaders_used = {shader_of(d) for d in real_dims}
    print("   %d shaderpacks in use: %s"
          % (len(shaders_used), ", ".join(sorted(s or "none" for s in shaders_used))))
    off = sorted(d for d in real_dims if skin_for(d)[0].get("shadersEnabled") is False)
    print("   dimensions with shaders OFF : %s" % (", ".join(off) if off else "none"))

    # Every shader actually in use must ship DH programs. Distant Horizons only renders with
    # shaders "built with DH support in mind" - without them the far terrain simply is not
    # there in that pocket dimension, silently. Nostalgia v5.1 is the one installed pack with
    # no dh_ programs, which is why survival and oceanblock moved to Complementary Unbound.
    # Read out of the zips, not from a list someone wrote down.
    import zipfile as _zip
    packs_dir = os.path.join(MC, "shaderpacks")
    for name in sorted(s for s in shaders_used if s):
        full = os.path.join(packs_dir, name)
        has = False
        if os.path.exists(full):
            with _zip.ZipFile(full) as z:
                has = any(n.split("/")[-1].startswith("dh_") for n in z.namelist())
        check("%-34s ships dh_ programs" % name[:34], has,
              "" if has else "Distant Horizons renders nothing in the pockets using it")

    print("\n%s" % ("ALL CHECKS PASSED" if not failures
                    else "FAILURES: " + ", ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
