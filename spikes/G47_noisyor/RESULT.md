# G47 — noisy-OR moves filtered MRR 0.2648 → 0.2746, and 70% of that gain is on the third that leaks

**AGENT-2, 2026-08-18, builder cycle C20.** The first row in this lane that
tries to **move** the metric rather than audit it. Three falsifiers stated in
`CHANNEL.md` before the run; **none fired.** 3 controls, all fire.

## The hypothesis is not new and it is not mine

G30's own `RESULT.md`, line 89: *"AnyBURL uses weighted confidence aggregation
(noisy-OR / linear combination), whereas G17 uses simple max confidence."* **It
named the lever and never pulled it.** This pulls it.

`max`: `score = max(conf_i)`. `noisy_or`: `score = 1 - Π(1 - conf_i)`, which
rewards a candidate several independent rules agree on. **No free parameter,
deliberately** — A26 says a knob is not a mechanism, and noisy-OR has none to fit.

## Results, on G46's partition, because the blend is not trustworthy on its own

| partition | | **max** | **noisy-OR** | gain |
|---|---|---|---|---|
| **all** | MRR | 0.2648 | **0.2746** | **+0.0098** |
| **same-pair** (30.0%) | MRR | 0.5318 | **0.5545** | **+0.0227** |
| **no same-pair** (70.0%) | MRR | 0.1503 | **0.1546** | **+0.0043** |

| partition | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|
| all | 0.1748 → **0.1997** | 0.3169 → 0.3202 | 0.3929 → 0.3974 |
| same-pair | 0.3147 → **0.3902** | 0.6607 → **0.6578** | 0.8146 → **0.8123** |
| no same-pair | 0.1148 → 0.1180 | 0.1694 → 0.1754 | 0.2121 → 0.2195 |

- **F1** *if noisy-OR does not raise the no-same-pair partition above 0.1503 by
  more than 0.002, the aggregation difference does not explain the gap.*
  **Did not fire** — +0.0043.
- **F2** *if the blend gains while the leakage-free partition does not, the gain
  is bought on the leaky third and must not be published as a method
  improvement.* **Did not fire** — both partitions gain.
- **F3** *if the blended arm returns exactly 0.2648, the rewrite is inert.*
  **Did not fire.**
- **C1, instrument identity:** the **rewritten file under `max`** returns
  **0.2648 / 0.3929 exactly**. The copy is the same instrument; the operator is
  the only variable. · **C2** `max(0.4, 0.5) = 0.5` vs `noisy_or = 0.7`, so the
  operators differ and F3's inertness was detectable. · **C3** the parts
  recombine.

## What the numbers say that the falsifiers do not

**F2 did not fire, and it still would be wrong to call this a 0.0098 method
improvement.** The blended gain decomposes as
`0.30 × 0.0227 + 0.70 × 0.0043 = 0.0098` — **70% of the headline gain comes from
30% of the queries**, and that 30% is the partition G46 showed is carried by
same-entity-pair leakage. The honest figure for a method claiming to predict
unseen links is **0.1503 → 0.1546, a gain of 0.0043**, and that is what this row
reports as the result.

**The mechanism is visible in the Hits columns and it is mostly tie-breaking.**
On the leaky partition Hits@1 jumps **+0.0755** while Hits@3 and Hits@10 both
*fall slightly*. Max aggregation puts many candidates at identical confidence;
noisy-OR separates them by counting how many rules agree. On the clean partition
the improvement is small and spread evenly across @1/@3/@10 — a real if modest
ranking gain rather than a tie-break windfall.

## Method: a copy, not an edit

`agg.py` is `spikes/G36_repro_g34/length1_constants.py` with **8 aggregation
sites** rewritten to a single `bump()` helper and **nothing else changed**.

```
g34 original  2955ff29946ee8a4b5dc93f93f6ff1f4e6dae8434ead97beb4390b0928447377
g47 copy      adb2bcb40a7e932db1094438bbaf81f9a51c8bc4d838526ca54d055990b9fefc
```

A mid-sweep edit to a shared generator is the `pick_parent` contamination C7
paid for; G39 took the same route for the same reason. The rewrite asserts its
own site count (`n == 8`) and that no aggregation site survived it, so a missed
anchor fails loudly rather than shipping an arm that changed nothing.

## The bar this is measured against is itself contaminated (ATOM-3, recorded with attribution)

`.github/autoloop/PROGRAM.md:40` writes the threshold and the measurement on one
line — `filtered_mrr >= 0.2500 (Current: 0.2648)`. **The bar was set just under
the value it gates, and that value is the leak-blended one.** A threshold
calibrated from the number it judges cannot fail the current method; it can only
reject a worse one. Same family as the prefilter cutoff this repo already killed
for being chosen by an oracle reading the ground truth.

**Consequence for this row, stated rather than sidestepped:** under noisy-OR the
blended figure is **0.2746**, which clears 0.25 more comfortably — and the
leakage-free figure is **0.1546**, which does not clear it at all. **Neither
number is evidence about the threshold, because the threshold came from the same
leak.** Re-baselining `min_acceptable` is autoloop's config and not this lane's
to set; flagged, not changed.

## Scope

**This retracts nothing and challenges no number.** G46 stands, G34's ablation
verdict stands, and `max` remains what G34 published. Whether to adopt noisy-OR
is a separate decision that should be made on **+0.0043 on the clean partition**,
not on +0.0098 on the blend.

## Files

`agg.py` (the copy; `AGG` is the one variable) · `run.py` (both arms × three
partitions, controls, `certify`) · `agg.json` · `provenance.json`.

```sh
python3 spikes/G47_noisyor/run.py     # ~180 s, ok=true, C1 pins 0.2648
```
