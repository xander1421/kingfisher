# G65 — replace G51 on head; do not stack

**GROK-2, 2026-08-19.** G63 stacked analog under the gate (+0.0001). This replaces G51 on head. `certify ok=true`. **F1 quiet. F2 fired. F3 quiet (+0.0012).** Official split. No literature MRR.

Against me: first run VOID on C3 — `apply_replace(..., "g51")` left G51 on for every head query (0.2650). Same class as G63's first run. Fixed; numbers below are the cached-rules rerun.

## Verdict

**Global replace loses**, as G62 measured first and G63 slices predicted: analog-on-head **0.2527** (G62 hybrid, this row B, byte-same at 4dp) / analog_only-on-head 0.2554 vs G59 **0.2679**. Analog is a better *prior* than counting (G63 analog_only +0.009; G62 analog-residual vs prior only +0.0035) and a worse *system* than G51+gate.

**Valid-selected replace** (per predicate, hashed before test): **0.2691** vs **0.2679** (+0.0012). Head 0.1727 vs 0.1703 (+0.0024). F2 fired: that is under the +0.005 bar. I am **not** moving the official headline. 0.2691 is a measured footnote, same rounding neighbourhood as G61/G63’s +0.0001, just larger.

| Arm | Head | Tail | MRR | Hits@10 |
|---|---|---|---:|---:|
| A | G59 pred-gate | G59 pred-gate | **0.2679** | 0.4037 |
| B | analog residual always | pred-gate | 0.2527 | 0.3814 |
| C | analog-only always | pred-gate | 0.2554 | 0.3855 |
| **D (headline)** | valid-picked {prior, analog, analog_only, g51} | pred-gate | 0.2691 | 0.4051 |

Valid head choice: **g51 172 / analog_only 28 / prior 14 / analog 9**. The gate still wants G51 on most heads.

## Head slice

| | MRR |
|---|---:|
| G59 gated head | 0.1703 |
| analog residual | 0.1398 |
| analog-only | 0.1453 |
| valid-select | 0.1727 |

Replacing G51 with analog globally **throws away** the lift G51 already had on head (0.1645–0.1703). Selection keeps G51 on 172/223 predicates and only swaps the rest.

## Controls

C1 20466. C2 leak 0. C3 pred-gate **0.2679**. C4 237. C5 train `6e4c2782169a…`.

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G65_head_replace/replace.py`. Check: `python3 kitchen/test_g65.py`.
