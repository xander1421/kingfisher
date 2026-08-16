# S15 — MeTTa on real Android hardware, byte-verified against the desktop

**Verdict: GREEN.** The M1 thesis is no longer a plan. A fuel-metered MeTTa job ran on a Galaxy S25 Ultra and produced results **byte-identical** to the same job on the desktop — same result hash, same result order, and the **same fuel count to the step** — across two different libcs and two different silicon vendors.

S2 proved `libhyperonc` *links* for Android and said so explicitly: *"Runtime execution was **not** tested — no device or emulator was attached, so this spike proves it links, not that it runs."* This spike closes that gap.

## Device under test
```
model      SM-S938B  (Samsung Galaxy S25 Ultra)
soc        SM8750    (Snapdragon 8 Elite), 8 cores, max 3,532,800 kHz
android    16        arm64-v8a, bionic
pagesize   4096      (so the Android-15 16 KB-page concern does not apply to this unit)
ram        11,113 MB
npu        libsnap_qnn.so present in /vendor/lib64 (Hexagon via QNN, not just NNAPI)
```
Desktop side: macOS 15 / Apple Silicon arm64 / libSystem, same source tree, rustc 1.96.1 stable.

## What was built
`fuelrun` (`fuelrun/src/main.rs`, ~110 LOC) — the port plan's M1.2 + M1.6 in miniature:
- drives `RunnerState::run_step()` in a loop instead of running to completion, so **the step count is the fuel meter**;
- stops at `fuel_limit` and reports `FUEL_EXHAUSTED` as a **result**, not an error;
- canonicalises results and prints two SHA-256 digests: `raw_hash` (interpreter order) and `sorted_hash` (set equality).

`raw_hash` is the interesting one. Set equality across devices would be a weak claim; **identical evaluation order** is what optimistic verification and step-bisection disputes actually need.

Built for the phone with the recipe from S2, unchanged:
```
ANDROID_NDK_HOME=$HOME/Library/Android/sdk/ndk/28.2.13676358 \
  cargo ndk -t arm64-v8a --platform 28 build --release
→ ELF 64-bit LSB pie executable, ARM aarch64, 3,993,824 B (3.81 MiB), 6.0 s
```

## Result 1 — a job that completes
`job_terminating.metta`: 14 `Inheritance` facts, two graph queries, a `parent`/`grandparent` rule, `fib 10`, `sumto 20`.

| | desktop (macOS/Apple Silicon) | phone (Android/Snapdragon) |
|---|---|---|
| status | OK | OK |
| **fuel_used** | **100,082** | **100,082** |
| n_results | 11 | 11 |
| **raw_hash** | `c2940ab5fcd50768…` | `c2940ab5fcd50768…` |
| **sorted_hash** | `651651defced520a…` | `651651defced520a…` |
| default_hash | `9f41a3bd84158189` | `9f41a3bd84158189` |
| boot_ms | 6–8 | 27 |
| run_ms | 92–113 | 246–279 |

Results identical down to ordering: `human chimp monkey rhino / mammal reptile earthworm / reptile / reptile / 55 / 210`.

## Result 2 — a job that runs out of fuel
`job_kb.metta` adds an unguarded transitive-closure rule that does not terminate. Capped at 2,000,000 steps:

| | desktop | phone |
|---|---|---|
| status | FUEL_EXHAUSTED | FUEL_EXHAUSTED |
| fuel_used | 2,000,000 | 2,000,000 |
| n_results | 14 | 14 |
| raw_hash | `4937b20a7490523b…` | `4937b20a7490523b…` |

`diff` of the two full outputs, excluding only `os` and timings: **identical**.

This is the stronger of the two results. A non-terminating job stopped at exactly the same step on both machines and had produced **exactly the same partial state** when it did. Fuel exhaustion is not an error to be handled — it is a reproducible, agreeable result, which is what makes it safe to pay for.

## Repeatability
5 runs on each machine, 10/10 identical `fuel_used` and `raw_hash`.

| | run_ms (5 runs) | steps/s |
|---|---|---|
| desktop | 113, 92, 94, 93, 93 | ~1.08 M |
| phone | 251, 248, 279, 246, 247 | ~404 k |

**The phone is 2.7× slower than an M-series laptop on symbolic reduction.** Not 20×. For a device that spends the night plugged in doing nothing, that is a workable ratio — and per S9's finding that this workspace's timings were taken on a loaded machine, the desktop figure here is if anything flattered (these runs were taken while a MORK build was idle, but no attempt at an idle-machine methodology was made; treat the ratio, not the absolutes, as the result).

## What this settles, and what it does not
**Settles:**
- MeTTa evaluates correctly on Android arm64 — not just links.
- Cross-libc, cross-vendor determinism holds at the byte level, including evaluation *order*.
- The fuel counter is reproducible to the step, so `fuel_used` can be compared in a result envelope exactly as `result_hash` is (S4 schema, field 6).
- A desktop can byte-verify a phone's work with `diff`. M1.6 needs no cleverness.

**Does not settle:**
- No WorkManager, no JNI, no app packaging — this is a command-line binary in `/data/local/tmp` driven over adb. The scheduling half of M1 (S6's spec) is untouched.
- No shard store; the program is a local file, not a CID.
- Nothing was measured under thermal load, on battery, or in Doze.
- The NPU was not used. `libsnap_qnn.so` is present, which is the concrete route for M2, but this spike is CPU only.

## Reproducing
```sh
cd spikes/S15_android_device/fuelrun
cargo build --release                                        # desktop
ANDROID_NDK_HOME=... cargo ndk -t arm64-v8a --platform 28 build --release
adb push target/aarch64-linux-android/release/fuelrun ../job_*.metta /data/local/tmp/kingfisher/
adb shell 'cd /data/local/tmp/kingfisher && ./fuelrun job_terminating.metta 5000000'
./target/release/fuelrun ../job_terminating.metta 5000000
```
