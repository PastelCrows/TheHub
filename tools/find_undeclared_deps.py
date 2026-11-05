# -*- coding: utf-8 -*-
"""Find mods that USE a library they never DECLARE.

WHY THIS EXISTS. Twice now a pack has validated completely clean and then died on launch, both
times for the same reason: a mod hard-references a class from another mod while its
`neoforge.mods.toml` lists only neoforge and minecraft.

    [Let's Do] Beachparty  -> top.theillusivec4.curios...ICurioItem    (Cobblemon instance)
    Cave Dweller 1.4-rc2   -> me.fzzyhmstrs.fzzy_config.config.Config  (Horror instance)

`validate_instance.py` cannot catch these: it reads declarations, and the declaration is the
thing that is wrong. The only signal left is the BYTECODE, which names every class a mod
actually touches.

HOW IT WORKS. Class names live in each class file's constant pool as UTF-8 entries, so the jars
are scanned for package-shaped strings and grouped by their first few segments. A package is
"provided" if some installed jar actually ships classes under it, or if it belongs to the JDK,
Minecraft, NeoForge or the mixin/loader stack. Anything referenced and not provided is a
candidate.

CANDIDATES, NOT VERDICTS - and the reason matters. Mods routinely reference optional
integrations behind a guard (`if (ModList.get().isLoaded("jei"))`), and such a reference is
harmless when the mod is absent: the class is never loaded, so the missing class never resolves.
Those live overwhelmingly in packages containing `compat`, `integration`, `plugin`, `addon` or
`hooks`, so references from THOSE paths are reported separately and ranked below the rest. A
reference from a mod's main package is the dangerous kind - that is where both real failures
were.

    python find_undeclared_deps.py                      # every instance
    python find_undeclared_deps.py "The Hub" Horror      # named instances only
"""
import io
import os
import re
import sys
import zipfile
import collections

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRISM = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances")

# Packages that are always present and must never be reported.
ALWAYS = (
    "java/", "javax/", "jdk/", "sun/", "com/sun/", "org/w3c/", "org/xml/",
    "net/minecraft/", "net/neoforged/", "com/mojang/", "cpw/mods/",
    "org/spongepowered/", "org/objectweb/", "it/unimi/dsi/", "com/google/",
    "org/apache/", "org/slf4j/", "org/joml/", "org/lwjgl/", "io/netty/",
    "com/electronwill/", "org/jetbrains/", "kotlin/", "kotlinx/", "org/intellij/",
    "javassist/", "org/checkerframework/", "net/jodah/", "org/antlr/",
)

# Soft-integration markers: a reference from a path containing one of these is usually guarded.
SOFT = ("compat", "integration", "plugin", "addon", "hooks", "mixin", "emi", "jei", "rei")

# Constant-pool entry sizes, by tag. Only Utf8 (1) is variable-length; the rest are fixed, and
# Long (5) and Double (6) notoriously take TWO pool slots each.
_FIXED = {7: 2, 8: 2, 16: 2, 19: 2, 20: 2,          # Class, String, MethodType, Module, Package
          15: 3, 17: 4, 18: 4,                       # MethodHandle, Dynamic, InvokeDynamic
          3: 4, 4: 4, 9: 4, 10: 4, 11: 4, 12: 4,     # Integer, Float, Field/Method/IfaceRef, NameAndType
          5: 8, 6: 8}                                # Long, Double


def class_refs(blob):
    """Every class-name string in a class file's constant pool.

    Parsed properly rather than pattern-matched. A byte regex over the raw file looked adequate
    and was not: the two-byte length prefix in front of each Utf8 entry gets swallowed as part of
    the name, which invented packages that do not exist - oxfacthd/axfacthd/kxfacthd for
    xfacthd, cdan200/idan200 for dan200. That turned the whole report into noise, and a tool that
    cries wolf is worse than no tool.
    """
    out = []
    try:
        if blob[:4] != b"\xca\xfe\xba\xbe":
            return out
        count = int.from_bytes(blob[8:10], "big")
        i = 10
        n = 1
        while n < count:
            tag = blob[i]
            i += 1
            if tag == 1:                                  # Utf8
                ln = int.from_bytes(blob[i:i + 2], "big")
                i += 2
                raw = blob[i:i + ln]
                i += ln
                try:
                    out.append(raw.decode("utf-8"))
                except Exception:
                    pass
            else:
                size = _FIXED.get(tag)
                if size is None:
                    return out                            # unknown tag: stop, do not guess
                i += size
                if tag in (5, 6):
                    n += 1
            n += 1
    except Exception:
        return out
    return out


CLASSNAME = re.compile(
    r"^[a-z][a-z0-9_]{1,20}(?:/[A-Za-z0-9_$]{1,40}){2,}$")

MIN_HITS = 3          # a package referenced once or twice is usually a string, not a dependency


def prefix(path, depth=3):
    parts = path.split("/")
    return "/".join(parts[:depth])


