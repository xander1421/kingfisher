# G75 — valid-select {ComplEx, G51, prior} is a real all-entity high

Official FB15k-237, filtered rank over **all 14,541 entities**. ComplEx is
the G72 column (seed 72, dim=64, min_epoch=10, C4 0.2755 exact). G51/prior
use support scores and −∞ elsewhere (same rank_from_scores as G59). The
selector picks **one scorer per (predicate, direction)** from valid MRR
(n≥20; small-n defaults to ComplEx). No additive residual. No global
override. Mask `17509ac9df1e` hashed before TEST. literature_compare
**unavailable**.

Do not quote 0.3034 as replacing G59 **0.2679**. That column is
observed+gate (G51-or-prior, support−∞). This row is the all-entity
protocol. Pair-disjoint G54 **0.2313** is a third column.

## Verdict

**Dir-select F 0.3034 / H@10 0.4665 vs ComplEx 0.2755 / 0.4452 (+0.0279).**
F1 quiet (bar +0.005). F2 quiet (hybrid > ComplEx). F3 quiet: on the 97
keys valid picked G51, median TEST G51−ComplEx = **+0.0287**; 22/97 lose
on test (frac 0.2268), not a majority.

Mechanism is complementary, not a stack. ComplEx is dense and wins most
keys (319/446). G51 wins 97 keys where the bilinear form is weak on a
concentrated support — worst ComplEx slice in the G51-picked set is
p=14 tail **0.0508 vs G51 0.4043**. Prior wins 30 keys. Pred-select
(ignore direction) 0.3029 is almost F; G60-shaped.

G59 pred-gate on these same G51/prior ranks is **0.2679** (C6). That is
not this mix.

| Arm | protocol | Head | Tail | MRR | Hits@10 |
|---|---|---:|---:|---:|---:|
| A prior support−∞ | all-entity | 0.1363 | 0.3305 | 0.2334 | 0.3541 |
| B G51 support−∞ | all-entity | 0.1645 | 0.3525 | 0.2585 | 0.3837 |
| C ComplEx (G72) | all-entity | 0.1851 | 0.3659 | 0.2755 | 0.4452 |
| D G59 pred-gate | all-entity / support−∞ | — | — | 0.2679 | 0.4037 |
| E pred-select | all-entity mix | — | — | 0.3029 | 0.4650 |
| **F dir-select** | all-entity mix | **0.2066** | **0.4001** | **0.3034** | **0.4665** |

Valid dir choice: **complex 319 / g51 97 / prior 30**. 210/446 keys had
n<20 and defaulted to ComplEx. `replace_used_{complex,g51,prior}=true`.

Head gap remains (0.2066 vs tail 0.4001) but both sides moved: head
+0.0215 vs ComplEx, tail +0.0342.

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | F − ComplEx < 0.005 | +0.0279 | quiet |
| F2 | F < ComplEx | 0.3034 > 0.2755 | quiet |
| F3 | median(TEST G51 − ComplEx \| valid G51) ≤ 0 | +0.0287 | quiet |

C1 test n=20466. C2 leak 0. C3 nent=14541. C4 ComplEx 0.2755. C5 G51
0.2585 / prior 0.2334. C6 G59 gate 0.2679. C7 mask hashed. C8
literature unavailable. `certify ok=true`.

Scoreboard: pair-disjoint **0.2313**, official observed+gate **0.2679**,
all-entity ComplEx **0.2755**, **all-entity valid-select 0.3034**.

Reproduce: `PYTHONUNBUFFERED=1 spikes/S5_hdc_prototype/.venv/bin/python spikes/G75_complex_gate/hybrid.py`
(reuses `complex_emb.npz` if present; delete it to retrain).
Check: `python3 kitchen/test_g75.py`.
