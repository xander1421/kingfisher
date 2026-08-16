# ADDENDUM — corrections and new results

Six spikes run after the original mission (S9–S14), each targeting a specific
weakness in the deliverables rather than opening new ground. Three of the
workspace's headline numbers are wrong. Two of its open questions are now
closed. One new result is strong enough to carry a milestone on its own.

Read with `FINAL_REPORT.md`; where they disagree, this file is later.

---

## What was wrong

### 1. Every wall-clock number in the workspace was taken on a loaded machine
**S9.** The original `hdc.py` was replayed unmodified at D=1024:

```
recorded (sweep_1024.json)   0.373 s    54.9 GOP/s   digest 8aba3d409add
replay   (idle machine)      0.070 s   290.7 GOP/s   digest 8aba3d409add
                                 5.3x           IDENTICAL OUTPUT
```

Byte-identical results, 5.3× apart. `DECISIONS.log` shows cargo builds of hyperon
and MORK, an openblas install, and a colima VM running during the same session.
Re-measured properly, warm throughput is **flat at 390–530 GOP/s across D=256 to
D=10000** — there is no D-dependent throughput effect, and S5's "353 GOP/s at
D=10000 versus 55–71 elsewhere" was cold samples compared against a warm one.
S5's own explanation (memory bandwidth) cannot be right: arithmetic intensity for
this kernel is ~2·q ops/byte, independent of D.

**Consequence:** S7's "85 ms of recompute per query" — the number the verification
economics in `RISKS.md` and `FINAL_REPORT.md` rest on — is from the same session
and is likely 4–5× pessimistic. The *ratio* S7 quotes is more robust than either
absolute.

### 2. The sparse/dense crossover was measured against a crippled baseline
**S13.** S3 used `brew install openblas` pinned to one thread. At n=1024 that
baseline runs at **109 GFLOP/s**. Single-threaded Accelerate on the same machine
runs the same problem at **1,641 GFLOP/s** — 15.0× faster; default Accelerate at
3,158 GFLOP/s, 28.9× faster. OpenBLAS does not target Apple's AMX units.

| n | S3 reported crossover | scipy, 1 thread | scipy, default |
|---|---|---|---|
| 256 | 5.624% | **1.378%** | 1.103% |
| 512 | 5.149% | **1.816%** | 1.352% |
| 1024 | 8.638% | **1.534%** | 1.129% |

Apples-to-apples the crossover is **3–6× too high**, and the "~9,800×" headline
recomputed against the real floor is **~340–654×**. The qualitative conclusion
survives; the shaping target does not. Concentrating a tile below 5–9% density is
a far weaker requirement than below ~1.5%, and whether Morton or community
reordering reaches 1.5% on a real graph is now an open question.

### 3. The recon read the wrong MORK branch
**S14.** `elders/MORK` is depth-1 on `main`. Upstream's README and wiki document
`server`, which is 305 commits ahead / 265 behind and a materially different tree.

- **The process boundary already exists.** `mork-server` is an HTTP server with a
  Python client, sub-space scoping (`work_at`, upstream calls them *lenses*), and
  bulk `import`/`export`. `PORT_PLAN.md` M1.6 plans to build what ships.
- **`/dev/shm` is a `main`-only blocker.** `grep -rn ACT_PATH` on `server` returns
  nothing. `BLOCKED.log` entry 4 rates it **high** severity; it should be re-tested
  before being carried forward.
