# Operation Kingfisher — workspace

Autonomous reconnaissance and foundation mission for a world computer for distributed hypergraph AI. Executed 2026-08-16.

**Start here: [`out/FINAL_REPORT.md`](out/FINAL_REPORT.md), then
[`out/ADDENDUM.md`](out/ADDENDUM.md) — which corrects three of its headline
numbers — then [`out/DEVICE_ADDENDUM.md`](out/DEVICE_ADDENDUM.md), which is the
first evidence from real hardware (Galaxy S25 Ultra).**

```
out/          FINAL_REPORT, STATE_OF_THE_UNION, PORT_PLAN, RISKS, PROPOSAL_DRAFT
              + ADDENDUM.md         (S9..S14 corrections; later than the other five)
              + DEVICE_ADDENDUM.md  (S15..S16, on an attached Galaxy S25 Ultra; latest)
analysis/     GAP_MATRIX.md (18 capabilities classified), LICENSE_LEDGER.md (21 repos, zero copies)
reports/      12 elder reports + ENVIRONMENT.md
spikes/       S1..S8 (recon) · S9..S14 (verification) · S15..S16 (real device),
              each with RESULT.md, code and logs
              bench.py   shared timing harness — cold/warm split, autoscaled samples
              hdcore.py  the S5 encoding, factored out so S9..S12 measure the same thing
papers/       7 PDFs + INDEX.md
elders/       21 shallow clones, read-only; all left at pristine HEAD
DECISIONS.log 23 entries · BLOCKED.log 5 entries
```

### The verification spikes (S9–S14)
| # | question | verdict |
|---|---|---|
| S9 | are S5's throughput numbers real? | **RED** — every timing taken on a loaded machine, 5.3× off |
| S10 | does the exact pre-filter generalise past one query shape? | **GREEN** — exact iff m ≥ 2 of 3 slots bound; survives Zipf |
| S11 | can a shard fit on a phone? | **GREEN** — 64× compression at recall 1.0, *if* clustered |
| S12 | is INT8 exact enough without a device? | **GREEN** — int16 accum safe; output requantisation is the one hazard |
| S13 | does the sparse/dense crossover replicate? | **RED** — baseline was 15× below the machine floor; crossover ~1.5%, not 5–9% |
| S14 | did the recon read the right MORK? | **YELLOW** — read `main`; upstream documents `server` |

### The device spikes (S15–S16) — Galaxy S25 Ultra over adb
| # | question | verdict |
|---|---|---|
| S15 | does MeTTa *run* on a phone and agree with the desktop? | **GREEN** — byte-identical results **and fuel count**; 2.7× slower |
| S16 | does MORK run on a phone; does its corpus agree cross-arch? | **GREEN** — 33/33 identical dumps + step counts, incl. 48 MB |

## Reproducing the spikes

```sh
# S1/S2 — build hyperon, then cross-compile for Android
cd elders/hyperon-experimental
cargo build --release --workspace && cargo test --release --workspace
ANDROID_NDK_HOME=$HOME/Library/Android/sdk/ndk/28.2.13676358 \
  cargo ndk -t arm64-v8a --platform 28 build --release -p hyperonc

# S3 — MORK (needs elders/PathMap as a sibling, and nightly)
cd elders/MORK && rustup override set nightly
cargo +nightly build --release -p mork
python3 differential/run.py --build
cargo bench -p linalg --bench crossover --features blas   # needs `brew install openblas`

# S4 — hyperjob schema
cd spikes/S4_hyperjob_schema
protoc --python_out=. hyperjob_v0.proto && ../S5_hdc_prototype/.venv/bin/python roundtrip_test.py

# S5 — hypervector pre-filter (venv with numpy lives here)
cd spikes/S5_hdc_prototype && ./.venv/bin/python hdc.py [D]

# S7 — TOPLOC-style commitment
cd spikes/S7_toploc_adapt && ../S5_hdc_prototype/.venv/bin/python commit.py

# S8 — local DAS (needs docker; on macOS + colima, export DOCKER_HOST)
export DOCKER_HOST=unix://$HOME/.colima/default/docker.sock
das-cli database start && das-cli attention-broker start && das-cli query-agent start

# S9..S12 — reuse the S5 venv; run on an IDLE machine or the numbers are fiction
cd spikes/S9_timing_rigor     && ../S5_hdc_prototype/.venv/bin/python bench_matmul.py 7
cd spikes/S10_pattern_classes && ../S5_hdc_prototype/.venv/bin/python patterns.py 1024
cd spikes/S11_bundling        && ../S5_hdc_prototype/.venv/bin/python bundle.py 1024
cd spikes/S12_int8_numerics   && ../S5_hdc_prototype/.venv/bin/python numerics.py

# S13 — own venv (needs scipy); run both baselines
cd spikes/S13_crossover_replication
python3 -m venv .venv && ./.venv/bin/pip install numpy scipy
./.venv/bin/python spgemm.py
VECLIB_MAXIMUM_THREADS=1 ./.venv/bin/python spgemm.py _1thread
```

## State left on this machine
- `~/.das/config.json` was created (and hand-patched — see `spikes/S8_das_up/RESULT.md`).
- The **colima** VM was started for S8 and left running; `colima stop` shuts it down. All four DAS containers were stopped.
- `elders/MORK` carries a `rustup override` to nightly. Nightly is an **accepted
  cost** as of `DECISIONS.log` 2026-08-16T16:05Z — but it must be pinned, not
  floated: `fast-slice-utils` uses `feature(core_intrinsics)` and MORK carries a
  future-incompat warning, so an unpinned nightly breaks without notice.
- `spikes/S14_mork_server/mork-server/` is a new depth-1 clone of MORK's **`server`**
  branch (the recon only ever read `main`). Read-only, pristine HEAD `2d6730b`.
- `spikes/S13_crossover_replication/.venv` is a new venv (numpy + scipy). The S5
  venv was deliberately left untouched so S5 reproduces exactly as documented.
- `elders/hyperon-experimental/target` (1.3 GB) and `elders/MORK/target` (444 MB) are build artefacts; safe to delete.
- Nothing was published, pushed, staked, or transacted. No wallets or keys were created or touched.
