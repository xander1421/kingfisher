# REPORT: MORK (MeTTa Optimal Reduction Kernel)

## 1. Identity
- URL: https://github.com/trueagi-io/MORK
- Commit: `0653b50fea0674a59afc5c125dbc76414ba2d57f` (2026-08-15 — one day before this recon; actively developed)
- License: **NONE FOUND → UNKNOWN → treat as all-rights-reserved.** No `LICENSE`/`COPYING` file, no `license` key in any of the 12 `Cargo.toml` files, no licence statement in `README.md`. Zero grep hits for "license" across all `.toml`/`.md`.
  **Consequence: read for ideas, copy nothing.** Every MORK-derived capability in the gap matrix is SPEC (clean-room), never PORT. This is the single biggest licence hazard in the elder set, because MORK is also the most technically load-bearing.
- Sibling dependency **PathMap** (`Adam-Vandervorst/PathMap`, v0.3.0) *is* **MIT** © 2025 Adam Vandervorst — the data structure underneath MORK is portable even though MORK is not.

## 2. Shape
- 238 tracked files. Rust 45 files / **32,720 LOC**; Python 9 / 1,161 (the differential harness + generators); 103 `.mm2` programs (the corpus); 51 `.expected` space dumps.
- Build: cargo workspace, **edition 2024, nightly-only**. No `rust-toolchain.toml` (undeclared).
- `default-members = ["kernel/"]`.

| dir | LOC | role |
|---|---|---|
| `kernel/` | 20,206 | the VM. `main.rs` 6,491 (CLI + in-binary tests), `leapfrog.rs` 4,026 (WCO join), `space.rs` 1,843, `sinks.rs` 1,415, `pure.rs` 1,300, `sources.rs` 260 |
| `linalg/` | ~5,000 | `jit.rs` 1,388 (cranelift), `csr.rs` 1,135, `einsum.rs` 1,080, `blocked.rs` 421, `ewise/dense/any/tensor` |
| `expr/`, `interning/`, `frontend/` | — | expression representation, symbol interning (gxhash), `.mm2` parser |
| `differential/` | — | the two-engine byte-compare harness + `.mm2` corpus + expected dumps |
| `experiments/` | — | `eval`, `eval-ffi`, `unification_test_laws` |

External deps of `kernel`: `pathmap` (sibling path), `gxhash` (git dep), `memmap2`, `clap`, `serde`, `rand`, `itertools`, `base64`, `hex`, `subprocess`, `futures`; optional `neo4rs`+`tokio` (`neo4j`), `wasmtime` (`wasm`).

## 3. Entry points
- `kernel/src/main.rs:6226` — `fn main()`, the `mork` CLI (clap). Subcommands include `run` and `test`.
- Library surface: `mork::space::{Space, transitions, unifications, writes, ACT_PATH}`.
- `mork run` prints exactly one line of accounting: `executing N steps took M ms (unifications ...)`.

## 4. Extraction targets

### Kernel data structure — pathmap / trie zipper
The space is a **PathMap** (sibling MIT crate): a trie whose cursors are *zippers*, so a subtree can be read, forked, and written by an independent thread without locking the whole structure. MORK builds two query engines on it:
- **ProductZipper** (`Space::query_multi`) — the reference engine.
- **Leapfrog** (`leapfrog.rs`, 4,026 LOC, `leapfrog` cargo feature) — a worst-case-optimal join, used only for flat conjunctive bodies it can handle, falling back to ProductZipper otherwise.
Relevant pathmap features MORK enables: `jemalloc`, `arena_compact`, `nightly`. `arena_compact` (`ArenaCompactTree`) is the on-disk/mmap serialisation — **and its path is hardcoded to `/dev/shm/`** (`kernel/src/space.rs:35`, used at `space.rs:1101` and throughout `main.rs`). Linux-tmpfs-only; breaks on macOS and Android.
There is also a `periodic_merkleize` cargo feature in `kernel/Cargo.toml` — i.e. **Merkle hashing of the space is already contemplated upstream**. That is the natural hook for content-addressing shards and for cheap "did we end in the same state" verification. It is off by default and was not exercised in S3.

