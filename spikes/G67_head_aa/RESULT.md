# G67 — Adamic–Adar on official-test HEAD only

**GROK-LOCAL.** Tail stays G59 pred-gate. Official split. `certify ok=true`.
**F1 FIRED. F2 FIRED. F3 FIRED.** No analog redo (G62/G63/G65). No β grid.
literature_compare unavailable. Official headline stays **0.2679**.

Against me: first run is VOID if D leaves G51 on for every head. This run
`replace_used_aa=true` (20466/20466 head queries used the AA rank).

## Verdict

**Global AA-head replace loses**, G62 class: D **0.2500** vs gated **0.2679**
(−0.0179). F1 fired (D ≤ 0.2679). AA is not a better head *prior* either:
0.1344 vs prior 0.1363 (−0.0019). G63 analog_only was a better head prior
(+0.009). Raw common-neighbor count is worse still (0.1192). Graph is
simple undirected train {s,o}, p ignored. The feature does not need a
train edge on (s,o); it still does not close P(s|p).

**Valid-select E is a footnote, not a new high** (0.2706 vs 0.2679, +0.0027
< +0.005; G65 +0.0012 class). Head 0.1757 vs gated 0.1703 (+0.0054 on the
slice, not the official bar). I am **not** moving the official headline.

| Arm | Head | Tail | MRR | Hits@10 |
|---|---|---|---:|---:|
| A | prior | prior | 0.2334 | 0.3541 |
| B | G51 | G51 | 0.2585 | 0.3837 |
| C | G59 pred-gate | G59 pred-gate | **0.2679** | 0.4037 |
| D | AA always | pred-gate | 0.2500 | 0.3887 |
| **E (headline)** | valid-picked {g51_gated, AA, prior} | pred-gate | 0.2706 | 0.4116 |

Valid head choice: **g51_gated 186 / aa 32 / prior 5**. Mask sha256 `3a68ff18f3e7…` hashed before test.

## Head slice

| | MRR |
|---|---:|
| prior | 0.1363 |
| G51 | 0.1645 |
| G59 gated | 0.1703 |
| AA | 0.1344 |
| CN (ablation) | 0.1192 |
| valid-select | 0.1757 |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | D ≤ 0.2679 | D=0.2500 | FIRED |
| F2 | E − 0.2679 < 0.005 | E=0.2706 Δ=+0.0027 | FIRED |
| F3 | AA head ≤ 0.1703 | AA head=0.1344 | FIRED |

## Controls

C1 test n=20466. C2 leak 0.
C3 pred-gate **0.2679**. C4 237 rels.
C5 select mask hashed before test (3a68ff18f3e7…).

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G67_head_aa/aa.py`.
Check: `python3 kitchen/test_g67.py`.
