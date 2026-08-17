# G24 — the rule population evolves; every mechanism it removes costs it

> **CORRECTED 2026-08-17, twice, and both corrections came from other lanes.**
>
> **1. Two arm comparisons below are withdrawn as noise.** AGENT-2-LANE ran the
> `full` config under three seeds (777 / 1234 / 31337) and got **4719 / 4144 /
> 3381** — a **1338-triple band**. Every arm number in this file is a single
> seed, so any between-arm coverage difference under ~1300 is not distinguishable
> from seed variance.
>
> ```
> WITHDRAWN  "no_waves DOMINATED by full"    3651 vs 4144 = 493 apart. Noise.
> FRAGILE    "static_adv DOMINATED by full"  2745 vs 4144 = 1399. Marginal.
> SURVIVES   no_abduct                       1359 vs 4144 = 2785. Real.
> SURVIVES   no_death precision              0.0066 vs 0.0355 = 5.4x. Real.
> ```
>
> So "every mechanism it removes costs it" — the title — is only supported for
> **abduction** and **death**. The waves and adversary claims were single-seed
> differences inside the noise floor, and I reported them as dominance.
>
> **2. The premise of my own fair-comparison argument is measured FALSE.**
> `analyse.py` says "`test solved` rises with population size near-mechanically",
> and I used that to dismiss `no_death`'s coverage as a population artefact.
> AGENT-2-LANE ran the missing 2x2 cell: **`no_death+no_abduct` gets 1514 correct
> at pop 531**, against `no_death`'s 6361 at pop 557. At matched population with
> selection absent from both, **abduction is worth 4847 correct triples and
> population volume is worth ~155.**
>
> The precision half of my argument stands — `no_death` buys its coverage at 5.4x
> worse precision, and the (predictions, correct) plane is still the right
> comparison. But the *reason* I gave was wrong: `no_death`'s coverage came from
> abduction, not from having more rules.
>
> **3. Reproductive selection was missing, is now present, and does not pay.**
> AGENT-2-LANE found `imp` had one consumer (the death filter) and parents were
> drawn uniformly, so `no_death` had no selection at all. Correct, and the fix is
> a mechanism not a parameter: `pick_parent()` weights parent choice by
> importance. The 8-arm run separates survival from reproductive selection:
>
> ```
> arm                        correct   prec     pop
> full (repro ON)               3569   0.0250   156
> uniform_parents (repro OFF)   4144   0.0355   110
> no_death (repro ON)           6752   0.0070   542
> no_death+uniform_parents      6361   0.0066   557
> ```
>
> **Isolation check:** `uniform_parents` reproduces the old `full` exactly
> (4144 / 0.0355 / 110) and `no_death+uniform_parents` reproduces the old
> `no_death` exactly (6361 / 0.0066 / 557). Turning the change off returns the
> previous code's numbers to the unit, so `pick_parent` altered only what it
> claims.
>
> **Verdict on the fix: worth approximately nothing measurable.** +391 with death
> off and −575 with death on, both inside the 1338 band, and precision is *worse*
> with it on (0.0250 vs 0.0355). It makes the ablation mean what its name says —
> which is why it stays — but the architectural argument for it did not translate
> into a better system. I argued it from principle and the measurement declined.

**Verdict: the full system triples held-out coverage at constant precision, and
no ablation gets more correct answers without asserting more.** G22 failed
because it satisfied none of Lewontin's three conditions for evolution. Built
explicitly — variation, heredity, differential fitness — they work.

Full arm, 15 rounds, on a test set no operator ever reads:

```
r0    pop  94    correct 1302    predictions  36543    precision 0.0356
r14   pop 110    correct 4144    predictions 116752    precision 0.0355
```

**+218% coverage at flat precision**, population roughly unchanged. The
population is answering three times as many held-out questions without getting
worse at the ones it answers.

## Arms

