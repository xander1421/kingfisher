#!/usr/bin/env python3
"""M1.5 — content-addressed shard store with LRU eviction.

CID format follows `spikes/S4_hyperjob_schema/hyperjob_v0.proto:22`: the
multihash is authoritative, the text form is advisory. Multihash is
sha2-256 (code 0x12, length 0x20); the text form is CIDv1 raw
(<0x01><0x55><multihash>) in lowercase base32 with the 'b' multibase prefix.

Stdlib only: hashlib for the digest, base64 for base32, sqlite3 for the index.
No IPFS dependency -- we address content, we do not join a network.
"""
import base64, hashlib, os, sqlite3, time

MH_SHA2_256 = b'\x12\x20'          # multihash: code 0x12, length 32
CIDV1_RAW   = b'\x01\x55'          # version 1, codec raw

def multihash(data: bytes) -> bytes:
    return MH_SHA2_256 + hashlib.sha256(data).digest()

def cid_text(mh: bytes) -> str:
    b32 = base64.b32encode(CIDV1_RAW + mh).decode('ascii').rstrip('=').lower()
    return 'b' + b32

def cid_of(data: bytes) -> str:
    return cid_text(multihash(data))

def parse_cid(text: str) -> bytes:
    """Return the multihash from a text CID. Raises on anything malformed --
    a store keyed by an unvalidated string is not content-addressed."""
    if not text.startswith('b'):
        raise ValueError(f'not base32 multibase: {text[:12]!r}')
    body = text[1:].upper()
    body += '=' * (-len(body) % 8)
    raw = base64.b32decode(body)
    if raw[:2] != CIDV1_RAW:
        raise ValueError('not a CIDv1 raw block')
    mh = raw[2:]
    if mh[:2] != MH_SHA2_256 or len(mh) != 34:
        raise ValueError('not sha2-256/32')
    return mh


class ShardStore:
    """Content-addressed blobs on disk, LRU-evicted against a byte budget.

    Eviction is by total bytes, not entry count: shards differ in size by
    orders of magnitude (B1: 6.41 MB at B=16 vs 34.83 MB at B=1), so a count
    cap would not bound residency on a phone.
    """

    def __init__(self, root: str, cap_bytes: int = 64 << 20):
        self.root = root
        self.cap = cap_bytes
        os.makedirs(os.path.join(root, 'blobs'), exist_ok=True)
        self.db = sqlite3.connect(os.path.join(root, 'index.db'))
        self.db.execute('''CREATE TABLE IF NOT EXISTS blobs(
            cid TEXT PRIMARY KEY, size INTEGER NOT NULL, atime REAL NOT NULL)''')
        self.db.commit()
        self.hits = self.misses = 0

    def _path(self, cid: str) -> str:
        # two-level fanout: a flat dir of 100k shards is slow to list on ext4
        return os.path.join(self.root, 'blobs', cid[1:4], cid)

    def put(self, data: bytes) -> str:
        cid = cid_of(data)
        p = self._path(cid)
        if not os.path.exists(p):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            tmp = p + '.tmp'
            with open(tmp, 'wb') as f:
                f.write(data)
            os.rename(tmp, p)                      # atomic: no torn blobs
        self.db.execute(
            'INSERT OR REPLACE INTO blobs VALUES(?,?,?)', (cid, len(data), time.time()))
        self.db.commit()
        self.evict()
        return cid

    def get(self, cid: str) -> bytes | None:
        parse_cid(cid)                             # reject malformed keys
        p = self._path(cid)
        if not os.path.exists(p):
            self.misses += 1
            return None
        data = open(p, 'rb').read()
        if cid_of(data) != cid:
            # corruption or a lying peer; a content-addressed store must notice
            os.remove(p)
            self.db.execute('DELETE FROM blobs WHERE cid=?', (cid,))
            self.db.commit()
            self.misses += 1
            return None
        self.db.execute('UPDATE blobs SET atime=? WHERE cid=?', (time.time(), cid))
        self.db.commit()
        self.hits += 1
        return data

    def has(self, cid: str) -> bool:
        return os.path.exists(self._path(cid))

    def total_bytes(self) -> int:
        return self.db.execute('SELECT COALESCE(SUM(size),0) FROM blobs').fetchone()[0]

    def evict(self) -> list:
        """Drop least-recently-used blobs until under cap. Returns evicted cids."""
        gone = []
        total = self.total_bytes()
        if total <= self.cap:
            return gone
        for cid, size in self.db.execute(
                'SELECT cid,size FROM blobs ORDER BY atime ASC').fetchall():
            if total <= self.cap:
                break
            p = self._path(cid)
            if os.path.exists(p):
                os.remove(p)
            self.db.execute('DELETE FROM blobs WHERE cid=?', (cid,))
            total -= size
            gone.append(cid)
        self.db.commit()
        return gone
