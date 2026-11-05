# -*- coding: utf-8 -*-
"""Fix starting chests that hand out one of everything.

THE BUG, AND WHY IT LOOKED LIKE A DESIGN CHOICE. Caveblock's chest was reported as holding a
single oak log and a single ice block, Skyblock and One Chunk as "singular items". The island
templates say otherwise - oak_log x4, ice x2, sand x32, torch x32, dirt x16 - so the quantities
were authored correctly and thrown away at load.

Minecraft 1.20.5 replaced the item-stack NBT key `Count` (a byte) with `count` (an int) as part
of the item-components rewrite. 1.21.1 reads `count`; a stack carrying only `Count` gets the
default of 1. Nothing errors, nothing logs, every stack silently becomes one item. These
templates were authored pre-1.20.5.

CHECKED AGAINST A PRIMARY SOURCE, not recalled: 1.21.1-era structure NBT shipped by mods built
for this version uses `['Slot', 'count', 'id']` - sampled from three AioStructures 4.9.4
structures. Ours used `['Count', 'Slot', 'id']`.

WHAT IT TOUCHES. Every `.nbt` under an instance's `config/skyblockbuilder/templates/`, plus any
other structure NBT given on the command line. Every item stack found anywhere in the tree -
nested shulkers and bundles included - gets `Count` renamed to `count` and written as an Int.
A `.precount` backup is left beside each file it rewrites, matching how the other tools here
behave.

    python fix_stack_counts.py              # report what would change
    python fix_stack_counts.py --apply      # rewrite, leaving .precount backups
"""
import io
import os
import shutil
import sys
import importlib.util

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")

_spec = importlib.util.spec_from_file_location("nbt", os.path.join(HERE, "nbt.py"))
nbt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nbt)


def walk_stacks(node, found):
    """Every item-stack-shaped dict in the tree, however deeply nested.

    Shulker boxes and bundles nest stacks inside stacks, so this cannot just look at a
    container's top-level Items list: a shulker in a starting chest would keep the old key and
    quietly stay at one item.
    """
    if isinstance(node, dict):
        if "id" in node and ("Count" in node or "count" in node):
            found.append(node)
        for v in node.values():
            walk_stacks(v, found)
    elif isinstance(node, list):
        for v in node:
            walk_stacks(v, found)
    return found


# Scanned, never written to: third-party jars are not ours to rewrite, and logs/saves/backups
# are either disposable or already-generated worlds where a template fix cannot help.
SKIP_DIRS = ("mods", "logs", "saves", "crash-reports", "libraries", "resourcepacks",
             "shaderpacks", "texturepacks", "versions", "assets")


def templates():
    """Every structure NBT an instance OWNS, not just the skyblockbuilder ones.

    The first version of this only walked config/skyblockbuilder/templates, which found the four
    standalone islands and missed eight more: The Hub keeps its own copies of the same structures
    under datapacks/hub_worldgen and kubejs/data, and those carried the identical pre-1.20.5 key.
    Fixing the standalones while leaving The Hub broken would have looked like a fix and shipped
    half of one.
    """
    out = []
    if not os.path.isdir(PRISM):
        return out
    for inst in sorted(os.listdir(PRISM)):
        mc = os.path.join(PRISM, inst, "minecraft")
        if not os.path.isdir(mc):
            continue
        for dirpath, dirs, files in os.walk(mc):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f.endswith(".nbt"):
                    out.append((inst, os.path.join(dirpath, f)))
    return out


def main():
    apply_it = "--apply" in sys.argv
    files = templates()
    extra = [a for a in sys.argv[1:] if a.endswith(".nbt") and os.path.exists(a)]
    files += [("<arg>", a) for a in extra]

    if not files:
        print("no skyblockbuilder templates found under " + PRISM)
        return 1

    print("%-14s %-56s %7s %7s" % ("instance", "structure", "stacks", "oldkey"))
    print("-" * 82)
    total_files = total_old = 0
    changed_files = []

    for inst, path in files:
        try:
            root = nbt.load(path)
        except Exception as e:
            print("%-14s %-46s  unreadable: %s" % (inst[:14], os.path.basename(path)[:46], e))
            continue
        stacks = walk_stacks(root, [])
        old = [s for s in stacks if "Count" in s]
        if not stacks:
            continue
        total_files += 1
        total_old += len(old)
        mark = "  <-- FIX" if old else ""
        print("%-14s %-56s %7d %7d%s"
              % (inst[:14], os.path.basename(path)[:56], len(stacks), len(old), mark))
        if old:
            changed_files.append((inst, path, root, old))

    print("-" * 82)
    print("templates with stacks: %d    stacks on the pre-1.20.5 key: %d"
          % (total_files, total_old))

    if not changed_files:
        print("\nnothing to do - every stack already uses the 1.21 'count' key.")
        return 0

    if not apply_it:
        print("\nreport only. re-run with --apply to rewrite (leaves .precount backups).")
        return 0

    print("")
    for inst, path, root, old in changed_files:
        for s in old:
            value = s.pop("Count")
            try:
                n = int(value)
            except Exception:
                n = 1
            s["count"] = nbt.Int(max(1, n))
        backup = path + ".precount"
        if not os.path.exists(backup):
            shutil.copy2(path, backup)
        nbt.save(path, root)
        # read it back and confirm, rather than trusting the write
        check = walk_stacks(nbt.load(path), [])
        bad = [c for c in check if "Count" in c]
        print("   %-14s %-44s %d fixed, %d remaining"
              % (inst[:14], os.path.basename(path)[:44], len(old), len(bad)))
    print("\nbackups: *.precount beside each rewritten template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
