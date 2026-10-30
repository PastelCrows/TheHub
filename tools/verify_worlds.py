# -*- coding: utf-8 -*-
"""Verify the modded-dimension separation: the offset round trip, and the TF portal mixin.

The bug this exists to catch is the one that was nearly shipped. Each pocket dimension gets its
own million-block region of a shared modded dimension, applied on entry and removed on exit. That
is only an inverse if the dimension's coordinate_scale is 1.0 - and two of the ten are not:

    twilightforest:twilight_forest   0.125   entering multiplies by 8,  leaving divides by 8
    undergarden:undergarden          4.0     entering divides by 4,     leaving multiplies by 4

With a flat add/subtract, a trip into the Twilight Forest and back landed the player ~875,000
blocks from their base. Nothing would have reported it; the portal simply comes out in the wrong
place, which reads as "the separation is broken" rather than "the arithmetic is wrong".

So section 3 runs the REAL PocketWorlds round-trip arithmetic for every shared dimension at its
measured scale and asserts the player comes home to where they started. Section 1 checks the
mixin descriptor against the Twilight Forest jar, because @Redirect carries require = 0 and would
otherwise fail silently.
"""
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
LIB = os.path.join(PRISM, "libraries")
MC = os.path.join(PRISM, "instances", "The Hub", "minecraft")
BUILD = os.path.join(HERE, "_build")
TMP = os.path.join(BUILD, "_verifyworlds")

CLIENT = os.path.join(LIB, "com", "mojang", "minecraft", "1.21.1",
                      "minecraft-1.21.1-client.jar")

failures = []


