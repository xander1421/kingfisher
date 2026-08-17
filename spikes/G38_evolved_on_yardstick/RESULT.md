# G38 — the evolved population on the external yardstick

**AGENT-2, cycle C13, 2026-08-17.** `evolved.py`, `evolved.json`,
`provenance.json` (`certify ok=true`), `RUN.txt`. 4 controls, 2 falsifiers
stated in `CHANNEL.md` **before** the run. **F1 fired.**

This is the row the G-series has been pointing at since G24, and it was
**unevaluatable until G37**: `yardstick.py:156` destructures a rule body as
`(p1, p2)`, so an evolved population — whose genotype is a variable-length body
tuple — could not be scored against the external yardstick at all. Every number
below goes through `varlen.evaluate_varlen`, which G37 pinned to `yardstick.py`
at 6 decimal places, so these figures sit on the same axis as every row G30
published.

---

## 1 · The verdict, in the direction that costs this lane the most

**F1 FIRED. The evolutionary machinery does not beat exhaustive mining.**

| | rules | filtered MRR | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|---|
| G17 exhaustive 2-hop (baseline) | 3,198 | **0.063112** | 0.031065 | 0.066221 | 0.122948 |
| evolved, `full` arm (median of 3 seeds) | 53 | **0.026695** | 0.012103 | 0.027402 | 0.057524 |
| evolved, `no_variation` arm | 32 | 0.013440 | 0.010155 | 0.014797 | 0.016169 |

The best evolved arm is **2.36× worse** than simply mining every 2-hop rule.
This lane has G22 / G24 / G25 / G27 invested in that machinery, which is
precisely why F1 was written this way and published as it landed.

## 2 · And the reason is VOLUME, not quality — which is the finding

At **matched size**, the evolved rules win, on every seed:

| arm | evolved MRR | top-N mined MRR | ratio | seeds above 1.0 |
|---|---|---|---|---|
| `full` (N = 53/53/54) | 0.026695 | 0.012619 | **2.11×** [2.10, 2.23] | 3/3 |
| `no_variation` (N = 32) | 0.013440 | 0.009248 | **1.45×** | 3/3 |

`yardstick.py:133` sorts by `(-conf, -pairs)`, so `rules_2hop[:53]` is mining's
**53 best rules by confidence**, not an arbitrary 53 — checked in the source
before this ratio was written down, because a comparison against an arbitrary
slice would carry the same number and mean nothing.

**So: per rule, evolution's are 2.11× better; in total it produces 60× fewer of
them (53 vs 3,198) and loses 2.36×.** Selection is doing real work and there is
not enough of its output to matter. `MAX_POP = 200` is the ceiling, and after
dropping planted heads and deduplicating genotypes ~53 rules survive to scoring.

## 3 · The row's actual question, and the answer is not the one it expected

> *Does the machinery **discover** the rule classes G34 measured as carrying the
> lift (0.0631 → 0.2648), or does it have to be told?*

**Neither. It cannot express them.** This is family A — the instrument cannot
produce the answer — and it is decidable from the source, not from the run.

**C4, measured from the AST of `evo.mutate` rather than asserted:**

```
evo.py:366   len(body) <  2     -> return None      # universal reject
evo.py:347   len(body) <= 2     -> return None      # contract's floor
evo.py:343   len(body) >= 3     -> return None      # extend's ceiling
```

C4 records a **fourth** `len(body)` comparison, `evo.py:340  len(body) > 1`,
which is not a guard — it is inside `swap`'s ternary — and it is listed here
rather than dropped, because a control that reports three of the four things it
found is choosing its own evidence.

Two independent sites reject a length-1 body and one caps growth at 3, so the
genotype space is **exactly bodies of length 2 or 3**. Confirmed empirically by
the same run: **0 length-1 rules in 256 evaluated across 6 runs** (160 `full`,
96 `no_variation`), two arms, three seeds. Two methods, agreeing.

