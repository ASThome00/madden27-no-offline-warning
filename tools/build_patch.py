#!/usr/bin/env python3
"""
build_patch.py - rebuild the Madden 27 "No Offline Warning" patch from an ORIGINAL
legacy .AST file exported from MMC Editor (Legacy Explorer -> Export).

    python build_patch.py <original.AST> <patched.AST>

The script auto-detects which asset it was given by searching the decompressed
"Apt Data" bytecode for one of the known byte patterns below, applies the
byte change(s), recompresses with zlib level 9 (matches EA's compressor, falls
back to zopfli if the stream comes out a few bytes too large) and writes a new
archive with the ORIGINAL header/TOC/layout untouched. It refuses to write
anything if a patch site isn't found unambiguously or the recompressed entry no
longer fits the original slot.

Ported from the CFB 27 mod (cfb27-no-offline-warning); the class names are the
same in Madden because the front-end login module is literally `madden.*`.

Patches
  v1.0  common/ui/node_com/scriptpod.ast
        madden.online.module.Login._ShowLoginFailedPopup: the gate
        `if (mShowLoginFailedPopup == true)` becomes
        `if (true < mShowLoginFailedPopup)` which is never true, so the
        "ACCOUNT ERROR" login-failure popup (the one MMC fills with
        "Mods require being offline...") is never opened. The failure callback
        that runs before the gate is untouched, so login flows still complete.
                                                                0x49 -> 0x48
"""
import struct, sys, zlib

PATCHES = [
    dict(
        name="v1.0 login-failed popup gate (node_com/scriptpod.ast)",
        # DefineFunction2 canary tail, then the function body:
        # 78 56 34 12 00 00 00 00 | 73 (true) | b9 01 (PushRegister this) | af 48 (GetNamedMember mShowLoginFailedPopup) | [49] Equals2 | b8 BranchIfFalse
        # (branch operand bytes after b8 are alignment padding, so they stay out)
        pattern=bytes.fromhex("785634120000000073b901af4849b8"),
        index=13, old=0x49, new=0x48, known_offset=1024677,
    ),
]

for _pt in PATCHES:  # normalize single-byte int entries to bytes
    if isinstance(_pt["old"], int):
        _pt["old"] = bytes([_pt["old"]])
        _pt["new"] = bytes([_pt["new"]])


def toc_entries(d):
    assert d[:8] == b"BGFA1.05", "not a BGFA1.05 archive"
    toc_off = struct.unpack_from("<i", d, 16)[0]
    toc_len = struct.unpack_from("<i", d, 24)[0]
    lens = [d[33 + i] for i in range(5)]          # unknown, id, start, size, extra
    shift, add, desc = d[38], d[40] * 4, d[44]
    entry_len = sum(lens) + desc + 1
    i, out = toc_off + add, []
    while i + entry_len <= toc_off + toc_len + add:
        e = d[i + 1:i + entry_len]
        p = lens[0]
        eid = e[p:p + lens[1]]; p += lens[1]
        start = int.from_bytes(e[p:p + lens[2]], "little") << shift; p += lens[2]
        size = int.from_bytes(e[p:p + lens[3]], "little")
        out.append((eid.hex(), start, size))
        i += entry_len
    return out


def find_sites(data):
    """Return [(patch, offset, how)] for every patch whose site is in this file.
    Different assets carry different (non-overlapping) sets of patches; every
    pattern that matches is applied. A pattern with multiple hits aborts."""
    found = []
    for pt in PATCHES:
        hits = []
        k = data.find(pt["pattern"])
        while k != -1:
            hits.append(k + pt["index"])
            k = data.find(pt["pattern"], k + 1)
        if len(hits) == 1:
            found.append((pt, hits[0], "pattern"))
        elif len(hits) > 1:
            sys.exit(f"{pt['name']}: pattern is ambiguous (hits={hits})")
        else:
            ko = pt["known_offset"]
            if ko is not None and len(data) >= ko + len(pt["old"]) and data[ko:ko + len(pt["old"])] == pt["old"]:
                found.append((pt, ko, "known offset"))
    if not found:
        for pt in PATCHES:
            ko = pt["known_offset"]
            if ko is not None and len(data) >= ko + len(pt["new"]) and data[ko:ko + len(pt["new"])] == pt["new"]:
                sys.exit(f"{pt['name']}: this file is already patched")
        sys.exit("could not locate any patch site in this file (is this an original export of a supported asset?)")
    return found


def main(src, dst):
    d = open(src, "rb").read()
    apt = None
    for eid, start, size in toc_entries(d):
        raw = d[start:start + size]
        try:
            dec = zlib.decompress(raw)
        except zlib.error:
            continue
        if dec.startswith(b"Apt Data"):
            apt = (eid, start, size, dec)
    if apt is None:
        sys.exit("no 'Apt Data' entry found")
    eid, start, size, data = apt
    print(f"Apt Data entry {eid}: archive offset {start}, compressed {size}, decompressed {len(data)}")

    sites = find_sites(data)
    patched = bytearray(data)
    expected_diffs = []
    for pt, off, how in sites:
        print(f"{pt['name']}: site found by {how} at offset {off}")
        cur = bytes(patched[off:off + len(pt["old"])])
        if cur == pt["new"]:
            print("  (already patched, skipping)")
            continue
        assert cur == pt["old"], f"unexpected bytes {cur.hex()} at {off}"
        patched[off:off + len(pt["new"])] = pt["new"]
        expected_diffs.extend(range(off, off + len(pt["new"])))
    if not expected_diffs:
        sys.exit("already patched")

    comp = zlib.compressobj(9, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
    s = comp.compress(bytes(patched)) + comp.flush()
    print(f"zlib-9 recompressed size {len(s)} (slot {size})")
    if len(s) > size:
        # EA's own stream was zlib-9 and fits by construction, but one changed byte can
        # push our stream over by a few bytes. zopfli produces a smaller but still
        # standard zlib stream, so the loader can't tell the difference.
        try:
            import zopfli.zlib
        except ImportError:
            sys.exit(f"recompressed entry ({len(s)}) larger than original slot ({size}); "
                     f"install zopfli (pip install zopfli) so the entry can be shrunk to fit")
        s = zopfli.zlib.compress(bytes(patched), numiterations=15)
        print(f"zopfli recompressed size {len(s)}")
        if len(s) > size:
            sys.exit(f"zopfli output ({len(s)}) still larger than slot ({size}); layout would need rewriting")
    s = s + b"\0" * (size - len(s))          # zero-pad if smaller (inflate stops at end-of-stream)
    new = d[:start] + s + d[start + size:]
    assert len(new) == len(d)

    # verify round trip
    chk = zlib.decompress(new[start:start + size])
    diffs = [i for i in range(len(data)) if data[i] != chk[i]]
    assert diffs == sorted(i for i in expected_diffs if data[i] != patched[i]), diffs
    open(dst, "wb").write(new)
    print(f"wrote {dst}: {len(diffs)} byte(s) changed at {diffs}; header/TOC unchanged")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
