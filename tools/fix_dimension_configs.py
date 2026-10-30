# -*- coding: utf-8 -*-
"""Find and fix mod settings that name a VANILLA dimension and are therefore dead in the hub.

This is a whole class of silent breakage, found while chasing the Cave Dweller. Dozens of mods
take a dimension allow-list, and they all ship it as ["minecraft:overworld"]. In a normal pack
that is correct. In the hub NOTHING is minecraft:overworld - every pocket dimension is its own
hub:<name>, with hub:<name>_nether and hub:<name>_end beside it - so every one of those settings
matches no dimension the player can ever stand in, and the feature it guards is simply off
everywhere. No error, no log line: Serene Seasons just never changes season, wild waystones
never generate, Mowzie's bosses never spawn, and the Cave Dweller never comes.

The fix is mechanical but needs OWNERSHIP, because a setting should only be widened to the
pocket dimensions whose standalone pack actually had that mod - a horror mob has no business in
skyblock just because the hub happens to load its jar. Ownership is derived the same way
modded_dims.json was: by looking at which standalone instance actually ships the jar, never by
guessing from the name.

Two kinds of setting, and only one is safe to rewrite:

  LIST settings  (dimensions = [...], whitelisted_dimensions = [...]) map cleanly: each vanilla
                 id is replaced by the corresponding id for every owning pocket dimension, so
                 one entry becomes N. These are rewritten.

  SCALAR settings (originDimension = "minecraft:overworld", the Aether portal return) cannot
                 express "whichever pocket dimension the player came from" at all. A single
                 value would hard-wire every pocket dimension to one of them, which is worse
                 than leaving it. These are REPORTED and left alone, because the right answer is
                 PocketWorlds doing it at runtime, not a config edit.

Run with no arguments to see the inventory. Run with --apply to write the list settings, which
backs up every file it touches first.
"""
import io
import json
import os
import re
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
INSTANCES = os.path.join(PRISM, "instances")
HUB_CFG = os.path.join(INSTANCES, "The Hub", "minecraft", "config")

VANILLA = {
    "minecraft:overworld": "",
    "minecraft:the_nether": "_nether",
    "minecraft:the_end": "_end",
}

# standalone instance folder -> pocket dimension name, exactly as the hub names its dimensions
POCKET_OF_INSTANCE = {
    "Skyblock": "skyblock",
    "Survival": "survival",
    "Caveblock": "caveblock",
    "Netherbound": "netherbound",
    "Oceanblock": "oceanblock",
    "Lost Cities": "lostcities",
    "One Chunk": "onechunk",
    "The Gauntlet": "gauntlet",
    "One Block": "oneblock",
    "Horror": "horror",
}
# Kewz's Cobblemon is READ-ONLY and is not a pocket dimension; it is deliberately absent.

# config file -> the mod whose jar decides ownership. Keyed by the config path as it appears
# under config/, because a mod id cannot be recovered from a file name reliably.
CONFIG_MOD = {
    "cave_dweller/server_config.toml": "cave_dweller",
    "sereneseasons/seasons.toml": "sereneseasons",
    "mowziesmobs-common.toml": "mowziesmobs",
    "quark-common.toml": "quark",
    "waystones-common.toml": "waystones",
    "alexsmobs-common.toml": "alexsmobs",
    "twilightforest-common.toml": "twilightforest",
    "aether-server.toml": "aether",
}

# settings whose value is a single dimension id - reported, never rewritten
SCALAR_HINT = re.compile(
    r'^\s*(?:"([^"]+)"|([A-Za-z_][\w.]*))\s*=\s*"(minecraft:(?:overworld|the_nether|the_end))"')
# settings whose value is a list containing dimension ids
LIST_START = re.compile(
    r'^(\s*)(?:"([^"]+)"|([A-Za-z_][\w.]*))\s*=\s*\[(.*)$')

DIM_WORDS = ("dimension", "dimensions", "dims", "world", "level")


def setting_name(m):
    return m.group(2) or m.group(3) or ""


def looks_dimensional(name):
    low = name.lower()
    return any(w in low for w in DIM_WORDS)


def mods_of_instance(inst):
    d = os.path.join(INSTANCES, inst, "minecraft", "mods")
    if not os.path.isdir(d):
        return []
    return [f.lower() for f in os.listdir(d) if f.endswith(".jar")]


def build_ownership():
    """mod key -> sorted list of pocket dimension names whose standalone pack ships it."""
    table = {}
    per_instance = {inst: mods_of_instance(inst) for inst in POCKET_OF_INSTANCE}
    for mod in set(CONFIG_MOD.values()):
        owners = []
        needle = mod.replace("_", "")
        for inst, pocket in POCKET_OF_INSTANCE.items():
            jars = per_instance[inst]
            if any(mod in j or needle in j.replace("_", "").replace("-", "")
                   for j in jars):
                owners.append(pocket)
        table[mod] = sorted(owners)
    return table, per_instance


