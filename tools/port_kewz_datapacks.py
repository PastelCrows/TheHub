# -*- coding: utf-8 -*-
"""Port Kewz's 27 custom datapacks from Fabric to NeoForge.

READ-ONLY on his instance. Reads his datapacks, writes new zips into ours.

WHY THIS IS THE CHEAP HALF. His custom work splits in two. The ~90 jars are recompiles and
original mods: real porting work, one at a time. The 27 datapacks are pure DATA - species JSON,
spawn pools, loot tables, recipes, worldgen - and data does not care which loader reads it.
Measured: 22 of the 27 contain no loader-specific syntax at all and copy across untouched. The
other 5 differ only in how they express "load this file only if...", and that difference is a
mechanical rename.

THE MAPPING WAS NOT REMEMBERED, IT WAS READ OFF SHIPPED FILES. Every shape below was taken from
a jar already installed in our instance, because guessing datapack syntax is exactly the kind of
thing that fails silently - a wrong condition key is not an error, it is a file that quietly
never loads. Carved Wood settles the question on its own: it ships BOTH spellings side by side
in the same recipe, which is as close to a spec as a jar can get.

    fabric:load_conditions                      ->  neoforge:conditions
    "condition": X                              ->  "type": X
    fabric:all_mods_loaded  values: [a]         ->  neoforge:mod_loaded  modid: a
    fabric:all_mods_loaded  values: [a, b]      ->  neoforge:and  values: [mod_loaded, ...]
    fabric:any_mods_loaded  values: [a, b]      ->  neoforge:or   values: [mod_loaded, ...]
    fabric:not  value: {...}                    ->  neoforge:not  value: {...}
    fabric:remove  (inside a tag file)          ->  remove

Sources, all in %APPDATA%\\PrismLauncher\\instances\\Cobblemon NeoForge\\minecraft\\mods:
    neoforge:conditions / mod_loaded   Cobblemon-neoforge-1.8.4, 3648 / 1558 occurrences
    neoforge:not                       applewoodrebarked-neoforge-1.2.2
    neoforge:and                       Cobblemon-neoforge-1.8.4 (create/farmersdelight compat)
    neoforge:or                        chipped-neoforge-1.21.1-4.0.2
    neoforge:false                     Cobblemon-neoforge-1.8.4 (apple_cider_fabric.json)
    remove inside a tag                FarmersDelight-1.21.1-1.3.4, supplementaries-4.0.2
    both spellings in one file         Carved Wood-neoforge-1.21.1-1.9.8-B

THE SENTINEL TRICK, AND WHY IT IS KEPT AS-IS. Several of his packs disable a recipe or loot
table by requiring a mod that does not exist and never will:

    {"condition": "fabric:all_mods_loaded", "values": ["kewz_log_fix_disabled_marker"]}

NeoForge ships `neoforge:false` for precisely this, and it is tidier. It is NOT substituted here.
The faithful translation of "require a mod that is absent" is "require a mod that is absent", and
collapsing it to `false` would discard his intent: the sentinel name says WHY the file is off
(`kewz_pokedolls_are_found_not_crafted`), and a future datapack could define that marker to turn
the behaviour back on. Rewriting it to `false` would make that impossible and lose the sentence.
Sentinels are reported so the choice stays visible.

    python port_kewz_datapacks.py            # report what would change, write nothing
    python port_kewz_datapacks.py --apply    # write ported zips into our instance
"""
import io
import json
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")
HIS = os.path.join(PRISM, "Kewz's Cobblemon", "minecraft", "datapacks")
OURS = os.path.join(PRISM, "Cobblemon NeoForge", "minecraft", "datapacks")

# A mod id is a sentinel if nothing could ever provide it. These are his, by name.
SENTINEL_HINTS = ("kewz_", "_disabled", "_marker", "are_found_not_crafted")


def is_sentinel(modid):
    low = modid.lower()
    return any(h in low for h in SENTINEL_HINTS)


def mod_loaded(modid):
    return {"type": "neoforge:mod_loaded", "modid": modid}


