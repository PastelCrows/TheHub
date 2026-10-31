# -*- coding: utf-8 -*-
"""Minimal NBT reader/writer for Minecraft structure templates.

REBUILT 2026-10-31. build_hub_room_v6.py has always done `import nbt` / `from nbt import Int`,
but this module was never committed - it lived only on the machine that first wrote the lobby,
and by the time anyone tried to regenerate hub_room.nbt it was gone:

    ModuleNotFoundError: No module named 'nbt'

So the generator for the single most visible structure in the pack could not run, and nobody
found out until it mattered. It is tracked now. This is NOT the PyPI `NBT` package, whose API is
entirely different - the contract here is the three names build_hub_room_v6.py actually uses:

    Int(value)          mark a Python int as TAG_Int
    save(path, root)    write a gzipped, unnamed root compound; returns bytes written
    load(path)          read one back as plain Python values

TYPES. NBT distinguishes byte/short/int/long/float/double; Python does not. Plain `int` is
written as TAG_Int and plain `float` as TAG_Double, which is what structure files use, and the
wrapper classes below exist for the cases where that is wrong. A `dict` is a compound, a `list`
is a TAG_List whose element type comes from its first entry, and an EMPTY list is written with
element type TAG_End - which is what vanilla does for an empty `entities` list.

Structure files are GZIPPED. Minecraft will not read an uncompressed one, and the failure is
silent at `place template` time rather than loud at load time.
"""
import gzip
import io
import struct

TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class Byte(int):
    nbt_tag = TAG_BYTE


class Short(int):
    nbt_tag = TAG_SHORT


class Int(int):
    nbt_tag = TAG_INT


class Long(int):
    nbt_tag = TAG_LONG


class Float(float):
    nbt_tag = TAG_FLOAT


class Double(float):
    nbt_tag = TAG_DOUBLE


class IntArray(list):
    nbt_tag = TAG_INT_ARRAY


class LongArray(list):
    nbt_tag = TAG_LONG_ARRAY


class ByteArray(bytes):
    nbt_tag = TAG_BYTE_ARRAY


def tag_of(value):
    """Which NBT tag a Python value serialises as."""
    tag = getattr(value, "nbt_tag", None)
    if tag is not None:
        return tag
    if isinstance(value, bool):
        return TAG_BYTE
    if isinstance(value, int):
        return TAG_INT
    if isinstance(value, float):
        return TAG_DOUBLE
    if isinstance(value, str):
        return TAG_STRING
    if isinstance(value, (bytes, bytearray)):
        return TAG_BYTE_ARRAY
    if isinstance(value, dict):
        return TAG_COMPOUND
    if isinstance(value, (list, tuple)):
        return TAG_LIST
    raise TypeError("no NBT tag for %r" % (type(value),))


# ------------------------------------------------------------------ writing
def _put_string(out, s):
    raw = s.encode("utf-8")
    out.write(struct.pack(">H", len(raw)))
    out.write(raw)


def _put_payload(out, tag, value):
    if tag == TAG_BYTE:
        out.write(struct.pack(">b", int(value)))
    elif tag == TAG_SHORT:
        out.write(struct.pack(">h", int(value)))
    elif tag == TAG_INT:
        out.write(struct.pack(">i", int(value)))
    elif tag == TAG_LONG:
        out.write(struct.pack(">q", int(value)))
    elif tag == TAG_FLOAT:
        out.write(struct.pack(">f", float(value)))
    elif tag == TAG_DOUBLE:
        out.write(struct.pack(">d", float(value)))
    elif tag == TAG_STRING:
        _put_string(out, value)
    elif tag == TAG_BYTE_ARRAY:
        raw = bytes(value)
        out.write(struct.pack(">i", len(raw)))
        out.write(raw)
    elif tag == TAG_INT_ARRAY:
        out.write(struct.pack(">i", len(value)))
        for v in value:
            out.write(struct.pack(">i", int(v)))
    elif tag == TAG_LONG_ARRAY:
        out.write(struct.pack(">i", len(value)))
        for v in value:
            out.write(struct.pack(">q", int(v)))
    elif tag == TAG_LIST:
        items = list(value)
        # An empty list takes TAG_End as its element type - that is what vanilla writes for an
        # empty `entities`, and a non-zero type with zero entries is rejected by some readers.
        et = tag_of(items[0]) if items else TAG_END
        out.write(struct.pack(">b", et))
        out.write(struct.pack(">i", len(items)))
        for item in items:
            if items and tag_of(item) != et:
                raise TypeError("heterogeneous TAG_List: %r in a list of tag %d" % (item, et))
            _put_payload(out, et, item)
    elif tag == TAG_COMPOUND:
        for k, v in value.items():
            t = tag_of(v)
            out.write(struct.pack(">b", t))
            _put_string(out, k)
            _put_payload(out, t, v)
        out.write(struct.pack(">b", TAG_END))
    else:
        raise TypeError("cannot write tag %d" % tag)


