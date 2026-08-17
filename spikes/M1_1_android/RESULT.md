# M1.1 — Android app skeleton. GREEN. It runs, and it settles the preflight number.

**S2 proved `libhyperonc` links. This proves it loads and runs inside a real
Android app process — and it produces the number M1.3 got wrong by 356x.**

## Built
- `libhyperonc.so`, `cargo ndk -t arm64-v8a --platform 28`, NDK 28.2.13676358.
- **6,745,752 B (6.43 MiB)**, default features. `hyperonc` has **no `[features]`
  block**, so it cannot select `hyperon`'s `pkg_mgmt`-only set from the CLI —
  S2's 4.00 MiB minimal build is not reachable without an upstream change. That
  is the `cfg`-gate item already in `HUMAN_NEEDED`; now confirmed as a hard
  blocker rather than a nicety.
- APK 9.27 MiB, `minSdk 29` (`getCurrentThermalStatus()` is API 29+),
  `useLegacyPackaging = false`, Java (not Kotlin — see toolchain note).

## 16 KB page alignment — S2 open item 3, now measured not assumed
```
LOAD align 0x4000
LOAD align 0x4000
LOAD align 0x4000
LOAD align 0x4000
```
All four segments at 16 KB. S2 said *"cargo-ndk 4.x sets this by default for
NDK >= 27, so likely already handled."* It is, and it is now verified on the
artifact rather than inferred from a changelog.

## It loads in-process
```
libhyperonc.so load: OK 1.342969 ms
```
6.43 MiB of Rust, dlopened by a real app's linker on Android 15, 16 KB pages.

## The preflight number, settled

M1.3 published *"batched preflight is 35.1 ms = 0.51x a warm job, so per-job
preflight is not viable."* That measured `adb shell` + `dumpsys` text parsing
over USB — the harness, not the mechanism. Measured here on the API path
`SCHEDULER_SPEC:19-20` actually specifies, 2,000 iterations each:

| call | cost |
|---|---|
| `getCurrentThermalStatus()` | 34.02 µs |
| `getIntProperty(BATTERY_PROPERTY_CAPACITY)` | 57.32 µs |
| `ACTION_BATTERY_CHANGED` sticky | **2.97 µs** |
| `StatFs.getAvailableBytes()` | 1.93 µs |
| **FULL PREFLIGHT** | **98.47 µs** |

```
adb + dumpsys (M1.3, published)   35,100 µs   0.51x a job
native sysfs read (M1.3b, floor)       8.4 µs
REAL spec path (here)                 98.5 µs   0.0014x a job
```

**356x cheaper than the published figure. Per-job preflight costs 0.14% of a
job** — trivially viable, and S6 marks it required (`Residue: yes`).

### An actionable detail the sweep turned up
The sticky `ACTION_BATTERY_CHANGED` broadcast is **19x cheaper** than
`BatteryManager.getIntProperty` — 2.97 µs against 57.32 µs — because it reads a
cached broadcast instead of making a binder round trip. `SCHEDULER_SPEC:19`
specifies `EXTRA_LEVEL`/`EXTRA_SCALE`, i.e. the sticky path; the "spec path"
bench above used `getIntProperty` and is therefore **pessimistic**. Following
S6 literally gives thermal + sticky + StatFs = **~38.9 µs**, another 2.5x
better.

Two spec recommendations, both vindicated on cost as well as correctness.

## Toolchain note, recorded because it cost time
- Gradle 9.7 **rejects all AGP 8.x**: *"relies on `InternalProblems`, a Gradle
  internal API removed in Gradle 9.6.0."* AGP 9.3.0 is the working pairing.
- AGP 9.3.0 pulls `kotlin-gradle-plugin:2.2.10` even for a **Java-only** app, so
  an offline build is impossible without it cached. Dropping Kotlin does not
  drop the Kotlin plugin.

## Not done
- **No JNI call into MeTTa.** The `.so` is loaded, not invoked. `metta_new_core`
  / `metta_run` through a JNI shim is the remaining half of M1.1 and needs a
  CMake/`externalNativeBuild` step.
- **No WorkManager worker.** `androidx.work` is not yet a dependency; the five
  declarative constraints are unbuilt. M1.3's residue policy is tested in Python
  and not yet ported to `doWork()`.
- **No `onStopped()` checkpointing** — still blocked on the S68 state commitment.
- Measurements are single-device, thermal status 0, battery 100%, charging.
  Cost under thermal pressure is unmeasured.