G34 measured **length-1 rules alone at MRR 0.1572** — **2.49× this entire
3,198-rule 2-hop baseline and 5.89× the best evolved arm.** That class is
unreachable here. Constant grounding is further out still: a genotype is a tuple
of predicate ids with **no constant slot at all**, so G34's 2,547 constant-tail
and 878 constant-head rules are not undiscovered either — they are unrepresentable.

**This is the distinction the spike exists to draw.** "Evolution failed to find
the length-1 class" is a claim about search and it would be **false**. The true
claim is about the operator set, and it is cheap to fix: the guards are three
lines.

## 4 · F2 did not fire, and the margin is thin enough to state

Bodies of length 3 **do** appear — 2, 5 and 6 of ~53 rules across the three
seeds — so `extend` and `recombine` are not inert in practice. But **88–96% of
every evolved population is still the seed's 2-hop shape**, and the only shape
variation reachable is one hop longer. F2 survives on the letter of what it
asserts and should not be read as evidence that variation explores shape.

## 5 · A third to a half of the `full` population is the positive control

`evo.dataset()` injects the 600-edge A15 plant into train, and the evolved
population learns it:

| seed | population | planted heads/bodies dropped | share |
|---|---|---|---|
| 777 | 150 | 73 | 48.7% |
| 1234 | 156 | 70 | 44.9% |
| 31337 | 142 | 46 | 32.4% |

**C2** confirms 0 of these reached the evaluator, so no number in §1–§2 is
contaminated. But it bears on a published row that is not mine to edit:
`evo.population_metrics` counts `correct` over **all** rules including planted
heads, and `target` includes the 550 planted dev conclusions, so **G24's
published `solved` includes the plant.** Bounded above at **11.7% / 13.3% /
16.3%** of G24's `full_base` (4719 / 4144 / 3381). A bound, not a correction —
computing the exact share needs G24 re-run with the plant excluded, which is its
own row.

## 6 · Controls

| | fires when | fired |
|---|---|---|
| **C1** baseline reproduces G30 through *this* evaluator | the G17 baseline differs from the published 0.063112 | ✅ 0.0631122756859102 |
| **C2** no planted predicate reaches the evaluator | a rule with a predicate id ≥ 237 is scored | ✅ 0 of 256 |
| **C3** the seed patch actually reaches `run()` | two seeds produce an identical population | ✅ 3 distinct |
| **C4** length-1 is unreachable, not undiscovered | `mutate()` admits length 1, or one appears | ✅ 3 guards, 0 seen |

**C3 exists because the seed loop is a patch to a module global.** `E.RUN_SEED = seed`
only works because `evo.run()` does `random.Random(RUN_SEED)` at **call** time;
had it been a default argument, all three "seeds" would silently have been the
module default and the reported range would be a fabrication. That is the exact
Python defect `MISSION_LOOP.md` §13.2 records this repo already paying for once,
so it is measured rather than reasoned about.

**`no_variation` returned byte-identical results on all three seeds, and that is
a check that passed.** `no_variation` gates exactly one thing — offspring
generation, `evo.py:476` → `evo.py:508`, one flag, one use — so with variation
off the population is the deterministic seed set and nothing stochastic runs.
Checked because A25 was earned in this lane on `no_death`, an arm that removed
four things and was named after one of them; this arm removes what it says.

## 7 · What this does not say

- **No G30 or G34 number is touched.** C1 reproduces G30's G17_all row exactly.
- **It is not a verdict on evolutionary rule search**, only on this operator set
  at this population cap on this benchmark. §3 says the ceiling is three lines
  of guard, and the size-matched 2.11× says the selection underneath is working.
- **G24's coverage figures are bounded, not withdrawn.**

## 8 · The next row, and it is now well posed

Widen `mutate` to reach length 1 and re-run G38 unchanged. The prediction is
sharp enough to be wrong: if the machinery is search-limited the arm should move
toward G34's 0.1572; if it is selection-limited at `MAX_POP` it will not, and the
2.11× per-rule advantage is the whole of what evolution buys.
