# S16 — MORK on Android, and a cross-**architecture** differential

**Verdict: GREEN, and it overturns the workspace's MORK portability verdict.** MORK cross-compiles and runs on a Galaxy S25 Ultra, and **33 of 33 corpus programs produce byte-identical space dumps and identical step counts on Android/Snapdragon and macOS/Apple Silicon.** The three blockers `reports/REPORT_MORK.md` rated "high" turn out to be one real constraint, one build-flag problem, and one that does not apply to `mork run` at all.

Related: S14 found the recon read the `main` branch while upstream documents `server`. This spike is on `main` — the branch that carries `differential/` and the corpus, which is what a differential test needs.

## Getting it to build for `aarch64-linux-android`

Six things had to be fixed. All six are build configuration; **none is a code change to MORK or PathMap.**

| # | failure | cause | fix |
|---|---|---|---|
| 1 | `failed to run custom build command for libz-ng-sys` — *"CMake was unable to find a build program"* | `pathmap`'s **default** `serialization` feature pulls `libz-ng-sys`, which builds zlib-ng with CMake; CMake's Android module could not find the NDK | export `ANDROID_NDK_ROOT`, and point `CMAKE_TOOLCHAIN_FILE` at a 4-line wrapper (`android-arm64.toolchain.cmake`) that sets `ANDROID_ABI`/`ANDROID_PLATFORM` as **cache** variables and then includes the NDK's own toolchain file. The `cmake` crate cannot pass `-DANDROID_ABI`, and the NDK toolchain reads it as a cache var — without the wrapper it defaults to armv7 and clang rejects `-march=armv7-a`. |
| 2 | `ld.lld: error: unable to find library -lgcc` | NDK r23+ removed libgcc; the rust android target still emits `-lgcc` | a 16-byte `libgcc.a` containing `INPUT(-lunwind)` on the link path (`libgcc-shim/`) |
| 3 | `Gxhash requires aes and neon intrinsics` | `gxhash` (used by PathMap for dag serialisation / merkleization) needs them named explicitly when cross-compiling | `RUSTFLAGS="-C target-feature=+aes,+neon"` |
| 4 | `ld.lld: undefined symbol: _rjem_malloc` (+5 more) | **jemalloc.** `tikv-jemalloc-sys` compiles for Android but does not export its symbols | **drop the `jemalloc` feature.** One word in `MORK/Cargo.toml`. |
| 5 | at runtime: `Pointer tag for 0x… was truncated` → `Aborted` | Android 11+ tags heap pointers in the top byte (TBI); PathMap's `slim_ptrs` packs its own bits into 64-bit inter-node pointers, so bionic sees a tag it did not issue | `LD_PRELOAD` a 6 KB shim (`notag.c`) whose constructor calls `mallopt(M_BIONIC_SET_HEAP_TAGGING_LEVEL /* -204 */, M_HEAP_TAGGING_LEVEL_NONE)`. An app would instead set `android:allowNativeHeapPointerTagging="false"` in its manifest — **one line, no shim, no LD_PRELOAD** |
| 6 | trying to avoid #5 by disabling `slim_ptrs` | PathMap's non-slim pointer path is bit-rotted (`no method named make_unique`, `new_empty`, `is_empty` on `TrieNodeODRc`, 6 errors) | don't; use the manifest flag instead |

Result: `mork` for Android, **5,947,128 B (5.67 MiB)**, ELF 64-bit LSB PIE aarch64.

```
$ adb shell './mork run corpus/programs/ctl.mm2 out_ctl.txt --timing'
loaded 317 expressions
executing 189 steps took 353 ms (unifications 25808, writes 95386, transitions 252303, max unify 14)
dumping 883 expressions
```

## The cross-architecture differential

