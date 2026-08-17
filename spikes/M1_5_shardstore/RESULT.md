# M1.5 — content-addressed shard store. GREEN. M1's exit criterion is now met.

**The phone fetches shards by CID, caches them, and on a warm cache runs the
whole corpus with zero bytes crossing the wire.**

Wired into M1.8, so the quorum pipeline no longer names a file path anywhere:
the job carries a CID and nothing downstream can reach the corpus.

## Measured — 67 programs, 3 workers, device gate open

| | cold cache | warm cache |
|---|---|---|
| bytes to device | **173.5 KiB** | **0.0 KiB** |
| phone median | 109.0 ms | **68.8 ms** |
| phone total | 18.0 s | 16.2 s |
| host-a median | 10.5 ms | 11.0 ms |
| verdicts | 66 UNANIMOUS / 1 NO_QUORUM | identical |

Host timings unchanged across both, which is the control: the treatment can
only touch the device path.

The 40 ms the phone saves per job is the transfer, and it is a **per-job** cost
that a residency-aware scheduler is trying to avoid — so this is the first
direct price on the locality argument that S61/S69/S70 model without measuring.

## The CID
Follows `hyperjob_v0.proto:22` — multihash authoritative, text advisory.
sha2-256 (`0x12 0x20`), text form CIDv1-raw (`0x01 0x55`) in lowercase base32
with multibase `b`, which is why every CID here reads `bafkrei…`. **Stdlib
only** — `hashlib`, `base64`, `sqlite3`. We address content; we do not join a
network, so there is no IPFS dependency.

## Invariants, and why each is asserted
`test_shardstore.py`, 22 assertions:

- **Malformed keys raise, never miss.** A store keyed by an unvalidated string
  is not content-addressed — it is a dict with extra steps.
- **Eviction is by BYTES, not entry count.** Shards differ by orders of
  magnitude (B1: 6.41 MB at B=16 vs 34.83 MB at B=1), so a count cap does not
  bound residency on a phone.
- **LRU order is checked by touching one blob and asserting the *other* is the
  victim** — an eviction test that only checks "something was evicted" passes
  for a store that evicts at random.
- **Corruption is detected and the blob deleted.** `get` re-hashes before
  serving, so a corrupt cache entry or a lying peer produces a miss, not a
  wrong answer. This is the property the whole quorum design rests on.
- **A blob larger than the cap must not wedge the store.**
- **The index survives reopen**, and dedup means identical bytes are one blob.

## What is NOT done
- **No AtomDB read subset.** PORT_PLAN M1.5 also asks for `get_atom`,
  `query_for_pattern`, `query_for_targets`, `query_for_incoming_set`,
  `atoms_exist` exposed through `space_new`'s C callback table. That is Rust/C
  work against `libhyperonc` and is untouched. **This store addresses whole
  blobs; it does not serve a graph.**
- **No canonical Atomspace serialisation.** Shards here are MeTTa source files.
  Turning a subgraph into canonical bytes is the harder half and is where a
  determinism hazard would live.
- **Device eviction is host-managed.** The phone holds a CID-named directory;
  the LRU lives on the coordinator. Fine for one device, wrong for a fleet.
- **No integrity check on the device side.** The host re-hashes on `get`; the
  phone trusts its own cache file. A device that corrupts its cache would be
  caught by quorum, not by the store.

## Files
`shardstore.py` · `test_shardstore.py` (22 assertions) ·
integration in `../M1_8_quorum3/{q3,worker}.py`
