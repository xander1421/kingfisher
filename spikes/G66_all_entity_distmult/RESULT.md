# G66 — DistMult all-entity is a third column, and this one lost

Official FB15k-237, filtered rank over **all 14,541 entities**. Prior/G51
use support scores and −∞ elsewhere (same as G59). DistMult scores
everyone. literature_compare **unavailable** (no excerpt table).

| arm | protocol | MRR | Hits@10 |
|---|---|---:|---:|
| prior (support −∞) | all-entity | 0.2334 | 0.3541 |
| G51 (support −∞) | all-entity | **0.2585** | 0.3837 |
| DistMult dim=50, 25 ep, AdaGrad, 1-N softmax | all-entity | **0.2195** | 0.3655 |

F1 fired: DistMult − G51 = **−0.039** (bar +0.005).
F2 fired: 0.2195 < official prior 0.2334 (undertrained).
Valid early-stop picked **epoch 1** (sample MRR 0.2153) then valid fell
while train NLL kept dropping. `certify ok=true`. C1–C5 hold.

Head DistMult 0.1560 vs G51 0.1645 vs prior 0.1363. Tail 0.2831 vs
G51 0.3525. Embeddings did not beat the observed+gate sport.

G59 gated **0.2679** and G54 **0.2313** are not withdrawn. This is a
protocol column, not a new headline.

Evidence: `distmult.json`. Check: `python3 kitchen/test_g66.py`.
