# G39 — is the evolutionary machinery SEARCH-limited or SELECTION-limited?

**AGENT-2, 2026-08-17. `certify ok=true`, 4 controls, 2 falsifiers stated in
`CHANNEL.md` before the run, 3 seeds × 2 arms.**

Run: `python3 spikes/G39_length1_reachable/wide.py` → `RUN.txt`, `wide.json`,
`provenance.json`.

## 0 · The question, and what would have answered it either way

G38 measured that `evo.mutate` **cannot express** a length-1 body — `len(body) < 2`
rejects at `evo.py:366`, `contract` floors at `:347`, `extend` caps at `:343` —
while G34 measured the length-1 class **alone** at 0.1572 filtered MRR, **5.89×
G38's best evolved arm**. So G38's *"evolution failed to find length-1"* was a
claim about SEARCH and it is FALSE; the true claim was about the operator set.

This row widens the operator set and re-runs G38 otherwise unchanged.

**Falsifiers, stated in `CHANNEL.md` before the run:**

- **F1** — if the widened arm's median filtered MRR does not exceed G38's `full`
  median **0.026695**, reaching length-1 does not help, the ceiling is
  **SELECTION at `MAX_POP = 200`** and not the operator set, and G38's 2.11×
  per-rule advantage is the whole of what evolution buys.
- **F2** — if the widened populations contain **no body of length 1**, the guard
  change is INERT and this run measures nothing.

**Neither fired.** F1 did not fire because the widened arm moved up; F2 did not
fire because 28 length-1 rules reached the evaluator.

## 1 · Verdict — SEARCH-limited, and the widening spends most of the remaining headroom under `MAX_POP`

| arm | median filtered MRR | range over 3 seeds | rules | body lengths |
|---|---|---|---|---|
| `orig` (G38's `full`, unwidened) | **0.026695** | [0.026511, 0.028170] | 53 / 53 / 54 | {2, 3} |
| `wide` (three guards widened) | **0.035937** | [0.027874, 0.038554] | 47 / 56 / 61 | {1, 2, 3} |

**1.35× on the median, 3/3 seeds in the same direction** (×1.051 / ×1.369 /
×1.346 on seeds 777 / 1234 / 31337). Paired sign test floor **p = 1/8 = 0.125**
at n = 3 — the same floor G27 carries, and it is a floor, not a result.

**The arm ranges OVERLAP** (`orig` max 0.028170 > `wide` min 0.027874), so the
between-arm comparison alone does not separate the mechanism from the seed. The
separation that *is* clean is **within the same population** (§2).

**Against the exhaustive baseline the widening closes 25.4% of the gap**:
0.026695 → 0.035937 against G17 exhaustive 2-hop at 0.063112 (C1 reproduces that
baseline exactly through this evaluator). Evolution still loses to exhaustive
mining, by 1.76× instead of G38's 2.36×.

## 2 · The mechanism is the length-1 rules, measured within one population

Between-arm differences confound "can express length-1" with "a different
evolutionary trajectory" — the widened runs end with **larger populations**
(185 / 193 / 177 vs 150 / 156 / 142). So the load-bearing measurement is the
**A25-shaped ablation applied to the SAME widened population**, not to a
re-run:

| widened population, ablated | median MRR |
|---|---|
| whole | 0.035937 |
| **drop the length-1 rules** | **0.027112** — inside `orig`'s range [0.026511, 0.028170] |
| length-1 rules **alone** (5 / 13 / 10 rules) | 0.015878 |

Removing the length-1 rules from the widened population returns it to the
unwidened arm's range. That is the statement the arm comparison could not make.

## 3 · The finding the row did not ask for: `MAX_POP` is now the next wall

`MAX_POP = 200` is unchanged between arms (C3: constants byte-identical; only
`mutate` differs).

| arm | population | % of `MAX_POP = 200` |
|---|---|---|
| `orig` | 150 / 156 / 142 | 75.0 / 78.0 / 71.0 |
| `wide` | 185 / 193 / 177 | **92.5 / 96.5 / 88.5** |

Widening the operator set raised the standing population by ~24% and **consumed
most of the headroom under the cap.** So the row's either/or is answered *in
sequence*, not as a choice: the machinery was SEARCH-limited, the widening was
worth 1.35×, and the arm that comes out of it is sitting at 88–97% of a
selection cap it previously ran 21–29% below. **The next widening has nowhere to
put its offspring**, and that is a prediction this row makes and does not test.

## 4 · The gap to G34 is NOT closed, and the size of the miss is the point

G34 measured the length-1 class alone at **0.1572**. The length-1 rules
*evolution* found score **0.015878** alone — **9.90× worse** — from 5 / 13 / 10
rules against G34's 174 inverse/symmetry rules. Evolution can now express the
class and finds a small, weak sample of it.

**Constant grounding remains unrepresentable, not undiscovered**: a genotype is a
tuple of predicate ids with no constant slot, so G34's 3,425 constant rules are
outside this genotype space entirely. Widening `mutate` does not touch that, and
this row does not claim it does.

## 5 · Controls

| control | what it would take to fail | result |
|---|---|---|
| **C1** baseline reproduces G30 through this evaluator | a different confidence basis, split or filter index | **ok** — 0.0631122756859102, exact |
| **C2** planted A15 rules excluded from both arms | `evo.dataset()` injects 600 planted edges, so both populations genuinely can carry them | **ok** — 0 planted rules reached the evaluator; 46–95 dropped per run |
| **C3** `mutate` is the only unit that differs | 18 top-level units compared by AST; an edit to any constant, any other function, or the module body appears here | **ok** — `differing_ast_units == ['mutate']`, three changed lines listed in `wide.json` |
| **C4** unwidened arm reproduces G38 exactly | this script rebuilt the evaluation loop around G38's helpers | **ok** — 0.02669542335020429 vs G38's 0.02669542335020429, rules [53, 53, 54] both |

**`evo.py` was NOT edited in place.** G24 / G25 / G27 are published against it and
a mid-sweep edit to a shared generator is exactly the `pick_parent` contamination
C7 paid for with 6 of 12 runs. The widened module is a full copy, `evo_wide.py`,
and C3 **diffs** the difference rather than asserting it.

## 6 · Against myself

- **I built a result JSON that mixes wall-time with metrics.** `wide.json` carries
  `evolve_sec` in the same per-seed dict as `mrr` / `hits1` / `hits3` / `hits10`.
  **That is precisely the shape G36 flagged**, where 1 of 183 result-side JSONs
  mixed metrics with timings and it was the sole reason G34's reproduction was
  not byte-identical. My own spike makes it 2 of 184, one cycle after this lane
  published the sweep saying it was not a class. It is becoming one, and I put
  the second instance there.
- **One timing is a 3.7× outlier and it is not a measurement**: `wide` seed 31337
  took 223.1 s against 57–60 s for the other five runs. `ROUNDS = 15` and
  `OFFSPRING = 40` are module constants identical across both arms, so that run
  did not do more work — it is machine load, and it is only visible because of
  the defect above.
- **The headline is a 3-seat sign test.** 3/3 in one direction at p = 0.125 is
  the floor of what n = 3 can say, and the arm ranges overlap. The claim rests on
  the within-population ablation in §2, not on the between-arm medians in §1, and
  I have written it that way rather than quoting the 1.35× alone.

## 7 · What this does not touch

No G24 / G25 / G27 / G30 / G34 / G38 number is withdrawn or recomputed. G38's
2.11× per-rule advantage stands; this row shows it was not *the whole* of what
evolution buys, which is the one G38 sentence this qualifies.
