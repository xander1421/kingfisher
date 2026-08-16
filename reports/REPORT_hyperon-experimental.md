# REPORT: hyperon-experimental

## 1. Identity
- URL: https://github.com/trueagi-io/hyperon-experimental
- Commit: `3f76dc460da6961f57f69f6c3e550c59c74ada83` (2026-02-11)
- Version: 0.2.10
- License: **MIT** (SPDX: MIT), (c) 2021 SingularityNET Foundation — `LICENSE`
- Gate: PORT allowed with attribution.

## 2. Shape
- 296 tracked files. Rust 85 files / 32,697 LOC; Python 65 / 6,800; C 9 / 1,122 (tests + demo); 67 `.metta` files (stdlib + tests).
- Build: cargo workspace (`Cargo.toml`) + CMake wrapper (`CMakeLists.txt`) for the C/Python artifacts. Rust edition 2021, **stable toolchain** (no nightly feature gates found).
- Workspace members: `hyperon-common`, `hyperon-atom`, `hyperon-space`, `hyperon-macros`, `lib`, `c`, `repl`.

Module map:
| dir | role |
|---|---|
| `hyperon-atom/` | `Atom` enum, unification/`matcher.rs` (1841 LOC), grounded-atom traits |
| `hyperon-space/` | `Space`/`SpaceMut` traits, observers, `index/trie.rs` atom index (930 LOC) |
| `lib/` | MeTTa proper: `metta/interpreter.rs` (2170), `metta/types.rs`, `metta/runner/` (modules, stdlib, pkg_mgmt, builtin_mods) |
| `c/` | `libhyperonc` cdylib+staticlib — **the phone embedding path** |
| `repl/` | `metta-repl` binary (rustyline + clap) |
| `python/` | `hyperonpy` bindings (pybind11 over the C API) |

## 3. Entry points
- REPL binary: `repl/src/main.rs` → `metta-repl`.
- Embedding: `Metta::new(...)` in `lib/src/metta/runner/mod.rs`; run loop = `metta_run` / `interpret_step`.
- C embedding: `c/src/lib.rs` re-exports `atom.rs`, `metta.rs`, `space.rs`, `module.rs`, `serial.rs`.

## 4. Extraction targets

### C API surface (`c/src/*.rs`, 4,745 LOC, 162 `extern "C"` fns)
- `metta.rs` 84 fns, `atom.rs` 45, `space.rs` 23, `module.rs` 6, `util.rs` 4.
- Crate type is `["cdylib","staticlib"]` with cbindgen (`c/cbindgen.toml`) → a `.so`/`.a` plus generated header. This is exactly what an Android JNI/NDK shim needs; no extra work to expose a stable ABI.
- **Mission-critical find — stepwise interpretation is already in the C ABI**: `interpret_init`, `interpret_step`, `step_has_next`, `step_get_result`, `step_to_str` (`c/src/metta.rs`). A host can drive evaluation one reduction at a time from outside the library. This is simultaneously:
  - the **fuel-metering hook** (count/limit steps without patching the interpreter), and
  - the **bisection-dispute primitive** for verification rung 1 (a challenger can replay to step *n* and compare `step_to_str`).
  No equivalent exists in the Python API path; it is C-first.
- Runner control: `metta_new_core`, `metta_new_with_stdlib_loader`, `metta_run`, `metta_evaluate_atom`, `metta_load_module_direct`, `metta_load_module_at_path`, `metta_get_module_space`, `metta_working_dir`.
- Parser/tokenizer exposed separately (`sexpr_parser_*`, `tokenizer_*`) → a job payload can be parsed and hashed before evaluation.

### Space implementation (`hyperon-space/src/lib.rs`, `lib/src/space/grounding/mod.rs`)
- `trait Space` (read-only: `query`, `subst`, `atom_count`, `visit`) + `SpaceMut` (`add`/`remove`/`replace`). Observers via `SpaceObserver::notify(&SpaceEvent)`.
- Default impl `GroundingSpace` (571 LOC) backed by `hyperon-space/src/index/trie.rs` (930 LOC) — an atom trie index, in-memory.
- **`space_new` in `c/src/space.rs` takes a C callback table + opaque payload** (`c/tests/c_space.c` is a working example of a Space implemented entirely in C). So a phone-side, content-addressed shard cache can be plugged in as a Space *without touching the Rust*. This is the cleanest integration seam in the whole elder set.
- Concurrency caveat: `SpaceObserverRef` is `Rc<RefCell<T>>`; the runner is **not `Send`/`Sync`**. Device agent must run one interpreter per OS thread and pass work by message, not by sharing a Space handle.

### Module system (`lib/src/metta/runner/modules/`, 839 + 655 LOC)
- Modules resolved by name (`mod_names.rs`) through a catalog (`pkg_mgmt/catalog.rs`, `git_catalog.rs`, `managed_catalog.rs`). Loading is by path, by git URL, or **direct** (`metta_load_module_direct` with a caller-supplied `ModuleLoader`).
- Direct loading matters: a device agent can inject a job's MeTTa program as a module from memory (from a CID) and never touch the filesystem or git.

### Built-in DAS module — **already exists** (`lib/src/metta/runner/builtin_mods/das.rs`, 611 LOC)
```
> !(import! &self das)
> !(bind! &das (new-das! (localhost:52000-52099) (localhost:40002)))
> !(match &das (Similarity "human" $S) ($S))
```
MeTTa can already query a remote distributed Atomspace as a Space, via the `metta-bus-client` crate pulled from `github.com/singnet/das` tag `1.0.2`. The knowledge-layer↔exact-engine link the mission assumes does not have to be built — it has to be made shardable and offline-capable.

### Dependency count (`lib/Cargo.toml`)
- 12 direct crates: `regex, log, env_logger, directories 5.0.1, smallvec, im 15.1, rand 0.9, dyn-fmt, itertools, unicode_reader, serde_json(opt)` + workspace-internal crates.
- Default features = `["pkg_mgmt","das"]`, which drag in **`git2` with `vendored-libgit2` (a C build)** and **`metta-bus-client` (tonic/gRPC + protobuf)**. Both are Android cross-compile hazards.
- **Recommendation for the device agent:** build `--no-default-features`. Core MeTTa is pure Rust with a small, boring dep tree — the two risky deps are both optional.

### wasm / Android CI
- `.github/workflows/`: `ci-auto.yml`, `ci-manual.yml`, `ci-nightly.yml`, `common.yml`, `das-tests.yml`, `release.yml`.
- **Zero** hits for `android`, `wasm32`, `ios`, or `aarch64` across all `.toml`/`.yml`/`.rs`/`.md` files. No mobile target has ever been exercised upstream. Our port is greenfield but unobstructed (see `spikes/S2_hyperon_android/RESULT.md`).

## 5. Verdict for the mission
Best-positioned elder by a wide margin: permissive licence, stable Rust, small dep tree, a C ABI that already exposes stepwise evaluation, a Space trait that already accepts a foreign backing store, and a working DAS client. The Android port is a build-system problem, not a design problem.
