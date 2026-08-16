# STATE OF THE UNION

Where the world computer stands on 2026-08-16, one layer per page. Everything below is either cited to a file in an elder repo or measured in a spike in this workspace. Claims with no citation are marked as such.

---

## Layer 1 — Knowledge (DAS shards, content-addressed subgraphs, growth agents)

### What exists
- **A distributed Atomspace, Apache-2.0, that runs.** `singnet/das`: 192 C++ sources, five agent types, five storage backends. Stood up locally in **S8** — redis + mongo + attention broker + query agent — loaded `animals.metta`, and answered `(Similarity "human" $S)` with monkey / chimp / ent.
- **A MORK-backed AtomDB already exists** (`src/atomdb/morkdb/MorkDB.cc`). The "fast engine behind the distributed store" integration is not hypothetical.
- **MeTTa can already query a remote DAS.** `hyperon-experimental/lib/src/metta/runner/builtin_mods/das.rs` (611 LOC) ships a `das` module: `!(bind! &das (new-das! ...))` then `!(match &das (Similarity "human" $S) ($S))`.
- **The attention economy is built and exposed as a service.** `attention_broker/StimulusSpreader.cc` implements rent collection (`rent_rate × importance`), arity-weighted spreading, and Hebbian edges from query co-occurrence. `get_importance(HandleList) → ImportanceList` and `stimulate(HandleCount)` are gRPC calls today.
- **Growth agents have registries, not stubs.** `agents/link_creation_agent/link_creators/LinkCreatorRegistry` and `agents/evolution/fitness_functions/FitnessFunctionRegistry` are extension points.

### What the spikes proved
- DAS is operable by one person on one laptop in under an hour (S8), including two upstream defects worked around (config wizard omits a required block; docker socket discovery ignores the active context).
- **The DAS service bus requires the agent to dial the client back.** Our host-side MeTTa REPL joined the bus, the agent took ownership of `pattern_matching_query`, and the query still failed — because the agent could not reach `localhost:52000` on the other side of the VM boundary. Every DAS participant must be a dialable peer.

### What is missing
- **A content-addressed shard.** DAS addresses *atoms* by handle inside a database; nothing addresses a *subgraph* by hash. No canonical serialisation, no CID, no manifest, no size/atom-count/layout-quality metadata. (GAP row 9, SPEC, M.)
- **An offline-capable phone-side cache.** The `AtomDB` read subset (`get_atom`, `query_for_pattern`, `query_for_targets`, `query_for_incoming_set`, `atoms_exist`) is small enough to implement on device; nothing implements it there.
- A phone can never be a DAS peer (above). The device agent must talk to a desktop shard host that fronts the bus.

---

## Layer 2 — Compute fleet (phone NPUs, phone CPUs, desktop GPUs)

### What exists
- **MeTTa runs on Android today.** S2: `cargo ndk -t arm64-v8a --platform 28 build --release -p hyperonc` → a stripped ARM64 ELF, **4.00 MiB**, 162 C functions exported, **15 seconds**, stable Rust, zero patches. Even the gRPC-carrying default build cross-compiles (6.46 MiB). Only the `git` feature fails (openssl-sys).
- **Stepwise evaluation is already in the C ABI**: `interpret_init`, `interpret_step`, `step_has_next`, `step_get_result`, `step_to_str`. Fuel metering and dispute bisection both fall out of this for free.
- **A foreign Space can back the interpreter.** `space_new` takes a C callback table + opaque payload; `c/tests/c_space.c` is a working Space written entirely in C. The phone's shard cache plugs in here without touching Rust.
- **A fast exact engine exists but is not ours to use.** MORK: 32,720 LOC, two independent query engines, WCO leapfrog join, PathMap zipper store. **No licence file anywhere** → all rights reserved. Its author *did* declare MIT publicly — issue #2, closed 2025-05-21, *"Yes! It's now under MIT."* — but never committed the file, and GitHub still reports the repo as unlicensed. So the ask is small and the answer is already yes; the gate stays shut until a file exists at HEAD.

### What the spikes proved
- **S1**: hyperon builds clean on stable Rust in 60 s; **472 tests pass, 0 fail**. Dropping the `das` feature cuts the shared library 5.83 → **3.53 MiB**.
- **S3**: MORK's differential harness runs **98 programs, 0 failures, in 1.4 s**, comparing two independently-written query engines **byte for byte** plus step counts. Determinism is a maintained upstream invariant, not an aspiration.
- **S3**: the density crossover, measured here: CSR SpGEMM beats dense BLAS below **5.1–8.6 %** density; at 0.01 % density it is **~9,800× faster** (2 µs vs 19,662 µs at n=1024). Dense costs a flat ~19.5 ms regardless of sparsity.
- **S5**: the INT8 hypervector pre-filter is **exactly lossless** for the canonical `(pred subj ?x)` pattern. Every matching triple scores exactly `2·|{d : Q_d ≠ 0}|`, known from the query alone. Measured over 100 queries / 1,031 matches / 100k triples: **recall 1.0, zero false positives**. At D=1024 a 100k-triple shard is **102 MB** of INT8.

