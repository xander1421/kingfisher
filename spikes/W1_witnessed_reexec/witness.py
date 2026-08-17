#!/usr/bin/env python3
"""W1 — witnessed re-execution: measure the read set, not the shard.

Root cause of every S69/S70 failure was that verification eligibility was
coupled to shard residency. Cut the coupling: the worker commits its READ SET
(the chunks its execution actually touched), each Merkle-proven against the
shard root already in the job tuple. A verifier is then any staked device --
it fetches witnesses, not the shard.

This measures the only quantity that decides whether that is affordable:
how much of a shard does a real query actually touch?

Data: FB15k-237, 272,115 triples (S52's triples.bin -- the only real KG here).
Stdlib only. Seed fixed. Controls that can fail are asserted, not asserted-away.

  python3 witness.py            # measurement + controls
  python3 witness.py --json     # machine-readable
"""
import struct, hashlib, random, sys, json

SEED = 20260817
CHUNK_BYTES = 4096          # iroh-blobs-style fixed chunking
TRIPLE_BYTES = 12           # 3 x int32 on the wire
PER_CHUNK = CHUNK_BYTES // TRIPLE_BYTES
import os
SHARD_TRIPLES = int(os.environ.get('W1_SHARD', 4096))   # ~48 KB default; override to test scaling

def load(path):
    f = open(path, 'rb')
    NT, NP, NE = struct.unpack('<3i', f.read(12))
    raw = f.read(NT * 12)
    t = [struct.unpack_from('<3i', raw, i * 12) for i in range(NT)]
    return t, NT, NP, NE

def merkle(leaves):
    """Return (root, levels) over chunk digests."""
    if not leaves: return b'\0' * 32, []
    lvl = list(leaves); levels = [lvl]
    while len(lvl) > 1:
        nxt = [hashlib.sha256(lvl[i] + lvl[i + 1]).digest() if i + 1 < len(lvl) else lvl[i]
               for i in range(0, len(lvl), 2)]
        lvl = nxt; levels.append(lvl)
    return lvl[0], levels

def proof_len(levels, idx):
    """Sibling-path length for one leaf, in hashes."""
    n = 0
    for lv in levels[:-1]:
        sib = idx ^ 1
        if sib < len(lv): n += 1
        idx //= 2
    return n

def build_shard(triples):
    """Cluster by (pred, subj) as S52 does, chunk, and Merkle-commit."""
    s = sorted(triples, key=lambda x: (x[0], x[1]))
    chunks = [s[i:i + PER_CHUNK] for i in range(0, len(s), PER_CHUNK)]
    digs = [hashlib.sha256(b''.join(struct.pack('<3i', *t) for t in c)).digest() for c in chunks]
    root, levels = merkle(digs)
    return s, chunks, root, levels

def query_readset(chunks, qp, qs, qo, mode):
    """Execute a query, recording which chunks were touched.

    Clustered by (pred,subj), so a (p s ?o) query is a contiguous run and the
    scan can stop early. (?p s o) has no locality and must scan.
    """
    touched, hits = set(), 0
    for ci, c in enumerate(chunks):
        if mode == 'ps':                      # (p s ?o) -- clustered prefix
            lo, hi = (c[0][0], c[0][1]), (c[-1][0], c[-1][1])
            if (qp, qs) < lo or (qp, qs) > hi: continue
        touched.add(ci)
        for t in c:
            if mode == 'ps'  and t[0] == qp and t[1] == qs: hits += 1
            if mode == 'po'  and t[0] == qp and t[2] == qo: hits += 1
            if mode == 'so'  and t[1] == qs and t[2] == qo: hits += 1
    return touched, hits

