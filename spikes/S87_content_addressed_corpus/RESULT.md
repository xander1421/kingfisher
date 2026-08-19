# S87 — Content-Addressed Shard Ingestion and Indexing for FB15k-237 Train (272,115 Triples)

`certify ok=true`, 4 controls, 3 falsifiers. **MISSION_LOOP §8 item 2 certified.**

## Summary

Loaded the canonical FB15k-237 training graph (`corpus/fb15k237/train.txt`, 272,115 triples) and partitioned it into 237 content-addressed predicate shards under `ShardStore` (`CIDv1 raw`, sha2-256 multihashes, SQLite index).

- **Total Triples:** 272,115
- **Predicate Shards:** 237
- **Total Ingested Bytes:** 21,004,940 B (~20.03 MB)
- **Master Manifest CID:** `bafkreibi5yrjzjgf7gvbpry6t4xgr5rh4eldea7y4r5nest2uov2g4n2yi`
- **Roundtrip Recovery:** 272,115 triples (100% exact parity; 0 lost, 0 mutated)
- **Average Shard Retrieval Latency:** 0.520 ms

Check: `python3 kitchen/test_s87.py`