- **Canonical serialisation exists.** `restore_paths` / `restore_tree` /
  `restore_from_dag` / `restore_symbols`, a `.paths` wire format, and the wiki's
  paged on-demand loading. `GAP_MATRIX.md` row 9 ("no elder has a content-addressed
  Atomspace shard", SPEC/M) should be re-scoped to "put a CID and a manifest on an
  existing format" — smaller.
- **Neither branch alone is the project**: `server` has no `linalg/` or
  `differential/`, so S3's benchmarks and the verification harness are `main`-only.
- **Still no licence on either branch.** M0.1 stands, and now has a contact:
  the wiki is maintained by charlie.derr@singularitynet.io.

---

## What is now settled that was not

### 4. The exact pre-filter generalises — with a sharp, derivable boundary
**S10.** S5 tested one query shape and generalised. Tested properly:

> **The pre-filter is exact iff the bound slots outvote the free ones (m ≥ 2 of 3).**

| class | m | answers/query | exact | recall@thr | false pos | candidate reduction |
|---|---|---|---|---|---|---|
| `(p s ?o)` | 2 | 10.4 | ✓ | 1.0 | 0 | 9,578× |
| `(p ?s o)` | 2 | 10.3 | ✓ | 1.0 | 0 | 9,671× |
| `(? s o)` | 2 | 1.0 | ✓ | 1.0 | 0 | 97,087× |
| `(p s o)` | 3 | 1.0 | ✓ | 1.0 | 0 | 99,010× |
| `(? s ?o)` | 1 | 98.4 | ✗ | — | — | recall@100 = 0.969 |
| `(p ?s ?o)` | 1 | 10,000 | ✗ | — | — | recall@100 = 0.010 |

Three of these are new. Exactness does not depend on *which* slots are bound, and
fully-ground lookups are exact under a different rule (`sum|Q|`).

**Under Zipf(1.0) data the exactness is unchanged** — recall 1.0, zero false
positives — because it is algebraic, not statistical. What skew degrades is
*rank*-based cutoffs, which is a second independent argument for the threshold
over top-k. `(p ?s ?o)` is not a pre-filtering failure so much as a query for 10%
of the database. Repeated variables `(p ?x ?x)` are not expressible as a query
vector at all and need a scan to ~10% of the store.

### 5. Narrow accumulation is not a risk; output requantisation is, and it is fixable
**S12.** M2.1 named three NPU hazards. Two are now closed without silicon:

- **The float32 path is integer-exact** at every D, verified against a true int32
  reference — S5 asserted this and never checked.
- **int16 accumulation is safe.** Scores are bounded by 3·D, so the worst case at
  D=10000 is 15,228 against an int16 ceiling of 32,767 (46.5%). Simulated int16
  wrapping *and* saturating accumulation produce **byte-identical** results to int32.
- **int8 output requantisation is the real hazard.** It collapses 397 distinct
  score values to 107 and — used naively — drops recall to **0.5395**, because the
  analytic cutoff `2·nnz(Q)` is in raw units and matches that round down fall below
  it. Snap the cutoff to the quantised grid and recall returns to **1.0 with zero
  false positives**.

**Consequences:** the envelope must carry the quantisation scale (same lesson as
S7's modulus); the cutoff must be `rint(2·nnz(Q)/scale)`, never the unrounded
form; and the scale must be pinned by the job, not chosen by the backend, or
honest replicas disagree and disputes fire on nothing. M2.1 shrinks from "is INT8
exact on device" to "does this backend requantise, and can the scale be pinned".

### 6. The 102 MB storage blocker is gone, and shaping now has a real number
**S11.** The spike S5 named and skipped. Bundling B triples per bucket:

| B | layout | store | recall (mean/min) | perfect | CPU rows checked |
|---|---|---|---|---|---|
| 1 | — | 102.4 MB | 1.0000 / 1.0000 | 100/100 | 0.01% |
| 8 | random | 12.8 MB | 0.4845 / 0.0000 | 1/100 | 3.96% |
| 8 | **clustered** | 12.8 MB | **1.0000** / 1.0000 | 100/100 | 10.08% |
| 64 | random | 1.6 MB | 0.9635 / 0.6364 | 76/100 | 85.80% |
| 64 | **clustered** | 1.6 MB | **1.0000** / 1.0000 | 100/100 | 11.82% |

**64× compression at recall 1.0000** — 16 bytes of pre-filter index per triple.
A phone-sized shard stops being multiple gigabytes. And random bundling at the
same ratio forces the CPU to check 86% of the store: at high B, an unshaped
bundle is a full scan wearing a pre-filter costume.

This is the first measured argument for the shaping job class that touches what
shards are *for*. `GAP_MATRIX.md` row 17 justifies M4 solely with S3's SpGEMM
crossover — a number S13 just invalidated. **M4 should rest on S11 instead.**

The tie rate (bucket dimensions where superposition cancelled to 0) falls from
0.262 to 0.005 for clustered and stays high for random. It is cheap, local, and
computable at shaping time — a better `ShardManifest` "layout quality" field than
block density, because it is measured on the representation the NPU consumes.

---

## Corrections to make in the original files

| file | change |
|---|---|
| `FINAL_REPORT.md` | 85 ms recompute figure is ~4–5× pessimistic (S9) |
| `STATE_OF_THE_UNION.md` L38 | crossover 5.1–8.6% → ~1.1–1.8%; ~9,800× → ~340–654× (S13) |
| `STATE_OF_THE_UNION.md` L39 | 102 MB per 100k triples → 1.6 MB at B=64 clustered (S11) |
| `GAP_MATRIX.md` row 7 | describes `main`; the server branch is the integration target (S14) |
| `GAP_MATRIX.md` row 9 | serialisation exists; re-scope to "add CID + manifest" (S14) |
| `GAP_MATRIX.md` row 12 | exact iff m ≥ 2 of 3, not universally (S10) |
| `GAP_MATRIX.md` row 17 | justify from S11's recall numbers, not S3's crossover |
| `PORT_PLAN.md` M1.6 | the process boundary ships as `mork-server` |
| `PORT_PLAN.md` M2.1 | narrowed to output requantisation + scale pinning (S12) |
| `PORT_PLAN.md` M2.4 | envelope also needs the quantisation scale (S12) |
| `PORT_PLAN.md` M4.2 | shaping target is ~1.5% density, not 5–9% (S13) |
| `BLOCKED.log` entry 4 | `/dev/shm` is `main`-only; re-test on `server` (S14) |
| `S3/RESULT.md` risk table | nightly demoted: accepted cost, pin it (`DECISIONS.log`) |

## Open questions, ranked

1. **Does a real backend requantise, and can the scale be pinned?** The whole of
   M2.1, now a much smaller question (S12).
2. **Can shaping actually reach ~1.5% tile density on a real graph?** S13 tripled
   the difficulty of M4's premise and nothing has tested it on non-synthetic data.
3. **Does clustered bundling survive a multi-pattern workload?** S11 clustered by
   the key it queried by — close to circular. Real shards serve many patterns and
   cannot cluster for all of them at once.
4. **Does `libhyperonc` run, not just link?** Unchanged since S2. Still the
   largest gap between claim and evidence in the workspace.
5. **Does the `server` branch build on stable, and does `.paths` round-trip
   byte-identically?** Both cheap, both untried (S14).
6. **Nested expressions and n-ary links.** S10's rule generalises to "a strict
   majority of slots bound", but that is derived, not measured, and nesting has no
   compositional term in this encoding at all.
7. **MORK's licence.** Unchanged, still the highest-leverage single action, now
   with a named contact.

## Reproducing

```sh
cd spikes/S9_timing_rigor        && ../S5_hdc_prototype/.venv/bin/python bench_matmul.py 7
cd spikes/S10_pattern_classes    && ../S5_hdc_prototype/.venv/bin/python patterns.py 1024
cd spikes/S11_bundling           && ../S5_hdc_prototype/.venv/bin/python bundle.py 1024
cd spikes/S12_int8_numerics      && ../S5_hdc_prototype/.venv/bin/python numerics.py
cd spikes/S13_crossover_replication && ./.venv/bin/python spgemm.py            # own venv: scipy
                                    VECLIB_MAXIMUM_THREADS=1 ./.venv/bin/python spgemm.py _1thread
```

`spikes/bench.py` (timing harness) and `spikes/hdcore.py` (the S5 encoding,
factored out) are shared. S13 has its own venv because it needs scipy; the S5
venv is untouched so S5 stays reproducible exactly as documented.
