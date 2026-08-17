# GRAPH_LEARNING — the G-series, consolidated

> **2026-08-17: G15 RETRACTED.** It was written up as *"discovery works on a
> corpus that has redundancy"* and is now RED. Adversarial review reproduced
> every number exactly and showed the **unit** was wrong: `ho_n` counted 2-hop
> paths, not endpoint pairs, so the headline's 489 "trials" are 15 pairs with
> one hit — pair-level confidence 0.067, not 0.501. The body predicates are a
> near-inverse pair (4↔130 at 0.808), the two top rules are the same rule
> (Jaccard 0.680), and both self-compositions are cliques of 12 and 18 entities.
> The pre-registered shuffle null existed only in prose; it was run inline and
> never saved, a B5 violation, and it would not have helped — a
> degree-preserving shuffle destroys exactly the cliques and inverse pairs that
> produced the signal. See `spikes/G15_analogy_realkg/RESULT.md`.
>
> **Consequence for this document:** the claim *"discovery needs redundancy"*
> is withdrawn as a measured result. G14's zero remains real; G15's positive
> does not. The series therefore stands at **no demonstrated discovery, six
> framings.**
>
> **2026-08-17 later: G17 partially restores it, and G18 caps every result in
> this file.**
>
> **G17** rebuilt G15 to the reviewer's specification — pair-level denominators,
> near-inverse bodies rejected (357 rules), `r == p or q` rejected (1331),
> self-loops dropped, no path cap, and the null *in the code*. A signal survives:
> real 0.441 against a degree-preserving null of 0.329 (n=24, sd 0.012, 0/24
> exceed real). That is **1.34×, not G15's 4–7×**, and the p is floor-limited —
> 24 draws was chosen as the smallest n where p<0.05 is reachable, which is
> legitimate only because it is stated. The positive control the reviewer found
> unused in the data (the tautology `81,q=>q` at conf 1.000) fires clean at zero.
>
> **G18 is the one that changes how every row below should be read.** The
> `match` primitive aborts the process at ≥1022 results — not `collapse`, which
> G16 blamed. **Every G-series program folds with a bare `collapse` over the
> whole space, so every result in this document was measured at 60 nodes and
> stops working above 1021.** Worse, conjunction order decides the outcome:
> `(, (bucket b0 $c) (imp 0 $c $v))` returns while
> `(, (imp 0 $c $v) (bucket b0 $c))` — same denotation — aborts. The
> architecture scales; these programs do not, as written. G19 is the rewrite.

Thirteen spikes testing one question: **can a self-modifying knowledge graph, run
on Hyperon across two devices, learn?**

Short answer: **the substrate works and the learning does not.** The graph
composes, replays byte-identically across machines and cycles, and forgets at
the level of a greedy oracle. It does not discover a rule, and five framings say
so.

Graded per `out/LEDGER.md`'s scale. Nothing here is A — an A requires a reviewer
to have specifically attacked the claim and failed, and no adversary has been
pointed at the G-series.

---

## LIVE — the substrate

| claim | grade | evidence |
|---|---|---|
| A MeTTa program can **derive atoms and write them back into its own space mid-run**, then reason over facts that did not exist at program start | **B** | G1: three passes, `add-atom` inside a `match`, pass 2 matches what pass 1 wrote |
| Self-modification is **byte-identical on desktop and phone**, output *and* fuel | **B** | G1: `raw_hash 5cb2e24b…`, `fuel_used 3765`, both machines. Cross-OS/cross-libc, **not cross-ISA** (both aarch64), per S57's correction of S15 |
| Determinism **survives iteration** — 6 loop cycles, per-cycle comparison | **B** | G11. State compounds across cycles, so a single-pass test structurally cannot detect drift. Provenance verified: both binaries built one minute apart, ~7 h before the hyperon patches |
| A deterministic fixed-point **ECAN runs in MeTTa** with A11's three clauses realised by the language | **B** | G5. Products before division, one floor division per quantity, `collapse` gives BSP double-buffering by construction |
| **Conservation holds** — 59,907 of 60,000, loss is floor division only | **B** | G5, control emitted into the program |

## LIVE — attention

| claim | grade | evidence |
|---|---|---|
| Attention-driven forgetting preserves **64% of findings at 43% of the graph**, against a 16% floor | **B** | G10, 5 query classes, 10 cycles |
| …and **matches a greedy oracle** shown the answers, 0–6% headroom | **B** | G10. Oracle is greedy per node, so an approximate upper bound, not an optimum |
| The loop **converges** — no collapse, no oscillation, monotone, decelerating | **B** | G10: last three cycles 69 → 66 → 64% |
| **Per-context** fields work: each preserves its own query and discards the other's | **B** | G8, diagonal 93%/100% against 0%/42% off-diagonal |
| Preservation tracks **what fits**, not policy quality | **B** | G10: at 26 live nodes, `q_invalid` 100% (7 nodes touched), `q_green` 23% (55 touched) — an arithmetic floor, not a failure |
| The result **survives the data's own 5% error rate** | **B** | G13: perturbed at measured rates, gap +44% mean, +39% worst, never negative |

