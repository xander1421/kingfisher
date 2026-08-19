# S41 — what transfers to the emulator: every digest, no timing, and not `i8mm`

**Verdict: GREEN for correctness, RED for performance, and the boundary is
measured rather than inferred.** The emulator reproduces **every digest the
phone produces, byte for byte**, and can produce **no usable timing at all** —
not merely noisy timing, but timing whose governor-invariant unit is
uncomputable there.

Run while **both devices were attached simultaneously** — real phone
`R5CY93675MK` (SM-S938B, Snapdragon 8 Elite) and `emulator-5554`
(`sdk_gphone64_arm64`, ranchu/QEMU, Android 16, arm64-v8a). Same binaries pushed
to both, same inputs, same commands. That window closes when the phone goes.

## 1. Correctness transfers completely

`fuelrun.v0.android`, `job_terminating.metta`, fuel 5,000,000:

| | phone | emulator | S15 recorded baseline |
|---|---|---|---|
| `fuel_used` | 100082 | **100082** | 100082 |
| `n_results` | 11 | **11** | — |
| `raw_hash` | `c2940ab5…1261ab3` | **identical** | `c2940ab5…1261ab3` |
| `sorted_hash` | `651651de…7eeaf51c` | **identical** | — |

`raw_hash` is over results **in interpreter order**, which S15 established is the
stronger property and the one optimistic verification actually needs. It holds
across QEMU.

`remeasure` (S50's pinned harness), digests at three store sizes:

| rows | phone | emulator |
|---|---|---|
| 195 | `e81e13183445ecaf` | **e81e13183445ecaf** |
| 3,125 | `6f34a55a25e0f453` | **6f34a55a25e0f453** |
| 100,000 | `ef9b19ff0a48e363` | **ef9b19ff0a48e363** |

**So the emulator can carry the determinism chain**, which is the only claim
group `out/LEDGER.md` records as never having been dented.

## 2. Timing does not transfer, and the reason is worse than noise

```
                        phone                    emulator
195 rows      MAD  16.9 ( 1.5%)          MAD  142.2 (12.4%)
3,125 rows    MAD  17.6 ( 0.1%)          MAD 2209.8 (13.3%)
100,000 rows  MAD 1090.7 ( 0.2%)         MAD 41961.1 ( 5.8%)
clock         2918-2918 MHz              0-0 MHz
```

Spread is an order of magnitude worse. **But the disqualifying fact is the clock
line, not the spread**: the emulator exposes no `scaling_cur_freq`, so it reads
**0 MHz**.

S50's central methodological result was *"report cycles/row, not GB/s — GB/s on
this device is a function of the governor; cycles/row held to three digits across
every clock and thermal state."* **Cycles/row cannot be computed where there is
no clock.** The emulator can therefore only emit GB/s, which is precisely the
unit the fleet retired. Its numbers are not merely soft; they are in the
abandoned unit and there is no conversion.

## 3. `i8mm` is absent — and a feature-flag reading is not a measurement

```
phone     … asimddp sha512 … frint  i8mm  bf16 rng bti ecv afp rpres    nproc=8
emulator  … asimddp sha512 … frint        bf16 afp sme2 smei8i32 …      nproc=1
```

The phone has **`i8mm` (SMMLA)** — the exact int8 matrix instruction AGENT-4
identified as the CPU's native exact kernel. The emulator does not. It carries
SME/SME2 instead, which the phone lacks.

**I expected the `-march=armv8.6-a+i8mm+dotprod` binary to SIGILL and it did
not — `rc=0` on both.** Running it is what corrected me: `remeasure.c` uses
`vcntq_u8` / `veorq_u64` / `vld1q_u64`, all baseline NEON. The `+i8mm` flag
*enables* the instruction; the code never *emits* it. So the packed-popcount
prefilter runs on the emulator unchanged, and the digests above prove it runs
correctly.

**What would break is any kernel that actually emits SMMLA or int8 SDOT** — i.e.
exactly the ~40-line SDOT/SMMLA kernel AGENT-4 proposed as the honest baseline
the NPU must beat. That work cannot be done here.

*Before reporting that a check failed to catch X, prove X is a change* —
ATTACKER-1's rule this morning, and it applies to absences too. Reading a
missing flag and predicting a crash would have shipped a false claim.

## 4. `nproc=1`

Every multi-core result is unreproducible: S51's 115.8 GB/s at T=7, S53's
residency-as-a-threads×size surface, S45b's thread-count reversal, S54's
background-cpuset finding (there is one core; there is no cpuset question).

## What may and may not be claimed from the emulator

| may | may not |
|---|---|
| byte-identical digests, cross-arch agreement | any wall-clock, GB/s or cycles/row |
| `fuel_used`, `raw_hash`, `sorted_hash` | anything multi-core |
| exactness gates, recall, rows-checked (counts) | `i8mm`/SDOT/SMMLA paths |
| protocol, schema, verifier logic | thermal, sustained-vs-burst, DVFS |
| — | anything about the NPU (never possible anyway) |

**Counts transfer. Clocks do not.** That is the same split S43/S44 found for
contention: every number stated as a count survived audit, every number stated in
seconds died.

## What this does not show

- One program, one kernel, one emulator image, one host. Digest agreement on
  three sizes is not agreement on the corpus — S16's 33/33 cross-arch comparison
  has not been repeated here and should be, since it is the broader claim.
- The emulator was not pinned or quiesced; its 12-13% MAD may improve. It would
  not matter — the clock is still 0.
- `ro.boot.qemu=1`, `hardware=ranchu`. This is QEMU, not a second silicon
  implementation, so agreement here is weaker evidence of cross-*hardware*
  determinism than the phone/laptop pair already in the ledger.

## Reproducing (needs both attached)

```sh
adb -s <device> push spikes/S30_speed_duel/bin/fuelrun.v0.android /data/local/tmp/kfsim/fuelrun
adb -s <device> shell 'cd /data/local/tmp/kfsim && ./fuelrun job_terminating.metta 5000000'
adb -s <device> shell 'cd /data/local/tmp/kfsim && ./remeasure 1'
```