### `linalg/` API and the crossover bench methodology
- Trait pair `tensor::{NDIndex, Sparse2D}` is the universal interface; `einsum::einsum("ab,bc->ac", &[&dyn NDIndex], &mut [...])` composes arbitrary specs over mixed sparse/dense operands at runtime (a small VM, `einsum.rs`), with an optional **cranelift JIT** (`jit.rs`) for the composed kernel.
- Representations: `Dense<T>` flat row-major, `Csr<u32,f32>` with sequential and rayon SpGEMM, `Blocked<N>` block-sparse (N=8,16) for batched attention.
- Bench methodology (`linalg/benches/crossover.rs`): sweep density on a **log grid, 4 steps per decade, 0.01 % → 100 %**, time sparse vs OpenBLAS pinned to **1 thread**, report the density where the sparse/BLAS ratio crosses 1.0, and abort the sweep once sparse is 4× slower. Correctness is checked against BLAS at full density before timing. This is a clean, honest methodology and we should copy the *shape* of it for NPU-vs-CPU crossover measurement on phones.
- Measured on this machine: SpGEMM crossover **5.1–8.6 %** density; Blocked attention crossover **0.5–1.6 %** (scalar fallback — the AVX2/FMA kernels at `blocked.rs:31-117` are `#[cfg(target_arch = "x86_64")]`, so **ARM has no SIMD path in linalg at all**). Full numbers in `spikes/S3_mork_bench/RESULT.md`.

### The differential byte-compare harness — our verification primitive
`differential/run.py` (Python stdlib only) + `differential/corpus/*.mm2` + `differential/expected/*`.
- Runs every corpus program through **both** engine builds and compares the dumped space **byte for byte** *and* the reported step count.
- Per-program metadata lives in ordinary `.mm2` comments, so a corpus entry stays a runnable program: `@desc`, `@steps N`, `@expect-steps N`, `@expect [path]`, `@aux file`, `@tags slow`, `@skip reason`.
- Measured: **98 ok / 0 failed / 5 skipped in 1.4 s** over 103 programs.
- Mapping to the mission: `@expect-steps` ≡ `fuel_used`; the byte-compared space dump ≡ `result_hash`; running two engines ≡ running two devices. Rung-1 verification is this harness with the process boundary moved. Because MORK is licence-UNKNOWN we reimplement it from this written description, which is why the description above is deliberately complete.

### Portability risks (nightly / jemalloc / paths)
1. **nightly required, undeclared** — edition 2024 plus `fast-slice-utils 0.1.2` using `feature(core_intrinsics)`. On stable: `error[E0554]`. A device agent shipping MORK inherits a nightly pin.
2. **jemalloc** via `pathmap` features. Not exercised on Android here. Android's move to 16 KB page sizes has historically broken jemalloc-based allocators; this needs a real device test before anyone plans around it. PathMap does expose the allocator as a cargo feature, so a `system`/mimalloc variant is probably available — untested.
3. **`/dev/shm` hardcoded** — see above. Also means MORK's persistence assumes a *RAM-backed* filesystem; on a phone the equivalent is app-private storage with very different durability and size characteristics.
4. **`cargo report future-incompatibilities`** flags `mork` itself.
5. `subprocess` and (optional) `wasmtime`/`neo4rs` in the kernel's dep graph — a phone build would want those out.

## 5. Verdict for the mission
Technically the best exact-matching engine available and the source of our verification design, but **legally untouchable as code** and **currently unportable to the target device**. Treat MORK as a specification and a benchmark partner: run it on desktop shard hosts (Linux, where `/dev/shm` and jemalloc are fine), and on phones run hyperon-experimental's MeTTa (MIT, builds for Android today — see `spikes/S2_hyperon_android/RESULT.md`) until MORK's three blockers are fixed upstream.
