# PORT PLAN — the ranked backlog

Every row of `analysis/GAP_MATRIX.md`, expanded into concrete tasks with source repo, files, licence note, effort, and order of attack.

**Milestone 1 is fixed by the mission:** *MeTTa evaluating a job on one Android phone, scheduled at charge time, result byte-verified by one desktop.* Everything before it is ordered to serve it; everything after is ordered by (proves-the-thesis ÷ cost).

Legend: **[PORT]** lift with attribution · **[ADAPT]** rework · **[SPEC]** clean-room from a written spec · **[BUILD]** novel.

---

## M1 — "One phone, one job, one verified result" · target ~6 weeks

The critical path, in dependency order. Nothing here is research; S1/S2/S4/S6 have already de-risked the hard parts.

### M1.1 — Android app skeleton around `libhyperonc` **[ADAPT, S]**
- Source: `elders/hyperon-experimental/c/` (MIT). Build recipe proven in `spikes/S2_hyperon_android/RESULT.md`.
- Tasks: Gradle project; `cargo ndk -t arm64-v8a --platform 28` in the build; JNI shim over `metta_new_core` / `sexpr_parser_*` / `metta_run`; pass an explicit working dir via `metta_working_dir` (the `directories` crate resolves XDG paths that are unwritable on Android); **actually run it on a device** — S2 proved it links, not that it runs.
- Ship with `--no-default-features --features pkg_mgmt` (3.53 MiB, no gRPC). Verify 16 KB page alignment on an Android 15 device (cargo-ndk 4.x should already pass `-Wl,-z,max-page-size=16384`).
- Licence: MIT, NOTICE entry for SingularityNET Foundation.

### M1.2 — Fuel metering **[PORT, S]**
- Source: `c/src/metta.rs` — `interpret_init`, `interpret_step`, `step_has_next`, `step_get_result` (MIT).
- Tasks: drive evaluation stepwise from the JNI layer instead of calling `metta_run`; count steps; stop at `fuel.max_steps` and return `RESULT_FUEL_EXHAUSTED` (a *result*, agreed by every honest device — not an error); add a heap ceiling; record `fuel_used` in the envelope.
- Why first: it is the unit of work, the unit of payment, the unit of interruption, and the unit of dispute. Everything downstream depends on it existing.

### M1.3 — Charge-time worker **[SPEC→code, S]**
- Source: `spikes/S6_scheduler/SCHEDULER_SPEC.md` (derived from BOINC, LGPL — **no code copied**).
- Tasks: `CoroutineWorker` + the five declarative constraints; in-worker preflight for thermal status (`PowerManager.getCurrentThermalStatus()`), battery floor (default 90 %), and cache space; `BackoffPolicy.EXPONENTIAL, 5 min`; honour `onStopped()` by checkpointing at a fuel boundary.

### M1.4 — Job/result wire format **[SPEC, S — mostly done]**
- Source: `spikes/S4_hyperjob_schema/` (compiled, 13/13 assertions pass).
- Remaining: add `ShardManifest` (size, atom count, layout quality) and a `platform` discriminator on `attestation`; generate Rust and Kotlin bindings; sign the envelope for real (S4 uses a SHA-256 stand-in).

### M1.5 — Minimal shard store **[SPEC, M]**
- Source: IPLD CID conventions; `elders/das/src/atomdb/AtomDB.h` for the read interface (Apache-2.0).
- Tasks: canonical serialisation of an Atomspace subgraph → CID; a phone-side LRU cache keyed by CID; implement the AtomDB *read* subset over it (`get_atom`, `query_for_pattern`, `query_for_targets`, `query_for_incoming_set`, `atoms_exist` — writes may be refused); expose it to the interpreter through `space_new`'s C callback table so no Rust changes are needed.

### M1.6 — Desktop verifier **[SPEC, S]**
- Source: the *design* of `elders/MORK/differential/run.py` (**MORK is licence-UNKNOWN — reimplement from the description in `reports/REPORT_MORK.md` §4, do not copy**).
- Tasks: run the same `(shard_cid, program, fuel, seed)` on the desktop; compare `result_hash` **and** `fuel_used` byte for byte; on mismatch, log both envelopes. Two devices, one comparison — the process boundary is the only difference from MORK's harness.

