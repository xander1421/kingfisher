# Conflict-of-interest audit — every field, against A22

**Test per field: who benefits if this value is wrong, and did they write it?**

Covers `hyperjob_v0.proto` and the live envelope in `worker.py`. A field is only
defective when it is **both** worker-supplied **and** outside anything that
compares it — cross-checking is what makes a self-reported field safe, not
honesty.

## In the quorum agreement key — a lone liar causes disagreement

| field | gates | verdict |
|---|---|---|
| `status` | acceptance, payment | **SAFE by comparison** |
| `fuel_used` | metering, payment | **SAFE by comparison** |
| `result_hash` / `results_text` | verification | **SAFE by comparison** |

These are worker-supplied and that is fine: a liar diverges from the quorum.
Note the limits established elsewhere — comparison fails against a *shared* bug
(G18), and against a nondeterministic job it launders at 21.5% (M1.8b).

## Worker-supplied and NOT compared — the actual exposure

| field | gates | status |
|---|---|---|
| `Timings.queue_ms/fetch_shard_ms/execute_ms/total_ms` (`:140-143`) | scheduling, reputation | **CONFLICT, unchecked.** Nothing today reads them; the moment scheduling does, a device profits by understating cost |
| `wall_ms` (envelope) | same | **CONFLICT, unchecked** |
| `n_results` (envelope) | nothing yet | **CONFLICT, unchecked** — not in the key, so a wrong value is invisible |
| `device_did` (`:169`) | identity, seat allocation | **CONFLICT** unless bound by `attestation` (`:171`) |
| `arch`, `os` (envelope) | previously the domain key | **FIXED** — now observed coordinator-side |

## Fixed by this work

| field | was | now |
|---|---|---|
| domain key | worker-declared `platform.node()`, own binary hash, own operator string | observed coordinator-side; `operator` pinned `UNATTESTED` |
| binary hash | worker reported what it ran | coordinator hashes what it **dispatched** |

Residual, stated: the coordinator can prove *which binary it sent*, never *which
binary was executed*. That needs attestation.

## The hole that does not exist yet — flag before it is built

`prefer_cached_cids` (`:114`) makes matching depend on **which shards a device
holds**, and `hyperjob_v0` has **no field for it**. When someone implements
locality matching, the natural shape is the device declaring its cache — *a
worker telling the matcher which jobs it should win*, which is a pure A22
violation and a direct route to the S69/S70 residency capture.

**Observed alternative:** the coordinator already knows. `M1_5_shardstore`
records every CID it pushed to the device and every cache hit (`bytes_pushed`
0 vs non-zero). Residency is derivable from what we sent, with no device claim
involved. Cheap now, ~free to keep, and it closes the hole before it opens.

## Verified-not-declared, for contrast
`seed_echo` (`:161`) must equal `Hyperjob.seed`, which the coordinator issued.
Worker-supplied and **safe**, because the checker holds the reference value.
That is the shape every conflicted field should be converted into where
possible: not "trust less", but "check against something you already hold".
