# -*- coding: utf-8 -*-
"""Run a headless NeoForge server to test things the client cannot show.

WHY THIS EXISTS. Cobblemon's TM registry is PackType.SERVER_DATA, so it only reloads when a
world loads - never at the title screen. The TM filter therefore cannot be verified by launching
the client and reading the log, and creating a world is a GUI action. A dedicated server loads
server data, generates a world, runs headless and logs everything, which is exactly the missing
piece. It is also a far better smoke test than the menu: it actually builds a world.

MINIMAL MOD SET, NOT THE WHOLE PACK. 302 jars include a lot of client-only mods that have no
business on a server, and their failures would drown the signal. So the server starts from a
named seed set and then resolves whatever NeoForge says is missing, by reading the loader's own
error messages:

    Mod gravels_extended_battles requires mega_showdown 1.0.2+1.8+1.21. or above

That name is looked up among the installed jars by modId and copied in, and the server is tried
again. The loop is bounded; it reports what it could not satisfy rather than spinning.

A superflat world is used on purpose: worldgen is not what is being tested here, and flat cuts
the run from minutes to seconds. The data reload that matters happens either way.

    python test_server.py --setup           # install/refresh the server and seed mods
    python test_server.py --run             # resolve deps, boot, report, stop
    python test_server.py --run --grep hubtmfilter
"""
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SERVER = os.path.join(REPO, "test-server")
PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher")
SRC_MODS = os.path.join(PRISM, "instances", "Cobblemon NeoForge", "minecraft", "mods")
WORLD = "tmtest"
JAVA = os.path.join(PRISM, "java", "java-runtime-delta", "bin", "java.exe")
NEOFORGE = "21.1.265"
ARGS = os.path.join("libraries", "net", "neoforged", "neoforge", NEOFORGE, "win_args.txt")
LOG = os.path.join(SERVER, "server-out.log")
NL = chr(10)

# Named profiles. Each names the instance to pull jars FROM, the minimal set needed to exercise
# one specific thing, and its own world - so two tests never share a level and leave each other
# half-generated chunks to trip over.
PROFILES = {
    # Cobblemon itself, the mod that ships the broken TMs, the loader shims, the mod under test.
    "tm": {
        "from": "Cobblemon NeoForge",
        "world": "tmtest",
        "seed": ["Cobblemon-neoforge-*.jar", "gravels_extended_battles-neoforge-*.jar",
                 "architectury-*-neoforge.jar", "kotlinforforge-*.jar", "hubtmfilter-*.jar",
                 "hubclientperf-*.jar"],
    },
    # Distant Horizons + Chunky + our ordering fix. The Hub's world-creation crash was SERVER
    # side - "Exception during promotion of chunk to FULL status" in a -server crash report - so
    # a dedicated server reproduces it exactly, which the client could only do by clicking.
    "chunky": {
        "from": "The Hub",
        "world": "chunkytest",
        "seed": ["DistantHorizons-*.jar", "Chunky-NeoForge-*.jar", "hubchunkyfix-*.jar"],
    },
    # The same pair WITHOUT our fix: the control that proves the crash is real and that the fix
    # is what prevents it.
    "chunky-control": {
        "from": "The Hub",
        "world": "chunkyctl",
        "seed": ["DistantHorizons-*.jar", "Chunky-NeoForge-*.jar"],
    },
}
PROFILE = "tm"

MAX_ROUNDS = 14


def modids(path):
    """What this jar PROVIDES, from its [[mods]] blocks only.

    Not every modId in the file: a `[[dependencies.x]]` block also carries a modId, and taking
    those too makes a jar look like it provides everything it merely requires. That bug had
    `mega_showdown` resolving to cobblemonraiddens - which only depends on it - so the loop
    copied the wrong jar and then reported the dependency as unsatisfiable. Same trap as the
    one in validate_instance.py, in a new place.
    """
    out = set()
    try:
        z = zipfile.ZipFile(path)
    except Exception:
        return out
    for t in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if t not in z.namelist():
            continue
        try:
            text = z.read(t).decode("utf-8", "replace")
        except Exception:
            break
        # take each [[mods]] section up to the next top-level [[...]] header
        for block in re.split(r"^\s*\[\[mods\]\]", text, flags=re.M)[1:]:
            block = re.split(r"^\s*\[\[", block, flags=re.M)[0]
            m = re.search(r'modId\s*=\s*"([^"]+)"', block)
            if m:
                out.add(m.group(1))
        break
    return out


def index_source():
    """modId -> jar path, across every jar in the Cobblemon instance."""
    idx = {}
    for f in sorted(os.listdir(SRC_MODS)):
        if not f.endswith(".jar"):
            continue
        p = os.path.join(SRC_MODS, f)
        for m in modids(p):
            idx.setdefault(m, p)
    return idx