### What is missing
- **Any NPU code at all.** No elder targets a phone NPU. Core ML / LiteRT export of the one-matmul model, and a bit-exactness test on real silicon, are unwritten and unmeasured. (GAP row 6, BUILD, M — the largest unknown in the plan.)
- **ARM SIMD in MORK's `linalg`.** `blocked.rs:31-117` gates its kernels on `x86_64 + avx2 + fma`; on ARM there is no SIMD path at all. Our entire fleet is ARM. A bounded, high-value contribution — if the licence is fixed.
- **MORK on any target we care about**: nightly-only (undeclared), jemalloc via PathMap (untested on Android's 16 KB pages), and `ACT_PATH = "/dev/shm/"` hardcoded at `kernel/src/space.rs:35` — which exists on neither macOS nor Android.

---

## Layer 3 — Coordination & incentives

### What exists
- **NuNet DMS, Apache-2.0, 165k LOC of Go, live mainnet.** A versioned deployment manifest (`EnsembleConfig`) with `redundancy`, `failure_recovery`, location constraints and edge RTT/bandwidth constraints; a pluggable `Executor` interface with a working no-op reference (`executor/null/`); libp2p networking; onboarding with capacity validation.
- **A real DID/UCAN capability system** (`lib/ucan/`, 4,793 LOC; `actor/`): every message authenticated at dispatch, hierarchical capability namespace, `did:key` and `did:prism` (Cardano/Identus) interop, revocable trust anchored wherever the user chooses. Attestation slots in as another anchor.
- **Settlement scaffolding**: six payment models, billing scheduler/trigger, pricing oracle, NTX on Ethereum + Cardano.
- **Reference designs for everything else**: BOINC's work-unit/quorum/credit schema and Android suspend policy (LGPL — spec only); iExec PoCo's staked, reputation-weighted, commit/reveal consensus with a per-job `trust` parameter (Apache-2.0); Akash's block-boundary sealed auction and four-section manifest (Apache-2.0); Bittensor's clipped stake-weighted median (Apache-2.0); Verde's refereed-delegation bisection (paper); TOPLOC's top-k polynomial commitment (MIT).

### What the spikes proved
- **S4**: hyperjob v0 compiles and round-trips; encoding is byte-stable across 100 serialisations (the signature depends on it) and unknown v1 fields survive a v0 parse (relays cannot invalidate signatures). Hyperjob 275 B, envelope 220 B.
- **S6**: BOINC's Android policy maps onto WorkManager with **6 rules becoming declarative constraints, 6 surviving as in-worker logic, and 2 deletable**. The deleted pair matters: the GUI-keepalive watchdog is an artefact of BOINC's two-process design, and `hr_class` homogeneous redundancy exists *only* because floating point isn't reproducible — which our workload is.
- **S7**: a top-k commitment over similarity scores is **34–514 bytes**, catches every ±1 tamper, and costs 0.006–0.8 % of the recomputation the verifier must do anyway. Verification is not cheaper than execution; the commitment buys a **1,000×+ smaller envelope** and lets a verifier be a random auditor instead of a mandatory second executor.

### What is missing
- **A power/thermal/NPU dimension in the capability model.** NuNet's `types/capability.go`, `hardware.go` and `resources.go` model CPU/RAM/GPU/disk/ports/VPN and nothing else. Charge-time scheduling has nothing to bind to. This is the schema gap our wedge fills.
- **Data-locality matching.** Golem and NuNet both match on *network* locality (region, ASN, RTT); no elder matches on *which data a node already holds*.
- **A pay-per-verified-result payment model.** All six NuNet models meter time or resources — the wrong unit for a device you cannot audit.
- **Commit/reveal with a worker-bound seal.** PoCo has it; nothing else does; **our own S4 schema does not yet have it**. Without it, a second replica can echo the first's hash and replication verifies nothing. Surfaced by this recon, folded into `PORT_PLAN.md`.
- **Anti-collusion in replica placement** beyond the `exclude_device_groups` field we invented in S4. Verde names this as an unsolved practical problem too.

---

## One-paragraph summary
The knowledge layer and the coordination layer both largely exist, under permissive licences, and are further along than the mission assumed — DAS ships an attention economy with a gRPC importance API, and NuNet ships a DID/UCAN capability system with a versioned manifest. The compute layer is where the work is, and it splits cleanly: the exact engine is *already portable to Android* (proven, 4 MiB, 15 seconds), while the NPU similarity runtime does not exist anywhere and must be built. The verification story is unexpectedly cheap — our workload is deterministic in a way ML is not, which deletes Verde's entire reproducible-operator problem, BOINC's homogeneous-redundancy machinery, and TOPLOC's tolerance model. Two capabilities are genuinely novel: the phone-NPU runtime and the shaping job class. They are exactly the two the mission named as the wedge.
