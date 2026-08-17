# G25 — the curves cross. Evolution bought a different trade, not a better one.

**Verdict: neither the evolved population nor the un-evolved seed dominates.**
G24 compared them at one arbitrary operating point each and I drew a conclusion
from it ("the population found recall, not truth"). Letting both abstain turns
each into a curve, and the curves cross.

```
 thresh        EVOLVED (full)                      SEED (no_variation)
           rules   preds   corr    prec        rules   preds   corr    prec
   0.00       69  116083   4144  0.0357           32    5112   1127  0.2205
   0.02       44   66644   3865  0.0580           32    5112   1127  0.2205
   0.05       28   24120   2633  0.1092           32    5112   1127  0.2205
   0.10       18    5745   1199  0.2087           32    5112   1127  0.2205
   0.15       13    3693    893  0.2418           32    5112   1127  0.2205
   0.20       12    3625    875  0.2414           21    4069    967  0.2377
   0.30        1      66     15  0.2273            3     158     35  0.2215
```

Threshold chosen on **dev**, measured on **test**. A threshold is a parameter,
and a parameter fitted on the set it is scored against makes the score
meaningless — the same leak G22's three-way split exists to prevent.

## The reading that matters: the seed has no dial

```
evolved       7 distinct operating points, precision 0.036 → 0.242
seed          3 distinct operating points, effectively ONE
```

The seed's curve is **flat** at 0.2205 from threshold 0.00 through 0.15, because
its rules are the top-60 enumerated *by dev confidence* — they all clear every
filter until the threshold reaches them. It cannot trade.

At its own single operating point the seed is slightly better than anything
evolution offers nearby (1127 correct @ 0.2205 vs evolved 1199 @ 0.2087 or
893 @ 0.2418). **Everywhere else on the frontier, only evolution has points at
all.** The entire high-coverage region — 2633 correct @ 0.109, 3865 @ 0.058,
4144 @ 0.036 — exists only because of evolution.

So evolution's contribution is **range**, not a uniformly better curve. That is
a weaker claim than G24's and a more useful one: if you want ~1100 correct
answers at ~22% precision, evolve nothing and enumerate. If you want 2600 or
4100, enumeration has no setting that reaches them.

## My own positive control was corrupting the measurement

The first run of this script returned:

> **SEED DOMINATES** — evolution bought nothing abstention could not buy more
> cheaply; G24's coverage gain was an operating-point artifact

**That verdict was wrong, and the cause was the A15 plant.** The planted rule's
conclusions live in dev by construction (that is what makes it a held-out
control), so the rule can never score on test: it contributed **568 predictions
and 0 correct**. Only the evolved arm ever discovers it, so the plant loaded 568
guaranteed-wrong assertions onto one side of the comparison.

```
threshold 0.15, evolved   with plant  0.2096      without plant  0.2418
                          seed 0.2205 → LOSES     seed 0.2205 → WINS
```

The tell was the `t=0.50` row reading **"1 rule, 568 predictions, 0 correct"**.
A rule that survives the strictest filter while getting nothing right is not a
bad rule; it is a rule being scored against the wrong set.

**This is a failure class I had not seen before and it is worth naming:** a
positive control that is correct-by-construction on the selection set and
impossible on the evaluation set becomes a systematic penalty against whichever
arm succeeds at discovering it. The better the system, the worse it scores. It
is the only instrument failure I have hit that *punishes* success.

## A second correction, to the analysis in this same file

The script's original test was "at matched-or-better precision, who covers
more". That scored 6/7 for the seed and reads like a clean loss for evolution.
**It is the wrong test for crossing curves** — it collapses a two-dimensional
comparison onto one axis by fixing precision, which necessarily favours whichever
system is tuned near that precision. The Pareto frontier asks the same question
without choosing an axis, and gives the correct answer: neither dominates.

Both the old test and the frontier are printed, so the disagreement is visible
rather than resolved silently.

## What this does NOT show

- **Not that evolution is worth running.** It buys reach into a region
  enumeration cannot express, at precision that falls to 3.6% to get there.
  Whether that is worth anything depends entirely on the use, and for
  knowledge-graph completion the high-coverage end is probably not usable.
- **Not that 0.2418 beats 0.2205 meaningfully.** Those are 893 and 1127 correct
  out of ~40,800 test triples. Single split, single seed, no repeats, no error
  bars. The two numbers are close enough that I would not defend the ordering.
- **Not a tuned threshold grid.** Nine fixed thresholds, chosen before running.
  A finer grid would move the frontier points around; it would not create a
  dial the seed does not have.
- **The plant is still in the training graph** for the evolved arm, which spends
  some of its wage pool on a rule that cannot pay off on test. Excluded from
  scoring here, but not from the evolution that produced the population.
- One dataset, one split, one machine.

## Reproduce

```sh
cd spikes/G25_abstain && python3 curve.py     # ~100 s, re-runs two G24 arms
```
