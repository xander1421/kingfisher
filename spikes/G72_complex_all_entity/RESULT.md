# G72 — ComplEx all-entity beats G51 support−∞ on this protocol

Official FB15k-237, filtered rank over **all 14,541 entities**. Prior/G51
use support scores and −∞ elsewhere (same as G59; reproduced 0.2334 /
0.2585). ComplEx scores everyone: Re(⟨h, r, conjugate(t)⟩).
literature_compare **unavailable** (no excerpt table).

Do not early-stop before epoch 10. Patience on VALID after that. Best
eligible epoch was **10** (valid sample MRR 0.2903); valid then fell
(patience 8, stop at 18). Epoch 5 valid sample was 0.2976 but
**ineligible**. Test was scored once, on the epoch-10 checkpoint (A26).

| arm | protocol | MRR | Hits@1 | Hits@10 |
|---|---|---:|---:|---:|
| prior (support −∞) | all-entity | 0.2334 | 0.1700 | 0.3541 |
| G51 (support −∞) | all-entity | 0.2585 | 0.1898 | 0.3837 |
| ComplEx dim=64, AdaGrad 1-N, ep 10 | all-entity | **0.2755** | 0.1916 | 0.4452 |

F1 quiet: ComplEx − G51 = **+0.0170** (bar +0.005).
F2 quiet: 0.2755 > official prior 0.2334.
`certify ok=true`. C1–C5 hold. n=20466 leak=0 nent=14541 npred=237.

Head ComplEx 0.1851 vs G51 0.1645 vs prior 0.1363. Tail 0.3659 vs
G51 0.3525 vs prior 0.3305. Hits@1 is almost G51 (0.1916 vs 0.1898);
the lift is Hits@10.

G66 DistMult on this same column was **0.2195** (early-stop epoch 1,
F1+F2 fired). This is not that run. G59 gated **0.2679** and G54
**0.2313** are a different protocol (support −∞ / gate) and are not
withdrawn.

Evidence: `complex.json`. Check: `python3 kitchen/test_g72.py`.