`crossrun.py` (stdlib only, modelled on MORK's own `differential/run.py`) runs the same corpus on both machines and compares the dumped space **byte for byte** plus the reported step count.

Where MORK's harness compares **two query engines on one machine**, this compares **one engine on two architectures**: macOS 15 / Apple Silicon / libSystem versus Android 16 / Snapdragon 8 Elite / bionic.

```
programs 35   steps_cap=200   timeout=45.0s
steps_cap=200  ok=33  mismatch=0  skipped=2
```

Every one of the 33 matched on both the dump hash and the step count. Highlights:

| program | steps | dump size | host s | phone s |
|---|---|---|---|---|
| `programs_exponential_fringe` | 46 | **48,393,277 B** | 1.2 | 2.5 |
| `programs_ctl` (CTL model checking) | 189 | 19,916 B | 0.1 | 0.3 |
| `programs_bfc7` | 129 | 17,660 B | 0.0 | 0.1 |
| `programs_lens_aunt` | 200 (capped) | 1,130 B | 0.1 | 0.2 |
| 20 × `unify/*` | 1–4 | 6–375 B | 0.0 | 0.0 |

A **48 MB** space dump identical to the byte across two libcs, two allocators, two vendors' silicon. Two programs (`bc0`, `exponential`) skipped on a 45 s host timeout, not on disagreement — notably the phone *finished* `exponential` in 40.1 s while the host was still going.

Phone/host wall-clock ratio on the programs that took measurable time: **2.1–3.0×**, matching S15's 2.7× on hyperon.

## Corrections to the workspace

`reports/REPORT_MORK.md` §4 and `BLOCKED.log` entry 4 list three "high"-severity portability blockers. Measured:

| claimed blocker | measured |
|---|---|
| **`/dev/shm` hardcoded** (`kernel/src/space.rs:35`) — "breaks on Android *and* macOS" | **Does not affect `mork run`.** It is reached only by the ArenaCompactTree backup/restore paths that `mork test` exercises. 33 corpus programs ran on Android without touching it. Still real for ACT persistence; wrong to rate it as blocking the engine. S14 additionally found it absent from the `server` branch. |
| **jemalloc** — "Android's 16 KB-page devices and jemalloc have a known bad history; untested" | Untested was right, "16 KB pages" was the wrong worry. This device has **4 KB** pages. jemalloc fails at **link** time (`_rjem_*` undefined), and dropping the feature costs one word. No page-size issue was reached. |
| **nightly required** | Confirmed and unchanged. The Android build is nightly too. |

And one new, undocumented blocker that matters more than any of them: **Android heap pointer tagging versus PathMap's `slim_ptrs`**. It is invisible until you run on a real device — it did not appear in any build, only at the first `free()`. Mitigation is one manifest line for an app, but a bare binary needs the LD_PRELOAD shim, and anyone testing MORK over adb will hit it.

## Consequences for the plan
- `GAP_MATRIX.md` row 7 says "ship hyperon on phones now; run MORK on Linux desktops only, **as a black box behind a process boundary**, until its licence and its three portability blockers are resolved." The *portability* half of that is now too conservative: MORK runs on the phone. The licence half is unchanged and remains the operator's accepted risk.
- `PORT_PLAN.md` M1.6 (desktop verifier) gets cheaper again: the comparison logic is `sha256(dump) == sha256(dump) && steps == steps`, and it now has cross-architecture evidence at 48 MB scale.
- A phone can be a *replica* for MORK jobs, not only for hyperon jobs. That widens the fleet's job classes considerably.

## Reproducing
```sh
# build (from elders/MORK, with pathmap's jemalloc feature removed)
export ANDROID_NDK_ROOT=$HOME/Library/Android/sdk/ndk/28.2.13676358
export CMAKE_TOOLCHAIN_FILE=$PWD/../../spikes/S16_mork_android/android-arm64.toolchain.cmake
export RUSTFLAGS="-L $PWD/../../spikes/S16_mork_android/libgcc-shim -C target-feature=+aes,+neon"
cargo +nightly ndk -t arm64-v8a --platform 28 build --release -p mork

# run the differential
python3 spikes/S16_mork_android/crossrun.py --steps 200 --timeout 45
```
`elders/MORK/Cargo.toml` carries one local edit (jemalloc feature removed) — see `DECISIONS.log`.