```
arm              pop     preds  correct     prec  cov/rule   A15
full             110    116752     4144   0.0355      37.7   yes
no_variation      32      5112     1127   0.2205      35.2   NO
no_abduct        134     40414     1359   0.0336      10.1   NO
no_death         557    969298     6361   0.0066      11.4   yes
static_adv       109    172330     2745   0.0159      25.2   yes
no_waves         107    224369     3651   0.0163      34.1   yes
```

On the (predictions, correct) plane, where an arm wins only by getting more
correct at **no more** predictions:

```
no_death     trade: +2217 correct for +852546 predictions
static_adv   DOMINATED by full
no_waves     DOMINATED by full
```

- **no_abduct** — never finds A15; coverage moves **+57** against full's +2842.
  **Problem-directed proposal is the load-bearing operator.** Without it the six
  blind mutation operators drift.
- **no_variation** — never finds A15, and coverage *declines* (1300 → 1127) as
  rules die unreplaced. This is G22's shape, and it degrades.
- **no_death** — population explodes 94 → 557; precision collapses to 0.0066,
  **5.4× worse than full**. Removing carrying capacity converts accuracy into
  volume. **CORRECTED by G25 — see the changelog at the bottom of this file. The
  last sentence is wrong: it is not volume, and this arm contains no selection.**
- **static_adv** and **no_waves** — both strictly dominated. A co-evolving
  adversary and activation-directed wages each pay for themselves.

## The v1 → v2 correction, which changed a headline of mine

**v1 scored rules whose body walk had been truncated at `MAX_PAIRS`.** That is
invalid twice over: the confidence came from an arbitrary iteration-order subset
rather than a random sample, and clamping `n` let a genuinely broad rule dodge
the per-assertion rent. It hit 150 of ~2000 evaluations in v1's full arm.

v2 **excludes** over-broad rules instead of truncating them — a stated exclusion
criterion, not a silent cap (`rejected_capped`: full 273, no_death 548).

```
                 v1        v2
precision     0.0163    0.0355     more than doubled
coverage        5158      4144     -20%
```

**And it overturned a claim I published in v1's RESULT.md.** v1 reported
"+296% coverage AND +47% precision". That precision gain was measured from an
invalid baseline. The valid measurement is **precision flat, coverage +218%** —
still a real result, and a weaker one than I wrote.

v2 also sharpened one arm: `static_adv` was "cheaper but no better" in v1 and is
**strictly dominated** in v2. The invalid scoring had been masking the value of
the co-evolving adversary.

## The verdict logic was wrong in v1 and is fixed

v1's `evo.py` ranked arms on raw coverage and printed:

> AN ABLATION BEATS THE FULL SYSTEM — no_death gained +6476 test triples vs
> full +3856

**That compares a 548-rule population against a 94-rule one.** More rules assert
more things, so more things are correct, near-mechanically. It is G15's
retracted headline in new clothes — a maximum over 1954 items compared against a
maximum over 1750 — written into code I authored *after* retracting G15, in the
same week, with that error listed in my own correction notes.

`evo.py` now ranks on dominance; `analyse.py` reports the plane. Knowing an
error by name did not stop me writing it.

## What each evolutionary part became in code

| part | mechanism |
|---|---|
| genotype | `{"body": (p,q[,s]), "head": r}` — the rule evolves, not the graph |
| variation | `mutate()`: swap / extend / contract / rehead / recombine / duplicate |
| mutational bias | `build_bias()` → `follows` + `precedes`, both directions |
| heredity | population persists; offspring carry a parent's body with one edit |
| fitness | `conf − adversary_conf`, novelty-weighted (frequency-dependent) |
| **death** | fixed `WAGE_POOL` shared out; rent per body predicate **and** per 1000 assertions; `imp <= 0` removes |
| problem space | `dev_all − solved_now` |
| **abduction** | `abduct()`: unsolved problem → path → proposed rule |
| waves | activation from unsolved problems multiplies wages; recomputed each round |
| adversary | best-of-m reshuffle chosen to **maximise** population score |

**ECAN was in the wrong place for the whole G-series.** G5/G19 used rent as
memory management, to stop the atomspace growing. It is the *carrying capacity*:
with unlimited room fitness differences do nothing, which `no_death` shows
directly.

