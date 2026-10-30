# Texture packs — the shortlist

Thirteen full-coverage packs are installed in `The Hub/minecraft/resourcepacks/`. I verified
each one is a valid pack with real block coverage; **I cannot judge how any of them look.** That
is what the showcase is for.

## How to browse them

In the hub, run **`/showcase`**. It drops you in redstone land at the gallery.

- **16 swatch rows** running along +z, 10 samples each — 160 blocks total. Row order:
  stone family, deepslate + sculk, logs, planks, ores, metal + mineral, terracotta, concrete,
  wool, glass, ground + foliage, leaves, nether, end + purpur, light sources, utility + redstone.
- **Build scenes** to the east: a house corner with a stepped roof and glass-pane windows, a
  gravel path, a flower garden, an oak tree, and water and lava pools side by side.

The scenes matter as much as the swatches — a pack can have beautiful individual textures and
still read badly in a wall, or look plain in swatches and come alive in a build.

Swap packs in Options → Resource Packs and walk it again. Redstone land is creative, so fly.

## What's installed

Sixteen packs, listed with their measured properties under **Measured, not advertised** below —
that table is the single source of truth. An earlier hand-written table lived here and had drifted
badly wrong (Excalibur recorded as 32x when it is 16x, Ovo's Rustic as 16x when it is 64x, Luna as
32x when it is 64x), which is the whole reason the properties are now read out of the zips by a
script instead of typed in by hand.

The one thing worth keeping from that effort: `pack_format` lies in both directions. Ashen
declares 89 and Excalibur 75, yet both cover 1.21.1 almost completely, while Prime's HD and
Majestica declare the correct 34 and cover 59% and 69%. Judge a pack on coverage, never on its
declared format.

## Not available on 1.21.1

**Stay True** and **John Smith Legacy** have no 1.21.1 release on Modrinth (only an unrelated
models add-on for the latter). Both are classics; neither can be used here.

## The MonkeyFarm pack — unresolved

**I could not confirm which pack MonkeyFarm used.** I'm not going to assert one and have you
install the wrong thing on my word. The plausible candidates from that era of Minecraft YouTube,
and their 1.21.1 status:

- **John Smith Legacy** — no 1.21.1 release
- **Conquest** — installed, and it is the closest living descendant of that John-Smith-ish
  medieval/rustic look
- **Dokucraft** — only a small "pink netherite" variant on Modrinth for 1.21.1, not the base pack
- **Sphax PureBDCraft** — not on Modrinth at all (distributed from its own site)
- **Soartex Grove** — installed; the modern continuation of Soartex Fanver's smooth look

If you can recall roughly what it looked like — medieval/rustic, smooth/clean, or bright and
cartoony — I can narrow it down, or go find the actual pack outside Modrinth.

## Measured, not advertised

`tools/get_texture_packs.py` downloads a pack and then opens it, because a name is marketing and
not a fact. Resolution is read from `block/stone.png`; coverage is the share of **all 1617 vanilla
block and item textures** in the 1.21.1 client jar that the pack actually supplies.

That denominator matters, and getting it wrong cost a decision. The first version of this tool
sampled twenty common block textures and reported **Majestica at 100%** when the true figure is
**69%** — twenty famous textures are exactly the ones every pack does first. A pack was chosen on
the back of that number. Likewise, Ashen was talked down for having `pack_format` 89 and turns out
to be **99%** complete; format tells you what version a pack was authored against, coverage tells
you what you will actually see.

| Pack | Res | Coverage | Format | For a newer MC |
|---|---|---|---|---|
| **Faithful 64x** | 64x | **100%** | **34** | 0 |
| Faithful 32x | 32x | **100%** | **34** | 0 |
| Ashen | 16x | 99% | 89 | 1714 |
| Bare Bones | 16x | 98% | **34** | 12 |
| **Excalibur** | 16x | 97% | 75 | 1463 |
| **JICKLUS** | 16x | 96% | 15 | 318 |
| Conquest | 32x | 93% | **34** | 934 |
| Patrix 32x basic | 32x | 87% | **34** | 2924 |
| Grove | 64x | 86% | 15 | 1290 |
| Flows HD Full | 128x | 85% | 36 | 379 |
| Ovo's Rustic Redemption | 64x | 82% | 46 | 83 |
| Steampunk | 32x | 82% | 999 | 20 |
| Majestica | 32x | **69%** | **34** | 166 |
| Default HD 128x *(demo)* | 128x | **69%** | 15 | 287 |
| Prime's HD | 32x | **59%** | **34** | 998 |
| Luna freepack | 64x | **31%** | 16 | 809 |

Anything much under ~85% shows vanilla 16x through, right beside the retextured blocks. A
mismatched `pack_format` only produces a cosmetic "different version" warning and still loads.

### On going higher than 64x

64x is the ceiling here, by decision. These packs retexture *vanilla*, and the hub loads 247 mods
whose thousands of blocks are untouched, so above 64x a retextured vanilla block sits beside an
untouched 16x modded one and the mismatch only gets louder. Resolution also multiplies atlas and
VRAM cost, and the atlas is rebuilt on **every pack switch** — so it directly lengthens the pause
`PocketSkins` has to take. The 128x packs stay installed to look at, not to use.