def hub_ids(owners, suffix):
    return ["hub:%s%s" % (p, suffix) for p in owners]


def is_blacklist(lines, i):
    """Is the dimension list at line i a blacklist rather than a whitelist?

    Quark pairs every dimension list with an "Is Blacklist" flag on the line above, inside a
    [...dimensions] table. If that flag were true, naming the pocket dimensions would EXCLUDE
    the feature from exactly the places it belongs - the precise opposite of the intent - so
    such a setting is left alone and reported instead. Checked per occurrence rather than per
    file, because one file holds dozens of these sections with their own flags.
    """
    for j in range(i - 1, max(-1, i - 4), -1):
        line = lines[j]
        m = re.match(r'\s*"?Is[ _]Blacklist"?\s*=\s*(true|false)', line, re.I)
        if m:
            return m.group(1).lower() == "true"
        if re.match(r"\s*\[", line):
            break                            # reached the table header; no flag above
    # a setting whose own name says blacklist
    name_line = lines[i] if i < len(lines) else ""
    return "blacklist" in name_line.lower()


def scan():
    findings = []
    for root, _dirs, files in os.walk(HUB_CFG):
        for f in files:
            if not f.endswith((".toml", ".json", ".json5", ".cfg", ".properties")):
                continue
            full = os.path.join(root, f)
            rel = os.path.relpath(full, HUB_CFG).replace("\\", "/")
            if rel.startswith(("ftbquests/", "kubejs/")):
                continue
            try:
                lines = io.open(full, encoding="utf-8").read().splitlines()
            except Exception:
                continue

            for i, line in enumerate(lines):
                if line.lstrip().startswith("#"):
                    continue
                if not any(v in line for v in VANILLA):
                    continue

                m = SCALAR_HINT.match(line)
                if m and looks_dimensional(setting_name(m)):
                    findings.append(("scalar", rel, i, setting_name(m), line.strip()))
                    continue

                lm = LIST_START.match(line)
                if lm:
                    name = lm.group(2) or lm.group(3) or ""
                    if looks_dimensional(name):
                        findings.append(("list", rel, i, name, line.strip()))
                    continue

                # a multi-line toml list: walk back to the setting name that opened it
                for j in range(i - 1, max(-1, i - 8), -1):
                    back = LIST_START.match(lines[j])
                    if back:
                        name = back.group(2) or back.group(3) or ""
                        if looks_dimensional(name) and "]" not in lines[j]:
                            findings.append(("list-cont", rel, i, name, line.strip()))
                        break
    return findings


def game_is_running():
    """NeoForge watches its config files and will undo an external edit.

    Learned the hard way: the first --apply run wrote all six files, the verify pass confirmed
    them, and cave_dweller/server_config.toml was back to "minecraft:overworld" moments later.
    The game was open, and NeoForge had rewritten that file from its in-memory copy - server
    configs are bound to the loaded world, so they are the ones it actively keeps in sync.
    The common configs happened to survive, but that is luck, not a rule, so refuse outright.
    """
    try:
        import subprocess as sp
        out = sp.run(["tasklist", "/FI", "IMAGENAME eq javaw.exe"],
                     capture_output=True, text=True, errors="replace").stdout
        return "javaw.exe" in out
    except Exception:
        return False                         # cannot tell -> do not block the user


