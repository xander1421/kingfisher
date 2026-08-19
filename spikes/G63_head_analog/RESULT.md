# G63 — head is flatter; analogical is a better head prior; it does not raise 0.2679

**GROK-2 (renamed from collided G61), 2026-08-19.** G60: dir-gate is a wash. `certify ok=true`, 5 controls, 3 falsifiers stated in CHANNEL before the directory. **F1 quiet. F2 quiet. F3 quiet at +0.0001 (rounding, not a high).** Official split. No literature MRR.

Against me: first run VOID on C3 — `gated_mix` left G51 on for every head query (0.2650 ≠ 0.2679). Fixed; numbers below are the second run.

## Verdict

Official head is hard because **subjects are flatter than objects** (median H 4.81 vs 3.88). A **head-only** analogical residual (G54 analog, tail untouched) beats the head frequency prior **0.1363 → 0.1453 (+0.0090)**. Put under the G59 predicate gate, overall MRR is **0.2680** against G59 **0.2679**. I will not quote 0.2680 as a new official high.

| Arm | What | MRR | Hits@10 |
|---|---|---:|---:|
| A | frequency prior | 0.2334 | 0.3541 |
| B | G51 | 0.2585 | 0.3837 |
| C | G59 pred-gate | **0.2679** | 0.4037 |
| **D (headline)** | head analog + same pred-gate | 0.2680 | 0.4055 |
| E | analog-only, both directions | 0.2432 | 0.3681 |

## Entropy (F1)

| | median H |
|---|---:|
| objects of p (tail prior) | 3.882 |
| subjects of p (head prior) | **4.809** |

F1 was “head is not flatter.” **Quiet.** The G60 prior gap is the same entropy story as G54 Q3, concentrated on the subject side.

## Head slice

| | MRR |
|---|---:|
| head prior | 0.1363 |
| head analog-only | **0.1453** (+0.0090) |
| head G51 | 0.1645 |
| head analog+G51 | 0.1673 |
| G59 gated head | 0.1703 |

F2 was “analog is not a better head prior by +0.005.” **Quiet.** Global analog failed G54 F3; **head-only** analog is a real prior, not a rewrite of tail.

F3: 0.2680 − 0.2679 = **+0.0001**. Hits@10 +0.0018. Same rounding class as G57 lift>1. Scoreboard stays G59 **0.2679** / G54 **0.2313**.

## Controls

C1 test 20466. C2 leak 0. C3 pred-gate **0.2679**. C4 237. C5 train hash `6e4c2782169a…`.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G63_head_analog/head_analog.py`. Check: `python3 kitchen/test_g63.py`.
