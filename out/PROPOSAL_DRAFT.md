# A World Computer for Hypergraph AI: phone NPUs, locality-aware jobs, and verification that is almost free

*Draft for the Hyperon forum / SingularityNET Deep Funding — 2026-08-16*

## The problem

Hyperon's knowledge layer scales in one direction and its compute layer scales in another. DAS can hold a distributed Atomspace across desktops; MORK can reduce MeTTa at speed on one machine. What does not exist is a way to *rent* the reasoning out — to run a hypergraph query across thousands of devices that nobody trusts, and know the answer is right.

Every existing decentralised compute network has had to solve verification the hard way, because their workloads are floating-point. Gensyn's Verde had to build **RepOps**, a library of bitwise-reproducible operators, before refereed delegation would work at all — *"hardware may provide different numerical results because floating point operations are not guaranteed to be associative"*. BOINC carries `hr_class` "homogeneous redundancy" for the same reason: replicas must be sent to numerically similar hosts. Prime Intellect's TOPLOC commits to top-k activations with an exponent-exact/mantissa-tolerant comparison, again because exactness is unavailable.

**Deterministic symbolic reduction does not have this problem.** That is the observation this proposal is built on.

## Evidence, measured this week

We built and ran the elders rather than reading about them. Everything below is a number from a spike in a reproducible workspace.

| claim | measurement |
|---|---|
| MeTTa is deterministic enough to verify by byte comparison | MORK's differential harness runs **98 programs through two independently-written query engines and compares the resulting spaces byte for byte, plus step counts: 0 failures, 1.4 s** |
| MeTTa runs on a phone today | `libhyperonc` cross-compiled to `aarch64-linux-android`: **4.00 MiB stripped ELF, 162 exported C functions, 15 seconds, stable Rust, zero patches** |
| Fuel metering already exists | hyperon's C ABI exposes `interpret_init` / `interpret_step` / `step_has_next`; MORK's CLI already prints `executing N steps` and its test corpus already pins it |
| An NPU pre-filter loses nothing | 100k triples, 100 queries: **recall 1.0, zero false positives** — a matching triple scores exactly `2·|{d : Q_d ≠ 0}|`, computable from the query alone, so the "approximate" filter has an **exact** cutoff |
| It fits in phone memory | **102 MB** of INT8 for a 100k-triple shard at D=1024, with margin to spare (exactness holds down to D=256 / 26 MB) |
| Sparsity is worth four orders of magnitude, but only while it lasts | CSR SpGEMM vs dense BLAS at n=1024: **~9,800× faster at 0.01 % density; they cross at 8.6 %** |
| Result envelopes stay tiny | a top-k polynomial commitment over similarity scores: **34–514 bytes**, 20/20 tampers rejected |

## The wedge — three things that exist nowhere

**1. Phone-NPU scheduling.** No project in the survey targets a phone NPU. BOINC's Android client is twenty years of charge/idle/thermal policy in a C++ daemon babysat by a Kotlin service; we mapped all fourteen of its rules onto modern `WorkManager` constraints and found that six become declarative, six survive as in-worker logic, and **two can be deleted** — including `hr_class`, which exists only for float reproducibility we do not need.

**2. Locality-aware, knowledge-graph-native matching.** Golem and NuNet both match on *network* locality — region, ASN, round-trip time. Akash matches on resources and signed attributes. **Nothing matches on which data a device already holds.** For hypergraph reasoning that is the dominant cost: our own measurements show throughput on the same code varying 26 → 353 GOP/s purely on memory locality.

**3. Shaping as a paid job class.** Reordering atoms so neighbours share memory tiles (Morton order, community reordering) does not change a graph's global density — it *concentrates* it, turning hypersparse chaos into NPU-ready blocks. The crossover table above is why that is worth money. And shaping is the rare job class whose verification is trivial: measure block density before and after. **A job whose product is making all future jobs cheaper, priced by a market that can see the improvement.**

## Architecture

