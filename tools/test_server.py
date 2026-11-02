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
JAVA = os.path.join(PRISM, "java", "java-runtime-delta", "bin", "java.exe")
NEOFORGE = "21.1.265"
ARGS = os.path.join("libraries", "net", "neoforged", "neoforge", NEOFORGE, "win_args.txt")
LOG = os.path.join(SERVER, "server-out.log")

# What the TM filter needs to be exercised at all: Cobblemon itself, the mod that ships the
# broken TMs, the loader shims they need, and the mod under test.
SEED = ["Cobblemon-neoforge-*.jar", "gravels_extended_battles-neoforge-*.jar",
        "architectury-*-neoforge.jar", "kotlinforforge-*.jar", "hubtmfilter-*.jar"]

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


def seed_mods():
    dest = os.path.join(SERVER, "mods")
    os.makedirs(dest, exist_ok=True)
    for pat in SEED:
        for p in glob.glob(os.path.join(SRC_MODS, pat)):
            shutil.copy2(p, dest)
    return len(os.listdir(dest))


def write_config():
    io.open(os.path.join(SERVER, "eula.txt"), "w", newline="\n").write("eula=true\n")
    io.open(os.path.join(SERVER, "server.properties"), "w", newline="\n").write(
        "level-type=minecraft\\:flat\n"
        "level-name=tmtest\n"
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


def run_once(timeout=420):
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

    if not run:
        return 0

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
        text = run_once()

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