## The desaturated pack — two different causes

The horror pack was reported as leaving leaves and amethyst still coloured. Those were two
unrelated problems, and measuring first is what separated them.

**Leaves were never a texture problem.** Vanilla `oak_leaves.png` has a mean saturation of
**0.017** and `spruce_leaves.png` is exactly **0.000** — leaf textures are near-greyscale *masks*
by design. Every bit of their green comes from the biome foliage tint in
`textures/colormap/foliage.png`, which the pack never overrode, so desaturating the textures
(which the original script did do) could not possibly have worked. The fix is a desaturated
colormap. `grass.png` got the same treatment unasked: grass, vines and sugar cane share the
mechanism, and green grass beside grey leaves would read as a bug.

The colormaps get **saturation reduction only, no darkening**. The tint is *multiplied* onto a
texture the transform has already darkened, so darkening the tint too would leave those blocks
noticeably darker than everything else rather than equally grey.

**Amethyst was genuinely skipped** — 0.499 vanilla, 0.499 in the pack, exactly like glowstone at
0.557. The original script preserved light sources, and amethyst clusters and buds emit light, so
the rule caught them. Overridden for the amethyst family only; other light sources keep their
colour, which is still asserted.

The original generator was never kept, so `tools/build_desaturated_pack.py` starts by
**recovering** it: it pairs pack pixels with their vanilla originals and grid-searches the
constants, landing on saturation **x0.25**, brightness **x0.75**, contrast **x1.05** at an RMSE of
3.7/255. New textures go through the recovered transform, so nothing looks subtly different from
the pack already in use.

## Current assignment - four packs, five shaders, nothing on vanilla

Shaders apply instantly; textures are deferred until you have landed (see the README). Every pack
here is >=96% coverage, and the hub carries Faithful 64x because it is the most widely shared,
which makes the most transits free.

**Shaders pair 1:1 with the texture packs.** That is not only aesthetic: it means a transit
changes *both* or *neither*, so no transit becomes slow that was not already slow, and the five
free ones stay free. A shader change on its own would have added an Iris recompile to a transit
that previously cost nothing.

| Texture pack | Shader | Perf tag | Pairing |
|---|---|---|---|
| Faithful 64x | Complementary Reimagined | untagged | vanilla-like lighting for vanilla-accurate art |
| Excalibur | BSL | **low** | warm and contrasty - medieval stone, nether fire |
| JICKLUS | Nostalgia | **medium** | warm vanilla-like fantasy, same palette as the textures |
| horror-desaturated | Spooklementary | untagged | purpose-built horror, Complementary-derived |
| *(Faithful 64x)* | MakeUp Ultra Fast | **potato** | redstone land only - see below |

Perf tags are Modrinth's own categories, not a guess. Nothing here is heavier than what was
already running everywhere (Complementary Reimagined), and two of the five are explicitly
lighter - so the spread costs nothing relative to before.

| Pocket dimension | Texture pack | Shader | Why |
|---|---|---|---|
| the hub | Faithful 64x | Reimagined | neutral lobby, and the shared baseline |
| Skyblock | Faithful 64x | Reimagined | the premise is plain vanilla blocks |
| One Chunk | Faithful 64x | Reimagined | same |
| One Block | Faithful 64x | Reimagined | same |
| Lost Cities | Faithful 64x | Reimagined | vanilla concrete and terracotta *are* the city |
| Redstone | Faithful 64x | **MakeUp Ultra Fast** | FPS while building beats atmosphere |
| Caveblock | Excalibur | BSL | carved medieval stonework |
| Netherbound | Excalibur | BSL | fire and fantasy |
| The Gauntlet | Excalibur | BSL | arms and the arena |
| Survival | JICKLUS | Nostalgia | warm, rustic, lived-in |
| Oceanblock | JICKLUS | Nostalgia | hand-painted sand and wood |
| Horror | horror-desaturated | Spooklementary | horror-exclusive, by standing decision |

Redstone land is the one declared exception to the 1:1 rule: same Faithful textures as the hub,
but the cheapest shader available, because large contraptions are where frames actually matter.
`tools/verify_skins.py` knows about that exception and still asserts the rule everywhere else.

Each pocket's nether and end inherit its pack and shader automatically; they need an entry only
to differ deliberately. Five of eleven transits are free, six pause.

**Liked but unassigned:** Conquest (93%, 32x, correct format) is the strongest reserve if any of
the four disappoints. Ovo's Rustic Redemption was liked for its flowing water specifically but
measures 82%. Ashen at 99% remains the best-covering pack not in use.

### A note on judging shaderpacks

`tools/get_shaderpacks.py` opens each zip and counts `.fsh`/`.vsh`/`.glsl` programs, because a
shaderpack and a shaderpack *addon* are indistinguishable from the outside and an addon renders
wrong without its base pack. Spooklementary is 0.5 MB against Nostalgia's 1.8 MB, which looked
exactly like an addon - it is not, it ships 379 programs and GLSL text simply compresses well.
Worth checking rather than assuming; file size is not evidence.
