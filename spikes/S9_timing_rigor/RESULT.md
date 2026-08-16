# S9 — re-measuring S5's throughput with a real methodology

**Verdict: RED for the original numbers, GREEN for the conclusion they supported.**
Every throughput figure in `S5_hdc_prototype/RESULT.md` is wrong by 4–9×, in the
pessimistic direction, and the 13.6× "cold vs warm" spread the report explained as
memory bandwidth was machine load. The operating point S5 recommended (D=1024)
survives, because it was chosen on memory and margin, not on timing.

Code: `bench_matmul.py` + `../bench.py`. Output: `timing.json`, `timing.log`.

## The defect

S5 shipped two files for the identical D=10000 workload, same seed:

| file | matmul | reported |
|---|---|---|
| `run1.json` | 7.731 s | 25.9 GOP/s |
| `run2.json` | 0.567 s | **352.9 GOP/s** |

The 352.9 became the headline; the D-sweep table carried cold numbers from a
different set of runs. A 13.6× methodology artefact was presented as a result,
and `RESULT.md` §Throughput rationalised it as "memory bandwidth on the 1 GB
INT8 array". That explanation cannot be right: for this kernel, ops = 2·q·n·D
and bytes touched = n·D, so arithmetic intensity is ~2·q ops/byte **independent
of D**. There is no bandwidth story to tell.

## Re-measurement — 7 reps per D, cold reported separately from warm median

```
matmul D=256    cold  35.568 ms | warm_med  13.057 ms | rsd 5.2% | cold/warm 2.72x | cold 144.0 warm 392.1 GOP/s
matmul D=512    cold  48.606 ms | warm_med  21.984 ms | rsd 8.5% | cold/warm 2.21x | cold 210.7 warm 465.8 GOP/s
matmul D=1024   cold  90.857 ms | warm_med  40.932 ms | rsd 1.1% | cold/warm 2.22x | cold 225.4 warm 500.3 GOP/s
matmul D=2048   cold  76.851 ms | warm_med  76.947 ms | rsd 0.7% | cold/warm 1.00x | cold 533.0 warm 532.3 GOP/s
matmul D=4096   cold 186.784 ms | warm_med 155.420 ms | rsd 1.1% | cold/warm 1.20x | cold 438.6 warm 527.1 GOP/s
matmul D=10000  cold 436.021 ms | warm_med 409.657 ms | rsd 6.5% | cold/warm 1.06x | cold 458.7 warm 488.2 GOP/s
```

Warm throughput is **flat at 390–530 GOP/s across a 39× range of D**, exactly as
the constant-arithmetic-intensity argument predicts. There is no D-dependent
throughput effect. S5's apparent one (55–71 GOP/s at D≤4096 versus 353 at
D=10000) was an artefact of comparing cold samples against a warm sample.

## The decisive check — replay the original, unmodified `hdc.py`

`spikes/S5_hdc_prototype/hdc.py` was re-run at D=1024 on an idle machine, with
no edits:

```
recorded (sweep_1024.json)  matmul 0.373 s   54.9 GOP/s   scores digest 8aba3d409add
replay   (today, idle)      matmul 0.070 s  290.7 GOP/s   scores digest 8aba3d409add
                                     5.3x           IDENTICAL OUTPUT
```

Byte-identical results, 5.3× apart in time. The code is not at fault and the
result is not at fault; **the measurement was taken on a loaded machine**. That
is consistent with the recon's own record: `DECISIONS.log` shows cargo builds of
hyperon and MORK, a `brew install openblas`, and a colima VM all running during
the same session S5 was measured in.

Note the recorded 0.373 s is worse than even a *cold* run on an idle machine
(0.091 s here). This was not a cold-cache effect. It was contention.

## What this changes

- **Every wall-clock and GOP/s number in S5 and S7 is unreliable** and should be
  re-taken. S7's "85 ms of recompute per query" — the number the entire
  verification-economics argument in `out/RISKS.md` and `out/FINAL_REPORT.md`
  rests on — was measured in the same session and is likely 4–5× pessimistic.
  The *ratio* S7 reports (commitment check is 0.006–0.8% of recompute) is a
  ratio of two contaminated numbers and is more robust than either.
- **The D=1024 recommendation stands.** It was argued from store size (102 MB per
  100k triples) and threshold margin (0.68), neither of which is a timing.
- **`bench.py` should be used for every future measurement in this workspace.**
  Cold and warm reported separately, spread printed, and inner-repeat scaling so
  no kernel is timed near the clock's resolution.

## What is still not measured
Absolute device throughput. Everything here is a laptop CPU through Accelerate,
which reaches ~500 GOP/s on this kernel. A phone NPU's number is unknown and is
not predictable from this — see S12 for what *can* be settled without silicon.
