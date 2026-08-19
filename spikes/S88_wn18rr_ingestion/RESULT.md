# S88 — WN18RR Canonical Ingestion & Content-Addressed Sharding

`certify ok=true`, 3 controls, 3 falsifiers. **Official WN18RR benchmark ingested from canonical commit 2e440e0, verified with exact SHA256 checksums, and partitioned into 11 content-addressed predicate shards with 100% roundtrip triple parity.**

## Dataset Metadata & Properties

* **Domain:** WordNet Lexical & Hierarchical Knowledge Graph (Dettmers et al., AAAI 2018).
* **Vocabulary:** 40,943 entities, 11 relation predicates.
* **Split Counts:**
  * `train.txt`: 86,835 triples (`038612e783c215ee5f3ca9fbfca27b8d0739be1028fe4ee7c174aecf0b83d5df`)
  * `valid.txt`: 3,034 triples (`453ce7202afa58094a04d2b1560ee2b02660f1c260b32ce6651c8ccedd1028ab`)
  * `test.txt`: 3,134 triples (`0383bceaaa1096cf3c03ec021ed0048068e2355dbfc0239b292cefdac821cec5`)
* **Content-Addressed Master Manifest:** `bafkreicguk6k72apxdfs6jsslzl2motb3sxjdrkysziaegxcyo5icx7hom`
* **Performance:** 86,835 triples ingested into SQLite-indexed CIDv1 blocks in $0.032\,\text{s}$ ($2.68\times 10^6\,\text{triples/s}$), read latency $1.515\,\text{ms}$/shard with $0$ lost and $0$ mutated triples.

Check: `python3 kitchen/test_s88.py`
