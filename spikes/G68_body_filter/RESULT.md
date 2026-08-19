# G68 — body-side spray filters hurt (or are a veto)

G57: spray is huge lift on rare false cands (write 5.40 vs true 2.72).
G61 capped lift at p95 of TRUE lifts (43627) and was inert: true answers
already live in the spray regime. This row filters the **path**, not the
lift size. Pre-registered, train-only. Official split.

Falsifiers stated before the run. **F1 fired. F2 fired. F3 fired.**
`certify ok=true`. C1 20466. C2 leak=0. C3 G51 **0.2585**. C4 gated **0.2679**.
C5 npred 237. Unfiltered firings match G54 200/200.

## Arms (official test)

| arm | MRR | Hits@10 | vs G51 / gated |
|---|---:|---:|---|
| A prior | 0.2334 | 0.3541 | — |
| B G51 unfiltered | 0.2585 | 0.3837 | — |
| C valid-gated (G59) | **0.2679** | 0.4037 | — |
| D G51 + hub filter | 0.2489 | 0.3790 | **−0.0096** |
| E G51 + mincount-2 | 0.2334 | 0.3541 | **−0.0251** (= prior) |
| F G51 + both | 0.2334 | 0.3541 | **−0.0251** (= prior) |
| G gated on D (valid-best of D/E/F) | 0.2656 | 0.4008 | **−0.0023** vs 0.2679 |

**Not a new high.** Scoreboard stays G59 **0.2679**. Literature unavailable.

## Filters (train-only)

**Hub cut = 72.** p95 of undirected unique-neighbour degree of train nodes
that appear as intermediates (in_deg>0 and out_deg>0; n=12,655). p95 of
*all* train node degrees is also 72. 626 hubs. Max deg 5,984.

Test path-firings: 81,249,857 unfiltered. Hub drops **31,131,823** (38.3%),
50,118,034 remain. Queries that still fire: 33,623 → 31,797.

**Mincount=2 is a complete last-hop veto.** Every official-train triple is
unique (max multiplicity 1; 0 triples with count≥2). Last-hop count is 0
or 1, so the filter drops 81,249,857 / 81,249,857 paths and G51 collapses
to the prior. Family A: this instrument cannot grade on a simple KG. Not a
test-grid pivot — the arm was pre-registered as triple multiplicity.

## Last-hop mapping

- Tail: `s -q-> z -r-> c`. Last hop `(z, r, c)` as (subject z, rel r, object c).
- Head: `cand -q-> z -r-> o`, walked via `in_adj` as `G54.collect_firings`
  (`o -r-> z -q-> cand`). Last hop of the walk that produces the candidate
  is `(cand, q, z)`. Hub is still z.

## Gate on G

G59 predicate mask (valid, unfiltered prior vs g51), sha256 `9559856568a9…`,
157 on / 66 off — same hash as G59. Applied to the valid-best of D/E/F,
which is D (valid hub MRR 0.2512 > mincount/both 0.2358). No new gate fitted.

## Why the unread fix failed

Same class as G61. True answers already travel through hub z. Cutting them
removes useful write with the spray. Tail Hits@10 rose (0.4979 → 0.5108)
while tail MRR fell (0.3525 → 0.3462) and head MRR fell more (0.1645 →
0.1517): fewer rare false cands in the top 10, and the true target demoted
when its path went through a hub.

The gate that works remains G54/G59's predicate-level "write nothing."

| F | stated | observed |
|---|---|---|
| F1 | hub-filter G51 ≤ 0.2585 | **fired.** 0.2489 (**−0.0096**) |
| F2 | mincount-2 G51 ≤ 0.2585 | **fired.** 0.2334 (**−0.0251**) |
| F3 | gated+filter ≤ 0.2679 | **fired.** 0.2656 (**−0.0023**) |

Evidence: `body.json`. Check: `python3 kitchen/test_g68.py`.
Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G68_body_filter/body.py`.
