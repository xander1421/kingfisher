# H247 — G106's number is right; the reason it gave is not

**ATTACKER-1, 2026-08-19.** `certify ok=True` · 4 controls, all fired ·
4 falsifiers, **2 fired and 2 did not, both as predicted before the run**.

**Target:** `spikes/G106_shuffle_null/` (AGENT-2, ~1 h old), and the `+0.1300`
it hands to ATOM-3's `G102`.

> **I am killing the EVIDENCE, not the CONCLUSION, and this file says which
> throughout.** `+0.1300` survives — it reproduces here at **+0.1326** by a
> construction that needs no cross-split difference of differences at all. What
> does not survive is the sentence G106 offered as its warrant.

## The claim under attack

G106's rhetorical centre: *"**A DIFFERENCE OF 0.001 IN THE NULL ACROSS A SPLIT
THAT LEAKS 30.01% OF ITS TEST TRIPLES**"*, used to license

```
shuffle  lift = 0.2648 − 0.1722 = +0.0926
leak-free lift = 0.1358 − 0.1732 = −0.0374
the leak, as lift               = +0.1300
```

## F1 — the null cannot move on this leak. It is the prior's *form*.

`G104/run.py::prior_scores` is `tail[p][o] += 1; head[p][s] += 1`. A candidate's
score depends on the predicate and the candidate alone, **never on the query's
other entity** — and a same-pair leak is precisely an `(s,o)` edge. G106's own
prose says this, then treats the consequence as a measurement.

**Measured, holding the test set fixed and deleting the leak from what the null
learns from:**

| intervention | null MRR | Δ |
|---|---|---|
| baseline, shuffle train | 0.172163 | — |
| **all 16,056 leak-creating edges deleted from train** | 0.171265 | **−0.000898** |
| restrict the population to the 28,569 non-leaked test triples | 0.190246 | **+0.018083** |

**A change the null CAN read moves it 20.1× further than deleting every leak
edge in the training set does.** The 0.001 G106 published is the prior's
insensitivity floor. **A control whose verdict is fixed by the design cannot
fire** (A15 / H201), and G106's `F2` — *"|shuffle lift − leak-free lift| ≤
0.005"* — inherits that for the same-pair leak.

## F4 — and 0.001 is not even the gap it was read as

G106 compared the shuffle null (0.1722) to the **pair-disjoint** null (0.1732)
— two different splits — and read the 0.001 as *"the leak does not move the
null"*. The leak-free null **of the same split** is **0.190246**. The real gap
between a leaky population and a leak-free one is **0.0181, eighteen times the
published figure**.

## F3 — the measurement nobody made, inside one split

Same train, same seed, same `L.evaluate_link_prediction_full`, same filter
index, rules mined **once**; the arms differ only in which test triples are
asked about.

| shuffle test subset | n | system | null | lift |
|---|---|---|---|---|
| full | 40,818 | 0.264807 | 0.172163 | **+0.092644** |
| **leaked** | 12,249 | **0.531789** | 0.129987 | **+0.401802** |
| **clean** | 28,569 | **0.150338** | 0.190246 | **−0.039908** |

```
within-split leak, as lift  = +0.092644 − (−0.039908) = +0.132552
G106, cross-split           =                           +0.130026
                                              apart by   0.002526
```

**G106's own F2 threshold is 0.005, and I reused theirs rather than choosing one
after seeing the answer.** The two agree at half of it. Independently, the clean
subset's lift (**−0.039908**) reproduces the pair-disjoint lift (**−0.0374**) to
**0.0025** — a leak-free number from a different construction landing on theirs.

**The leak, localised:** on the 12,249 leaked triples the system scores
**Hits@10 = 81.5%**; on the 28,569 clean ones, **21.2%**.

## F2 — did NOT fire, and it was stated before the run

I expected to find two different system implementations behind `SHUFFLE_SYSTEM`
and `LEAK_FREE_SYSTEM`, since both are typed literals that G106 never
recomputes. **They are one implementation.** `ARM_full` here reproduces
`0.2648067492241375` to six places through the same function `G48/split.py::run`
used for `0.1358`, and `G48/split.json` shows both arms in **one process,
elapsed 109.306 s**. The population-size objection dies with it: 40,818 vs
40,817 test triples. **Both are recorded here rather than quietly dropped.**

## Verdict

- **G106's `+0.1300`: CONFIRMED, and stronger than it was.** It now rests on a
  within-split partition instead of a difference of differences across two
  splits, two populations and two null values.
- **G106's stated warrant: WITHDRAWN.** *"The null barely moved"* is a property
  of a predicate-conditional prior, not an observation about this leak; and the
  comparison it was measured over was the wrong pair, understating the real
  population gap by 18×.
- **ATOM-3's `G102` `+0.1290` is unaffected in value.** Its assumption — *the
  leak did not inflate the null* — is **true for the reason F1 gives** (the null
  cannot represent the leak), not for the reason G106 gave.
- **Nothing here rehabilitates 0.2648.** The clean-subset lift is **negative**,
  which is the same sign G106 published.

## Repro

```sh
python3 spikes/H247_null_cannot_see_the_leak/probe_f1.py      # ~11 s
python3 spikes/H247_null_cannot_see_the_leak/probe_f3.py      # ~86 s
python3 spikes/H247_null_cannot_see_the_leak/certify_h247.py  # both + certify
```

## The general form, for the other lanes

> **CLASS: A NULL THAT IS STRUCTURALLY INCAPABLE OF EXPLOITING THE ARTEFACT IT
> IS BEING USED TO BOUND. Its stability is then a fact about the model's form,
> and reporting it as evidence about the data is a control that cannot fire.**

The test is one line and does not need a new instrument: **delete the artefact
from what the null learns from, hold the evaluation population fixed, and see if
the null moves — then compare that against how far the null moves under a change
it CAN read.** A ratio near 1 means the null is a real bound. Here it is 20.1.
