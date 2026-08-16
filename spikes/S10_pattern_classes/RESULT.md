# S10 — does S5's exact pre-filter generalise past one query shape?

**Verdict: GREEN, with a sharp boundary.** S5's "exactly lossless" result extends
to *every* two-bound pattern and to fully-ground lookups, and survives power-law
data unchanged. It fails exactly where the algebra says it must: one-bound
patterns. The honest rule is not "the pre-filter is exact" but:

> **The pre-filter is exact iff the bound slots outvote the free ones — m ≥ 2 of 3.**

Code: `patterns.py`. Output: `patterns.json`, `patterns.log`. D=1024, 100k triples,
100 queries per class.

## Why this had to be run

S5 tested one shape — two bound slots, one free variable — and its own caveat
section said the rest "will be genuinely approximate" without measuring any of
them. `analysis/GAP_MATRIX.md` row 12 and the whole rung-2 design in
`out/PORT_PLAN.md` M2.3 inherit that untested generalisation.

## The algebra, derived before running

A triple is `T_d = sign(b_d + u_d)`, with `b_d` the sum of the m **bound**
role-filler products and `u_d` the sum of the (3−m) unbound ones. The query is
`Q_d = b_d`. A matching triple scores `sum_d Q_d · sign(Q_d + u_d)`.

| m | `Q_d` range | `u_d` range | outcome |
|---|---|---|---|
| 2 | {−2, 0, +2} | {−1, +1} | \|Q_d\| always beats \|u_d\| → score = **2·nnz(Q)**, exact |
| 3 | {−3,−1,+1,+3} | {0} | score = **sum\|Q_d\|**, exact |
| 1 | {−1, +1} | {−2, 0, +2} | u_d can flip the sign → **data dependent**, approximate |

## Measured — uniform data

| class | m | answers/query | exact rule | recall@thr | false pos | candidate reduction |
|---|---|---|---|---|---|---|
| C1 `(p s ?o)` | 2 | 10.4 | **true** | 1.0 | 0 | 9,578× |
| C2 `(p ?s o)` | 2 | 10.3 | **true** | 1.0 | 0 | 9,671× |
| C3 `(? s o)` | 2 | 1.0 | **true** | 1.0 | 0 | 97,087× |
| C6 `(p s o)` | 3 | 1.0 | **true** | 1.0 | 0 | 99,010× |
| C4 `(p ?s ?o)` | 1 | 10,000 | — | — | — | — |
| C5 `(? s ?o)` | 1 | 98.4 | — | — | — | — |

C1 is S5's case, reproduced. **C2, C3 and C6 are new** — the result does not
depend on *which* slots are bound, only on how many, and the fully-ground lookup
(a different threshold rule, `sum|Q|`) is exact too.

The candidate reductions above are the defensible "speedup" numbers for the
pre-filter: 9,578×–99,010×, with recall provably 1.0 and zero false positives.

## Measured — the one-bound failures, and why they matter less than they look

| class | recall@10 | @100 | @500 | @1000 | @5000 |
|---|---|---|---|---|---|
| C4 `(p ?s ?o)` | 0.001 | 0.010 | 0.050 | 0.100 | 0.500 |
| C5 `(? s ?o)` | 0.103 | 0.969 | **1.000** | 1.000 | 1.000 |

C4 is not a pre-filtering problem at all: with 10 predicates over 100k triples,
`(p ?s ?o)` **has 10,000 answers — 10% of the store**. Recall@k tracks k/10000
exactly because the query asks for a tenth of the database. No pre-filter helps;
the right answer is a full scan, or an index.

C5 is the interesting one. 98.4 answers per query, and top-k reaches recall 1.0
at k=500 — usable, but with **no exactness guarantee and no analytic cutoff**.
A one-bound query with a selective slot works as a heuristic shortlist and must
be treated as one.

## Power-law data — exactness survives, top-k does not

Re-run with Zipf(a=1.0) subjects and objects instead of uniform:

| class | exact rule | recall@thr | false pos | recall@100 (uniform → zipf) |
|---|---|---|---|---|
| C1 | true | 1.0 | 0 | 1.0000 → 0.9995 |
| C2 | true | 1.0 | 0 | 1.0000 → 0.9812 |
| C3 | true | 1.0 | 0 | 1.0000 → 1.0000 |
| C6 | true | 1.0 | 0 | 1.0000 → 1.0000 |
| C5 | — | — | — | 0.9689 → 0.9641 (and @1000 only 0.9904) |

**The exactness is algebraic, so it is invariant to the data distribution** —
confirmed, not assumed. What skew changes is answer-set size (C2 goes from 10.3
to 17.4 answers per query), which degrades *rank*-based cutoffs while leaving the
threshold rule untouched. This is a second, independent argument for the
threshold over top-k, beyond the one S5 gave.

## Repeated variables — not expressible, and the fallback is not a pre-filter

`(p ?x ?x)` (subject and object must be the same entity) has no query-vector
form in this encoding: the constraint is between two free slots, not between a
slot and a constant. The fallback is a one-bound pre-filter on the predicate plus
a CPU equality check.

Measured: reaching full recall requires scanning to a mean/worst depth of
**9.95% of the store**. That is a full predicate slice. Repeated-variable
patterns get no NPU acceleration from this design.

## What this does NOT show
- Nested expressions (`(p s (q ?x))`) are untested; the encoding has no
  compositional term for them and they are a design gap, not just a measurement gap.
- Three-slot triples only. Higher-arity links (DAS links are n-ary) would change
  the m-vs-(n−m) vote count and therefore the boundary — the rule generalises to
  "m > n−m", i.e. a strict majority of slots bound, but that is derived, not measured.
- `patterns.json` has a `match_score.constant` field that aggregates across
  queries with different thresholds; it is meaningless. The per-query check
  (`threshold.every_match_hits_threshold_exactly`) is the one to read.
