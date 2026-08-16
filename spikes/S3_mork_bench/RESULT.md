# S3 — MORK build, tests, differential harness, linalg crossover

**Verdict: YELLOW** — everything that matters builds and runs and the numbers are excellent, but two hard portability blockers (`/dev/shm` and nightly+jemalloc) stand between MORK and a phone.

Machine: Apple Silicon arm64, 14 cores, 24 GB. Toolchain: **nightly** (`rustup override set nightly` inside `elders/MORK`).

## Getting it to build at all
Two undocumented prerequisites, both logged in `DECISIONS.log`:

1. **Missing sibling repo.** `MORK/Cargo.toml` declares `pathmap = { path = "../PathMap/", features = ["jemalloc","arena_compact","nightly"] }`. There is no `trueagi-io/PathMap` (404). The crate lives at **`Adam-Vandervorst/PathMap`** (MIT, © 2025 Adam Vandervorst) and must be cloned as a *sibling directory* of the MORK checkout. Nothing in MORK's README says this.
2. **Nightly is mandatory and not declared.** No `rust-toolchain.toml` in the repo. Both MORK (edition 2024) and the transitive dep `fast-slice-utils 0.1.2` (`feature(core_intrinsics)`) refuse to compile on stable: `error[E0554]: #![feature] may not be used on the stable release channel`.

```
cargo +nightly build --release -p mork   → exit 0, binary 5,100,208 B (4.86 MiB)
```
Warning emitted: *"the following packages contain code that will be rejected by a future version of Rust: mork v0.1.0"* — MORK relies on something already on cargo's future-incompat list.

## `mork test` — partial pass, **RED for portability**
Runs a long sequence of in-binary tests (CTL model checking, backward chaining, pi-calculus, sorting, proof search — all producing correct spaces) and then hard-panics:

```
thread 'main' panicked at kernel/src/main.rs:1976:79:
called `Result::unwrap()` on an `Err` value: Os { code: 2, kind: NotFound }
```
Root cause, `kernel/src/space.rs:35`:
```rust
pub static ACT_PATH: &'static str = "/dev/shm/";
```
The ArenaCompactTree persistence path is a **hardcoded Linux tmpfs path**. macOS has no `/dev/shm`, and — critically for this mission — **neither does Android**. Every `backup_tree` / `open_mmap` call site is affected (`space.rs:1101`). Fix is one line (make it a config/env value), but it must be fixed before any mobile or macOS story exists.

## Differential harness — **GREEN, and this is our verification primitive**
```
python3 differential/run.py --build
programs: 103
98 ok, 0 failed, 5 skipped in 1.4s
```
Two independently-written query engines — the ProductZipper reference (`Space::query_multi`) and the worst-case-optimal leapfrog join (`leapfrog::query_multi_leapfrog`, behind the `leapfrog` cargo feature) — run the same 98-program `.mm2` corpus and their resulting spaces are compared **byte for byte**, plus their reported step counts.

Three things this proves for us, at once:
- **Determinism is already a maintained invariant of MeTTa evaluation in MORK**, not an aspiration. Two different join algorithms produce byte-identical spaces on 98 programs.
- **The `mork run` CLI already prints a fuel counter**: `executing N steps took M ms`, and the harness already pins it (`@expect-steps`). Fuel metering for the hyperjob tuple does not need to be invented — it needs to be exposed and made binding.
- **The harness itself is the shape of our replicate-or-challenge verifier.** Swap "two engines on one machine" for "two devices on one job" and the comparison logic is unchanged. `differential/run.py` is 100% Python stdlib, ~400 lines, and licence-blocked from copying (see below) — but the *design* is what we want, and it is small enough to clean-room.

## linalg crossover bench — **the number that justifies "the beak"**
Ran with a `brew install openblas` (OpenBLAS pinned to 1 thread). Full log: `crossover.log`.

### SpGEMM: `Csr<u32,f32>` vs dense `sgemm`
| n | CSR beats BLAS below | rayon-parallel CSR beats BLAS below |
|---|---|---|
| 256 | **5.62 %** density | 17.64 % |
| 512 | **5.15 %** density | 27.46 % |
| 1024 | **8.64 %** density | 30.04 % |

The raw sweep at n=1024 is the headline:

| density | nnz | CSR µs | BLAS µs | speedup |
|---|---|---|---|---|
| 0.01 % | 100 | **2** | 19,662 | **~9,800×** |
| 0.1 % | 1,005 | 7 | 19,639 | 2,800× |
| 1 % | 10,262 | 732 | 19,701 | 27× |
| 10 % | 104,662 | 20,893 | 19,556 | 0.94× (crossed) |
| 100 % | 1,048,576 | — | 19,285 | (sparse abandoned) |

Dense BLAS costs a flat ~19.5 ms regardless of density; sparse cost tracks nnz. A hypergraph shard at realistic knowledge-graph density (0.01–0.1 %) is **three to four orders of magnitude** cheaper sparse. The whole shaping thesis lives in this table: shaping is only worth paying for when it can push a *tile* over ~5–10 % local density while the *global* matrix stays hypersparse. That is precisely what Morton/community reordering does — it does not change global density, it concentrates it.

### Blocked attention vs batched BLAS
| config | Blocked8 crossover | Blocked16 crossover |
|---|---|---|
| b32_s512_h12_d32 | 1.44 % | 0.53 % |
| b8_s1024_h12_d64 | 1.56 % | 0.58 % |
| b8_s1024_h16_d64 | 1.41 % | 0.65 % |

**Caveat that is actually an opportunity:** `linalg/src/blocked.rs:31-117` gates its SIMD kernels on `#[cfg(all(target_arch = "x86_64", target_feature = "avx2", target_feature = "fma"))]`. On this arm64 machine those kernels **do not exist** — the numbers above are the scalar fallback losing to a hand-tuned NEON OpenBLAS. So (a) these crossovers are a floor, not a ceiling, and (b) **there are no ARM NEON kernels in MORK's linalg at all**, which is a concrete, bounded, high-value contribution for a project whose entire compute fleet is ARM. Correctness against BLAS at full density passed for every config (`full-density correctness vs BLAS ok`), so the scalar path is right, just slow.

## Portability risk summary for the device agent
| risk | severity | note |
|---|---|---|
| `/dev/shm` hardcoded | **high** | breaks on Android *and* macOS; one-line fix but touches persistence |
| nightly-only (edition 2024 + `core_intrinsics` in a dep) | **high** | pins the whole device agent to nightly, or forces a fork of `fast-slice-utils` |
| jemalloc (pathmap feature) | **high** | Android's 16 KB-page devices and jemalloc have a known bad history; untested here |
| no NEON kernels in `linalg` | medium | opportunity, not blocker |
| future-incompat warning on `mork` itself | medium | upstream will have to fix or MORK stops building |
| undeclared sibling-path dependency | low | annoying, documented now |
