# hubworldgenfix — built, NOT installed

This mod compiles and verifies, and it is deliberately **not** in the instance.

## What it does

Replaces jigsaw `pool` identifiers that are not valid resource locations with `minecraft:empty`,
at HEAD of `StructureTemplate.load`. Port of the generic half of Kewz's `kewz-worldgen-compat`.

## What is established

Scanning all **1,928 structure `.nbt` files across 303 jars**, four carry the pool literally
`"minecraft:"` — a namespace with an empty path, which `ResourceLocation.tryParse` rejects:

```
legendarymonuments:traditional_village/pagoda/burned_tower_2.nbt
legendarymonuments:traditional_village/pagoda/burned_tower_3.nbt
legendarymonuments:traditional_village/pagoda/burned_tower_4.nbt
legendarymonuments:turnback_cave/connectors/connector.nbt
```

His other remap, `bca:feature/berries` → `bca:general/berries`, is **not** implemented: the BCA
mod is not in this pack, and a remap for a mod nobody runs is dead code pretending to be a fix.

## What is NOT established, and why it is shelved

**No failure could be reproduced from those four files.** On the headless test server, with
Legendary Monuments installed and this mod absent:

```
/place template legendarymonuments:traditional_village/pagoda/burned_tower_4
   -> Loaded template "...burned_tower_4" at 0, -60, 0      (no error)
/place template legendarymonuments:turnback_cave/connectors/connector
   -> Loaded template "...connector" at 20, -60, 0          (no error)
```

The reason is structural: `StructureTemplate.load` keeps block-entity NBT as an opaque
`CompoundTag`. The `pool` string is only parsed into a `ResourceLocation` later, during jigsaw
assembly. So the malformation is real but inert on the path that was exercised.

A follow-up run tried `/place structure` and `/place jigsaw` to reach the assembly path and
produced no command output at all — console stdin delivery to the server is not reliable enough
yet in `tools/test_server.py` to call that a negative result either. It is simply untested.

## Verdict

**Not needed, on the evidence.** The malformation is real in four files and completely inert
across every path that could be exercised: template load and full jigsaw assembly. This is a fix
for a bug that does not reproduce in this pack, so it stays out of the instance.

It is kept, built and documented rather than deleted because the four bad files are still there:
if a region structure ever fails to place with an invalid-identifier error, this is already
written and one `python tools/build_mod.py hubworldgenfix` away. A mixin on vanilla's structure loader that fixes
nothing observable is a liability, not insurance — the TM filter was installed precisely because
its effect WAS demonstrated (17 of 704, matching the static prediction exactly).
