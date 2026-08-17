# G37 — filtered-MRR evaluation for rule bodies of any length

**Verdict: DONE, `certify ok=true`, 3 controls, F1 stated first and it did NOT
fire. The generalised walk reproduces `yardstick.py` to 6 decimal places on all
four metrics, so results ARE comparable across it. Planted length-1 and length-3
rules score MRR 1.0000 under it; the 2-hop instrument does not mis-score them —
it RAISES.**

Run: `python3 spikes/G37_varlen_bodies/varlen.py` → `RUN.txt`, `varlen.json`.

---

## 1 · The blocker this removes

This lane evolved rule populations across G22/G24/G25/G27 and scored them with
`top12` mean held-out confidence — the heuristic G30 retired and whose evidence
G33 corrected. The obvious repair is to score those populations on G30's
filtered-MRR yardstick instead. **It could not be done**, and the reason is
structural rather than a matter of effort:

| | |
|---|---|
| `evo.py:26` | GENOTYPE is *"(body predicate tuple, head predicate)"*, and `OPS` includes `extend` and `contract` — **bodies are variable length** |
| `yardstick.py:143` | `rules_by_head[r["head"]].append((r["body"], r["conf"]))` |
| `yardstick.py:156` | `for (p1, p2), conf in rules_by_head.get(p, ()):` — **a body is destructured as exactly two predicates**, then walked by two hard-coded nested loops |

So **every number G30 published is about 2-hop rules by construction.** That is
also the honest reading of G30's "gap to AnyBURL", since AnyBURL mines lengths
1, 2 and 3 — the gap was partly a statement about what the instrument could
represent, not only about what the miner could find. Neither spike is wrong.
They could not be connected, and this is the connector.

## 2 · F1 — instrument identity, which is the whole risk

A generalisation that changes the numbers is a **different instrument**, and
every cross-spike comparison made across it would be silently wrong. So F1 was
stated in `CHANNEL.md` before the run as an exact match, not an approximate one:

| metric | G30 published | `yardstick.py` re-run | G37 general walk | match |
|---|---|---|---|---|
| MRR | 0.0631 | 0.063112 | **0.063112** | OK |
| Hits@1 | 0.0311 | 0.031065 | **0.031065** | OK |
| Hits@3 | 0.0662 | 0.066221 | **0.066221** | OK |
| Hits@10 | 0.1229 | 0.122948 | **0.122948** | OK |

**F1 did not fire.** Identical on all four metrics to 6 dp, on the same 3,198
mined 2-hop rules over all 40,818 test triples.

This mattered more than a formality: the two ways to get this wrong both
*inflate* the result while looking like a successful generalisation — dropping
the distinct-node guard, or scoring an endpoint reached by two distinct paths
twice. The guards are transcribed rather than reinvented (`yardstick.py`'s
per-hop `b_node != s` / `c_node != s and c_node != b_node`, which `evo.py:160`
states as *"no step returns"*), and ranking, filtering and tie-breaking are
copied unchanged so that **only the walk differs**. C1 is what demonstrates that
claim instead of asserting it.

## 3 · C2 / C3 — the generalisation is load-bearing, and the old instrument REFUSES

A planted synthetic relation entailed by a chain of exactly *n* predicates:

| planted rule | G37 general walk | `yardstick.py` 2-hop walk |
|---|---|---|
| length-1 | **MRR 1.0000** | `ValueError: not enough values to unpack (expected 2, got 1)` |
| length-3 | **MRR 1.0000** | `ValueError: too many values to unpack (expected 2, got 3)` |

**Sharper than expected, and it is good news:** the 2-hop evaluator does not
score a non-2-hop rule badly — it **raises**. Handing an evolved population to
G30's instrument would have thrown, not silently produced a low number that
someone reported as "evolution does not help". That is family B avoided by
accident of implementation: the instrument refuses rather than reporting
fiction. Worth recording precisely because the failure mode this repo keeps
paying for is the other one.

Both controls state the input that would make them fail, and both are two-sided
— each requires the general walk to succeed **and** the 2-hop walk not to. A
control that only showed the general walk succeeding could not distinguish
generalisation from a scoring change.

## 4 · Scope — what this spike deliberately does NOT do

§2: *PARTIAL is not a verdict — split the item and finish the piece you can.*

**Delivered:** the evaluator, pinned to the existing instrument, with controls.

**Not delivered, and it is a separate row:** evaluating an actual evolved
population. `G24_population/evo.json` and `G27_budget/budget.json` persist
summary stats (`arms`, `verdict`, `rows`) and **not the populations**, so this
needs the evolution re-run to regenerate them. That is the next row, and it is
now unblocked — which it was not before this spike.

## 5 · What this sets up

G34 measured that length-1 and constant-grounded rules carry most of the lift
over pure 2-hop composition (0.0631 → 0.2648, reproduced independently in G36).
`evo.py` can **already** produce length-1 bodies via `contract` and longer ones
via `extend`. So the open question this makes askable for the first time is
whether the evolutionary/ECAN machinery discovers those classes on its own, and
what it costs relative to mining them directly — the difference between a search
that finds what is worth computing and one that has to be told.
