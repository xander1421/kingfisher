# G77 — adding DistMult to G75's set is a thin new high

Official FB15k-237, filtered all-entity. Loads G75 ComplEx embeddings and
G76 DistMult embeddings (no retrain). Valid-select per (p, dir) among
{DistMult, ComplEx, G51, prior}. Small-n (n<20) defaults to DistMult.
No additive stack. literature_compare **unavailable**.

C4: the 3-way {ComplEx, G51, prior} on these same rows is **0.3034** and
its mask sha256 `17509ac9df1e` matches G75. DistMult 0.2852 / ComplEx
0.2755 / G51 0.2585 / prior 0.2334 / G59 gate 0.2679 all reproduce.

## Verdict

**4-way G 0.3101 / H@10 0.4746 vs G75 0.3034 (+0.0067).** F1 quiet
(bar +0.005, clears it). F2 quiet. F3 quiet on a thin margin:
DistMult-picked keys (283 with test mass) have median TEST
DistMult−ComplEx **+0.0037**, and **130/283 = 45.9% lose** on test. The
signed falsifier asked for median ≤ 0; it did not fire. It is not a
clean DistMult-dominates-ComplEx story.

Choices: **distmult 291 / g51 77 / complex 53 / prior 25**. DistMult
took most of the keys G75 had given to ComplEx.

Do not move G59 **0.2679**. That is still the observed+gate column.

| Arm | Head | Tail | MRR | Hits@10 |
|---|---:|---:|---:|---:|
| prior | 0.1363 | 0.3305 | 0.2334 | 0.3541 |
| G51 | 0.1645 | 0.3525 | 0.2585 | 0.3837 |
| ComplEx G72 | 0.1851 | 0.3659 | 0.2755 | 0.4452 |
| DistMult G76 | 0.1923 | 0.3781 | 0.2852 | 0.4552 |
| G59 pred-gate | — | — | 0.2679 | 0.4037 |
| G75 3-way | 0.2066 | 0.4001 | 0.3034 | 0.4665 |
| **G77 4-way** | **0.2130** | **0.4071** | **0.3101** | **0.4746** |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | G − 0.3034 < 0.005 | +0.0067 | quiet |
| F2 | G < 0.3034 | 0.3101 | quiet |
| F3 | median(TEST DistMult − ComplEx \| valid DistMult) ≤ 0 | +0.0037 | quiet |

`certify ok=true`. Mask `db2e8614dbe9` hashed before TEST.

Scoreboard: pair-disjoint **0.2313**, official observed+gate **0.2679**,
all-entity DistMult **0.2852**, all-entity 3-way **0.3034**,
**all-entity 4-way 0.3101**.

Reproduce: `PYTHONUNBUFFERED=1 spikes/S5_hdc_prototype/.venv/bin/python spikes/G77_distmult_select/mix.py`
Check: `python3 kitchen/test_g77.py`.
