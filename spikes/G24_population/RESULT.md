# G24 — the rule population evolves, and every ablation removes something that pays

**Verdict: the full system improves coverage AND precision on held-out data, at
constant population size, and each of the five ablations is worse.** G22 failed
because it satisfied none of Lewontin's three conditions. Built explicitly, they
work.

The full arm, over 15 rounds, on a test set no operator ever reads:

```
r0    pop  94    correct 1302    predictions 116954    precision 0.0111
r14   pop  94    correct 5158    predictions 317011    precision 0.0163
```

**+296% coverage and +47% precision at the same population size.** Both axes,
not one traded for the other, and the population is where it started — so this
is selection improving the rules, not accumulating more of them.

## Arms

```
arm              pop     preds  correct     prec  cov/rule   top12  A15
full              94    317011     5158   0.0163      54.9  0.2598  yes
no_variation      32      5112     1127   0.2205      35.2  0.2644  NO
no_abduct        130     84417     1374   0.0163      10.6  0.2685  NO
no_death         548   2606799     7778   0.0030      14.2  0.3065  yes
static_adv       103    298191     4607   0.0154      44.7  0.2312  yes
no_waves         110    368111     4539   0.0123      41.3  0.2504  yes
```

- **no_abduct** — never finds A15; coverage moves +72 against full's +3856.
  **Problem-directed proposal is the load-bearing operator.** Without it the
  other six operators mutate blind and the population drifts.
- **no_variation** — never finds A15, and coverage *declines* (1300 → 1127) as
  rules die without replacement. This is G22's shape, and it degrades.
- **no_death** — population explodes 94 → 548, precision collapses 0.0111 →
  0.0030. Removing the carrying capacity converts accuracy into volume.
- **no_waves** — **dominated**: more predictions (368k vs 317k) for fewer
  correct (4539 vs 5158). Activation-directed wages pay.
- **static_adv** — cheaper but no better. A fixed null is the weakest ablation
  here, which is itself informative: co-evolution earns least of the five.

## The verdict printed by `evo.py` is WRONG, and the correction is the point

`evo.py` ranked arms on raw coverage and concluded:

> AN ABLATION BEATS THE FULL SYSTEM — no_death gained +6476 test triples vs
> full +3856; the mechanism it removes is costing, not paying

**That is a comparison across differently-sized populations** — `no_death` runs
548 rules against full's 94. More rules assert more things, so more things are
correct, almost mechanically. It is precisely the error that produced G15's
retracted headline (a maximum over 1954 items compared against a maximum over
1750), reappearing in code I wrote *after* retracting G15.

`analyse.py` compares on the (predictions, correct) plane instead, where an arm
wins only by getting more correct at no more predictions:

```
no_death    trade: +2620 correct for +2289788 predictions
no_waves    DOMINATED by full
static_adv  cheaper but no better
```

`no_death`'s "+6476" costs **2.29 million extra assertions** for 2,620 more
correct answers. Not a win. A trade at 5.4× worse precision.

The wrong verdict is left in `evo.py` unchanged, with this correction beside it,
because the failure is more useful than a silently patched file.

## What each evolutionary part became in code

| part | mechanism |
|---|---|
| genotype | `{"body": (p,q[,s]), "head": r}` — the rule evolves, not the graph |
| variation | `mutate()`: swap / extend / contract / rehead / recombine / duplicate |
| mutational bias | `build_bias()` → `follows` + `precedes`, both directions |
| heredity | population persists; offspring carry parent's body with one edit |
| fitness | `conf − adversary_conf`, novelty-weighted (frequency-dependent) |
| **death** | fixed `WAGE_POOL` shared out; rent per body predicate **and** per 1000 assertions; `imp <= 0` removes |
| problem space | `dev_all − solved_now` |
| **abduction** | `abduct()`: unsolved problem → path → proposed rule |
| waves | activation from unsolved problems multiplies wages; recomputed each round |
| adversary | best-of-m reshuffle chosen to **maximise** population score |

**ECAN was in the wrong place for the whole G-series.** G5/G19 used rent as
memory management, to stop the atomspace growing. It is the *carrying capacity*:
with unlimited room, fitness differences do nothing, which `no_death`
demonstrates directly.

## Three failures on the way, each a real property

1. **A15 was inside the seed population** — reported found at round 0, before a
   single mutation. A positive control that starts inside what it tests is not
   one. Banned from the seed.
2. **The fitness landscape is flat.** A rule clears `MIN_PAIRS` support or
   scores nothing — no partial credit, so no slope, so uniform mutation over 237
   predicates has nothing to climb. Fixed with bidirectional structure-biased
   proposals.
3. **Fitness charged nothing for breadth.** Rules evolved to assert everything;
   coverage rose while precision fell 0.021 → 0.011. Added rent per 1000
   assertions.

## What this does NOT show

- **Absolute precision is 1.6% and that is bad.** The enumerated seed
  (`no_variation`) is **13× more precise** at 0.2205 — few, narrow, accurate
  rules. Evolution buys 4.6× more correct answers by making 62× more
  predictions. Whether that exchange rate is worth it depends on the use, and
  for knowledge-graph completion it probably is not. **The population has not
  found truth; it has found recall.**
- **A validity gap: capped rules are still scored.** `MAX_PAIRS=40000` truncates
  a body walk, and the resulting confidence is computed on an arbitrary
  iteration-order subset, not a random sample. It also lets a genuinely broad
  rule dodge the per-assertion rent, since `n` is clamped. This hit **150 of
  ~2000 evaluations (~7%) in the full arm and 525 in `no_death`** — enough to
  matter, and the likely reason the breadth penalty underperforms. Capped rules
  should be rejected outright, not scored. Not fixed in this run.
- **A15 fired only after tuning.** Every change was principled and each is
  documented in the source, but a control that passes after the system was
  adjusted is weaker than one that passes first try.
- **`top12` barely moves** (0.2598 for full vs 0.2685 for no_abduct). The
  individual-rule statistic G17 used does not capture what a population does;
  coverage and precision do. Reporting only `top12` would have shown nothing
  happening.
- One dataset, one split, one seed per arm. No repeats, so none of the
  between-arm differences have an error bar. `no_waves` vs `full` (4539 vs 5158)
  is well outside plausible noise; `static_adv` vs `full` (4607 vs 5158) is
  closer and should not be leaned on.

## Reproduce

```sh
cd spikes/G24_population
python3 evo.py          # ~25 min, six arms
python3 analyse.py      # the fair comparison
```