def scan_instance(inst):
    mods = os.path.join(PRISM, inst, "minecraft", "mods")
    if not os.path.isdir(mods):
        return None
    jars = sorted(f for f in os.listdir(mods) if f.endswith(".jar"))
    if not jars:
        return None

    provided = {}                      # package prefix -> jar that ships it
    refs = collections.defaultdict(lambda: collections.Counter())   # jar -> prefix -> hits
    soft = collections.defaultdict(set)                             # jar -> soft prefixes

    for f in jars:
        p = os.path.join(mods, f)
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        names = z.namelist()
        for n in names:
            if n.endswith(".class"):
                provided.setdefault(prefix(n[:-6]), f)
            # Shaded and JarJar'd libraries live in NESTED jars, and skipping them made this
            # tool report 168 candidates that were almost all a jar's own bundled library -
            # xaero/lib/common inside the xaero jar, net/peanuuutz/tomlkt inside fzzy_config,
            # malte0811/dualcodecs inside Immersive Engineering. Same nested-jar trap that has
            # already been documented twice elsewhere in this repo.
            elif n.endswith(".jar") and ("jarjar" in n or "jars/" in n):
                try:
                    inner = zipfile.ZipFile(io.BytesIO(z.read(n)))
                except Exception:
                    continue
                for m in inner.namelist():
                    if m.endswith(".class"):
                        provided.setdefault(prefix(m[:-6]), f + " > " + os.path.basename(n))
        for n in names:
            if not n.endswith(".class"):
                continue
            try:
                blob = z.read(n)
            except Exception:
                continue
            own = prefix(n[:-6])
            is_soft = any(s in n.lower() for s in SOFT)
            for ref in class_refs(blob):
                # A pool Utf8 is also used for descriptors and arbitrary strings, so the whole
                # entry must match a class name, anchored - not merely contain one.
                if not CLASSNAME.match(ref):
                    continue
                # ...and a class name's last segment is a type, so it starts uppercase. Without
                # this, slash-separated RESOURCE paths pass: LibX's village/savanna/zombie and
                # bastion/treasure/walls, fzzy_config's widget/scroll/vanilla. They are strings
                # the mod stores, not classes it calls.
                if not ref.rsplit("/", 1)[-1][:1].isupper():
                    continue
                if ref.startswith(ALWAYS):
                    continue
                pre = prefix(ref)
                if pre == own:
                    continue
                refs[f][pre] += 1
                if is_soft:
                    soft[f].add(pre)
    return jars, provided, refs, soft


def declared_modids(mods_dir, jar):
    out = set()
    try:
        z = zipfile.ZipFile(os.path.join(mods_dir, jar))
    except Exception:
        return out
    for t in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if t in z.namelist():
            try:
                s = z.read(t).decode("utf-8", "replace")
            except Exception:
                break
            out |= set(re.findall(r'modId\s*=\s*"([^"]+)"', s))
            break
    return out


def main():
    want = [a for a in sys.argv[1:] if not a.startswith("--")]
    insts = want or sorted(
        d for d in os.listdir(PRISM)
        if os.path.isdir(os.path.join(PRISM, d, "minecraft", "mods")))

    grand_hard = 0
    for inst in insts:
        res = scan_instance(inst)
        if not res:
            continue
        jars, provided, refs, soft = res
        mods_dir = os.path.join(PRISM, inst, "minecraft", "mods")

        hard_rows, soft_rows = [], []
        for jar, counter in refs.items():
            decl = declared_modids(mods_dir, jar)
            for pre, hits in counter.items():
                if hits < MIN_HITS or pre in provided:
                    continue
                # if the mod declares a modId that looks like this package, it knows about it
                tail = pre.split("/")[-1].lower()
                if any(tail in d.lower() or d.lower() in tail for d in decl):
                    continue
                row = (hits, jar, pre)
                (soft_rows if pre in soft.get(jar, ()) else hard_rows).append(row)

        hard_rows.sort(reverse=True)
        soft_rows.sort(reverse=True)
        print("=" * 100)
        print("%s   (%d jars)" % (inst, len(jars)))
        if hard_rows:
            print("  LIKELY HARD - referenced from a non-integration path, nothing provides it:")
            for hits, jar, pre in hard_rows[:12]:
                print("    %-54s -> %-34s %d refs" % (jar[:54], pre, hits))
            grand_hard += len(hard_rows)
        else:
            print("  no likely-hard undeclared references")
        if soft_rows:
            print("  probably-guarded integrations (%d), top few:" % len(soft_rows))
            for hits, jar, pre in soft_rows[:5]:
                print("    %-54s -> %-34s %d refs" % (jar[:54], pre, hits))
    print("=" * 100)
    print("total likely-hard candidates across scanned instances: %d" % grand_hard)
    print("These are CANDIDATES. Confirm by launching, or by checking whether the referencing")
    print("class is reachable during mod construction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