def main():
    apply = "--apply" in sys.argv
    if apply and game_is_running() and "--force" not in sys.argv:
        print("REFUSING TO WRITE: Minecraft (javaw.exe) is running.\n")
        print("   NeoForge watches these files and will revert the edit from its in-memory copy,")
        print("   silently and after any verification this script could do. Close the game first,")
        print("   then re-run with --apply.  (--force overrides, but the write will not stick.)")
        return 2
    ownership, per_instance = build_ownership()

    print("OWNERSHIP, derived from which standalone pack ships each jar")
    for mod in sorted(ownership):
        own = ownership[mod]
        print("   %-16s %s" % (mod, ", ".join(own) if own else "NO standalone pack ships it"))

    findings = scan()
    print("\nSETTINGS NAMING A VANILLA DIMENSION  (%d)" % len(findings))

    by_file = {}
    for kind, rel, i, name, text in findings:
        by_file.setdefault(rel, []).append((kind, i, name, text))

    actionable, scalars, unknown = [], [], []
    for rel in sorted(by_file):
        mod = CONFIG_MOD.get(rel)
        print("\n   %s   [mod: %s]" % (rel, mod or "UNMAPPED"))
        for kind, i, name, text in by_file[rel]:
            print("      line %-5d %-9s %s" % (i + 1, kind, text[:88]))
            if kind == "scalar":
                scalars.append((rel, i, name))
            elif mod is None:
                unknown.append((rel, i, name))
            else:
                actionable.append((rel, i, name, mod))

    print("\nPLAN")
    print("   list settings rewritable : %d" % len(actionable))
    print("   scalar settings reported : %d  (left alone - PocketWorlds handles these)"
          % len(scalars))
    print("   unmapped config files    : %d  (no ownership known, left alone)" % len(unknown))
    if unknown:
        for rel, i, name in unknown[:10]:
            print("      %s : %s" % (rel, name))

    if not apply:
        print("\n   inventory only. Re-run with --apply to write the list settings.")
        return 0

    # ------------------------------------------------------------ apply
    #
    # LINE-TARGETED, not a file-wide string replace. A blanket replace looked fine until
    # quark-common.toml line 813 turned up:
    #     "Blocks To Replace" = [..., "minecraft:netherrack|minecraft:the_nether", ...]
    # which is a BLOCK list that happens to contain dimension ids as part of compound values.
    # Rewriting those would be nonsense. So only the exact lines the scan identified as
    # dimensional list settings are touched, and each is re-checked for a blacklist flag first.
    print("\nAPPLYING")
    touched, skipped_black = 0, []
    by_line = {}
    for rel, i, name, mod in actionable:
        by_line.setdefault(rel, []).append((i, name, mod))

    for rel in sorted(by_line):
        full = os.path.join(HUB_CFG, rel.replace("/", os.sep))
        lines = io.open(full, encoding="utf-8").read().splitlines(True)
        changed = False

        for i, name, mod in by_line[rel]:
            owners = ownership.get(mod) or []
            if not owners:
                print("   %-34s line %-5d skipped: no owning pocket dimension" % (rel, i + 1))
                continue
            if is_blacklist(lines, i):
                skipped_black.append((rel, i + 1, name))
                continue
            line = lines[i]
            for vanilla, suffix in VANILLA.items():
                token = '"%s"' % vanilla
                if token not in line:
                    continue
                line = line.replace(token, ", ".join('"%s"' % d
                                                     for d in hub_ids(owners, suffix)))
            if line != lines[i]:
                lines[i] = line
                changed = True

        if changed:
            if not os.path.exists(full + ".prehubfix"):
                shutil.copy2(full, full + ".prehubfix")
            io.open(full, "w", encoding="utf-8", newline="").write("".join(lines))
            touched += 1
            print("   %-34s rewritten -> %s" % (rel, ", ".join(ownership[CONFIG_MOD[rel]])))

    if skipped_black:
        print("\n   skipped because the setting is a BLACKLIST (inverting it would be wrong):")
        for rel, ln, name in skipped_black:
            print("      %s line %d  %s" % (rel, ln, name))

    print("\n   files rewritten: %d  (each has a .prehubfix backup beside it)" % touched)

    # ------------------------------------------------------------ verify
    print("\nVERIFY")
    ok = True

    # 1. every touched toml must still parse
    try:
        import tomllib
        for rel in sorted(by_line):
            if not rel.endswith(".toml"):
                continue
            full = os.path.join(HUB_CFG, rel.replace("/", os.sep))
            try:
                tomllib.load(open(full, "rb"))
                print("   parses as valid TOML                 : %s" % rel)
            except Exception as ex:
                print("   PARSE FAILED                         : %s  %s" % (rel, ex))
                ok = False
    except ImportError:
        print("   (tomllib unavailable, skipping parse check)")

    # 2. no actionable vanilla reference may remain
    left = [f for f in scan()
            if f[0] != "scalar" and CONFIG_MOD.get(f[1]) is not None
            and not is_blacklist(
                io.open(os.path.join(HUB_CFG, f[1].replace("/", os.sep)),
                        encoding="utf-8").read().splitlines(True), f[2])]
    print("   actionable vanilla references remaining: %d %s"
          % (len(left), [(f[1], f[2] + 1) for f in left[:4]]))
    ok = ok and not left

    # 3. spot-check the one that started this: the Cave Dweller must now be able to spawn
    cd = io.open(os.path.join(HUB_CFG, "cave_dweller", "server_config.toml"),
                 encoding="utf-8").read()
    cd_ok = "hub:horror" in cd and "minecraft:overworld" not in cd
    print("   cave dweller whitelisted in hub:horror : %s" % cd_ok)
    ok = ok and cd_ok

    # 4. and it must NOT have leaked into a pocket dimension that never had the mod
    leak = [p for p in ("skyblock", "survival", "redstone", "oneblock")
            if ('"hub:%s"' % p) in cd]
    print("   cave dweller absent from non-horror    : %s %s" % (not leak, leak))
    ok = ok and not leak

    print("\n   %s" % ("ALL CHECKS PASSED" if ok else "PROBLEMS FOUND"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
