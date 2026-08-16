# S52 — attack on S50. The harness is right and the headline core is unreachable.

**Verdict: S50's residency conclusion survives but is scoped narrower than stated. Its 2.26× core-placement finding is real and *unbankable* — Android's cpuset policy forbids the deployment configuration from ever touching the core it was measured on. One latent harness defect, immaterial at current magnitudes.**

S50 asked to be attacked before anything is built on it. Five findings, ranked by what they cost.

---

## 1. The prime core is not reachable from the deployment configuration — measured on device

S50's headline is cpu7 at 49.8 GB/s, and "core placement is worth 2.26×". Read the device's own scheduler policy:

```
background           0-1,4-5
system-background    0-1,4-5
restricted           0-1,4-5
foreground           0-5
top-app              0-7          <- the only cpuset containing cpu6/cpu7

cpu0 max = 3,532,800 kHz     cpu2 max = 3,532,800 kHz
cpu6 max = 4,473,600 kHz     cpu7 max = 4,473,600 kHz
```

**cpu6 and cpu7 appear in `top-app` and nowhere else.** A WorkManager worker doing charge-time compute is `background` by definition — it is confined to cpus 0-1,4-5, and `sched_setaffinity(cpu7)` from that cgroup is overridden by the cpuset. Even a *foregrounded* app tops out at cpu0-5. The prime cores belong to whatever the user is looking at.

So S50 measured the one core class the product can never have:

| | GB/s | reachable by a background worker? |
|---|---|---|
| cpu7 (prime), S50 headline | 49.8 | **no** |
| cpu0 (perf), S50's "slow" arm | 21.7 | yes |
| cpu0 scaled to its own max 3.53 GHz | ~26.4 | yes, if the governor cooperates |

**Every capacity figure derived from the 49.8 number is ~1.9× optimistic.** The deployment-relevant number is S50's cpu0 arm, and even that was taken at 2,900 of cpu0's 3,532 MHz — 82% of the core's own ceiling.

This does not make the 2.26× wrong. It makes it **unbankable**: the finding is that core placement matters enormously and *we do not get to choose*. That belongs in `SCHEDULER_SPEC` and in `out/`, next to the WorkManager 10-minute and dataSync 6h/24h caps, because it is the same class of constraint — the OS decides, not us.

## 2. The residency sweep only defeats one kind of locality

`bench_run` grows `inner` until a bracket exceeds 20 ms. At 195 rows (24 KB) that is ~18,000 back-to-back passes over the same buffer, permanently L1-resident. At 800,000 rows it is a handful of passes streaming from DRAM. **Both arms are perfectly sequential linear scans.**

A working hardware prefetcher makes a sequential DRAM scan behave like a resident one. That is what prefetchers are for. So "flat across 4,300× of store size" establishes:

> a *sequential* scan runs at the same rate whether or not it fits in cache

and not the stated general claim that residency buys nothing. The two are different, and the difference is exactly where VTCM lives: VTCM is a scratchpad for access patterns a prefetcher **cannot** predict.

Consequences:
- **For the prefilter, S50 is right.** The kernel is a linear scan; nothing to recover; conclusion holds.
- **For stage 2 it is unproven.** Joins, shortlist gathers and PathMap trie walks are pointer-chasing, and no spike has measured them at any store size.
- The control that would settle it is ~5 lines: a `--stride` or shuffled row-order arm that defeats the prefetcher. If it stays flat, residency is dead for good. If it collapses, the sequential result was the prefetcher's doing and N3's justification is alive for irregular work.

## 3. Four points is not a sweep

`sizes[] = {195, 3125, 100000, 800000}`. The claim "flat across 4,300×" rests on four samples, and the interesting transitions — L1→L2, L2→SLC, SLC→DRAM — all sit *between* consecutive points. With four samples a knee cannot be seen even if it exists. S46, whose evidence S50 replaces, had six. A twelve-point logarithmic sweep costs seconds and would make the claim unassailable.

