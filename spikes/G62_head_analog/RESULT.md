# G62 — head analog loses to the gate

Official-test head is 0.1703 vs tail 0.3655 because the **prior** is
0.1363 vs 0.3305. Same-pair leak is 0, so length-1 inverse features
cannot fire. Analog (object-signature Jaccard) was the leftover
observed model that is not a rewrite of P(c|p) in disguise.

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | hybrid ≤ G59 gated 0.2679 | **fired.** 0.2527 (**−0.0152**) |
| F2 | analog head ≤ gated head 0.1703 | **fired.** 0.1398 (**−0.0305**) |

`certify ok=true`. C1 20466. C2 leak=0. C3 gated **0.2679**. C4 237.

## Arms (official test)

| arm | MRR |
|---|---:|
| prior | 0.2334 |
| G51 | 0.2585 |
| valid-gated (G59) | **0.2679** |
| gated tail + analog head | 0.2527 |

Head only: prior 0.1363, analog **0.1398** (+0.0035 — same size as G54's
global analog +0.0032 vs prior), G51 0.1645, gated **0.1703**. Analog
is still a noisy prior. Replacing the gate on head throws away the
2-hop lift that *does* exist there (+0.0282).

Scoreboard unchanged. Literature unavailable. Head gap unread as a
*new model*; it is the frequency of subjects, not a missing analog.

Evidence: `head_analog.json`. Check: `python3 kitchen/test_g62.py`.