def apply_profile(name):
    """Point the harness at one profile: source instance, seed set, world."""
    global SRC_MODS, WORLD, PROFILE
    cfg = PROFILES[name]
    PROFILE = name
    SRC_MODS = os.path.join(PRISM, "instances", cfg["from"], "minecraft", "mods")
    WORLD = cfg["world"]
    return cfg


def seed_mods(clear=True):
    dest = os.path.join(SERVER, "mods")
    os.makedirs(dest, exist_ok=True)
    if clear:
        # A profile switch must not inherit the previous profile's jars; leftovers are how a
        # test ends up proving something about a mod set nobody asked about.
        for f in os.listdir(dest):
            if f.endswith(".jar"):
                os.remove(os.path.join(dest, f))
    for pat in PROFILES[PROFILE]["seed"]:
        for p in glob.glob(os.path.join(SRC_MODS, pat)):
            shutil.copy2(p, dest)
    return len(os.listdir(dest))


def write_config():
    io.open(os.path.join(SERVER, "eula.txt"), "w", newline="\n").write("eula=true\n")
    io.open(os.path.join(SERVER, "server.properties"), "w", newline="\n").write(
        "level-type=minecraft\\:flat\n"
        "level-name=" + WORLD + "\n"
        "online-mode=false\n"
        "view-distance=4\n"
        "simulation-distance=4\n"
        "max-players=1\n"
        "spawn-protection=0\n"
        "sync-chunk-writes=false\n"
        "motd=hub test server\n")
    io.open(os.path.join(SERVER, "user_jvm_args.txt"), "w", newline="\n").write("-Xmx4G\n")


def missing_from_log(text):
    """modIds NeoForge says are missing, read off its own messages."""
    out = []
    for m in re.finditer(r"requires\s+([A-Za-z0-9_\-]+)\s", text):
        out.append(m.group(1))
    for m in re.finditer(r"Mod\s+[A-Za-z0-9_\-]+\s+requires\s+([A-Za-z0-9_\-]+)", text):
        out.append(m.group(1))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def write_harness_datapack(commands):
    """Put the commands in a datapack function that runs on world load.

    Console stdin to a NeoForge server proved unreliable here: some runs executed the commands
    and some produced no output at all, which makes silence uninterpretable - and a negative
    result you cannot interpret is worthless. A function tagged `minecraft:load` is run by the
    server itself every time the world loads, needs no console, and cannot half-arrive. It is
    written into the test world's own datapacks folder so it travels with that world and
    nothing else.

    HARNESS-BEGIN / HARNESS-END bracket the output so the log can be checked for the commands
    having actually run, rather than inferring it from the absence of an error.
    """
    world = os.path.join(SERVER, WORLD)
    root = os.path.join(world, "datapacks", "harness")
    fn_dir = os.path.join(root, "data", "harness", "function")
    tag_dir = os.path.join(root, "data", "minecraft", "tags", "function")
    for d in (fn_dir, tag_dir):
        os.makedirs(d, exist_ok=True)
    io.open(os.path.join(root, "pack.mcmeta"), "w", encoding="utf-8", newline=NL).write(
        '{"pack": {"pack_format": 48, "description": "hub test harness"}}' + NL)
    body = ["say HARNESS-BEGIN"] + list(commands) + ["say HARNESS-END"]
    io.open(os.path.join(fn_dir, "run.mcfunction"), "w", encoding="utf-8",
            newline=NL).write(NL.join(body) + NL)
    io.open(os.path.join(tag_dir, "load.json"), "w", encoding="utf-8", newline=NL).write(
        '{"values": ["harness:run"]}' + NL)
    return os.path.join(fn_dir, "run.mcfunction")


def run_once(timeout=420, commands=None):
    """Start the server, wait for it to be up or fail, stop it, return the log."""
    if os.path.exists(LOG):
        os.remove(LOG)
    with io.open(LOG, "wb") as out:
        proc = subprocess.Popen(
            [JAVA, "-Xmx4G", "@" + ARGS, "--nogui"],
            cwd=SERVER, stdout=out, stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE)
    done = re.compile(r'Done \([0-9.]+s\)|Failed to start|ModLoadingException|'
                      r'Error during pre-loading|A fatal error')
    deadline = time.time() + timeout
    text = ""
    while time.time() < deadline:
        time.sleep(4)
        if proc.poll() is not None:
            break
        try:
            text = io.open(LOG, encoding="utf-8", errors="replace").read()
        except Exception:
            text = ""
        if done.search(text):
            break
    if proc.poll() is None and commands:
        # Sent only once the server reports Done. Superflat generates no structures, so
        # `/place template <id>` is the only way to make StructureTemplate.load run on a
        # chosen file - which is exactly what the jigsaw pool repair needs to be exercised.
        for c in commands:
            try:
                proc.stdin.write((c + chr(10)).encode())
                proc.stdin.flush()
            except (OSError, ValueError):
                break
            time.sleep(3)
        time.sleep(4)
    if proc.poll() is None:
        try:
            proc.stdin.write(b"stop\n")
            proc.stdin.flush()
        except Exception:
            pass
        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(2)
        if proc.poll() is None:
            proc.kill()
    try:
        return io.open(LOG, encoding="utf-8", errors="replace").read()
    except Exception:
        return text


