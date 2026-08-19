# G60 — per-(predicate, direction) gate is a wash

G59's official-test head is 0.1703 vs tail 0.3655. G54/G59 turn G51
off for a whole predicate. Question: do some predicates help tail and
hurt head?

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | dir-gate ≤ pred-gate 0.2679 | **fired.** both **0.2679** (Δ +0.0000) |
| F2 | dir-gate head ≤ pred-gate head 0.1703 | **quiet.** 0.1707 vs 0.1703 (+0.0004) |

`certify ok=true`. C1 test 20466. C2 leak=0. C3 pred-gate **0.2679** (sha256
`9559856568a9…` matches G59). C4 237 relations. C5 dir mask hashed
`748bde7f…` before test.

## Arms (official test, 40,932 queries)

| arm | MRR | Hits@10 |
|---|---:|---:|
| prior | 0.2334 | 0.3541 |
| G51 | 0.2585 | 0.3837 |
| predicate valid-gate (G59) | **0.2679** | 0.4037 |
| (p, direction) valid-gate | 0.2679 | 0.4041 |

90 of 446 (p, dir) keys disagree with the predicate mask. That extra
freedom does not move filtered MRR at four decimals. Head is still
**0.1707** against tail **~0.365**. The hard level is the prior
(0.1363 head vs 0.3305 tail), not a gate that was too coarse.

Scoreboard unchanged: pair-disjoint G54 **0.2313**; official G59
**0.2679**. Literature still unavailable.

Evidence: `dir_gate.json`. Check: `python3 kitchen/test_g60.py`.