- **Knowledge**: DAS shards on desktops (Apache-2.0, stood up locally in an hour); content-addressed subgraphs cached on phones; replica count driven by the DAS attention broker's existing `get_importance` gRPC call — an importance economy with rent, wages and Hebbian spreading that is **already implemented and already a service**.
- **Compute**: phone NPUs run one giant INT8 matmul as an exact pre-filter; phone CPUs run exact MeTTa pattern matching over the shortlist; desktop GPUs take heavy batches. End-to-end lossless.
- **Coordination**: an extension of the **NuNet** stack (same SingularityNET ecosystem, live mainnet since 2026-03-02, NTX settlement on Ethereum and Cardano) rather than a new network. Their DID/UCAN capability system already accepts tokens from third-party vetting anchors, so device attestation slots in without a new trust model.
- **Verification ladder**: rung 1, deterministic MeTTa — optimistic acceptance with staked challenge and ⌈log₂(steps)⌉ **bisection over `interpret_step`**; rung 2, INT8 similarity — exact, with a 66-byte commitment for envelope size; rung 3, peer scoring — **a corner case**, because rungs 1 and 2 have exact ground truth and even shaping has an objective measure.

## What exists vs what we build

Of eighteen capabilities in our gap matrix: **5 can be lifted** under permissive licences (exact engine, fuel metering, rung-2 commitments, attention-driven replication, desktop agent), **5 adapted**, **6 implemented from written specs**, and exactly **2 are genuinely novel** — the phone-NPU similarity runtime and the shaping job class. Those two are the wedge; the rest is assembly.

Three findings we did not expect, offered as evidence of diligence: MORK ships **no licence at all** (we treat it as all-rights-reserved and reimplement from written descriptions; a one-line fix upstream would change six rows of our matrix); the Golem/yagna monorepo **has been deleted from GitHub** (an argument for building where maintainers still ship); and TOPLOC's `find_injective_modulus` **can return a composite modulus**, which broke 1 in 20 of our honest verifications until we added a primality check — reported upstream.

## Milestones

| # | deliverable | why it is the gate |
|---|---|---|
| **M1** (~6 wk) | **MeTTa evaluating a job on one Android phone, scheduled at charge time, result byte-verified by one desktop.** | Falsifies the whole thesis cheaply if it fails. Fuel metering, WorkManager worker, CID shard cache, phone-initiated transport, desktop verifier. |
| **M2** (~8 wk) | NPU similarity runtime: Core ML / LiteRT export, **INT8 bit-exactness measured on real silicon first**, two-stage query path, rung-2 commitments. | One measurement (bit-exactness) decides whether rung 2 is free or needs a tolerance model. |
| **M3** (~1 qtr) | Marketplace: NuNet capability extension (power/thermal/NPU — proposed upstream in week 1), `executor/metta`, tick-based locality-aware auction, commit/reveal + bisection disputes, `pay_per_verified_result`. | Makes the fleet economically real. |
| **M4** (~1 qtr) | **The beak**: layout metrics in the shard manifest, shaping as a priced job class, ARM NEON kernels, attention-driven replication. | The differentiator, once there is a market to price it. |

## The ask

Fund M1 and M2 as one block. They are cheap, they are sequenced so that the two riskiest assumptions (fuel-bounded MeTTa inside an OS-controlled window; bit-exact INT8 on a real NPU) are tested first, and each ends in an artefact a sceptic can run: a phone that computes a verified MeTTa result overnight, and a benchmark showing when the NPU beats the CPU on a real shard.

The upstream contributions are useful even if the market never ships: a power/thermal/NPU capability model for NuNet, ARM SIMD for MORK's linalg, a licence for MORK, and the Android port of `libhyperonc` — which, as of this week, takes fifteen seconds.

---
*Supporting material: `analysis/GAP_MATRIX.md` (18 capabilities classified), `analysis/LICENSE_LEDGER.md` (21 repositories, zero files copied), `reports/` (12 elder reports with commit hashes and file citations), `spikes/S1`–`S8` (build logs, benchmarks, and reproducible code).*
