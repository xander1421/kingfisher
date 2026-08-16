# S1 — hyperon-native build & test

**Verdict: GREEN**

Machine: Apple Silicon arm64 (14 cores, 24 GB), macOS Darwin 25.4.0, rustc 1.96.1 **stable**.
Repo: `elders/hyperon-experimental` @ `3f76dc46` (v0.2.10).

## Build
```
cargo build --release --workspace   → Finished in 1m 00s, exit 0
```
No nightly, no patches, no system deps beyond what was already installed. Clean first try.

## Tests
```
cargo test --release --workspace    → exit 0
```
All 18 test binaries pass: **472 tests passed, 0 failed, 5 ignored** (largest suite: 298 in `hyperon`; 72 in `hyperon-atom`; 23 + 9 + 6 + 3 in the MeTTa integration/stdlib suites).

## Artifact sizes (release, `strip = "symbols"`)

| artifact | default features (`pkg_mgmt`,`das`) | `--no-default-features --features pkg_mgmt` |
|---|---|---|
| `libhyperonc.dylib` | 6,108,704 B (5.83 MiB) | **3,698,624 B (3.53 MiB)** |
| `libhyperonc.a` | 37,647,912 B | 27,807,448 B |
| `metta-repl` | 6,996,208 B (6.67 MiB) | n/a |

Dropping the `das` feature (which pulls `metta-bus-client` → tonic/gRPC/protobuf) removes **2.41 MiB / 40%** of the shared library. That is the build a phone should ship: on-device MeTTa talks to the shard store through our own transport, not gRPC.

## Two porting facts discovered while measuring

1. **`--no-default-features` does not compile.** `lib/src/metta/runner/builtin_mods/json.rs:184,269` uses `serde_json` unconditionally, but `serde_json` is optional and gated behind the `pkg_mgmt` feature. 8 errors (E0432/E0433). Upstream bug. The minimum working feature set is `--no-default-features --features pkg_mgmt`. A one-line `#[cfg(feature = "pkg_mgmt")]` on the `json` builtin would make a truly minimal core build possible — worth an upstream PR, and worth ~another few hundred KB.
2. **Workspace feature inheritance masks this.** `hyperon = { workspace = true, default-features = false }` in `c/Cargo.toml` is silently ignored by cargo (`warning: default-features is ignored for hyperon, since default-features was not specified for workspace.dependencies.hyperon`). Measuring the lean build requires replacing the workspace inheritance with a direct `path` dep. Any downstream slimming effort will hit this first.

## Repo hygiene note
All measurements were taken with a temporary edit to `c/Cargo.toml`, restored immediately after each build (`cp /tmp/c_Cargo.toml.bak c/Cargo.toml`). The clone is back at its pristine HEAD.