### M1.7 — Phone-initiated transport **[ADAPT, S]**
- Source: `elders/prime-rl/src/prime_rl/transport/` for the pattern (Apache-2.0).
- Tasks: HTTP long-poll or equivalent; **the phone always dials**, never listens (S8's finding: the DAS bus dials clients back, and a phone cannot accept that). Ship a filesystem-backed transport too — prime-rl's trick for testing a whole pipeline without a network.

**M1 exit criterion**: a phone plugged in overnight fetches a shard by CID, evaluates a MeTTa program under a fuel limit, uploads an envelope, and a desktop reproduces `result_hash` and `fuel_used` exactly. No market, no payment, no attestation.

---

## M2 — "The NPU earns its place" · target ~8 weeks

### M2.1 — INT8 bit-exactness on real silicon **[BUILD, S — do this before anything else in M2]**
- The whole rung-2 design rests on INT8×INT8→INT32 being exact on device. Some NNAPI/Core ML paths requantise or accumulate narrow. **Measure it**: same input, phone vs desktop, byte-compare. If it fails, adopt TOPLOC's tolerance model wholesale (MIT, 1,200 lines) and say so.

### M2.2 — One-matmul similarity model **[BUILD, M]**
- Export the S5 kernel (`Q @ T.T`, INT8) to Core ML and LiteRT; benchmark against the CPU path; find the shard size where the NPU wins. Reuse MORK's crossover *methodology* (log-grid density sweep, single-thread baseline, abort at 4× — `reports/REPORT_MORK.md` §4) rather than inventing one.
- Operating point from S5: **D=1024**, 102 MB per 100k triples, margin 0.68.

### M2.3 — Two-stage query path **[BUILD, S]**
- NPU pre-filter → analytic threshold `2·|{d : Q_d ≠ 0}|` → exact MeTTa match on the shortlist. S5 measured recall 1.0 / zero false positives for two-bound-slot patterns; **extend the measurement to patterns S5 did not test**: two free slots, repeated variables, nested expressions. Those will be genuinely approximate.

### M2.4 — Rung-2 commitments **[PORT, S]**
- `spikes/S7_toploc_adapt/commit.py` productionised in Rust; k=16 default (66 B); **prime modulus enforced** (the upstream bug we found); file an issue on `PrimeIntellect-ai/toploc`.

---

## M3 — "A market with two sides" · target ~1 quarter

### M3.1 — NuNet capability extension **[ADAPT, M]**
- Source: `elders/nunet-dms/types/{capability,hardware,resources}.go` (Apache-2.0).
- Add power state, charging, thermal headroom, metered-network flag, NPU/INT8 capability, and cached-CID advertisement. **This is the concrete upstream contribution that makes us a NuNet extension rather than a fork** — propose it as an MR early, before we depend on it.

### M3.2 — `executor/metta` **[ADAPT, M]**
- Source: `elders/nunet-dms/executor/null/executor.go` as the skeleton (~150 LOC, Apache-2.0); `types/executor.go` for the 20-method interface.
- `Run` drives `interpret_step`; `Stats` reports fuel, not CPU%; `Pause`/`Resume` are genuinely implementable because the interpreter is stepwise (containers can only approximate this).

### M3.3 — Locality-aware matcher **[BUILD, L]**
- Tick-based sealed auction at a block boundary, **never first-come-first-served** (Akash `x/market/keeper/keeper.go`: `CreateLease` "should only be called by the EndBlock handler"). Score bids by price × data locality (`prefer_cached_cids`) × device readiness (charging, thermal, idle).
- Borrow Golem's flat namespaced property bag (`ya-client/specs/market-api.yaml`) so new capabilities don't require schema changes, and its `propertyQuery` so the matcher can ask a phone "how long would this shard take for you?" — **LGPL, so specification only**.

### M3.4 — Replication and disputes **[SPEC, M]**
- Optimistic + staked challenge with **⌈log₂(steps)⌉ bisection** over `interpret_step` (Verde, `papers/gensyn_verde_2502.19405.pdf`; our `BisectionProbe`/`BisectionResponse`).
- **Add commit/reveal with a worker-bound seal** — `iExecBlockchainComputing/PoCo/contracts/facets/IexecPoco2Facet.sol:106` (Apache-2.0). *This is a gap in our own S4 schema*: without a seal binding the hash to the worker, a second replica can copy the first's answer and replication proves nothing. Highest-value single fix identified by this recon.
- Adopt PoCo's per-job **`trust`** parameter in place of a fixed quorum count: `group_weight × trust > total_weight × (trust − 1)`.
- Anti-collusion: enforce `exclude_device_groups` by operator, attestation root, and network origin.

### M3.5 — Settlement **[ADAPT, M]**
- Source: `elders/nunet-dms/tokenomics/contracts/processors/*.go` (Apache-2.0) — one file per payment model.
- Add `pay_per_verified_result`; net off-chain, settle on-chain in batches. **Never one transaction per contribution** (the reason PoCo's design cannot be lifted as-is).

### M3.6 — Attestation **[ADAPT, M]**
- Source: `elders/nunet-dms/lib/ucan/` + `lib/did/` (Apache-2.0); Akash `x/audit`/`x/cert` for the "third party vouches for an attribute" pattern.
- Play Integrity / App Attest verified server-side, issued as a UCAN capability from a vetting anchor. No new trust model needed — NuNet's README already describes this role.

---

## M4 — "The beak" · target ~1 quarter, and the reason the project is interesting

### M4.1 — Shard layout metrics **[BUILD, M]**
- Define layout quality: block density at the tile size the NPU wants, plus locality of the incoming/outgoing sets. Measure before and after. Put it in `ShardManifest`.

### M4.2 — Shaping as a paid job class **[BUILD, L]**
- Morton-order and community-detection reordering of atoms within a shard; the product is a new CID with a better manifest.
- **Verification is trivial and that is the point**: recompute the density metric on the output shard. No replication, no challenge, no bisection.
- Pricing must reflect the externality: shaping makes *future* jobs cheaper, so the marketplace should pay it out of a levy on the jobs that subsequently run on the shaped shard.
- The number that justifies it (S3): CSR beats dense BLAS below ~5–9 % density and by ~10,000× at 0.01 %. Shaping does not change global density — it concentrates it into tiles.

### M4.3 — ARM NEON kernels for `linalg` **[contribution, M — blocked on licence]**
- `elders/MORK/linalg/src/blocked.rs:31-117` is `x86_64 + avx2 + fma` only. Our fleet is entirely ARM. **Blocked on MORK having no licence** — see M0.1.

### M4.4 — Attention-driven replication **[PORT, S]**
- `get_importance(HandleList) → ImportanceList` from the DAS attention broker (Apache-2.0) drives replica count; `stimulate(HandleCount)` reports what each job touched. Consume the existing service; do not build one.

---

## M0 — Do these in week 1, they are cheap and they unblock others

| # | task | why |
|---|---|---|
| **M0.1** | **Ask trueagi-io to put a licence on MORK.** | One issue. It currently makes the fastest engine, the fuel counter, the differential harness and the crossover benches untouchable. Several GAP rows flip from SPEC to PORT if they say "MIT". |
| M0.2 | PR hyperon: `#[cfg(feature = "pkg_mgmt")]` on `builtin_mods/json.rs` | `--no-default-features` currently fails to compile (8 errors). Unblocks a truly minimal phone build. |
| M0.3 | Issue on `PrimeIntellect-ai/toploc`: `find_injective_modulus` must return a **prime** | Fermat inversion needs it; 1 in 20 of our commitments failed honest verification. Two-line fix. |
| M0.4 | Issues on das-toolbox: config wizard omits `agents.command_router.http_api`; docker SDK ignores the active docker context | Both block a first-time contributor on macOS. Cost us 20 minutes each. |
| M0.5 | Clone `PrimeIntellect-ai/prime` and read `shardcast` | The mission asked for it; it is not in prime-rl or OpenDiLoCo (`BLOCKED.log`). It is the closest existing answer to shard distribution. |
| M0.6 | Report MORK's `/dev/shm` hardcoding (`kernel/src/space.rs:35`) | One line; blocks macOS and Android entirely. |

## Ordering rationale
M1 is sequenced to make the *thesis* falsifiable as early as possible: if MeTTa cannot run under a fuel limit inside a WorkManager window and be byte-reproduced by a desktop, nothing else matters and we should learn that in week 6, not month 6. M2 is gated on a single measurement (M2.1) that could invalidate the rung-2 design; do it first and cheaply. M3 is deliberately last of the "make it work" phases because every part of it exists in some form in NuNet and can be negotiated with upstream rather than written. M4 is the differentiator, and it is scheduled after the market exists because a shaping job with no marketplace to price it is a research demo.
