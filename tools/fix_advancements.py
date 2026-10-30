# -*- coding: utf-8 -*-
"""Repair mod advancements that use the pre-1.20.2 `placed_block` condition shape.

THE BUG, as it was reported: "no matter what dimension i'm in i unlock 2 advancements the second
i place literally anything on a fresh world, `second chances` and `going up?`".

Both belong to Cyclic, and both are supposed to fire only when you place one specific block:

    data/cyclic/advancement/automation/launch_hidden.json      cyclic:plate_launch
    data/cyclic/advancement/enchanting/disenchanter_hidden.json cyclic:disenchanter

They ship the old shape, where `location` is an OBJECT holding a block predicate:

    "conditions": { "location": { "block": { "blocks": ["cyclic:plate_launch"] } } }

Since 1.20.2 the trigger is ItemUsedOnLocationTrigger and `location` is a LIST of loot
conditions. The field is read with a lenient optional codec, so an object does not raise a
datapack error - it parses to "no value", and a `placed_block` criterion with no conditions
matches EVERY block placement. Hence two hidden advancements popping on the first block of a
fresh world, in every dimension, with `announce_to_chat` on.

The correct 1.21.1 shape, taken from vanilla's own plant_any_sniffer_seed:

    "conditions": { "location": [ { "condition": "minecraft:block_state_property",
                                    "block": "cyclic:plate_launch" } ] }

The whole mods folder is scanned, not just Cyclic, because the failure is silent by nature and
any mod can carry it. At the time of writing 42 criteria across the pack use the correct list
form and exactly these 2 use the broken object form.

Repairs are written as KubeJS data overrides (kubejs/data/<ns>/advancement/...), which load after
mod data packs and so win, and which live in the instance rather than inside a jar - so a Cyclic
update does not quietly restore the bug. If a future Cyclic fixes it upstream, re-running this
reports nothing to fix and the override can be deleted.

Only single-block predicates are converted automatically. A predicate naming several blocks or a
tag cannot become a block_state_property and is reported instead of being guessed at.
"""
import io
import json
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
MODS = os.path.join(MC, "mods")
OVERRIDES = os.path.join(MC, "kubejs", "data")


def single_block(location):
    """The one block id this old-style location predicate names, or None."""
    if not isinstance(location, dict):
        return None
    block = location.get("block")
    if not isinstance(block, dict):
        return None
    if set(block) - {"blocks"}:
        return None                      # state/nbt/tag - not a plain block check
    blocks = block.get("blocks")
    if isinstance(blocks, str):
        return blocks
    if isinstance(blocks, list) and len(blocks) == 1:
        return blocks[0]
    return None


def scan():
    """(jar, entry path, parsed json, [(criterion, block id)]) for every repairable advancement."""
    found = []
    for name in sorted(os.listdir(MODS)):
        if not name.endswith(".jar"):
            continue
        try:
            z = zipfile.ZipFile(os.path.join(MODS, name))
        except Exception:
            continue
        with z:
            for entry in z.namelist():
                if "/advancement" not in entry or not entry.endswith(".json"):
                    continue
                try:
                    data = json.loads(z.read(entry).decode("utf-8", "replace"))
                except Exception:
                    continue
                if not isinstance(data, dict):
                    continue
                broken = []
                for crit_name, crit in (data.get("criteria") or {}).items():
                    if not isinstance(crit, dict):
                        continue
                    if crit.get("trigger") != "minecraft:placed_block":
                        continue
                    location = (crit.get("conditions") or {}).get("location")
                    if isinstance(location, dict):
                        broken.append((crit_name, single_block(location)))
                if broken:
                    found.append((name, entry, data, broken))
    return found


def main():
    if not os.path.isdir(MODS):
        print("mods folder not found: " + MODS)
        return 1

    found = scan()
    if not found:
        print("No advancement uses the broken object-form `location`. Nothing to do.")
        print("(If overrides exist under kubejs/data from an earlier run, they are now redundant.)")
        return 0

    written = 0
    skipped = []
    for jar, entry, data, broken in found:
        # data/<ns>/advancement/<path>.json -> kubejs/data/<ns>/advancement/<path>.json
        parts = entry.split("/")
        if parts[0] != "data":
            skipped.append(entry + " (unexpected path)")
            continue

        unconvertible = [c for c, b in broken if b is None]
        if unconvertible:
            skipped.append(entry + " (criteria " + ", ".join(unconvertible)
                           + " name several blocks or a tag - convert by hand)")
            continue

        for crit_name, block_id in broken:
            data["criteria"][crit_name]["conditions"]["location"] = [{
                "condition": "minecraft:block_state_property",
                "block": block_id,
            }]

        out = os.path.join(OVERRIDES, *parts[1:])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, "w", encoding="utf-8", newline="\n").write(
            json.dumps(data, indent=2) + chr(10))
        written += 1
        print("FIXED    " + jar)
        print("         " + entry)
        for crit_name, block_id in broken:
            print("         " + crit_name + " -> fires only on " + block_id)

    for s in skipped:
        print("SKIPPED  " + s)

    print("")
    print("Wrote " + str(written) + " override(s) under kubejs/data.")
    print("These are datapack files: they apply on world load, so they take effect on the next")
    print("launch. An advancement already granted stays granted - /advancement revoke <player>")
    print("only cyclic:automation/launch_hidden and cyclic:enchanting/disenchanter_hidden on an")
    print("existing world, or just start the fresh world the smoke test uses anyway.")
    return 1 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
