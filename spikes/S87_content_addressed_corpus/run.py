#!/usr/bin/env python3
"""S87 — Content-Addressed Shard Ingestion and Indexing for FB15k-237 Train (272,115 Triples).

Satisfies MISSION_LOOP §8 item 2:
"Real corpus loaded (FB15k-237 train, 272,115 triples) via content-addressed shards".

Protocol:
1. Load canonical corpus/fb15k237/train.txt (272,115 triples across 237 predicates).
2. Partition triples deterministically into 237 per-predicate content-addressed shards.
3. Ingest shards into ShardStore (CIDv1 raw multihashes, sha2-256, SQLite index).
4. Verify 100% roundtrip triple parity and byte recovery.
5. Ingest master Manifest mapping each predicate -> shard CID.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "spikes" / "harness"))
sys.path.insert(0, str(ROOT / "spikes" / "M1_5_shardstore"))

import kfcheck
from provenance import Control, Falsifier
from shardstore import ShardStore, cid_of

CORPUS_DIR = ROOT / "corpus" / "fb15k237"
CORPUS_TRAIN = CORPUS_DIR / "train.txt"
STORE_DIR = HERE / "store"
N_TRIPLES_EXPECTED = 272115
N_PREDS_EXPECTED = 237


def load_train_triples(path: Path) -> list[tuple[str, str, str]]:
    triples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 3:
                parts = line.split()
            if len(parts) == 3:
                s, p, o = parts
                triples.append((s, p, o))
    return triples


def main() -> int:
    t0 = time.time()
    print("=== Spike S87: Content-Addressed Shard Ingestion for FB15k-237 Train ===")

    if STORE_DIR.exists():
        shutil.rmtree(STORE_DIR)
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    triples = load_train_triples(CORPUS_TRAIN)
    n_triples = len(triples)
    print(f"Loaded {n_triples} triples from {CORPUS_TRAIN}")

    by_pred = defaultdict(list)
    for s, p, o in triples:
        by_pred[p].append((s, p, o))

    n_preds = len(by_pred)
    print(f"Partitioned into {n_preds} predicate groups.")

    store = ShardStore(str(STORE_DIR), cap_bytes=64 << 20)

    # 1. Ingest shards
    t_ingest_start = time.time()
    manifest = {}
    total_shard_bytes = 0
    cids = set()

    for p, p_triples in sorted(by_pred.items()):
        # Encode deterministically: sorted lines
        sorted_triples = sorted(p_triples)
        payload = "\n".join(f"{s}\t{p}\t{o}" for s, p, o in sorted_triples).encode("utf-8")
        cid = store.put(payload)
        manifest[p] = {
            "cid": cid,
            "count": len(p_triples),
            "bytes": len(payload),
        }
        total_shard_bytes += len(payload)
        cids.add(cid)

    # Ingest master manifest
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    manifest_cid = store.put(manifest_bytes)
    t_ingest = time.time() - t_ingest_start
    print(f"Ingested {len(manifest)} predicate shards + master manifest ({total_shard_bytes} B) in {t_ingest:.3f}s")
    print(f"Master Manifest CID: {manifest_cid}")

    # 2. Roundtrip verification
    t_read_start = time.time()
    recovered_triples = []
    mismatch_count = 0

    # Retrieve manifest from store
    raw_m = store.get(manifest_cid)
    if raw_m is None or cid_of(raw_m) != manifest_cid:
        mismatch_count += 1
    m_recovered = json.loads(raw_m.decode("utf-8"))

    for p, meta in m_recovered.items():
        cid = meta["cid"]
        raw_shard = store.get(cid)
        if raw_shard is None or cid_of(raw_shard) != cid:
            mismatch_count += 1
            continue
        lines = raw_shard.decode("utf-8").strip().split("\n")
        for line in lines:
            if line:
                s, rel, o = line.split("\t")
                recovered_triples.append((s, rel, o))

    t_read = time.time() - t_read_start
    avg_read_lat_ms = (t_read / (len(manifest) + 1)) * 1000.0

    print(f"Roundtrip recovered {len(recovered_triples)} triples in {t_read:.3f}s (avg {avg_read_lat_ms:.3f} ms/shard)")

    # Parity check
    orig_set = set(triples)
    rec_set = set(recovered_triples)
    parity_ok = (orig_set == rec_set) and (len(recovered_triples) == n_triples)
    print(f"Parity check: {parity_ok} (orig {len(orig_set)} vs rec {len(rec_set)})")

    # Metrics & Controls
    c1_ok = n_triples == N_TRIPLES_EXPECTED
    c2_ok = parity_ok and mismatch_count == 0
    c3_ok = len(cids) == n_preds
    c4_ok = total_shard_bytes <= 32 * 1024 * 1024

    controls = [
        Control("C1_triple_count", why="Corpus must have exactly 272,115 triples", can_fail_because="corrupted corpus", null_must_contain="wrong count"),
        Control("C2_roundtrip_parity", why="100% triple parity on content-addressed roundtrip", can_fail_because="shard data loss", null_must_contain="mismatch"),
        Control("C3_unique_cids", why="All predicate shards produce distinct valid CIDs", can_fail_because="hash collision", null_must_contain="collision"),
        Control("C4_footprint", why="Total sharded corpus footprint <= 32MB", can_fail_because="bloated encoding", null_must_contain="too large"),
    ]
    controls[0].observe(c1_ok, {"n_triples": n_triples, "expected": N_TRIPLES_EXPECTED})
    controls[1].observe(c2_ok, {"parity_ok": parity_ok, "mismatches": mismatch_count})
    controls[2].observe(c3_ok, {"n_cids": len(cids), "n_preds": n_preds})
    controls[3].observe(c4_ok, {"total_bytes": total_shard_bytes})

    f1 = len(recovered_triples) != N_TRIPLES_EXPECTED
    f2 = mismatch_count > 0
    f3 = avg_read_lat_ms > 1.0

    falsifiers = [
        Falsifier("F1_data_loss", refutes="that shard store preserves 272,115 triples exactly", fires_when="recovered != 272115", null_must_contain="data loss"),
        Falsifier("F2_cid_mismatch", refutes="that shard retrieval verifies multihash integrity", fires_when="mismatch > 0", null_must_contain="cid mismatch"),
        Falsifier("F3_retrieval_latency", refutes="that shard retrieval is low-latency (<= 1.0 ms)", fires_when="avg_ms > 1.0", null_must_contain="slow read"),
    ]
    falsifiers[0].observe(f1, {"recovered": len(recovered_triples)})
    falsifiers[1].observe(f2, {"mismatches": mismatch_count})
    falsifiers[2].observe(f3, {"avg_read_lat_ms": avg_read_lat_ms})

    res = {
        "spike": "S87",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "corpus": {
            "path": str(CORPUS_TRAIN),
            "n_triples": n_triples,
            "n_predicates": n_preds,
            "total_bytes": total_shard_bytes,
            "manifest_cid": manifest_cid,
        },
        "performance": {
            "ingest_time_sec": round(t_ingest, 4),
            "retrieval_time_sec": round(t_read, 4),
            "avg_shard_read_latency_ms": round(avg_read_lat_ms, 4),
            "hits": store.hits,
            "misses": store.misses,
        },
        "verification": {
            "parity_ok": parity_ok,
            "recovered_triples": len(recovered_triples),
            "mismatch_count": mismatch_count,
        },
        "controls": {
            "C1_triple_count": {"ok": c1_ok},
            "C2_roundtrip_parity": {"ok": c2_ok},
            "C3_unique_cids": {"ok": c3_ok},
            "C4_footprint": {"ok": c4_ok},
        },
        "falsifiers": {
            "F1_data_loss": {"fired": f1},
            "F2_cid_mismatch": {"fired": f2},
            "F3_retrieval_latency": {"fired": f3},
        }
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_DIR)],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="FB15k-237 content-addressed sharding data loss or integrity failure",
        allow_dirty=True,
        note="S87: Content-addressed shard ingestion for FB15k-237 train (272,115 triples). Satisfies §8 item 2.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike S87 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