def main():
    setup = "--setup" in sys.argv
    run = "--run" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--profile" and i + 1 < len(sys.argv):
            name = sys.argv[i + 1]
            if name not in PROFILES:
                print("unknown profile %r; have: %s" % (name, ", ".join(sorted(PROFILES))))
                return 1
            apply_profile(name)
            print("profile: %s   (from %s, world %s)"
                  % (name, PROFILES[name]["from"], PROFILES[name]["world"]))

    commands = []
    for i, a in enumerate(sys.argv):
        if a == "--cmd" and i + 1 < len(sys.argv):
            commands.append(sys.argv[i + 1])
    pattern = None
    if "--grep" in sys.argv:
        i = sys.argv.index("--grep")
        if i + 1 < len(sys.argv):
            pattern = sys.argv[i + 1]
    if not (setup or run):
        print(__doc__)
        return 0
    if not os.path.isdir(SERVER):
        print("no test-server/ - install it first with the NeoForge installer")
        return 1

    if setup:
        write_config()
        print("seeded mods: %d" % seed_mods())

    for i, a in enumerate(sys.argv):
        if a == "--add" and i + 1 < len(sys.argv):
            _idx = index_source()
            _p = _idx.get(sys.argv[i + 1])
            if _p:
                shutil.copy2(_p, os.path.join(SERVER, "mods"))
                print("added: %s" % os.path.basename(_p))
            else:
                print("cannot add %r - no installed jar provides it" % sys.argv[i + 1])

    if not run:
        return 0

    if "--via-datapack" in sys.argv and commands:
        if os.path.isdir(os.path.join(SERVER, WORLD)):
            print("harness datapack: %s" % write_harness_datapack(commands))
            commands = []        # the datapack runs them; do not also send them on stdin
        else:
            print("no world yet - do one plain --run first, then --via-datapack")

    idx = index_source()
    print("source jars indexed by modId: %d" % len(idx))
    dest = os.path.join(SERVER, "mods")

    unresolved = []
    for rnd in range(1, MAX_ROUNDS + 1):
        have = set()
        for f in os.listdir(dest):
            if f.endswith(".jar"):
                have |= modids(os.path.join(dest, f))
        print("\n--- round %d: %d jars, %d modIds" % (rnd, len(os.listdir(dest)), len(have)))
        text = run_once(commands=commands)

        if re.search(r'Done \([0-9.]+s\)', text):
            print("   SERVER STARTED")
            break

        want = [m for m in missing_from_log(text)
                if m not in have and m not in ("minecraft", "neoforge", "java")]
        added = []
        for m in want:
            p = idx.get(m)
            if p:
                shutil.copy2(p, dest)
                added.append("%s (%s)" % (m, os.path.basename(p)))
            else:
                unresolved.append(m)
        if added:
            for a in added:
                print("   + " + a)
            continue
        print("   cannot proceed; nothing left to add")
        for line in text.splitlines():
            if "requires" in line or "Failed to start" in line or "Missing" in line:
                print("      " + line.strip()[:150])
        break

    text = io.open(LOG, encoding="utf-8", errors="replace").read()
    print("\n" + "=" * 92)
    started = bool(re.search(r'Done \([0-9.]+s\)', text))
    print("  server started : %s" % started)
    print("  log size       : %d KB" % (len(text) // 1024))
    errs = len(re.findall(r'/ERROR|/FATAL', text))
    print("  ERROR/FATAL    : %d" % errs)
    if unresolved:
        print("  unresolved deps: %s" % ", ".join(sorted(set(unresolved))))
    if pattern:
        print("\n  lines matching %r:" % pattern)
        hits = [l for l in text.splitlines() if pattern.lower() in l.lower()]
        for l in hits[:40]:
            print("     " + l.strip()[:150])
        if not hits:
            print("     (none)")
    print("=" * 92)
    return 0 if started else 1


if __name__ == "__main__":
    raise SystemExit(main())
