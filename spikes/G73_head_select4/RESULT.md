# G73 — valid-select HEAD among {gated-G51, analog_only, AA, prior}

**GROK-LOCAL.** Tail stays G59 pred-gate. Official split. `certify ok=true`.
**F1 FIRED. F2 FIRED. F3 FIRED.**
analog_only is G63 (rank analog scores, not residual-on-prior). AA is G67.
G67 0.2706 did **not** include analog_only. literature_compare unavailable.
Official headline stays **0.2679**.

Against me: first run is VOID if D leaves G51 on for every head, or if
analog_only is residual-on-prior (head 0.1398). This run
`replace_used_analog_only=true`
(20466/20466 head queries used analog_only)
`replace_used_aa=true`
(20466/20466 head queries used AA).

## Verdict

**Global analog_only-head replace loses**: D **0.2554** vs gated **0.2679**
(-0.0125). F1 fired (D ≤ 0.2679). analog_only head 0.1453 vs prior 0.1363 vs gated 0.1703.
Global AA-head E **0.2500** (-0.0179); AA head 0.1344.

**Valid-select F is a footnote, not a new high** (0.2714 vs 0.2679, +0.0035 < +0.005). Head 0.1774 vs gated 0.1703. G67 0.2706 was {g51_gated, AA, prior} without analog_only; this row is a new measurement. I am **not** moving the official headline.

| Arm | Head | Tail | MRR | Hits@10 |
|---|---|---|---:|---:|
| A | prior | prior | 0.2334 | 0.3541 |
| B | G51 | G51 | 0.2585 | 0.3837 |
| C | G59 pred-gate | G59 pred-gate | **0.2679** | 0.4037 |
| D | analog_only always | pred-gate | 0.2554 | 0.3855 |
| E | AA always | pred-gate | 0.2500 | 0.3887 |
| **F (headline)** | valid-picked {g51_gated, analog_only, AA, prior} | pred-gate | 0.2714 | 0.4126 |

Valid head choice: **g51_gated 167 / aa 30 / analog_only 25 / prior 1**. Mask sha256 `6b16b2d9ad6d…` hashed before test.

## Head slice

| | MRR |
|---|---:|
| prior | 0.1363 |
| G51 | 0.1645 |
| G59 gated | 0.1703 |
| analog_only | 0.1453 |
| AA | 0.1344 |
| valid-select | 0.1774 |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | D ≤ 0.2679 | D=0.2554 | FIRED |
| F2 | F − 0.2679 < 0.005 | F=0.2714 Δ=+0.0035 | FIRED |
| F3 | analog_only head ≤ 0.1703 | analog_only head=0.1453 | FIRED |

## Controls

C1 test n=20466. C2 leak 0.
C3 pred-gate **0.2679**. C4 237 rels.
C5 select mask hashed before test (6b16b2d9ad6d…).
C6 analog_only head **0.1453** (G63 0.1453, not residual 0.1398).
C7 AA head **0.1344** (G67 0.1344).

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G73_head_select4/head_select.py`.
Check: `python3 kitchen/test_g73.py`.
