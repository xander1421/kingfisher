# G76 — DistMult under G72's protocol is not G66

Official FB15k-237, filtered rank over **all 14,541 entities**. G66
DistMult **0.2195** lost to the prior because valid early-stop picked
**epoch 1**. This row uses G72's protocol: dim=64, unfiltered 1-N
softmax, AdaGrad, no eligible checkpoint before epoch 10, patience 8.
literature_compare **unavailable**.

G66 0.2195 is not withdrawn as a measurement of that run. It is not a
DistMult verdict.

## Verdict

**DistMult 0.2852 / H@10 0.4552 vs G51 0.2585 (+0.0267) vs official
prior 0.2334 vs ComplEx 0.2755 (+0.0097).** F1 quiet. F2 quiet. F3
quiet — real bilinear, trained past epoch 1, **beats this tree's
ComplEx** on the same protocol. Head 0.1923 / tail 0.3781.

Valid sample at epoch 5 was 0.3083 and **ineligible** (G66 trap). Best
eligible is epoch 10 (0.3054), then valid fell (patience 8, stop at
18). Test scored once on that checkpoint (A26).

| arm | protocol | MRR | Hits@1 | Hits@10 | best_epoch |
|---|---|---:|---:|---:|---:|
| prior (support −∞) | all-entity | 0.2334 | 0.1700 | 0.3541 | — |
| G51 (support −∞) | all-entity | 0.2585 | 0.1898 | 0.3837 | — |
| G66 DistMult dim=50 | all-entity | 0.2195 | — | 0.3655 | **1** |
| G72 ComplEx dim=64 | all-entity | 0.2755 | 0.1916 | 0.4452 | 10 |
| **G76 DistMult dim=64** | all-entity | **0.2852** | 0.2008 | **0.4552** | **10** |

Do not move G59 **0.2679** (observed+gate). Do not move G75 **0.3034**
(valid-select mix). This is the honest single-model DistMult column.

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | DistMult − G51 < 0.005 | +0.0267 | quiet |
| F2 | DistMult < 0.2334 | 0.2852 | quiet |
| F3 | DistMult < ComplEx 0.2755 | 0.2852 | quiet |

C1 20466. C2 leak 0. C3 nent=14541. C4 field order. C5 best_epoch=10.
C6 prior 0.2334. C7 literature unavailable. `certify ok=true`.

Scoreboard: pair-disjoint **0.2313**, official observed+gate **0.2679**,
all-entity ComplEx **0.2755**, all-entity DistMult **0.2852**,
all-entity valid-select **0.3034**.

Reproduce: `PYTHONUNBUFFERED=1 spikes/S5_hdc_prototype/.venv/bin/python spikes/G76_distmult_min10/distmult.py`
Check: `python3 kitchen/test_g76.py`.
