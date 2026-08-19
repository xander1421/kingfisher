# G79 — RotatE under G72's protocol is a working latent, not the winner

Official FB15k-237, filtered rank over **all 14,541 entities**. Same
trainer as G72/G76: dim=64, unfiltered 1-N softmax, AdaGrad, min_epoch=10,
patience 8. Score −||h ◦ r − t||² with |r_i|=1.

Sun 2019 Table 5 RotatE **0.338 / H@10 0.533** and the pinned README
**.337 ± .001 / H@10 .533** are now stored at
`corpus/refs/sun-2019-rotate-fb15k237.txt`. That run is self-adversarial
negative sampling, dim=1000, 100k steps. **literature_compare stays
unavailable as a headline.** Do not read 0.2643 vs 0.338 as a refutation
of RotatE (A18).

## Verdict

**RotatE 0.2643 / H@10 0.4200 vs DistMult 0.2852 (−0.0209) vs ComplEx
0.2755 (−0.0112) vs G51 0.2585 (+0.0058) vs prior 0.2334.** F1 fired.
F2 quiet — it is a working model. F3 fired. Head 0.1715 / tail 0.3572.
Best eligible epoch **17** (valid sample 0.2669).

On *this* trainer DistMult is still the single-model latent column.
RotatE's paper win is not portable to 1-N softmax dim=64.

| arm | protocol | MRR | Hits@1 | Hits@10 | best_epoch |
|---|---|---:|---:|---:|---:|
| prior (support −∞) | all-entity | 0.2334 | 0.1700 | 0.3541 | — |
| G51 (support −∞) | all-entity | 0.2585 | 0.1898 | 0.3837 | — |
| G79 RotatE dim=64 | all-entity | 0.2643 | 0.1869 | 0.4200 | 17 |
| G72 ComplEx dim=64 | all-entity | 0.2755 | 0.1916 | 0.4452 | 10 |
| G76 DistMult dim=64 | all-entity | **0.2852** | 0.2008 | **0.4552** | 10 |
| Sun 2019 RotatE (excerpt) | self-adv dim=1000 | 0.338 | 0.241 | 0.533 | — |

Do not move G59 **0.2679**. Do not move G77 **0.3101**.

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | RotatE − DistMult < 0.005 | −0.0209 | **FIRED** |
| F2 | RotatE < 0.2334 | 0.2643 | quiet |
| F3 | RotatE < ComplEx 0.2755 | 0.2643 | **FIRED** |

C1 20466. C2 leak 0. C3 nent=14541. C5 best_epoch=17. C6 prior 0.2334.
C7 excerpt present. C8 literature_compare=unavailable. `certify ok=true`.

`cite.py attributions`: Sun 2019 / Trouillon 2016 / Bordes 2013 /
Toutanova 2015 now resolve. Galárraga 2015 and Meilicke 2018/2019 stay
unsourced (AMIE/AnyBURL still have no excerpt).

Reproduce: `PYTHONUNBUFFERED=1 spikes/S5_hdc_prototype/.venv/bin/python spikes/G79_rotate_all_entity/rotate.py`
Check: `python3 kitchen/test_g79.py`.