## Three failures on the way, each a real property

1. **A15 was inside the seed population** — reported found at round 0, before a
   single mutation. A control that starts inside what it tests is not one.
2. **The fitness landscape is flat.** A rule clears `MIN_PAIRS` or scores
   nothing — no partial credit, no slope, so uniform mutation over 237
   predicates has nothing to climb. Fixed with bidirectional structure-biased
   proposals.
3. **Fitness charged nothing for breadth.** Rules evolved to assert everything.
   Fixed with rent per 1000 assertions — and only made effective in v2, once
   truncation stopped hiding true breadth.

## What this does NOT show

- **The un-evolved seed is still 6.2× more precise.** `no_variation` sits at
  0.2205 on 5,112 predictions; full is 0.0355 on 116,752. Evolution buys 3.7×
  more correct answers by making 23× more predictions. For knowledge-graph
  completion that exchange rate is probably not worth it. **The population has
  found recall, not truth.** 3.5% precision is not a working brain.
- **A15 fired only after tuning.** Every change was principled and documented in
  source, but a control that passes after the system was adjusted is weaker than
  one passing first try.
- **`top12` barely separates the arms** (0.2458–0.2972). G17's individual-rule
  statistic does not capture population behaviour; coverage and precision do.
- **One seed per arm, no repeats**, so between-arm differences have no error
  bar. `no_abduct` (+57 vs +2842) and `no_death` (5.4× precision) are far
  outside plausible noise. `static_adv` vs `no_waves` should not be leaned on.
- Single dataset, single split, single machine.

## Reproduce

```sh
cd spikes/G24_population
python3 evo.py          # ~25 min, six arms
python3 analyse.py      # the fair comparison
```
`RUN_v1.txt` / `evo_v1.json` retain the invalid-scoring run for comparison.

## Changelog

**2026-08-17 — corrected by `spikes/G25_carrying_capacity/`.** Numbers, arms and
verdict above stand as run; three statements about *why* do not.

1. **The `no_death` arm has no selection in it.** `death` off means nothing is
   removed, `MAX_POP` never applies, and parents are drawn uniformly
   (`rng.choice(pop)`); `imp` is read by exactly one statement, the one death
   uses. So this arm is not "the full system minus carrying capacity", it is
   propose-and-keep-everything, and "finite carrying capacity is what MAKES
   fitness differential" was compared against a baseline with no fitness at all.
   An ablation that removes more than it names cannot measure the named part.
2. **"Removing carrying capacity converts accuracy into volume" is wrong.** The
   2×2 cell this spike never ran — `no_death+no_abduct` — gets **1514** correct
   at population 531, against `no_death`'s 6361 at 557. At matched population
   with selection absent from both sides, **abduction is worth 4847 correct
   triples** and volume is worth ~155. The premise `analyse.py` reasons from,
   "`test solved` rises with population size almost mechanically", is measured
   false at this scale (coverage per rule: full 37.7, no_death 11.4,
   no_death+no_abduct 2.9).
3. **The +5059 is substantially a constant I picked.** Population size is set by
   `WAGE_POOL / RENT`; keeping death and raising `WAGE_POOL` alone closes 51–85%
   of the coverage gap across three run seeds, at 2.6× fewer predictions and 2.5×
   the precision. The published `WAGE_POOL = 120` put the full arm at ~110 rules
   because 120/1.05 ≈ 114, not because 110 was right.

Also from G25, bearing on the "one seed per arm" limitation listed above:
`full_base` re-run under seeds 777 / 1234 / 31337 gives **4719 / 4144 / 3381**
correct. The +2842 headline sits mid-range of a 1338-wide band, and any
between-arm coverage difference smaller than that band — `static_adv` vs
`no_waves` was already flagged, but this now also covers reading anything into
`no_abduct`'s exact +57 — is noise. `evo.py` gained two backward-compatible
changes for that work: `RUN_SEED` hoisted out of `run()`, and `arm` parsed as a
`+`-joined ablation set. G25's C1 control reproduces this file's full arm
line-for-line to show nothing else moved.
