# S4 — hyperjob v0 schema

**Verdict: GREEN.** Protobuf schema written, compiled with `protoc 35.1`, 13/13 round-trip and property assertions pass.

Files: `hyperjob_v0.proto`, `roundtrip_test.py` (+ generated `hyperjob_v0_pb2.py`).
Run: `protoc --python_out=. hyperjob_v0.proto && python roundtrip_test.py`.

```
ok   hyperjob round-trips
ok   fuel survives
ok   replication survives
ok   locality hint survives
ok   envelope round-trips
ok   seed echoes the job
ok   fuel_used present
ok   lsh modulus is prime-looking (odd, >2^15)
ok   encoding is byte-stable across 100 re-serialisations
ok   encoding is byte-stable after a parse round trip
ok   unknown v1 field is retained through a v0 parse
ok   unknown field does not disturb known fields
ok   bisection messages round-trip

Hyperjob wire size: 275 B   ResultEnvelope wire size: 220 B
FAILURES: none
```

## Why protobuf and not JSON Schema
Two properties the envelope needs are structural, not stylistic:
- **Byte-stable encoding.** `ResultEnvelope.signature` covers the canonical encoding of the other fields, and two honest devices must produce identical bytes. Verified: 100 re-serialisations give one distinct byte string, and a parse→re-serialise round trip is byte-identical. JSON key ordering and number formatting make this a fight.
- **Unknown-field retention.** A v0 relay must be able to forward a v1 envelope without invalidating its signature. Verified by appending an unknown field 999 and confirming re-serialisation reproduces the input exactly, with known fields untouched.

## What the schema says that the elders don't

| decision | rationale, with the elder it corrects |
|---|---|
| `FuelLimit.max_steps` counts **MeTTa reduction steps**, not FLOPs or seconds | BOINC's `rsc_fpops_bound` exists for the same purpose but is an *estimate-based* bound; steps are exact and identical across devices. Both hyperon (`interpret_step`) and MORK (`executing N steps`) already produce this number. |
| `deadline_secs` is explicitly *not* a result — `RESULT_DEADLINE_EXCEEDED` is unpaid infrastructure failure, while `RESULT_FUEL_EXHAUSTED` **is** a valid, agreed-upon result | Conflating the two is how you get a payment model that pays for wall clock. NuNet's six payment models are all time/resource metered (`tokenomics/contracts/payments.go`). |
| `ReplicationPolicy` is a **mode enum**, covering optimistic+challenge, quorum, and sampled audit in one field | BOINC hardcodes quorum (`min_quorum`, `target_nresults`); Gensyn hardcodes optimistic+bisection. Different job classes want different rungs; the price should differ accordingly. |
| `exclude_device_groups` | Neither BOINC nor NuNet models collusion between replicas. Replication across three phones owned by one operator verifies nothing. |
| `DevicePreferences` carries `require_charging`, `min_battery_pct`, `max_thermal_status`, `require_npu_int8` | **The gap named in `reports/REPORT_NuNet_DMS.md` blocker #6**: their `types/capability.go` has no power, thermal, or NPU dimension at all. |
| `prefer_cached_cids` | NuNet matches on *network* locality (`region`, `asn`, `rtt`); nothing in any elder matches on *which data a node already holds*. This one field is the marketplace wedge. |
| `seed` + `seed_echo` | Even for an engine with no RNG, echoing the seed makes "the job I ran" unambiguous in a dispute. |
| `BisectionProbe` / `BisectionResponse` | The Verde-shaped dispute, expressible only because `interpret_step` exists in hyperon's C ABI. |
| `LshCommitment.modulus` is transmitted and must be prime | Direct consequence of the bug found in S7. |

## Naming compatibility with NuNet (mission §10.5)
`version` as a leading string (their `version: "V1"`), `redundancy` and `failure_recovery` semantics taken from `dms/jobs/ensemble.md`, and "allocation" reserved for their meaning. A future DMS integration should be able to carry a `Hyperjob` as an allocation's execution spec (`execution.type: metta`) rather than needing a parallel scheduler. No NuNet code is copied; the vocabulary is mirrored deliberately.

## Known gaps in v0
- No shard *manifest* type — `shard_cid` is opaque, so nothing yet describes a shard's size, atom count, or layout quality. The shaping job class needs that (measuring block density before/after is the whole verification story for shaping), so v1 needs a `ShardManifest`.
- No pricing/bid message. Deliberate: the market protocol should be settled against NuNet's actual bid flow (`dms/orchestrator/bid.go`) rather than invented here.
- `attestation` is `bytes` with no discriminator; needs a platform enum once we know whether Play Integrity and App Attest can be verified by the same code path.
