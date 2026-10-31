# Sharing The Hub

The pack installs and updates itself from this repository. Someone you share it with creates an
empty Prism instance, pastes one pre-launch command into it, and every launch from then on pulls
whatever has changed — the same shape as Kewz's Cobblemon pack, without the 54 MB signed
executable.

## Status: live

The repository is public and every host the installer touches has been checked by hand:

```
pack.toml            (raw.githubusercontent)   HTTP 200
index.toml                                     HTTP 200
a mod metafile                                 HTTP 200
a metafile with spaces in the name             HTTP 200
twilightforest       (release asset)           HTTP 206
pocketquests         (release asset)           HTTP 206
sodium               (Modrinth CDN)            HTTP 206
ftb-quests           (maven.ftb.dev)           HTTP 206
packwiz-installer-bootstrap.jar (GitHub)       HTTP 200
```

Making the repository public also published the commit history, which carries the author's real
email address on every commit - a known and accepted trade, recorded here so it is not a surprise
later. There are no tokens, keys or addresses in the tree; a handful of tool constants and
`config/litematica.json` carry the Windows username.

## What the installer gets

| | |
|---|---|
| 248 mods | Modrinth CDN, resolved by file hash |
| 4 mods | `maven.ftb.dev` — FTB publish their own, no key needed |
| 2 mods | release assets here: `pocketquests` (ours) and Twilight Forest (LGPL-2.1, unmodified, licence and source linked on the release) |
| 3 texture packs | Faithful 64x, Excalibur, JICKLUS — from Modrinth, by hash |
| 5 shaderpacks | BSL, Complementary Reimagined, MakeUp UltraFast, Nostalgia, Spooklementary — from Modrinth, by hash |
| 3453 files | `kubejs/`, `config/`, `defaultconfigs/`, the generated `horror-desaturated` pack, and the shaderpack `.zip.txt` settings that pin motion blur off |

Nothing third-party is redistributed. packwiz hands the client a URL and the client fetches from
source, which is why the texture and shader packs can be in the pack even though 603 MB of them
are deliberately absent from this repository.

## What it does not get

**Worlds.** By design — a new install generates its own hub, seeds its own pocket dimensions and
places its own return portals on first entry.

**The dozen unused texture packs** sitting in the instance from the evaluation pass. Only the
four `pocketskins.json` actually references are in the pack.

## Setting up an instance

1. Prism Launcher → **Add Instance** → Minecraft **1.21.1** → **NeoForge 21.1.265**.
2. Instance → **Edit** → **Settings** → **Custom commands** → tick **Custom commands**.
3. Paste into **Pre-launch command**:

```
"$INST_JAVA" -jar packwiz-installer-bootstrap.jar -s client https://raw.githubusercontent.com/PastelCrows/TheHub/main/pack/pack.toml
```

4. Download `packwiz-installer-bootstrap.jar` into the instance's `.minecraft` folder:
   <https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar>
   — sha256 `A8FBB24DC604278E97F4688E82D3D91A318B98EFC08D5DBFCBCBCAB6443D116C`, 98,989 bytes.
5. Memory: **12 GB**. Set it in the Prism UI, not by editing `instance.cfg` — Prism holds that
   file open and rewrites it on exit.
6. Launch. The first run downloads about 900 MB and takes a while; later launches fetch only
   what changed.

The command deliberately omits `-g`. That flag suppresses the installer's progress window, and
that window is the thing worth having: it is what makes an update visibly an update rather than a
launch that appears to hang. It is also the small box Kewz's pack shows, without the 54 MB
executable behind it.

## Updating the pack

```
python tools/build_packwiz.py --write
git add pack && git commit && git push
```

Every hash in `pack/` is computed from the jars actually installed on this machine, so the pack
always describes a state that really ran. Bump `version` in `tools/build_packwiz.py` when the
change is worth announcing.

`pack/config` and `pack/kubejs` duplicate `instance/config` and `instance/kubejs`. That is the
cost of packwiz needing its own hashed tree at the path it installs to; the generator rewrites
`pack/` from the instance every run, so `instance/` stays the source of truth.
