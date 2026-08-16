# RISKS — top 10, with mitigations

Ordered by (probability × damage). Every risk is anchored to something observed in this recon, not imagined.

---

## 1. Verification economics: nobody pays for the second run
**Observed:** S7 measured it directly — verifying a rung-2 job costs **85 ms of recomputation** against 0.005–0.688 ms of commitment checking. The commitment is free; **re-execution is the entire cost**. TOPLOC's advertised "100× faster validation" is a latency artefact of autoregressive decode that our workload does not have. Verde names the same problem as unsolved: *"incentives are needed to compensate trainers both for running the original"* computation and verifying it.
**Damage:** if every job is replicated, the network's useful throughput halves and our price per unit of work doubles against centralised compute. If no job is replicated, results are unverified and the token is a lottery.
**Mitigation:** never replicate by default. Ship `REPLICATION_SAMPLED_AUDIT` with a tunable `audit_rate` as the normal mode (S4 schema), and make the *penalty*, not the *probability*, carry the deterrence: stake seizure sized so that `audit_rate × stake > expected gain from cheating`. Reserve full quorum for jobs the requestor explicitly pays extra for (PoCo's per-job `trust`). Use the free signals first: fuel-count mismatch is a cheat detector that costs nothing to check.
**Early warning:** model the economics *before* M3.5, with real numbers from M1's measured job costs.

## 2. MORK's missing licence
**Observed:** no LICENSE file, no `license` key in any of 12 `Cargo.toml`s, zero grep hits for "license" in any `.md`. Verified three ways (`analysis/LICENSE_LEDGER.md`).
**Damage:** the fastest exact engine, the fuel counter, the differential harness and the crossover benchmarks are all legally untouchable. Six GAP rows sit at SPEC that could be PORT. Worse, an incautious contributor may copy from it anyway, contaminating the codebase.
**Mitigation:** M0.1 — ask. It is almost certainly an oversight in an otherwise open ecosystem. Until then: hyperon on phones (MIT, and it already cross-compiles), MORK only as a black box behind a process boundary on desktops, and every MORK-derived document in this workspace written as a behavioural description rather than a transcription. Add a CI check that no file in our tree carries MORK provenance.
**Do not** assume "SingularityNET ecosystem" implies a licence grant. It does not.

## 3. MORK's portability: nightly + jemalloc + `/dev/shm`
**Observed:** `kernel/src/space.rs:35` hardcodes `ACT_PATH = "/dev/shm/"` — absent on macOS *and* Android; `mork test` panics on it. Edition 2024 plus a dep using `feature(core_intrinsics)` means **nightly is mandatory and undeclared** (no `rust-toolchain.toml`). PathMap is pulled with the `jemalloc` feature, untested against Android's 16 KB pages. Cargo already flags `mork` itself as future-incompatible.
**Damage:** any plan that puts MORK on a phone is a plan to fork and maintain three separate patches, on a nightly pin, in a codebase we may not legally modify (risk 2).
**Mitigation:** treat MORK as Linux-desktop-only for at least a year. The `/dev/shm` fix is one line and worth reporting (M0.6). Do not let the device agent inherit a nightly pin — hyperon builds on stable and that is a feature worth protecting.

## 4. The NPU may not be bit-exact
**Observed:** S5's entire result — recall 1.0, zero false positives, an analytic threshold — assumes INT8×INT8→INT32 with exact integer accumulation. That is true of numpy and of the ISA; it is **not guaranteed** of an NNAPI or Core ML delegate, which may requantise, saturate, or accumulate narrow. **Nothing in this mission ran on an NPU.**
**Damage:** if inexact, the analytic threshold stops being a proof, rung 2 stops collapsing into rung 1, and TOPLOC's tolerance model (with its accept/reject threshold, its grey-zone disputes, and its tuning) comes back.
**Mitigation:** M2.1 measures this before anything else in M2 — same input, phone vs desktop, byte-compare. Cheap, decisive, and it is written into the plan as a gate. Fallback is known and small: TOPLOC is MIT and 1,200 lines.

## 5. iOS is not addressable, and half the premium fleet is iOS
**Observed:** `BGProcessingTaskRequest` (`requiresExternalPower`, `requiresNetworkConnectivity`) grants runtime opportunistically with no completion guarantee and a hard expiration handler. BOINC — twenty years of consumer-device scheduling — **ships no iOS client**, and this is why.
**Damage:** the addressable fleet shrinks to Android, and the devices with the best NPUs per watt are largely excluded. It also weakens the pitch: "every phone" becomes "some phones".
**Mitigation:** be explicit rather than optimistic. Android-only through M3. If iOS is attempted, scope it to small best-effort rung-2 pre-filter jobs that are never on a critical path, and design the market so a device that vanishes mid-job costs the requestor nothing (Akash's `ReclamationWindow` + `LeaseStartReclaim` is the pattern).

## 6. NuNet coupling: we extend a stack we do not control
**Observed:** our plan puts a power/thermal/NPU dimension into `types/capability.go`, a `metta` executor next to `executor/null/`, and a seventh payment model into `tokenomics/contracts/processors/`. All three are additive — and all three require upstream to accept them. NuNet's DMS is 165k LOC of Go with its own roadmap, and its build matrix is Linux/macOS/Windows with a `.deb` + systemd packaging model that assumes a daemon (`reports/REPORT_NuNet_DMS.md` blocker #2).
**Damage:** if the capability-model MR is rejected or stalls, we either fork (and inherit 165k LOC) or maintain a patch set against a moving target. Golem is the cautionary tale in this very report set: **the yagna monorepo was deleted from GitHub**, and anyone who had built on it lost their upstream entirely.
**Mitigation:** propose M3.1 as an MR **in week 1 of M3, before any of our code depends on it** — it is small, self-contained, and useful to them independent of us. Keep our own components (device agent, shard store, hyperjob schema) behind interfaces that do not name NuNet types, so a fork or a switch costs weeks rather than quarters. Mirror our own clone of the DMS.

## 7. Licence contamination
**Observed:** the two elders richest in operational wisdom — BOINC (LGPL-3.0) and Golem (GPL-3.0/GPL-2.0/LGPL-3.0) — are both copyleft, and MORK is all-rights-reserved. Meanwhile our `S6` scheduler spec quotes BOINC's constants and file paths extensively, because that is what makes it a usable spec.
**Damage:** a single copied function from BOINC's `cs_prefs.cpp` or MORK's `differential/run.py` obliges us to relicense, or exposes us to a claim.
**Mitigation:** the discipline is already established in this workspace — `analysis/LICENSE_LEDGER.md` records that **zero files were copied**, and the specs are written as behavioural descriptions with citations rather than transcriptions. Keep it: a NOTICE file from day one, a CI grep for copied identifiers from copyleft elders, and a rule that anyone implementing from `SCHEDULER_SPEC.md` or `REPORT_MORK.md` works from the spec, not from the elder's source, and says so in the commit.

## 8. Charge-time windows are rarer and shorter than the model assumes
**Observed:** S6 — `setRequiresDeviceIdle(true)` combined with `setRequiresCharging(true)` and `NetworkType.UNMETERED` is a genuinely narrow intersection, Doze defers work, and WorkManager can stop a worker at any moment with no guaranteed runtime.
**Damage:** the effective fleet is a nightly batch, not a live pool. A market whose latency expectation is "minutes" cannot be served by devices available for one multi-hour window per day. Job sizing, replication timing, and challenge windows all inherit this.
**Mitigation:** design for the batch, not the pool: jobs must fit a window or checkpoint at fuel boundaries (M1.3); challenge windows measured in **days**, not minutes; desktops as the always-on tier for anything latency-sensitive. Offer a relaxed "screen off, charging" mode as a user preference (BOINC's `suspendWhenScreenOn`), accepting the UX risk knowingly.

## 9. Sybil and collusion in replica placement
**Observed:** replication only verifies anything if replicas fail independently. Verde says so explicitly: *"a robust ecosystem of trainers is needed, which are unlikely to collude or suffer related faults (e.g. by running the same third party data center)"*. **No elder implements this** — BOINC assumes a trusted project server, NuNet has no notion of correlated devices, and our own `exclude_device_groups` field (S4) is a placeholder with no enforcement behind it.
**Damage:** three phones on one desk, one operator, one attestation root, produce three identical wrong answers and a unanimous quorum.
**Mitigation:** attestation raises Sybil cost but does not prove independence — a real device farm passes Play Integrity. Enforce diversity on the axes we can observe: operator DID, attestation root, network origin/ASN, and timing correlation. Bittensor's clipped stake-weighted median limits the payoff even when collusion succeeds. Treat unanimity from correlated devices as *weaker* evidence than disagreement between uncorrelated ones.

## 10. Our own schema is missing commit/reveal
**Observed:** PoCo binds a submitted `resultHash` to a `resultSeal` derived from the worker's identity, precisely so a second worker cannot copy the first's hash off-chain (`IexecPoco2Facet.sol:106`). **Our S4 `ResultEnvelope` has `result_hash` and a signature, but no seal binding the hash to this worker before disclosure.**
**Damage:** in an optimistic or sampled-audit mode, a lazy device can observe another's published hash and submit it as its own, earning payment for nothing and — worse — manufacturing false agreement that suppresses a genuine dispute.
**Mitigation:** add it in M3.4; it is a small schema change (commitment = H(result_hash ‖ device_did ‖ nonce), revealed later) and it is the highest-value single fix this recon surfaced. Until it exists, do not present replication as a security property.

---

## Two risks deliberately *not* on this list
- **"MeTTa might not be deterministic enough to verify."** It is. MORK's differential harness compares two independently-written query engines byte for byte over 98 programs and passes in 1.4 s (S3). This was the mission's central bet and it is the best-evidenced claim in the whole recon.
- **"MeTTa might not fit on a phone."** It does. 4.00 MiB, cross-compiled in 15 seconds, on stable Rust, first attempt (S2).

---

# R-NEW — The settlement layer has never been costed, and built the obvious way it caps ~3,350× below the device capacity we measured

**Added 2026-08-16 (S59-adjacent, from reading `acurast-substrate`). Arguably the largest hole in the plan, and it was invisible because nobody costed the chain.**

Every figure below was re-derived from the cloned runtime, not taken on trust.

## The arithmetic

Acurast's runtime: 6 s blocks (`runtime/common/src/constants.rs:19`), `MAXIMUM_BLOCK_WEIGHT = (2 s ref_time, MAX_POV_SIZE)` (`acurast-mainnet/src/constants.rs:48-51`), `NORMAL_DISPATCH_RATIO = 75%` (`:45`). Benchmarked weights:

| extrinsic | PoV bytes | PoV-bound | ref-bound | **ceiling** |
|---|---|---|---|---|
| `report` | 38,282 | 103/block | 8,190/block | **17.1/s** |
| `heartbeat_with_metrics` | 15,088 | 261/block | 30,051/block | **43.4/s** |
| `heartbeat` | 4,990 | 788/block | 83,333/block | **131.3/s** |

**PoV binds in every case, by two to three orders of magnitude.** That determines the shape of any fix: the constraint is *proof size*, not execution time, so a faster chain buys nothing. Only smaller or fewer proofs do.

## Why it is our problem specifically

`PORT_PLAN` M3.5 proposes `pay_per_verified_result`, and our design puts `result_hash` + `fuel_used` on the settlement path **per job**. That is precisely the `report` shape.

```
report-shaped settlement, 1x            17.1 jobs/s
with 2x replication (we require it)      8.6 jobs/s
S32 device-side claim                28,700 jobs/s
shortfall                                3,353x
```

S32's 28,700 jobs/s is already flagged in `LEDGER` as unadjudicated and falsified three times — but even taken at face value it describes a device fleet feeding a settlement layer four orders of magnitude too small. **The bottleneck was never the phones.**

## What Acurast did instead, and why it is the whole game

They made the unit of payment **committed capacity, measured periodically, weighted by stake** — not a verified result. Three mechanisms:

1. **Schedule amortisation.** `MAX_EXECUTIONS_PER_JOB = 6_308_000` (`marketplace/src/types.rs:15`, commented *"run a job every 5 seconds for a year"*). One `propose_matching` covers all of them, so match cost per execution falls to ~0.06 bytes of PoV.
2. **Reward bypasses the job path.** `pallets/compute` is staking, not a work queue. Payment is a share of an epoch's `RewardBudget` proportional to stake-weighted × reported metric — **one `MetricCommit` per processor per epoch**, and the epoch is `131072` blocks = **9.1 days** (`acurast-mainnet/src/constants.rs:153`). At 250k devices against 43.4 metric-heartbeats/s, each device reports roughly every **1.6 h** — ample, and the off-chain compute between reports is unbounded.
3. **Verification is one-time.** `submit_attestation` validates an X.509 chain once at pairing; after that the device is trusted, with slashing as enforcement.

**The chain never sees the work.** Compute throughput is deliberately decoupled from chain throughput.

## The fork, now concrete rather than philosophical

> Acurast's architecture is what you build once you decide verification is a one-time hardware fact. Ours is what you build when you refuse to trust the hardware. **The price of refusing is ~38 KB of proof per result, and nobody here had priced it.**

Refusing may still be right — TEEs get broken, and a vendor-rooted revocation list is a central kill switch that we specifically do not want. But it now has to be argued against a known cost.

## Directions, none of them costed yet

- **Aggregate.** Commit a Merkle root of N results per epoch instead of N reports. Turns per-job PoV into per-epoch PoV; verification becomes an inclusion proof presented only on challenge. This is the obvious fix and directly matches the optimistic rung-1 design we already have.
- **Copy the epoch.** 9.1 days of reward granularity is far coarser than anything we assumed, and it is what makes their numbers work.
- **Settle off-chain**, anchoring periodically. Moves the problem rather than solving it, but the problem it moves is the binding one.
- **Challenge-only settlement.** Post nothing per job; post a bond, and let anyone force a reveal. Fraud-proof shape, and it is the only one of these that preserves trustlessness at the same PoV cost as Acurast's trusted design.

## Status
**Unresolved, unassigned, and gating.** M3.5 cannot be specified until one of the above is costed. Add to `LEDGER` NEVER MEASURED.

## Open questions I could not close
- Whether Acurast's `report` is mandatory for every job class or only one-shot deployments. `finalize_job` is marked *"DEPRECATED: cleanup logic has been moved to the final report call"* — "final" implies reports are per execution with settlement at the end, which would mean their `report` path carries more traffic than this analysis assumes.
- Whether reports batch. No batching extrinsic found; `hooks.rs` not fully read.
- Our own numbers assume an Acurast-shaped parachain. A different DA layer or a rollup changes the PoV budget, and that has not been explored at all.

## R-NEW addendum — the succinct-proof answer, measured from `risc0`

**38 KB per result is not a floor. It is an artefact of settling per job. A Groth16 proof is 256 bytes and its size does not depend on how much computation it attests to.**

Cloned `risc0/risc0` and `succinctlabs/sp1` (both **Apache-2.0**, licence read from `LICENSE-APACHE` in the git object). Measured from `risc0` `groth16_proof/groth16/verifier.sol`, not from documentation:

```solidity
function verifyProof(
    uint256[2]    calldata _pA,          //  64 B
    uint256[2][2] calldata _pB,          // 128 B
    uint256[2]    calldata _pC,          //  64 B
    uint256[5]    calldata _pubSignals   // 160 B
) public view returns (bool)
```

`Seal { a: [Fp;2], b: [Fp;4], c: [Fp;2] }` (`risc0/groth16-sys/src/lib.rs:102-104`) = 8 field elements = **256-byte proof**. The pairing check is `staticcall(…, 8, _pPairing, 768, …)` — 768 bytes = **4 pairings**, standard Groth16, via Ethereum's `ecPairing` precompile.

**The property that matters: 256 bytes is constant.** One proof attests to a hundred reduction steps or a hundred billion, at the same size. `risc0/circuit/recursion-*` provides the composition that folds N proofs into one.

### The correct comparison, stated carefully
38,282 is **PoV** — the storage proof a parachain collator supplies for the state a `report` extrinsic touches. 420 bytes is **calldata**. They are not the same unit and I will not pretend they are.

The real saving is structural: **per-result state access disappears.** Settling a batch of N results is one verification and one state write, so PoV per result becomes `PoV_batch / N`. The verification key is a fixed, cacheable read.

| batch N | proof bytes/result | settlement ceiling (Acurast-shaped chain) |
|---|---|---|
| — (report-shaped, per job) | 38,282 PoV | **17/s**, 8.6/s with replication |
| 1 | 420 | — |
| 1,000 | 0.42 | ~10⁶/s |
| 100,000 | 0.0042 | ~10⁸/s |

**Even a batch of one is 91× smaller than our current per-job record**, because 38 KB is not a proof of anything — it is the cost of touching per-job chain state.

### Why this fits our workload specifically
A zkVM can only prove a **deterministic** computation. S57 and S58 established exactly that for MeTTa: byte-identical reduction and identical fuel counts across two ISAs and three platforms, 360,847 steps. **The determinism work is the precondition for this route, and it is already done.** The fuel count is the natural public input.

We also do not need *zero-knowledge* — nothing is secret. We need **succinctness**, which is strictly weaker and admits more constructions.

### The honest costs, none of them measured here
1. **Proving is expensive** — zkVM proving runs on the order of 10⁵–10⁶× native execution. **A phone cannot prove.** This relocates cost from the chain to a prover; it does not remove it. Unmeasured and now the gating question for this route.
2. **Groth16 needs a per-circuit trusted setup.** STARK-based (risc0's native receipts) and PLONK-family avoid it at larger proof size. Ours would be one circuit — the MeTTa interpreter — so a single ceremony, but it is a real ceremony.
3. **Gas figures are not locally verified.** The contract structure above is measured; EIP-1108 pricing (`ecPairing` = 45,000 + 34,000·k, so ~181,000 gas at k=4, ~250k total) is stated from knowledge and should be confirmed against a client before use.
4. Our chain is Substrate, not EVM. `risc0/groth16/src/` is Rust and a pallet verifier is plausible, but nobody has checked `no_std` compatibility or benchmarked its PoV.

### The combination that actually resolves R-NEW
Optimistic settlement with **proof only on challenge**:

- Happy path: post nothing per result beyond a bond and a commitment. **Zero proofs, Acurast's cost.**
- Disputed path: the challenged party produces one succinct proof, 256 bytes, verified in constant time.

That is Acurast's throughput with our trust model, and it needs no TEE, no vendor attestation and no revocation list. It is also the natural completion of the rung-1 optimistic bisection already in `PORT_PLAN` — bisection finds *which* step is wrong; a succinct proof removes the need to re-execute in order to check it.

**This is now the recommended direction for M3.5**, superseding `pay_per_verified_result`. Gating unknown: prover cost and who bears it.
