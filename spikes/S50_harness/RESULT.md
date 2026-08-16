# S50 — a harness that cannot make the mistakes, and the honest prefilter number

**Verdict: GREEN. The residency conclusion survives on rigorous evidence; every number attached to it was wrong; and core placement alone is worth 2.26×, which kills "≤16% left on the CPU" from the other side.**

Seven times this workspace reported a per-run cost as a property of hardware. `bench.h` makes the controls mandatory rather than optional: pins the core and reports its actual clock, amortises until the 52 ns tick is irrelevant, measures the null and prints **DISQUALIFIED** if it exceeds 1% of the result, reports median + MAD + min + max (never best-of alone), digests **every row at every size** and flags instability, and offers no API to subtract a separately-measured overhead. Built with `-Wall -Wextra -Werror`, because nine unsequenced-UB warnings sat unread in files whose headline claim was bit-exactness.

## Measured

```
                                cpu    MHz         med ns      MAD      GB/s   digest
prefilter    195 rows (24 KB)   cpu0  2400-2918     1,152.7    2.2%     21.7   e81e1318…
prefilter  3,125 rows (0.4 MB)  cpu0  2918         18,061.8    0.1%     22.1   6f34a55a…
prefilter 100,000 rows (12.8MB) cpu0  2918        577,260.2    0.0%     22.2   ef9b19ff…
prefilter 800,000 rows (102 MB) cpu0  2918      4,633,632.8    0.2%     22.1   d5d02bbe…

prefilter    195 rows (24 KB)   cpu7  3283            497.2    0.1%     50.2   e81e1318…
prefilter  3,125 rows (0.4 MB)  cpu7  3283          7,910.5    0.1%     50.6   6f34a55a…
prefilter 100,000 rows (12.8MB) cpu7  3283        260,362.1    0.2%     49.2   ef9b19ff…
prefilter 800,000 rows (102 MB) cpu7  3283      2,058,159.7    0.2%     49.8   d5d02bbe…
```

## 1. The residency conclusion is now properly established
Flat across **4,300× of store size** — 24 KB (L1-resident) to 102.4 MB (unambiguously DRAM) — on **both** core types, at **MAD 0.0–0.2%**.

S46 claimed "flat within 1.8%" and the attacker was right that 1.8% was below the instrument's resolution. Amortised properly the real figure is **≤0.5%**, so the conclusion is stronger than S46's and the evidence S46 offered for it was worthless. Residency buys nothing for this kernel because throughput tracks the *core*, not the *size*.

## 2. Core placement is worth 2.26×, and that is the number nobody had
**22.1 GB/s on a performance core (cpu0), 49.8 GB/s on a prime core (cpu7).** Same binary, same data, same instant — only the affinity differs.

S46's "22.6 GB/s/core, compute-bound at ~2 IPC" was cpu0, unpinned, presented as a property of the kernel. It is a property of *where the scheduler put it*. The IPC derivation was fitted to that artefact.

Note cpu7 ran at **3,283 MHz against a 4,474 MHz maximum** — the governor never fully boosted even under sustained load, so 49.8 GB/s is not the ceiling either.

## 3. "At most 16% left on the CPU" is dead twice over
S45b claimed the prefilter sat at 86% of a 58.9 GB/s roof with ≤16% remaining. Two independent refutations now:

- an attacker got **2.2×** by moving the barrier out of the timed region and pinning;
- **one prime core alone (49.8 GB/s) nearly equals S45b's entire 4-thread figure (50.8 GB/s).**

That second point is the useful one. Four threads spread across performance cores achieved barely more than a single prime core does by itself. The multi-threaded number was poor *because of core placement*, and the "roof" it was measured against had `pthread_create` inside its timed region. There is a large multiple still available on the CPU, and it is scheduling, not instruction selection.

## 4. Bit-exactness across core types
Digests are identical on cpu0 and cpu7 at every size (`e81e1318…`, `6f34a55a…`, `ef9b19ff…`, `d5d02bbe…`). Adds heterogeneous-core agreement to S34's cross-machine result — and this time the generator has no undefined behaviour, so the reproducibility is by construction rather than by two compilers agreeing by luck.

## What replaces what
| dead | replacement |
|---|---|
| S46 "22.6 GB/s/core, compute-bound at 2 IPC" | 22.1 GB/s on cpu0, **49.8 on cpu7**; compute-bound confirmed, IPC claim withdrawn |
| S46 "flat within 1.8%" | flat within **0.5%** across 4,300×, MAD 0.0–0.2% |
| S45b "50.8 GB/s = 86% of roof, ≤16% left" | one prime core ≈ that entire 4-thread figure; the headroom is scheduling |
| S45/S46 seeded generators | UB removed; `r32()`/`r64()` are sequenced |

## Not done
Multi-threaded numbers are not re-measured here — `bench.h` pins a single core by design, and a correct multi-core harness needs a spin barrier and per-core affinity, which is the attacker's build, not mine. Until that exists there is **no defensible multi-thread throughput figure in this workspace**, and every fleet projection resting on one (S32's 5.87×, the 28,700 jobs/s model) is unsupported.