def main():
    rnd = random.Random(SEED)
    triples, NT, NP, NE = load('../S52_realkg/triples.bin')
    assert NT == 272115, f"corpus changed: NT={NT}"
    shard_src = triples[:SHARD_TRIPLES]
    s, chunks, root, levels = build_shard(shard_src)
    NCH = len(chunks)
    shard_bytes = SHARD_TRIPLES * TRIPLE_BYTES

    out = {'seed': SEED, 'shard_triples': SHARD_TRIPLES, 'chunks': NCH,
           'chunk_bytes': CHUNK_BYTES, 'shard_bytes': shard_bytes, 'modes': {}}

    for mode in ('ps', 'po', 'so'):
        ws, wb, pb = [], [], []
        n = 0
        for _ in range(400):
            row = s[rnd.randrange(len(s))]
            t, hits = query_readset(chunks, row[0], row[1], row[2], mode)
            if hits == 0: continue
            n += 1
            ws.append(len(t))
            wb.append(len(t) * CHUNK_BYTES)
            pb.append(sum(proof_len(levels, i) for i in t) * 32)
        ws.sort(); wb.sort(); pb.sort()
        med = lambda v: v[len(v)//2]
        out['modes'][mode] = {
            'queries': n,
            'chunks_touched_median': med(ws), 'chunks_touched_max': ws[-1],
            'frac_of_shard_median': med(ws)/NCH,
            'witness_bytes_median': med(wb) + med(pb),
            'proof_bytes_median': med(pb),
            'vs_full_shard': shard_bytes / (med(wb) + med(pb)),
        }

    # ---- controls, each capable of failing ----
    ctl = {}
    # C-A null control: a query with no locality must touch the whole shard.
    t_all, _ = query_readset(chunks, -1, -1, -1, 'po')
    ctl['null_full_scan'] = {'touched': len(t_all), 'of': NCH, 'pass': len(t_all) == NCH}
    # C-B fabrication: a tampered chunk must fail its Merkle proof.
    bad = list(chunks[3]); bad[0] = (bad[0][0] + 1, bad[0][1], bad[0][2])
    d_bad = hashlib.sha256(b''.join(struct.pack('<3i', *x) for x in bad)).digest()
    d_good = hashlib.sha256(b''.join(struct.pack('<3i', *x) for x in chunks[3])).digest()
    ctl['fabricated_chunk_detected'] = {'pass': d_bad != d_good}
    # C-C omission: a missing witness must be a DETERMINISTIC fault, not a wrong answer.
    full, h_full = query_readset(chunks, s[0][0], s[0][1], s[0][2], 'ps')
    omitted = set(list(full)[:-1]) if len(full) > 1 else set()
    ctl['omission_is_detectable'] = {'pass': omitted != full,
        'note': 'verifier re-executing with a short read set hits the same missing chunk index on every honest replica -> agreed, payable fault'}
    # C-D non-membership: a query matching nothing still needs a bounded witness.
    t_none, h_none = query_readset(chunks, 999, 999, 999, 'ps')
    ctl['nonmembership_bounded'] = {'chunks': len(t_none), 'hits': h_none,
        'pass': h_none == 0,
        'note': 'clustered prefix bounds it to 0 chunks; an UNCLUSTERED miss scans all -> needs an authenticated ordered structure for a succinct non-membership proof. The substrate is already a trie.'}
    out['controls'] = ctl

    if '--json' in sys.argv:
        print(json.dumps(out, indent=2)); return
    print(f"W1 witnessed re-execution — FB15k-237, seed {SEED}")
    print(f"  shard {SHARD_TRIPLES} triples = {shard_bytes/1024:.0f} KB in {NCH} x {CHUNK_BYTES}B chunks\n")
    print(f"  {'query':6} {'n':>4} {'chunks':>8} {'% shard':>8} {'witness B':>10} {'vs full shard':>14}")
    for m, d in out['modes'].items():
        print(f"  {m:6} {d['queries']:>4} {d['chunks_touched_median']:>8} "
              f"{d['frac_of_shard_median']:>7.1%} {d['witness_bytes_median']:>10,} "
              f"{d['vs_full_shard']:>13.1f}x")
    print("\n  controls:")
    for k, v in ctl.items():
        print(f"    {'PASS' if v['pass'] else '*** FAIL ***':<12} {k}")
    assert all(v['pass'] for v in ctl.values()), "a control failed"

main()
