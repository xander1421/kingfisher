#!/usr/bin/env python3
"""S88 — WN18RR Canonical Ingestion & Content-Addressed Sharding.

Ingests the official WN18RR benchmark (86,835 train, 3,034 valid, 3,134 test triples)
from DeepGraphLearning/KnowledgeGraphEmbedding@2e440e0, verifies all file hashes against
SOURCE.txt, and partitions train into 11 content-addressed predicate shards under ShardStore.
"""
from __future__ import annotations

import hashlib
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
from shardstore import ShardStore

CORPUS_WN = ROOT / "corpus" / "wn18rr"
STORE_DIR = HERE / "store"

PIN_F001 = "590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f"
PIN_F002 = "c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9"

EXPECTED_HASHES = {
    "train.txt": "038612e783c215ee5f3ca9fbfca27b8d0739be1028fe4ee7c174aecf0b83d5df",
    "valid.txt": "453ce7202afa58094a04d2b1560ee2b02660f1c260b32ce6651c8ccedd1028ab",
    "test.txt": "0383bceaaa1096cf3c03ec021ed0048068e2355dbfc0239b292cefdac821cec5",
    "entities.dict": "3dc41455a835d7523b68a2d449a8ae9429ba8cf8be7db7e29b4cbadf6fbc092f",
    "relations.dict": "0cf033f5ea243c938d86e8e5e89b43676df040b9196ce495b92382e54ad59916",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_triples(path: Path) -> list[tuple[str, str, str]]:
    triples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 3:
                s, p, o = parts
                triples.append((s, p, o))
    return triples


def main() -> int:
    t0 = time.time()
    print("=== Spike S88: WN18RR Canonical Ingestion & Content-Addressed Sharding ===")

    # 1. Verify File Checksums
    print("Verifying official WN18RR file checksums against SOURCE.txt...")
    actual_hashes = {}
    hash_mismatches = []
    for fname, exp_hash in EXPECTED_HASHES.items():
        fpath = CORPUS_WN / fname
        if not fpath.is_file():
            hash_mismatches.append(f"{fname}: MISSING")
            continue
        act_hash = sha256_file(fpath)
        actual_hashes[fname] = act_hash
        if act_hash != exp_hash:
            hash_mismatches.append(f"{fname}: {act_hash} != {exp_hash}")
        else:
            print(f"  {fname}: OK ({act_hash[:16]}...)")

    if hash_mismatches:
        print(f"FAILED: Hash mismatches found: {hash_mismatches}")
        return 1

    # 2. Parse Splits
    train_triples = load_triples(CORPUS_WN / "train.txt")
    valid_triples = load_triples(CORPUS_WN / "valid.txt")
    test_triples = load_triples(CORPUS_WN / "test.txt")

    n_train = len(train_triples)
    n_valid = len(valid_triples)
    n_test = len(test_triples)
    print(f"Parsed splits: train={n_train}, valid={n_valid}, test={n_test}")

    entities = set()
    relations = set()
    for s, p, o in train_triples + valid_triples + test_triples:
        entities.add(s)
        entities.add(o)
        relations.add(p)

    n_entities = len(entities)
    n_relations = len(relations)
    print(f"Vocabulary: {n_entities} entities, {n_relations} relations.")

    # 3. Content-Addressed Sharding under ShardStore
    if STORE_DIR.exists():
        shutil.rmtree(STORE_DIR)
    STORE_DIR.mkdir(parents=True, exist_ok=True)

    store = ShardStore(STORE_DIR)
    by_predicate = defaultdict(list)
    for s, p, o in train_triples:
        by_predicate[p].append((s, o))

    t_ingest0 = time.time()
    shard_manifest = {}
    total_sharded_bytes = 0
    for p_name, pairs in sorted(by_predicate.items()):
        # Canonical binary format: UTF-8 lines of "s\to\n"
        raw_lines = "".join(f"{s}\t{o}\n" for s, o in sorted(pairs))
        raw_bytes = raw_lines.encode("utf-8")
        cid = store.put(raw_bytes)
        shard_manifest[p_name] = {
            "cid": cid,
            "count": len(pairs),
            "bytes": len(raw_bytes),
        }
        total_sharded_bytes += len(raw_bytes)

    # Put master manifest
    manifest_bytes = json.dumps(shard_manifest, sort_keys=True, indent=2).encode("utf-8")
    master_manifest_cid = store.put(manifest_bytes)
    t_ingest = time.time() - t_ingest0

    print(f"Sharded {n_train} triples into {len(shard_manifest)} predicate shards.")
    print(f"Master Manifest CID: {master_manifest_cid}")
    print(f"Ingestion time: {t_ingest:.3f}s ({n_train / t_ingest:.1f} triples/s)")

    # 4. Roundtrip Parity Verification
    t_read0 = time.time()
    recovered_manifest_bytes = store.get(master_manifest_cid)
    recovered_manifest = json.loads(recovered_manifest_bytes.decode("utf-8"))

    recovered_triples = []
    for p_name, meta in sorted(recovered_manifest.items()):
        cid = meta["cid"]
        shard_data = store.get(cid).decode("utf-8")
        for line in shard_data.splitlines():
            line = line.strip()
            if line:
                s, o = line.split("\t")
                recovered_triples.append((s, p_name, o))
    t_read = time.time() - t_read0

    orig_set = set(train_triples)
    rec_set = set(recovered_triples)
    lost_count = len(orig_set - rec_set)
    mutated_count = len(rec_set - orig_set)
    parity_ok = (len(recovered_triples) == n_train) and (lost_count == 0) and (mutated_count == 0)

    print(f"Roundtrip parity: ok={parity_ok} (recovered {len(recovered_triples)}/{n_train}, lost={lost_count}, mutated={mutated_count})")
    print(f"Read latency: {t_read * 1000 / len(shard_manifest):.3f} ms/shard")

    # Metrics & Controls
    c1_ok = len(hash_mismatches) == 0
    c2_ok = len(shard_manifest) == 11
    c3_ok = len(set(train_triples) & set(test_triples)) == 0

    controls = [
        Control("C1_official_hashes", why="All WN18RR split file hashes match SOURCE.txt", can_fail_because="corrupted or unpinned download", null_must_contain="hash mismatch"),
        Control("C2_shard_count", why="Exactly 11 predicate shards created", can_fail_because="missing predicates", null_must_contain="wrong shard count"),
        Control("C3_zero_leak", why="0 overlap between train and test triples", can_fail_because="data leakage", null_must_contain="train/test leakage"),
    ]
    controls[0].observe(c1_ok, {"actual_hashes": actual_hashes})
    controls[1].observe(c2_ok, {"n_shards": len(shard_manifest)})
    controls[2].observe(c3_ok, {"train_test_overlap": len(set(train_triples) & set(test_triples))})

    f1 = not parity_ok
    f2 = len(hash_mismatches) > 0
    f3 = n_train != 86835

    falsifiers = [
        Falsifier("F1_roundtrip_loss", refutes="that ShardStore recovers 100% of triples with 0 mutations", fires_when="not parity_ok", null_must_contain="triple lost or mutated"),
        Falsifier("F2_hash_mismatch", refutes="that official split files match commit 2e440e0 hashes", fires_when="len(hash_mismatches) > 0", null_must_contain="hash mismatch"),
        Falsifier("F3_train_count", refutes="that train set contains exactly 86,835 triples", fires_when="n_train != 86835", null_must_contain="wrong train count"),
    ]
    falsifiers[0].observe(f1, {"lost": lost_count, "mutated": mutated_count})
    falsifiers[1].observe(f2, {"mismatches": hash_mismatches})
    falsifiers[2].observe(f3, {"n_train": n_train})

    res = {
        "spike": "S88",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 2),
        "dataset": "WN18RR (WordNet hierarchical semantic graph)",
        "source": {
            "git": "https://github.com/DeepGraphLearning/KnowledgeGraphEmbedding",
            "commit": "2e440e0f9c687314d5ff67ead68ce985dc446e3a",
            "citation": "Dettmers et al. (AAAI 2018)",
        },
        "stats": {
            "train_triples": n_train,
            "valid_triples": n_valid,
            "test_triples": n_test,
            "entities": n_entities,
            "relations": n_relations,
            "predicate_shards": len(shard_manifest),
            "master_manifest_cid": master_manifest_cid,
            "total_sharded_bytes": total_sharded_bytes,
        },
        "benchmarks": {
            "ingestion_sec": round(t_ingest, 3),
            "ingestion_triples_per_sec": round(n_train / t_ingest, 1),
            "recovery_sec": round(t_read, 3),
            "read_latency_ms_per_shard": round(t_read * 1000 / len(shard_manifest), 3),
        },
        "controls": {
            "C1_official_hashes": {"ok": c1_ok},
            "C2_shard_count": {"ok": c2_ok},
            "C3_zero_leak": {"ok": c3_ok},
        },
        "falsifiers": {
            "F1_roundtrip_loss": {"fired": f1},
            "F2_hash_mismatch": {"fired": f2},
            "F3_train_count": {"fired": f3},
        }
    }

    out_json = HERE / "result.json"
    out_json.write_text(json.dumps(res, indent=2) + "\n")

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(CORPUS_WN)],
        artifacts=[str(out_json)],
        controls=controls,
        falsifiers=falsifiers,
        captures=[("result_json", json.dumps(res, sort_keys=True))],
        falsifier="WN18RR ingestion fails hash verification or roundtrip parity",
        allow_dirty=True,
        note="S88: WN18RR Canonical Ingestion & Content-Addressed Sharding.",
    )
    print(f"\nD6 Provenance Certified: ok={ok}")
    for pr in problems:
        print(f"  PROBLEM: {pr}")

    print(f"\n=== Spike S88 Completed in {time.time()-t0:.2f}s ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
