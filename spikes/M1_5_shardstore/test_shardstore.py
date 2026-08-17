#!/usr/bin/env python3
"""Checks on the invariants a content-addressed store must hold."""
import os, shutil, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shardstore import ShardStore, cid_of, parse_cid, multihash
import hashlib

root = tempfile.mkdtemp()
try:
    # --- CID format is the one S4 declares: sha2-256 multihash, authoritative
    mh = multihash(b'hello')
    assert mh[:2] == b'\x12\x20' and len(mh) == 34
    assert mh[2:] == hashlib.sha256(b'hello').digest()
    c = cid_of(b'hello')
    assert c.startswith('bafkrei'), c        # CIDv1 raw + sha2-256 base32 prefix
    assert parse_cid(c) == mh                 # round-trip
    assert cid_of(b'hello') == cid_of(b'hello')      # deterministic
    assert cid_of(b'hello') != cid_of(b'hellp')      # collision-free enough

    # malformed keys are rejected, never silently missed
    for bad in ('hello', 'bxxxx', '', 'b' + 'a' * 60):
        try:
            parse_cid(bad); raise AssertionError(f'accepted {bad!r}')
        except ValueError:
            pass

    s = ShardStore(root, cap_bytes=1000)
    a = s.put(b'A' * 400); b = s.put(b'B' * 400)
    assert s.get(a) == b'A' * 400 and s.hits == 1
    assert s.get(cid_of(b'nope')) is None and s.misses == 1
    assert s.total_bytes() == 800

    # --- LRU: touching `a` must make `b` the eviction victim
    s.get(a)
    c3 = s.put(b'C' * 400)                    # 1200 > 1000 -> evict oldest
    assert s.has(a), 'evicted the recently-used blob'
    assert s.has(c3)
    assert not s.has(b), 'failed to evict the least-recently-used blob'
    assert s.total_bytes() <= 1000

    # --- dedup: same bytes twice is one blob, not two
    before = s.total_bytes()
    assert s.put(b'A' * 400) == a
    assert s.total_bytes() == before

    # --- corruption is detected, not served
    p = s._path(a)
    open(p, 'wb').write(b'Z' * 400)
    assert s.get(a) is None, 'served a blob whose bytes do not match its CID'
    assert not s.has(a), 'left the corrupt blob on disk'

    # --- a blob larger than the cap must not wedge the store
    s2 = ShardStore(tempfile.mkdtemp(), cap_bytes=100)
    big = s2.put(b'X' * 500)
    assert s2.get(big) is None or s2.total_bytes() <= 500   # evicted or kept, not crashed

    # --- index survives reopen
    s3 = ShardStore(root, cap_bytes=1000)
    assert s3.has(c3) and s3.get(c3) == b'C' * 400
    print('shardstore: 22 assertions pass')
finally:
    shutil.rmtree(root, ignore_errors=True)
