# G56 — G54's DEV gate is a mechanism, not 237-way selection noise

Question first: G54 moved TEST 0.2274 → **0.2313** by turning G51 off on
105 predicates using DEV Δ. That can be multiple-testing. Google card:
look at the noise.

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | DEV-gated is not above the 95th percentile of 1000 same-size random masks | **did not fire.** 0/1000 ≥ 0.2313 |
| F2 | train-entropy hard gate ≤ G51 | **fired.** 0.2235 vs 0.2274 (−0.0039) |

`certify ok=true`. C1 0.1732. C2 0.2274. C3 leak=0. C4 `(p,s,o)`. C5 reconstructed DEV-gated **0.2313** matches G54.

## Arms

| arm | MRR |
|---|---:|
| prior | 0.1732 |
| G51 always-on | 0.2274 |
| **DEV-gated G51** (n&lt;20 keep, else G51 iff DEV Δ&gt;0) | **0.2313** |
| train-entropy gate (G51 iff H(p) &gt; train median) | 0.2235 |

## Null (1000 random OFF-sets of size 105 among 235 eligible)

| | MRR |
|---|---:|
| random min | 0.1792 |
| random median | 0.2031 |
| random p95 | 0.2192 |
| random max | 0.2272 |
| DEV-gated | **0.2313** |

Randomly turning G51 off on 105 names **hurts** (median 0.2031, even the
luckiest 0.2272 still ≤ always-on G51). The DEV mask is not a lucky
draw from that distribution. P(rand ≥ 0.2313) = **0/1000**.

Entropy cannot replace DEV: low-H predicates still have small *positive*
lift (G54 Q0 Δ+0.0082). Turning them off loses 0.0039, the same
magnitude DEV *gains* by turning off the actual hurting names.

## What this is as a model

The architecture that currently exists and is not a rewrite of the prior:

```
score = G51_lift(c | s, p)   if DEV says Δ(p) > 0 or n_dev < 20
      = log P(c | p)         otherwise
```

Mask hashed before TEST. No extra β. Type, analog, stack, entropy, and
G53 attention are not this. Analog still +0.0032 vs prior (G54 F3),
under the +0.005 bar.

G51 may rank. The mask is kitchen. Neither enters F001.

Evidence: `gate_null.json`. Check: `python3 kitchen/test_g56.py`.