## DEAD — refuted, with the refuting spike

| claim | killed by |
|---|---|
| a rule can be **learned** from the corpus (spike-level, n=50) | G2: LOO 0.760 vs 0.740 baseline, permutation **p = 0.129** |
| …the failure was **weak features** | G4: better features, worse result |
| …the failure was **missing negatives** | G4: 26 real negatives found, **p = 0.452** |
| "failure is recorded as prose; 0 negatives exist" | G4: 26 struck-through rows exist inside LIVE sections, my parser required `**A\|B\|C\|D\|E\|INVALID**` and skipped them all |
| **in-degree** is a usable stimulus | G6: INVERTED — keeps foundational GREEN spikes, drops the recently-refuted INVALID ones an audit needs |
| a **global** importance field can serve several queries | G7: conservation makes attention zero-sum across tasks; training on A actively harms B |
| contexts can be **discovered** by touch-set clustering | G9: rank 4/25 over all partitions, exact **p = 0.160** |
| **iteration** is load-bearing | G12: every prune rate gives 64% at the same final size; one shot equals 23 cycles, and the ranking is IDENTICAL after epoch 1 |

## The three results worth carrying out of the series

**1. A deterministic wrong answer is still wrong.** G5's first ECAN had an
un-epoch-indexed atom that multiplied the join 6×. It was perfectly
deterministic while broken — same fuel, same hash, every run, both machines.
**Conservation caught it; the hash could not.**

> Replication catches disagreement. It cannot catch a shared bug. Byte-identical
> agreement verifies that the same computation ran, never that it was the right
> one. Correctness needs invariants shipped **inside** the job, because the
> verifier only ever sees hashes.

That is a constraint on the whole verification design and it is not in
`PORT_PLAN` or the LEDGER.

**2. Conservation makes attention zero-sum, and DAS already knew.** G7 built one
global field and reproduced from first principles the failure that
`AttentionBrokerServer.cc:369-375` exists to prevent — a map of Hebbian networks
keyed by context. First time this workspace has confirmed an elder's design by
independently failing without it.

**3. Allocate contexts, do not discover them.** G9: preservation is monotone in
the *number* of contexts and nearly indifferent to membership — 1 → 48%,
3 → 72.8% median over **all** partitions, 5 → 86%. You need enough separate
budgets, not the right ones. Far cheaper to build than discovery, and consistent
with DAS letting the caller pass any string.

## NEVER MEASURED

| gap | note |
|---|---|
| **Label validity** | G13 audited the *parse* (5% verdict, 4.8% citation error, survivable). It says nothing about whether the labels are right. G4 found they partly encode *whether a claim was attacked*, not whether it was wrong — unmeasured and larger than 5% |
| **On-device orchestration** | G11 verified the ECAN *epoch* cross-device. Query and prune ran host-side. Closing it needs M1.1/M1.3 |
| **Iteration with moving stimulus** | G12 proved iteration is inert with a *fixed* query set. It would become load-bearing under a shifting query mix, arriving atoms, or importance feeding back into what gets queried. None tested |
| **Scale** | 60 nodes, 460 atoms, 5 query classes, one graph. Every result — and G18 shows this was not merely a budget choice: the programs **cannot** exceed 1021 nodes as written |
| **Capability** | Nothing measures whether the graph *reasons* well. The whole series measures retention and determinism |

## Standing rules this series produced

1. **A two-sided control is not optional.** Three conclusions changed because of
   a `keep_low`-style arm that a treatment-vs-null design would have missed
   (N1c, G6, G7).
2. **A lenient threshold fires on noise.** G2 said `REAL SIGNAL` on 5 shuffles;
   G9 said `DISCOVERY WORKS` on a two-point gap. Both died to an exhaustive or
   permutation control. Report the exact test, not the quotient.
3. **A uniform shape across every row is the instrument, not the data.** G13's
   audit reported 22.5% error with every row listing its own id; G9's first
   metric was 100% at every B. The tell is never a wrong number.
4. **Report gaps against a floor, not absolutes.** G13 measured why: error that
   hits both arms equally cannot flip a comparison. Absolute preservation moved
   5 points under perturbation; the gap moved 3.

## Where it leaves the thesis

The architecture in `analysis/THE_BRAIN.md` claims a self-evolving graph. What
is demonstrated is a **self-modifying, replayable, near-optimally forgetting**
graph. "Evolving" requires learning, and thirteen spikes across five framings
did not produce it at this scale.

That is not a refutation of the idea. It is the measured floor: **a graph plus
attention plus determinism buys you auditable retention, and nothing yet buys
you discovery.**