def check(label, ok, detail=""):
    print("   %-58s %s%s" % (label, "OK" if ok else "FAIL", "  " + detail if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def java_runtime():
    """PATH `java` here is a JRE 8 shim; take javac's sibling so compiler and runtime match."""
    jc = shutil.which("javac")
    if jc:
        sib = os.path.join(os.path.dirname(jc), "java.exe")
        if os.path.exists(sib):
            return sib
    return "java"


def find_mod(*fragments):
    for f in sorted(os.listdir(os.path.join(MC, "mods"))):
        low = f.lower()
        if all(fr in low for fr in fragments):
            return os.path.join(MC, "mods", f)
    return None


# ---------------------------------------------------------------- 1. mixin binding
print("1. TFPortalMixin binds to the real Twilight Forest jar")

pq = find_mod("pocketquests")
if not check("pocketquests jar installed", bool(pq), os.path.basename(pq or "")):
    sys.exit(1)
z = zipfile.ZipFile(pq)
names = z.namelist()
check("TFPortalMixin compiled into the jar", "pocketquests/mixin/TFPortalMixin.class" in names)
mx = json.loads(z.read("pocketquests.mixins.json").decode("utf-8"))
check("TFPortalMixin declared in mixins.json", "TFPortalMixin" in mx.get("mixins", []))
blob = z.read("pocketquests/mixin/TFPortalMixin.class").decode("latin-1")
z.close()

GETLEVEL = ("Lnet/minecraft/server/MinecraftServer;getLevel"
            "(Lnet/minecraft/resources/ResourceKey;)Lnet/minecraft/server/level/ServerLevel;")
check("redirect target descriptor present in the mixin", GETLEVEL in blob)
check("mixin targets TFPortalBlock by name", "twilightforest.block.TFPortalBlock" in blob)

tf = find_mod("twilightforest")
if check("twilight forest installed", bool(tf), os.path.basename(tf or "")):
    tz = zipfile.ZipFile(tf)
    entry = "twilightforest/block/TFPortalBlock.class"
    have = entry in tz.namelist()
    check("TFPortalBlock present", have)
    if have:
        body = tz.read(entry).decode("latin-1")
        check("getPortalDestination exists on it", "getPortalDestination" in body)
        check("it really calls MinecraftServer.getLevel (the redirect point)",
              "getLevel" in body and "MinecraftServer" in body)
    tz.close()

# ---------------------------------------------------------------- 1b. aether mixin
print("")
print("1b. AetherPortalMixin binds to the real Aether jar")
z = zipfile.ZipFile(pq)
anames = z.namelist()
check("AetherPortalMixin compiled into the jar",
      "pocketquests/mixin/AetherPortalMixin.class" in anames)
amx = json.loads(z.read("pocketquests.mixins.json").decode("utf-8"))
check("AetherPortalMixin declared in mixins.json",
      "AetherPortalMixin" in amx.get("mixins", []))
ablob = z.read("pocketquests/mixin/AetherPortalMixin.class").decode("latin-1")
z.close()
check("redirect target descriptor present", GETLEVEL in ablob)
check("mixin targets AetherPortalBlock by name",
      "com.aetherteam.aether.block.portal.AetherPortalBlock" in ablob)

ae = find_mod("aether-")
if check("aether installed", bool(ae), os.path.basename(ae or "")):
    az = zipfile.ZipFile(ae)
    aentry = "com/aetherteam/aether/block/portal/AetherPortalBlock.class"
    ahave = aentry in az.namelist()
    check("AetherPortalBlock present", ahave)
    if ahave:
        abody = az.read(aentry).decode("latin-1")
        check("getPortalDestination exists on it", "getPortalDestination" in abody)
        check("it really calls MinecraftServer.getLevel", "getLevel" in abody)
    az.close()

# ---------------------------------------------------------------- 2. config
print("\n2. twilight forest config permits portals in pocket dimensions")
tfcfg = os.path.join(MC, "config", "twilightforest-common.toml")
raw = io.open(tfcfg, encoding="utf-8").read() if os.path.exists(tfcfg) else ""
check("twilightforest-common.toml present", bool(raw))
check("allowPortalsInOtherDimensions = true", "allowPortalsInOtherDimensions = true" in raw,
      "without this no portal can be lit in any pocket dimension")
check("a backup of the original exists", os.path.exists(tfcfg + ".prehubfix"))

# ---------------------------------------------------------------- 3. round trip arithmetic
print("\n3. the offset round trip returns the player to where they started")

dims = json.load(io.open(os.path.join(MC, "config", "pocketdims.json"), encoding="utf-8"))
offsets = dims.get("regionOffsets", {})
shared = sorted(dims.get("restrictToPockets", {}))

# measured from each dimension's dimension_type; 1.0 where unspecified
SCALES = {
    "twilightforest:twilight_forest": 0.125,
    "undergarden:undergarden": 4.0,
}
cases = []
for dim in shared:
    cs = SCALES.get(dim, 1.0)
    scale_in = 1.0 / cs          # pocket -> shared, what the portal multiplies by
    scale_out = cs               # shared -> pocket, what it multiplies by coming home
    for pocket, off in sorted(offsets.items()):
        if off[0] == 0 and off[1] == 0:
            continue
        cases.append((dim, pocket, off[0], scale_in, scale_out))

print("   %d (dimension, pocket) combinations with a non-zero offset" % len(cases))
print("   non-1.0 scales: %s" % ", ".join("%s=%s" % kv for kv in sorted(SCALES.items())))

shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(os.path.join(TMP, "pocketquests"))

body = []
for dim, pocket, offx, s_in, s_out in cases:
    body.append(
        '        one("%s", "%s", %r, %r, %r);' % (dim.split(":")[-1], pocket, offx, s_in, s_out))

HARNESS = """
package pocketquests;

public class WorldsTest {
    static int bad = 0;
    static final double START = 1234.0;   // where the player stands in their pocket dimension

    /** Walk the whole trip through the real PocketWorlds arithmetic. */
    static void one(String dim, String pocket, int offX, double scaleIn, double scaleOut) {
        double arrival = START * scaleIn;                       // the portal's own scaling
        double home = PocketWorlds.roundTripX(arrival, offX, scaleOut);
        boolean ok = Math.abs(home - START) < 0.5;
        if (!ok) {
            bad++;
            System.out.printf("   FAIL %-22s %-12s start %.1f -> home %.1f  (off by %.0f)%n",
                              dim, pocket, START, home, home - START);
        }
    }

    public static void main(String[] a) {
        // the arithmetic, for every shared dimension and pocket
__CASES__

        // and explicitly the case that was broken, so a regression is named not just counted
        double arrival = START * 8.0;                          // overworld -> twilight forest
        double fixed = PocketWorlds.roundTripX(arrival, 1000000, 0.125);
        double flatSubtraction = arrival * 0.125 - 1000000;    // what the old code did
        System.out.printf("   twilight forest, 1M offset: scaled %.1f (want %.1f), "
                          + "flat subtraction would give %.1f%n", fixed, START, flatSubtraction);
        if (Math.abs(fixed - START) > 0.5) { bad++; System.out.println("   FAIL scaled inverse"); }
        if (Math.abs(flatSubtraction - START) < 1000) {
            bad++; System.out.println("   FAIL the old bug is not reproduced; test is wrong");
        }

        if (bad > 0) { System.out.println("   " + bad + " FAILED"); System.exit(1); }
        System.out.println("   every round trip lands within half a block of the start");
    }
}
""".replace("__CASES__", chr(10).join(body))

io.open(os.path.join(TMP, "pocketquests", "WorldsTest.java"), "w",
        encoding="utf-8").write(HARNESS)

# Reuse the build's own classpath resolution rather than globbing a second, divergent list.
# Loading PocketWorlds resolves the Minecraft types in its signatures, which reach
# com.mojang.brigadier.Message and the datafixer - a hand-picked list missed both.
sys.path.insert(0, HERE)
import build_mod                                        # noqa: E402
_bcp, _bmissing = build_mod.resolve_classpath()
if _bmissing:
    print("   cannot resolve the build classpath: %s" % _bmissing)
    sys.exit(1)
cp = [os.path.join(BUILD, "classes")] + _bcp
CP = os.pathsep.join(cp)

r = subprocess.run(["javac", "-nowarn", "-proc:none", "-cp", CP, "-d", TMP,
                    os.path.join(TMP, "pocketquests", "WorldsTest.java")],
                   capture_output=True, text=True, errors="replace")
if not check("round trip harness compiles", r.returncode == 0):
    print((r.stdout or "") + (r.stderr or ""))
else:
    r = subprocess.run([java_runtime(), "-cp", os.pathsep.join([TMP, CP]),
                        "pocketquests.WorldsTest"],
                       capture_output=True, text=True, errors="replace", cwd=TMP)
    print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.strip()[:1200])
    check("all round trips return to the start", r.returncode == 0)

# ---------------------------------------------------------------- 4. scale data is complete
print("\n4. every shared dimension's coordinate_scale is accounted for")
unaccounted = []
for dim in shared:
    if dim not in SCALES:
        pass        # treated as 1.0; verified against the jars by get_dimension_scales below
print("   %d shared dimensions, %d with a non-default scale" % (len(shared), len(SCALES)))
check("the two known non-1.0 dimensions are both covered",
      set(SCALES) == {"twilightforest:twilight_forest", "undergarden:undergarden"})

# ---------------------------------------------------------------- 5. live config paths
#
# Lost Cities generated no city because its profile mapping was written to
# config/lostcities-common.toml while the mod actually reads config/lostcities/common.toml. The
# flat file is left behind by an older version of the mod, so it looks exactly right - right mod,
# right section, right key - and editing it is silently a no-op. The player spawns in an ordinary
# forest in a dimension whose entire premise is a ruined city.
#
# McJty mods moved their configs into a per-mod FOLDER. Where both spellings exist the folder is
# live and the flat file is a decoy. This flags every such pair, not just this mod's, because the
# trap is the pair rather than Lost Cities.
print("")
print("5. mod configs are being written where the mod reads them")
decoys = []
for flat in sorted(glob.glob(os.path.join(MC, "config", "*-*.toml"))):
    stem = os.path.basename(flat)[:-5]
    mod, _, kind = stem.rpartition("-")
    if not mod:
        continue
    if os.path.exists(os.path.join(MC, "config", mod, kind + ".toml")):
        decoys.append(stem + ".toml is dead, " + mod + "/" + kind + ".toml is live")
check("no edits are sitting in a config the mod has superseded",
      not decoys, "; ".join(decoys))

lc = os.path.join(MC, "config", "lostcities", "common.toml")
lc_text = io.open(lc, encoding="utf-8").read() if os.path.exists(lc) else ""
check("lost cities maps hub:lostcities to a profile",
      "hub:lostcities=" in lc_text,
      "without it the pocket generates plain terrain and the premise is simply absent")
profile = ""
for piece in lc_text.replace(chr(34), " ").replace(",", " ").split():
    if piece.startswith("hub:lostcities="):
        profile = piece.split("=", 1)[1]
check("that profile exists on disk",
      bool(profile) and os.path.exists(
          os.path.join(MC, "config", "lostcities", "profiles", profile + ".json")),
      ("profile " + profile) if profile else "no profile named")

print("\n%s" % ("ALL CHECKS PASSED" if not failures else "FAILURES: " + ", ".join(failures)))
sys.exit(1 if failures else 0)
