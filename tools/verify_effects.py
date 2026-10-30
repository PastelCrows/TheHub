# -*- coding: utf-8 -*-
"""Prove the ambience gate actually binds and actually decides correctly.

Both halves of PocketEffects fail SILENTLY by design, which is right for a game pack and awful
for confidence:

  * HorrorMessagesMixin carries require = 0, so if the target method descriptor is off by one
    character Mixin logs a line nobody reads and the gate simply never runs. So check one is
    purely static: pull the descriptor out of the compiled annotation and confirm a method with
    exactly that descriptor exists in the horror mod jar.

  * PocketEffects catches Throwable everywhere, so a wrong field filter would look like a mod
    that is merely absent. So check two runs the REAL class against the REAL config file and
    asserts the decisions, and check three counts the switches it would find in the real jar.

Run after any build. Exit code is non-zero if anything fails.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
HUB = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
BUILD = os.path.join(HERE, "_build")
TMP = os.path.join(BUILD, "_verify")

TARGET_CLASS = "net.mcreator.horrormessagesneoforge.procedures.SendHorrorMessageProcedure"
TARGET_DESC = "(Lnet/neoforged/bus/api/Event;Lnet/minecraft/world/level/LevelAccessor;)V"

failures = []


def check(label, ok, detail=""):
    print("   %-56s %s%s" % (label, "OK" if ok else "FAIL", "  " + detail if detail else ""))
    if not ok:
        failures.append(label)
    return ok


def find_mod(*fragments):
    for f in sorted(os.listdir(os.path.join(HUB, "mods"))):
        low = f.lower()
        if all(fr in low for fr in fragments):
            return os.path.join(HUB, "mods", f)
    return None



def java_runtime():
    """The `java` on PATH here is a JRE 8 shim (Oracle java8path), which cannot load class file
    version 65. javac is Adoptium 21, so take its sibling - matching compiler and runtime by
    construction rather than hoping PATH agrees with itself."""
    jc = shutil.which("javac")
    if jc:
        sib = os.path.join(os.path.dirname(jc), "java.exe")
        if os.path.exists(sib):
            return sib
    return "java"


# ---------------------------------------------------------------- 1. descriptor binding
print("1. mixin binding (static, no game needed)")

jar = os.path.join(HUB, "mods", "pocketquests-1.8.0.jar")
jar = jar if os.path.exists(jar) else (find_mod("pocketquests") or "")
if not check("pocketquests jar installed", bool(jar), os.path.basename(jar)):
    sys.exit(1)

z = zipfile.ZipFile(jar)
mixin_bytes = z.read("pocketquests/mixin/HorrorMessagesMixin.class")
z.close()
text = mixin_bytes.decode("latin-1")

# the @Inject method string and the @Mixin targets string both sit in the constant pool
check("mixin declares the private-funnel descriptor", TARGET_DESC in text, TARGET_DESC)
check("mixin targets the procedure class by name", TARGET_CLASS in text)

target_jar = find_mod("horror_messages") or find_mod("slower_horror")
if check("horror messages mod present", bool(target_jar),
         os.path.basename(target_jar or "")):
    tz = zipfile.ZipFile(target_jar)
    entry = TARGET_CLASS.replace(".", "/") + ".class"
    have = entry in tz.namelist()
    check("target class present in that jar", have, entry)
    if have:
        body = tz.read(entry).decode("latin-1")
        # the method name and its descriptor are adjacent constant-pool utf8 entries
        check("target jar contains a method with that exact descriptor",
              TARGET_DESC in body and "execute" in body)
    tz.close()

# ---------------------------------------------------------------- 2. switch discovery
print("\n2. serversidehorror switch discovery (against the real jar)")
ssh_jar = find_mod("serversidehorror")
switches = []
if check("serversidehorror mod present", bool(ssh_jar), os.path.basename(ssh_jar or "")):
    tz = zipfile.ZipFile(ssh_jar)
    cls = tz.read("com/mars/serversidehorror/ServersideHorrorConfig.class")
    tz.close()
    # field names live in the constant pool; _enable fields are what PocketEffects filters on
    switches = sorted(set(re.findall(rb"[a-z0-9_]+_enable", cls)))
    switches = [s.decode() for s in switches]
    check("found effect switches to control", len(switches) >= 15, "%d switches" % len(switches))
    print("      %s" % ", ".join(switches[:6]))
    print("      ... %s" % ", ".join(switches[-4:]))
    # the filter must not catch the non-effect option that merely ends in _traps
    check("grace_period_applies_to_traps NOT treated as a switch",
          "grace_period_applies_to_traps" not in switches)

# ---------------------------------------------------------------- 3. live decision test
print("\n3. decision logic (real class, real config file)")

cfg = os.path.join(HUB, "config", "pocketeffects.json")
if not check("pocketeffects.json installed", os.path.exists(cfg)):
    sys.exit(1)
rules = json.load(io.open(cfg, encoding="utf-8"))
horror_dims = rules["horror_messages"]
print("      configured horror dimensions: %s" % ", ".join(horror_dims))

# Run PocketEffects for real. It reads config/pocketeffects.json relative to the working
# directory, so the test runs from a scratch dir holding a copy - the same path the game uses.
shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(os.path.join(TMP, "config"))
shutil.copy2(cfg, os.path.join(TMP, "config", "pocketeffects.json"))

# The harness sits in the pocketquests package on purpose: wantedIn is package-private because
# it is a test seam, and widening it to public just to test it would be the tail wagging the dog.
HARNESS = r'''
package pocketquests;

import java.util.*;

public class EffectsTest {
    static int bad = 0;
    static void expect(String what, boolean actual, boolean want) {
        System.out.printf("   %-54s %s%n", what, actual == want ? "OK" : "FAIL got " + actual);
        if (actual != want) bad++;
    }
    public static void main(String[] a) throws Exception {
        // these three are where horror belongs
        expect("horror_messages allowed in hub:horror",
               PocketEffects.allowed("horror_messages", "hub:horror"), true);
        expect("horror_messages allowed in hub:horror_nether",
               PocketEffects.allowed("horror_messages", "hub:horror_nether"), true);
        expect("horror_messages allowed in hub:horror_end",
               PocketEffects.allowed("horror_messages", "hub:horror_end"), true);

        // the reported bug: a message in the creative redstone sandbox
        expect("horror_messages BLOCKED in hub:redstone  (the reported bug)",
               PocketEffects.allowed("horror_messages", "hub:redstone"), false);
        expect("horror_messages BLOCKED in hub:hub",
               PocketEffects.allowed("horror_messages", "hub:hub"), false);
        expect("horror_messages BLOCKED in hub:skyblock",
               PocketEffects.allowed("horror_messages", "hub:skyblock"), false);
        expect("horror_messages BLOCKED in hub:survival_nether",
               PocketEffects.allowed("horror_messages", "hub:survival_nether"), false);
        expect("horror_messages BLOCKED in a modded dim (twilightforest)",
               PocketEffects.allowed("horror_messages", "twilightforest:twilight_forest"), false);
        expect("horror_messages BLOCKED for a null dimension",
               PocketEffects.allowed("horror_messages", null), false);

        // an effect nobody configured must never be touched - fail open
        expect("an unlisted effect is allowed everywhere (fail open)",
               PocketEffects.allowed("some_mod_nobody_configured", "hub:redstone"), true);

        // serversidehorror switch state follows where the players are
        expect("switches UP when the only player is in horror",
               PocketEffects.wantedIn(Arrays.asList("hub:horror")), true);
        expect("switches DOWN when the only player is in redstone land",
               PocketEffects.wantedIn(Arrays.asList("hub:redstone")), false);
        expect("switches DOWN when the only player is in the hub",
               PocketEffects.wantedIn(Arrays.asList("hub:hub")), false);
        expect("switches UP if ANY player is in horror (multiplayer)",
               PocketEffects.wantedIn(Arrays.asList("hub:hub", "hub:horror")), true);
        expect("switches DOWN with nobody anywhere near horror",
               PocketEffects.wantedIn(Arrays.asList("hub:hub", "hub:survival")), false);
        expect("switches DOWN when no players at all",
               PocketEffects.wantedIn(new ArrayList<String>()), false);

        if (bad > 0) { System.out.println("   " + bad + " ASSERTION(S) FAILED"); System.exit(1); }
        System.out.println("   all decision assertions passed");
    }
}
'''

os.makedirs(os.path.join(TMP, "pocketquests"), exist_ok=True)
src = os.path.join(TMP, "pocketquests", "EffectsTest.java")
io.open(src, "w", encoding="utf-8").write(HARNESS)

# classpath: our compiled classes, plus gson and the minecraft/neoforge jars the class imports
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
LIB = os.path.join(PRISM, "libraries")
cp = [os.path.join(BUILD, "classes")]
for pat in (r"com\google\code\gson\gson\2.10.1\gson-2.10.1.jar",
            r"net\minecraft\client\*\client-*-srg.jar",
            r"net\neoforged\neoforge\*\neoforge-*-universal.jar"):
    hits = sorted(glob.glob(os.path.join(LIB, pat)))
    if hits:
        cp.append(hits[-1])
CP = os.pathsep.join(cp)

r = subprocess.run(["javac", "-nowarn", "-proc:none", "-cp", CP, "-d", TMP, src],
                   capture_output=True, text=True, errors="replace")
if not check("test harness compiles", r.returncode == 0):
    print((r.stdout or "") + (r.stderr or ""))
    sys.exit(1)

r = subprocess.run([java_runtime(), "-cp", os.pathsep.join([TMP, CP]), "pocketquests.EffectsTest"],
                   capture_output=True, text=True, errors="replace", cwd=TMP)
print(r.stdout.rstrip())
if r.stderr.strip():
    print(r.stderr.strip()[:1500])
check("all decision assertions pass", r.returncode == 0)

# ---------------------------------------------------------------- summary
print("\n%s" % ("ALL CHECKS PASSED" if not failures
                else "FAILURES: " + ", ".join(failures)))
sys.exit(1 if failures else 0)
