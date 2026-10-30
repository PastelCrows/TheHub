# Session handoff — 2026-10-29

The session that built everything up to `pocketquests-1.13.0` is **permanently stuck**: its
transcript is 32 MB and it now answers every prompt with `Prompt is too long`, including
`/compact` itself. Nothing is lost — the state was recovered from disk and is recorded here.

## Where the old state lives

| What | Path |
|---|---|
| Full transcript (32 MB, 10,712 rows) | `%USERPROFILE%\.claude\projects\C--Users-Fejcr-Desktop-Custom-Games-Minecraft-Skyblock\ce6e2274-042c-4c0d-b48a-391d6df80d33.jsonl` |
| Last compaction summary (the real handoff) | row 10657 of that file |
| Last smoke-test report + full game log | row 10639 → preserved as `tools/_logs/smoke-2026-10-29.log` |

Final state at the break: `pocketquests-1.13.0.jar`, 251 jars, difficulty 7 hard / 3 normal /
2 peaceful, `verify_all.py` 8/8 PASS, pushed to `PastelCrows/TheHub` (`cf46f76`, `963eac3`).

## Open queue — the user's 2026-10-29 smoke test

1. **Hub didn't spawn** on a fresh world; had to be seeded manually.
2. **Motion blur** in the shaderpack is awful — must be **off by default** in every shader config.
3. **Ex Deorum gate leaked in survival**: `exdeorum:oak_sieve` and `exdeorum:string_mesh` both
   crafted despite `pocketrules.json` denying `exdeorum:*` for `hub:survival`.
   *(The mesh goes onto a placed sieve by right-clicking — there is no "combine" recipe, so that
   part is expected behaviour, not a bug.)*
4. Twilight Forest portal round trip — **works**.
5. Horror chat messages outside `hub:horror` — **gone** (gating holds).
6. **Two advancements auto-unlock** (`second chances`, `going up?`) on placing any block, in every
   dimension, on a fresh world.
7. Health-report screenshot was attached to the old session (image, not recoverable as text).

## New evidence from the log

- All five `[pocketquests]` boot lines are present — **no mixin failed silently**:
  `ambience: 2 effects`, `serversidehorror: 23 effect switches`, `modded dimensions: 10
  access-gated, 10 region offsets`, `difficulty: 12 dimensions`, `skins: 12 dimensions`.
- **No `pocketrules` / crafting-rules boot line appears at all** — prime suspect for item 3.
- **Texture-swap duration, measured at last:** `92850 ms`, `80448 ms`, `97930 ms` — 80–98 s per
  reload, not seconds. This is the number `PocketSkins` was built to report.
- A **duplicate reload** fired at 20:32:55 and again at 20:34:34 for the *same* pack set
  (`[vanilla, Faithful 64x]`), costing a second 80 s pause for no change.
- Stack traces originate at `PocketSkins.applyShader` lines 240/249.