## 4. The digest proves repeatability, not correctness

`bench_run` aborts if the digest moves between reps. That catches nondeterminism, which was the S46 failure. It does not catch a *wrong* kernel: there is no oracle, no recall check, no false-positive count — all of which S45 and S47 had.

This matters more than usual here because the kernel was **rewritten** for S50 (UB removed, RNG resequenced), so its scores legitimately differ from S45's and cannot be cross-checked against any previously published digest. A correctness regression introduced during that rewrite would be invisible to every control in the harness. The fix is one assertion: run the 12-row ground-truth query from S45 through the new kernel and check recall and false positives before reporting any bandwidth.

## 5. The null control cannot fire — latent, not material

`bench.h` rule 3 promises the null bracket has "the same shape" as the measurement. It does not:

```c
measurement:  for (i<inner) fn(ctx);          /* indirect, cannot be inlined */
null:         for (i<inner) bench_noop(ctx);  /* static inline, direct       */
```

Measured (`nullshape.c`, host, `-O3 -Wall -Wextra -Werror`):

```
S50 null bracket   (static inline, as written) :    0.400 ns/iter
same call INDIRECT (as the measurement is)     :    0.511 ns/iter
understated by                                  :      1.3x
```

So the DISQUALIFIED gate is computed from the wrong shape and understates by ~1.3×. **At S50's magnitudes this changes nothing** — 0.400 ns against a 1,100 ns smallest measurement is 0.036%, and the honest figure 0.0465% is still three orders of magnitude below the 1% threshold. The gate would not have fired either way.

It is reported because a control that *cannot* fail is not a control, and this harness exists precisely to stop that pattern. One-line fix: reach the no-op through a `volatile` function pointer so the null pays the same indirect call.

## 6. `2.26×` bundles two effects, only one of which travels

cpu0 at 2,900 MHz → 21.7 GB/s = **7.48 GB/s/GHz**
cpu7 at 3,283 MHz → 49.8 GB/s = **15.18 GB/s/GHz**

Per clock the gap is **2.03×**, which is microarchitecture (prime Oryon issues more vector work per cycle) and is stable across devices and thermal states. The remaining 1.13× is the clock difference, which is a DVFS state on the day. Report GB/s/GHz alongside GB/s; only the normalised figure transfers.

Compounding this: neither core was near its ceiling, and not by the same fraction — cpu7 reached 73% of 4,473 MHz, cpu0 reached 82% of 3,532 MHz. `khz_before`/`khz_after` are sampled at two instants with the autoscale loop between them; nothing samples frequency *during* the 15 timed reps. MAD ≤0.2% suggests it was stable, but stability is not the same as being measured.

---

## What survives

S50 is the largest methodological improvement in this workspace and I am not disputing its direction. Pinning, amortisation to 20 ms brackets, MAD over best-of, digest verification and `-Werror` all close real holes, and the residency conclusion is now properly established **for sequential access**. The retraction discipline is working.

What has to change before anything is built on it:

1. **Do not use 49.8 GB/s in any capacity model.** Use the cpu0 arm. `background` cpuset excludes cpu6/7 on this device.
2. Add a prefetcher-defeating arm before generalising "residency buys nothing" past sequential scans.
3. Add a correctness oracle, not just a stability digest.
4. Report GB/s/GHz.
5. Twelve sweep points, not four.

## And a second gap alongside the declared one

S50 declares that no defensible multi-threaded number remains. Agreed — and note it takes my own S44 V3 figure (3.4× on 10 threads) with it, which had no affinity control either.

But the multi-thread harness that replaces it must pin to the **background cpuset** (0-1,4-5), which is four cores of one class, not eight of two. A spin-barrier harness measuring 8 threads across both core types would produce another number the product can never reach.

## Reproducing

```sh
cc -O3 -Wall -Wextra -Werror -o nullshape nullshape.c && ./nullshape
adb shell 'for s in background foreground top-app; do cat /dev/cpuset/$s/cpus; done'
```
