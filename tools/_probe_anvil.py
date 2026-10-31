# -*- coding: utf-8 -*-
"""Feasibility probe: can the hub room be read straight out of the saved region files?

Not a tool yet - just proving the three things a capture tool would need:
  1. the region header locates a chunk
  2. the chunk payload decompresses to NBT we can walk
  3. a section's block palette and packed indices resolve to real block ids
"""
import gzip
import io
import os
import struct
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def parse_nbt(buf, pos=0, named=True):
    def u1():
        nonlocal pos
        v = buf[pos]; pos += 1; return v

    def u2():
        nonlocal pos
        v = struct.unpack_from(">H", buf, pos)[0]; pos += 2; return v

    def i4():
        nonlocal pos
        v = struct.unpack_from(">i", buf, pos)[0]; pos += 4; return v

    def name():
        nonlocal pos
        n = u2()
        s = buf[pos:pos + n].decode("utf-8", "replace"); pos += n; return s

    def payload(t):
        nonlocal pos
        if t == 1:
            v = struct.unpack_from(">b", buf, pos)[0]; pos += 1; return v
        if t == 2:
            v = struct.unpack_from(">h", buf, pos)[0]; pos += 2; return v
        if t == 3:
            return i4()
        if t == 4:
            v = struct.unpack_from(">q", buf, pos)[0]; pos += 8; return v
        if t == 5:
            v = struct.unpack_from(">f", buf, pos)[0]; pos += 4; return v
        if t == 6:
            v = struct.unpack_from(">d", buf, pos)[0]; pos += 8; return v
        if t == 7:
            n = i4(); v = buf[pos:pos + n]; pos += n; return v
        if t == 8:
            return name()
        if t == 9:
            it = u1(); n = i4()
            return [payload(it) for _ in range(n)]
        if t == 10:
            d = {}
            while True:
                tt = u1()
                if tt == 0:
                    return d
                k = name()
                d[k] = payload(tt)
        if t == 11:
            n = i4(); v = list(struct.unpack_from(">%di" % n, buf, pos)); pos += 4 * n; return v
        if t == 12:
            n = i4(); v = list(struct.unpack_from(">%dq" % n, buf, pos)); pos += 8 * n; return v
        raise ValueError("unknown tag %d at %d" % (t, pos))

    t = u1()
    if named:
        name()
    return payload(t)


def read_chunk(region_path, cx, cz):
    """Return the chunk NBT at world chunk coords, or None if ungenerated."""
    with io.open(region_path, "rb") as f:
        header = f.read(4096)
        idx = ((cx & 31) + (cz & 31) * 32) * 4
        off = int.from_bytes(header[idx:idx + 3], "big")
        count = header[idx + 3]
        if off == 0 or count == 0:
            return None
        f.seek(off * 4096)
        length = struct.unpack(">i", f.read(4))[0]
        comp = f.read(1)[0]
        data = f.read(length - 1)
    if comp == 1:
        data = gzip.decompress(data)
    elif comp == 2:
        data = zlib.decompress(data)
    return parse_nbt(data)


def unpack_states(longs, bits, count):
    """1.21 packing: entries never straddle a long; leftover high bits are padding."""
    per = 64 // bits
    mask = (1 << bits) - 1
    out = []
    for i in range(count):
        word = longs[i // per]
        shift = (i % per) * bits
        out.append((word >> shift) & mask)
    return out


MC = os.path.expandvars(r"%APPDATA%\PrismLauncher\instances\The Hub\minecraft")
world = sys.argv[1] if len(sys.argv) > 1 else "New World (4)"
region_dir = os.path.join(MC, "saves", world, "dimensions", "hub", "hub", "region")
print("world  :", world)
print("region :", region_dir)
if not os.path.isdir(region_dir):
    print("NOT FOUND")
    raise SystemExit(1)

# the lobby sits at -32..32 x, -14..14 z -> chunk (-1, -1) is inside it
cx, cz = -1, -1
path = os.path.join(region_dir, "r.%d.%d.mca" % (cx >> 5, cz >> 5))
print("file   :", os.path.basename(path), os.path.getsize(path), "bytes")

chunk = read_chunk(path, cx, cz)
if chunk is None:
    print("chunk not generated")
    raise SystemExit(1)

print("status :", chunk.get("Status"))
print("keys   :", sorted(k for k in chunk if k in
                         ("sections", "block_entities", "Heightmaps", "DataVersion")))
print("DataVersion:", chunk.get("DataVersion"))

found = 0
for sec in chunk.get("sections", []):
    bs = sec.get("block_states") or {}
    palette = bs.get("palette") or []
    names = [p.get("Name") for p in palette]
    interesting = [n for n in names if n and n != "minecraft:air"]
    if not interesting:
        continue
    y = sec.get("Y")
    data = bs.get("data")
    if data:
        bits = max(4, (len(palette) - 1).bit_length())
        idxs = unpack_states(data, bits, 4096)
        distinct = len(set(idxs))
        print("  section Y=%-4d palette=%-3d bits=%-2d distinct-indices=%d"
              % (y, len(palette), bits, distinct))
    else:
        print("  section Y=%-4d palette=%-3d (single block, no data array)" % (y, len(palette)))
    print("      e.g. " + ", ".join(interesting[:6]))
    found += 1
    if found >= 4:
        break

be = chunk.get("block_entities") or []
print("block entities in this chunk:", len(be),
      ("e.g. " + ", ".join(sorted({b.get("id", "?") for b in be}))[:120]) if be else "")
print()
print("PROBE OK - region header, chunk NBT and block palettes all read cleanly.")
