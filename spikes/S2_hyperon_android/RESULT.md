# S2 — hyperon on Android (aarch64-linux-android)

**Verdict: GREEN** — and stronger than the mission assumed. MeTTa cross-compiles to Android arm64 today, unmodified, in 15 seconds.

## Environment
- NDK **28.2.13676358** (`~/Library/Android/sdk/ndk/`), host toolchain dir `darwin-x86_64` (runs under Rosetta on this arm64 Mac; works fine).
- `cargo-ndk` 4.1.2, target `aarch64-linux-android` already installed, rustc 1.96.1 **stable**.
- Build command (the `--platform` flag is required; `-p` is cargo's package flag and cargo-ndk panics on `-p 28`):
  ```
  ANDROID_NDK_HOME=$HOME/Library/Android/sdk/ndk/28.2.13676358 \
  cargo ndk -t arm64-v8a --platform 28 build --release -p hyperonc
  ```

## Results

| feature set | outcome | `libhyperonc.so` | `libhyperonc.a` |
|---|---|---|---|
| `--no-default-features --features pkg_mgmt` | **OK**, 15.1 s | **4,193,944 B (4.00 MiB)** | 27.8 MB |
| default (`pkg_mgmt` + `das`, i.e. tonic/prost/gRPC) | **OK**, 79 crates compiled | 6,775,584 B (6.46 MiB) | 53.4 MB |
| `+ git` (git2 / vendored libgit2) | **FAIL** | — | — |

```
$ file target/aarch64-linux-android/release/libhyperonc.so
ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked, stripped
188 exported dynamic symbols
```

Both working configurations produce a real stripped ARM64 ELF with the full 162-function C ABI exported. **A 4 MiB `.so` is an unremarkable payload for an Android app** — smaller than most ML runtimes it would sit beside.

The `das` feature cross-compiling is a bonus: `metta-bus-client` + tonic + prost all build for Android, so a phone could in principle speak the existing DAS gRPC protocol directly. We still shouldn't ship it (see S1: 2.4 MiB of the binary, and gRPC-to-a-desktop is the wrong transport for an intermittently-connected phone), but it is not a blocker.

## The one failure, and it doesn't matter
```
error: failed to run custom build command for `openssl-sys v0.9.117`
```
The `git` feature → `git2` → `libgit2-sys` → `openssl-sys`, which has no Android cross-build recipe without `OPENSSL_DIR` or the `vendored` openssl feature. `libgit2-sys` itself compiled fine; only the TLS backend broke. The `git` feature is **not** in the default set, and on-device git module fetching is something the device agent should never do anyway (module bytes arrive by CID from the shard store). Fix if ever needed: `openssl = { features = ["vendored"] }` or `libgit2-sys` with rustls.

## What a full Android app still needs (nothing here is research)
1. A JNI shim or `ndk-glue`-free `android_main`; the C ABI is already the hard part and it's done.
2. `libc++_shared.so` packaging — not needed for the two working configs (no C++ in the graph once `git` is off).
3. 16 KB page-size alignment for Android 15+ devices: pass `-Wl,-z,max-page-size=16384`. Not tested here; cargo-ndk 4.x sets this by default for NDK ≥ 27, so likely already handled.
4. `directories` crate (a hyperon dep) resolves config paths via XDG on Linux/Android — on Android it will point somewhere unwritable. Feed an explicit working dir through `metta_working_dir` instead of relying on `Environment` defaults.
5. Runtime execution was **not** tested — no device or emulator was attached, so this spike proves it *links*, not that it *runs*. That is the first task of the port milestone (§PORT_PLAN M1).

## Repo hygiene
Every measurement used a temporary edit to `c/Cargo.toml`, restored after each run. `git status --porcelain` on the clone is empty.