def dumps(root, name=""):
    """Serialise a root compound to uncompressed NBT bytes."""
    if not isinstance(root, dict):
        raise TypeError("the NBT root must be a compound (dict)")
    out = io.BytesIO()
    out.write(struct.pack(">b", TAG_COMPOUND))
    _put_string(out, name)
    _put_payload(out, TAG_COMPOUND, root)
    return out.getvalue()


def save(path, root, name=""):
    """Write a GZIPPED structure file. Returns the number of bytes on disk."""
    raw = dumps(root, name)
    with gzip.open(path, "wb") as f:
        f.write(raw)
    import os
    return os.path.getsize(path)


# ------------------------------------------------------------------ reading
class _Reader(object):
    def __init__(self, buf):
        self.buf = buf
        self.pos = 0

    def take(self, n):
        v = self.buf[self.pos:self.pos + n]
        self.pos += n
        return v

    def u1(self):
        return struct.unpack_from(">b", self.buf, self._adv(1))[0]

    def _adv(self, n):
        p = self.pos
        self.pos += n
        return p

    def string(self):
        n = struct.unpack_from(">H", self.buf, self._adv(2))[0]
        return self.take(n).decode("utf-8", "replace")

    def payload(self, tag):
        if tag == TAG_BYTE:
            return struct.unpack_from(">b", self.buf, self._adv(1))[0]
        if tag == TAG_SHORT:
            return struct.unpack_from(">h", self.buf, self._adv(2))[0]
        if tag == TAG_INT:
            return struct.unpack_from(">i", self.buf, self._adv(4))[0]
        if tag == TAG_LONG:
            return struct.unpack_from(">q", self.buf, self._adv(8))[0]
        if tag == TAG_FLOAT:
            return struct.unpack_from(">f", self.buf, self._adv(4))[0]
        if tag == TAG_DOUBLE:
            return struct.unpack_from(">d", self.buf, self._adv(8))[0]
        if tag == TAG_STRING:
            return self.string()
        if tag == TAG_BYTE_ARRAY:
            n = struct.unpack_from(">i", self.buf, self._adv(4))[0]
            return self.take(n)
        if tag == TAG_INT_ARRAY:
            n = struct.unpack_from(">i", self.buf, self._adv(4))[0]
            return [struct.unpack_from(">i", self.buf, self._adv(4))[0] for _ in range(n)]
        if tag == TAG_LONG_ARRAY:
            n = struct.unpack_from(">i", self.buf, self._adv(4))[0]
            return [struct.unpack_from(">q", self.buf, self._adv(8))[0] for _ in range(n)]
        if tag == TAG_LIST:
            et = self.u1()
            n = struct.unpack_from(">i", self.buf, self._adv(4))[0]
            return [self.payload(et) for _ in range(n)]
        if tag == TAG_COMPOUND:
            out = {}
            while True:
                t = self.u1()
                if t == TAG_END:
                    return out
                k = self.string()
                out[k] = self.payload(t)
        raise TypeError("cannot read tag %d" % tag)


def loads(raw):
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    r = _Reader(raw)
    tag = r.u1()
    if tag != TAG_COMPOUND:
        raise ValueError("NBT root is tag %d, expected a compound" % tag)
    r.string()
    return r.payload(TAG_COMPOUND)


def load(path):
    with open(path, "rb") as f:
        return loads(f.read())


def _self_test():
    """Round-trip the shapes a structure file actually uses, including the empty list."""
    root = {
        "DataVersion": Int(2730),
        "size": [Int(3), Int(4), Int(5)],
        "entities": [],
        "palette": [{"Name": "minecraft:stone"},
                    {"Name": "minecraft:oak_log", "Properties": {"axis": "y"}}],
        "blocks": [{"pos": [Int(0), Int(1), Int(2)], "state": Int(1)}],
    }
    back = loads(dumps(root))
    assert back["size"] == [3, 4, 5], back["size"]
    assert back["entities"] == []
    assert back["palette"][1]["Properties"]["axis"] == "y"
    assert back["blocks"][0]["pos"] == [0, 1, 2]
    assert back["DataVersion"] == 2730
    return "nbt round-trip self-test passed"


if __name__ == "__main__":
    print(_self_test())
