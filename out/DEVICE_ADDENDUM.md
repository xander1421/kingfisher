# DEVICE ADDENDUM — the phone showed up

Two spikes run on real hardware after `ADDENDUM.md`: a **Samsung Galaxy S25 Ultra** (SM-S938B, Snapdragon 8 Elite / SM8750, Android 16, arm64-v8a, bionic, 11 GB, 4 KB pages) attached over adb, against the macOS/Apple-Silicon desktop.

Read after `FINAL_REPORT.md` and `ADDENDUM.md`. Where all three disagree, this file is latest.

| spike | question | verdict |
|---|---|---|
| **S15** | does MeTTa *run* on a phone, and does it agree with the desktop? | **GREEN** — byte-identical results, identical fuel count, 2.7× slower |
| **S16** | does MORK run on a phone, and does its corpus agree across architectures? | **GREEN** — 33/33 byte-identical dumps and step counts, incl. a 48 MB dump |

---

## 1. The M1 thesis is demonstrated, not planned

`PORT_PLAN.md` set M1 as *"MeTTa evaluating a job on one Android phone, scheduled at charge time, result byte-verified by one desktop"* and budgeted ~6 weeks to falsify it. The compute-and-verify half is done:

```
                        desktop (macOS/Apple Silicon)   phone (Android/Snapdragon)
status                  OK                              OK
fuel_used               100,082                         100,082
raw_hash                c2940ab5fcd50768…               c2940ab5fcd50768…
sorted_hash             651651defced520a…               651651defced520a…
run_ms (5 runs)         113,92,94,93,93                 251,248,279,246,247
```

`raw_hash` is over results **in interpreter order**, not sorted — so this is agreement on *evaluation order*, not merely on the answer set. That is the stronger property, and it is the one optimistic verification and step-bisection disputes actually require.

The non-terminating job is the better result: capped at 2,000,000 steps, both machines stopped at exactly 2,000,000, with 14 identical partial results and the same hash. **Fuel exhaustion is a reproducible, agreeable outcome, not an error** — which is what makes it safe to pay for, and it is why `hyperjob.proto` separates `RESULT_FUEL_EXHAUSTED` (deterministic, payable) from `RESULT_DEADLINE_EXCEEDED` (infrastructure, unpaid).

What remains in M1 is packaging, not risk: JNI, WorkManager, a CID shard store, phone-initiated transport.

## 2. MORK runs on the phone, and its corpus agrees across architectures

Where MORK's own `differential/run.py` compares **two query engines on one machine**, `S16/crossrun.py` compares **one engine on two architectures**:

```
programs 35   steps_cap=200
ok=33  mismatch=0  skipped=2 (host timeout on bc0, exponential — not disagreement)
```

Including `programs_exponential_fringe`: a **48,393,277-byte** space dump, identical to the byte, macOS/libSystem/Apple-Silicon vs Android/bionic/Snapdragon.

Six build fixes were needed and **none is a source change to MORK or PathMap**: a CMake wrapper toolchain so zlib-ng finds the NDK; a 16-byte `libgcc.a` shim (`INPUT(-lunwind)`); `-C target-feature=+aes,+neon` for gxhash; dropping the jemalloc feature; and an `LD_PRELOAD` shim calling `mallopt(-204, 0)` to switch off bionic heap pointer tagging.

## 3. Corrections to earlier conclusions

### 3a. MORK's portability verdict was too pessimistic
`REPORT_MORK.md` and `BLOCKED.log` rate three blockers "high". Measured on hardware:

| claimed | measured |
|---|---|
| `/dev/shm` hardcoded — "breaks on Android *and* macOS" | **does not affect `mork run`** — only the ArenaCompactTree paths `mork test` exercises. 33 programs ran on Android without touching it. (S14: absent from the `server` branch entirely.) |
| jemalloc + Android 16 KB pages | wrong failure mode. This device has **4 KB** pages; jemalloc fails at **link** time (`_rjem_*` undefined) and dropping it costs one word |
| nightly required | confirmed, unchanged |

`GAP_MATRIX.md` row 7 ("run MORK on Linux desktops only … until its three portability blockers are resolved") should be rewritten: MORK is a phone-capable engine today. The licence question is unchanged and is the operator's accepted risk.

### 3b. A new blocker nobody had, because nobody had run it
**Android heap pointer tagging vs PathMap's `slim_ptrs`.** Android 11+ tags heap pointers in the top byte; `slim_ptrs` packs its own bits there, and bionic aborts on the first `free()`:
```
Pointer tag for 0x6e88c20060 was truncated
Aborted
```
Invisible in every build; appears only on a device. An app disables it with one manifest line (`android:allowNativeHeapPointerTagging="false"`); a bare binary needs the LD_PRELOAD shim. Turning `slim_ptrs` *off* is not an option — PathMap's non-slim path no longer compiles (6 errors).

**This is the general lesson of both spikes: the failures that mattered were invisible until real silicon.** Everything cross-compiled cleanly and then aborted, or ran and agreed perfectly. There is no substitute for the device.

### 3c. A phone is ~2.7× slower than a laptop, not an order of magnitude
S15: 404k vs 1.08M interpreter steps/s. S16: 2.1–3.0× on MORK wall-clock. Per S9's finding that this workspace's timings were taken on a loaded machine, treat the **ratio** as the result, not the absolutes. A 2–3× ratio is what makes a nightly charge-time fleet arithmetically interesting; 20× would not have been.

## 4. How this lands against S9–S14

- **S12** (INT8 exactness, de-risked in simulation) now has its hardware target identified: `libsnap_qnn.so` is present in `/vendor/lib64`, so the route is **Qualcomm QNN / Hexagon**, not only NNAPI. M2.1 remains the one unmeasured hazard — output requantisation and whether the scale can be pinned by the job.
- **S11** (64× bundling compression at recall 1.0) plus this device's 11 GB RAM means shard size is comfortably a non-issue on this class of phone; the binding constraint is the OS execution window (S6), not memory.
- **S13** (crossover ~1.5%, not 5–9%) is unaffected — it is a desktop-BLAS measurement — but the shaping target it tightened should be re-measured on the phone's actual kernels before M4 commits to it.
- **S14** (wrong MORK branch) still stands: this spike is on `main`, because `differential/` and the corpus only exist there. The `server` branch's HTTP boundary should be tested on-device next.

## 5. What is still unmeasured
No WorkManager, no JNI, no app; a command-line binary in `/data/local/tmp` over adb. Nothing measured on battery, under thermal load, or in Doze. No NPU. No shard store. The device was plugged in and cool for every run.