def convert_condition(c, stats):
    """One fabric condition object -> one neoforge condition object."""
    if not isinstance(c, dict):
        return c
    kind = c.get("condition")
    if kind is None:
        return c

    if kind in ("fabric:all_mods_loaded", "fabric:any_mods_loaded"):
        vals = c.get("values") or ([c["value"]] if "value" in c else [])
        for v in vals:
            if isinstance(v, str) and is_sentinel(v):
                stats.setdefault("sentinels", set()).add(v)
        inner = [mod_loaded(v) for v in vals if isinstance(v, str)]
        if len(inner) == 1:
            stats["mod_loaded"] = stats.get("mod_loaded", 0) + 1
            return inner[0]
        joiner = "neoforge:and" if kind.endswith("all_mods_loaded") else "neoforge:or"
        stats[joiner] = stats.get(joiner, 0) + 1
        return {"type": joiner, "values": inner}

    if kind == "fabric:not":
        stats["not"] = stats.get("not", 0) + 1
        return {"type": "neoforge:not",
                "value": convert_condition(c.get("value", {}), stats)}

    if kind in ("fabric:and", "fabric:or"):
        j = "neoforge:and" if kind.endswith("and") else "neoforge:or"
        stats[j] = stats.get(j, 0) + 1
        return {"type": j,
                "values": [convert_condition(v, stats) for v in c.get("values", [])]}

    # An unrecognised fabric condition must NOT be silently passed through - a condition
    # neoforge cannot parse makes the whole file fail to load. Report it and keep the file
    # unported so it is dealt with deliberately.
    stats.setdefault("unknown", set()).add(kind)
    return None


def convert_doc(doc, is_tag, stats):
    """Returns (new_doc, changed)."""
    if not isinstance(doc, dict):
        return doc, False
    changed = False

    if "fabric:load_conditions" in doc:
        out = []
        for c in doc["fabric:load_conditions"]:
            nc = convert_condition(c, stats)
            if nc is None:
                return doc, False          # unknown condition: leave the file alone
            out.append(nc)
        doc = dict(doc)
        doc.pop("fabric:load_conditions")
        doc["neoforge:conditions"] = out
        changed = True

    if is_tag and "fabric:remove" in doc:
        doc = dict(doc)
        doc["remove"] = doc.pop("fabric:remove")
        stats["tag_remove"] = stats.get("tag_remove", 0) + 1
        changed = True

    return doc, changed


def port(src_zip, dst_zip, apply_it):
    stats, touched = {}, 0
    zin = zipfile.ZipFile(src_zip)
    buf = io.BytesIO()
    zout = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)
    for info in zin.infolist():
        if info.filename.endswith("/"):
            continue
        data = zin.read(info.filename)
        if info.filename.endswith(".json") and b"fabric:" in data:
            try:
                doc = json.loads(data.decode("utf-8"))
            except Exception:
                zout.writestr(info.filename, data)
                continue
            is_tag = "/tags/" in info.filename
            new, changed = convert_doc(doc, is_tag, stats)
            if changed:
                data = json.dumps(new, indent=2).encode("utf-8")
                touched += 1
        zout.writestr(info.filename, data)
    zout.close()
    zin.close()
    if apply_it:
        with open(dst_zip, "wb") as f:
            f.write(buf.getvalue())
    return touched, stats


def main():
    apply_it = "--apply" in sys.argv
    if not os.path.isdir(HIS):
        print("his datapacks folder not found: " + HIS)
        return 1
    if apply_it:
        os.makedirs(OURS, exist_ok=True)

    packs = sorted(f for f in os.listdir(HIS)
                   if f.endswith(".zip") and f.startswith("kewz-"))
    print("his kewz- datapacks: %d" % len(packs))
    print("%-44s %6s %7s  %s" % ("datapack", "files", "ported", "conversions"))
    print("-" * 96)

    total_files = total_touched = 0
    all_sent, all_unknown, blocked = set(), set(), []
    for f in packs:
        src = os.path.join(HIS, f)
        dst = os.path.join(OURS, f)
        n_files = sum(1 for i in zipfile.ZipFile(src).infolist()
                      if not i.filename.endswith("/"))
        touched, stats = port(src, dst, apply_it)
        sent = stats.pop("sentinels", set())
        unk = stats.pop("unknown", set())
        all_sent |= sent
        all_unknown |= unk
        if unk:
            blocked.append((f, unk))
        total_files += n_files
        total_touched += touched
        note = ", ".join("%s=%s" % (k, v) for k, v in sorted(stats.items())) or "-"
        if unk:
            note = "UNKNOWN: " + ", ".join(sorted(unk))
        print("%-44s %6d %7d  %s" % (f[:44], n_files, touched, note))

    print("-" * 96)
    print("%-44s %6d %7d" % ("TOTAL", total_files, total_touched))
    print("")
    if all_sent:
        print("Sentinel mod ids he uses to switch a file OFF (kept verbatim, not collapsed to")
        print("neoforge:false - the name is the reason, and a datapack could define it later):")
        for s in sorted(all_sent):
            print("   " + s)
    if blocked:
        print("")
        print("NOT PORTED - unrecognised fabric conditions, left alone on purpose:")
        for f, unk in blocked:
            print("   %-44s %s" % (f[:44], ", ".join(sorted(unk))))
    print("")
    if apply_it:
        print("written to: " + OURS)
    else:
        print("report only. re-run with --apply to write the ported zips.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
