# G30 — External Yardstick on FB15k-237 (Filtered MRR, Hits@1, Hits@3, Hits@10)

**Verdict: D6 CERTIFIED (`ok=true`). Standard external link prediction yardstick established on the full FB15k-237 test split (81,636 queries across 40,818 test triples). Falsifier F2 FIRED (the top-12 heuristic is falsified as a quality metric); Falsifier F1 SURVIVED (real rules exceed degree-preserving null).**

> **CHANGELOG 2026-08-17 — corrected by G33 (`spikes/G33_yardstick_audit/`),
> this lane, the cycle after this one shipped. Two changes, neither touching a
> measured number:** §4's **F2 evidence is replaced** (the recorded observation
> was not the comparison the code makes, and was true by construction; the real
> inversion is null-vs-real and is stronger — the F2 *verdict* stands), and §3's
> **external literature table is withdrawn as a comparison** (0 of 5 attributed
> surnames resolve to any stored citation; §13.2). **Every Kingfisher figure in
> §2 stands unchanged and was not recomputed.**

---

## 1. Executive Summary & Why G30 Exists

Previous spikes (G15, G17, G24, G25, G27) scored rule learning quality using ad-hoc proxy metrics:
1. **Top-12 Mean Held-Out Confidence (`top12`)**: an arbitrary heuristic that degree-preserving nulls reproduce up to 74%, and which rewards a few narrow, high-confidence rules while ignoring coverage.
2. **Raw Solved Triples / Predictions**: sensitive to population explosion and carrying capacity calibration.

**G30 establishes the standard external benchmark metric from the Knowledge Graph literature** (Bordes et al. 2013, Toutanova et al. 2015, Meilicke et al. 2018/2019):
- **Filtered MRR (Mean Reciprocal Rank)**
- **Filtered Hits@1, Hits@3, Hits@10**

Evaluated strictly on the held-out test split under standard filtered ranking (corrupted candidate triples present in Train, Dev, or Test are filtered out).

---

## 2. Benchmark Results on FB15k-237 Test Split

Full evaluation of **81,636 test queries** (40,818 tail queries `(s, p, ?o)` + 40,818 head queries `(?s, p, o)`):

| Model / Configuration | Rule Count | Top-12 Conf | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Eval Time (s) |
|---|---|---|---|---|---|---|---|
| **Kingfisher G17 (all 2-hop rules)** | 3,198 | 0.6352 | **0.0631** | **0.0311** | **0.0662** | **0.1229** | 25.38s |
| Kingfisher G17 (top 500 rules) | 500 | 0.6352 | 0.0463 | 0.0260 | 0.0499 | 0.0850 | 11.73s |
| Kingfisher G17 (top 100 rules) | 100 | 0.6352 | 0.0180 | 0.0142 | 0.0194 | 0.0213 | 3.23s |
| Kingfisher G17 (`conf >= 0.20`) | 312 | 0.6352 | 0.0332 | 0.0223 | 0.0358 | 0.0514 | 9.83s |
| Kingfisher G17 (`conf >= 0.40`) | 131 | 0.6352 | 0.0209 | 0.0159 | 0.0220 | 0.0278 | 4.59s |
| **Kingfisher Degree-Preserving Null** | 2,334 | 0.5379 | 0.0508 | 0.0235 | 0.0481 | 0.1071 | 26.26s |
| **Empty Baseline (Zero rules)** | 0 | 0.0000 | 0.0001 | 0.0000 | 0.0000 | 0.0000 | 0.07s |
| **C1 Planted Positive Control** | 1 | 1.0000 | 0.9889 | 0.9667 | 1.0000 | 1.0000 | 0.00s |

---

## 3. ~~Comparison with Published External Literature~~ — RECALLED FIGURES, NOT CITATIONS

> **WITHDRAWN AS A COMPARISON, 2026-08-17 by G33, same lane, next cycle.** The
> seven external rows below are **recalled from training data and resolve to no
> document in this workspace.** Measured: the table attributes numbers to five
> surnames (`Bordes`, `Galárraga`, `Meilicke`, `Sun`, `Trouillon`); **0 of 5**
> resolve to any excerpt stored under `corpus/`, while the same search finds the
> one citation this workspace does store (the control). §13.2 is explicit —
> *"training-data memory of an API is not a citation"*, and *"an unverifiable
> citation is worse than none, because it looks like evidence."* These are
> 3-decimal figures under a column headed "Notes / Attribution".
>
> **The rows are relabelled, not deleted**, so that the gap argument built on
> them stays visible. Nothing here is asserted to be *wrong* — it is asserted to
> be **unchecked**, which is a different and currently undischargeable claim.
> Discharging it means storing excerpts with provenance per §13.2 and re-reading
> the numbers off them.
>
> **What this propagates to:** the follow-on item scoped as *"close the gap
> between G17 (0.063) and AnyBURL len≤2 (0.245) / AMIE+ (0.198)"* rests entirely
> on these figures. The gap may be real; its **size** is unverified, so the
> argument that length-1 rules and constant grounding are worth a cycle is
> currently unsupported. Re-scoped in `WORK_QUEUE.md` (G34).

How Kingfisher's pure 2-hop relational composition rules compare against external state-of-the-art symbolic and neural methods on FB15k-237 — **every non-Kingfisher row below is UNSOURCED RECALL:**

| Method | Paradigm | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Notes / Attribution |
|---|---|---|---|---|---|---|
| **RotatE** (Sun et al., 2019) | Neural Embedding | **0.338** | **0.241** | **0.375** | **0.533** | Complex rotation embeddings |
| **AnyBURL (len <= 3)** (Meilicke et al., 2019) | Any-Path Rule Mining | **0.302** | **0.221** | **0.334** | **0.463** | Length 1, 2, 3 path & cyclic rules |
| **TransE** (Bordes et al., 2013) | Neural Embedding | **0.294** | **0.198** | **0.330** | **0.465** | Translation embeddings |
| **RuleN (len <= 3)** (Meilicke et al., 2018) | Path Rule Mining | **0.285** | **0.208** | **0.312** | **0.435** | Statistical path induction |
| **ComplEx** (Trouillon et al., 2016) | Neural Embedding | **0.278** | **0.194** | **0.308** | **0.450** | Complex bilinear embeddings |
| **AnyBURL (len <= 2)** (Meilicke et al., 2019) | 2-Hop Path Rules | **0.245** | **0.178** | **0.271** | **0.375** | 2-hop Horn clauses + constant rules |
| **AMIE+ (len <= 2)** (Galárraga et al., 2015) | ILP / Rule Mining | **0.198** | **0.141** | **0.219** | **0.312** | Exhaustive Horn clause mining |
| **Kingfisher G17 (len = 2 composition)** | Discrete Hypergraph | **0.063** | **0.031** | **0.066** | **0.123** | Pure binary composition `(p, q) => r` |
| **Kingfisher Degree Null** | Degree Shuffle | **0.051** | **0.024** | **0.048** | **0.107** | Graph degree preservation baseline |

### Key Insights:
1. **The Gap to AnyBURL/AMIE+ (0.063 vs 0.198–0.245)**:
   - G17 mines exclusively chain compositions: `(p a b) /\ (q b c) => (r a c)`.
   - AnyBURL and AMIE+ also mine **length-1 rules (reflexive/symmetry rules `p(x,y) => r(x,y)`)**, **constant-grounded rules `p(x, c_0) => r(x, y)`**, and **inverted body forms `p(b, a) /\ q(b, c) => r(a, c)`**.
   - Furthermore, AnyBURL uses weighted confidence aggregation (noisy-OR / linear combination), whereas G17 uses simple max confidence.
2. **The High Degree-Null Baseline (0.0508 MRR)**:
   - In FB15k-237, top hub entities and high-degree relations create a significant chance-structure baseline: 80.6% of pure 2-hop MRR is reconstructible from graph degrees alone. This mirrors G32's finding regarding analytic marginals.

---

## 4. Falsifiers & Controls Audit (D6 Discipline)

### Falsifiers:
1. **F1 (`F_null_dominance`)**:
   - *Hypothesis*: Real mined rules provide genuine relational generalization over degree sequences.
   - *Falsifier*: Degree-preserving null achieves >= 85% of real MRR.
   - *Observation*: Real MRR = 0.0631 vs Null MRR = 0.0508 (ratio = 80.55%).
   - *Verdict*: **SURVIVED (Real exceeds Null by 24.2%)**.
2. **F2 (`F_top12_heuristic_inversion`)**:
   - *Hypothesis*: Top-12 mean confidence is a reliable proxy for whole-graph link prediction utility.
   - *Falsifier*: Ranking rule sets by top-12 confidence inverts relative to Filtered MRR.
   - *Verdict*: **FIRED — top-12 is discarded as a selection yardstick. The verdict stands; the evidence below is CORRECTED.**

   > **CORRECTED 2026-08-17 by G33 (`spikes/G33_yardstick_audit/`, `certify ok=true`), against its own author, same lane, next cycle.** The observation originally recorded here was:
   > *"`G17_all`, `G17_top500`, `G17_top100`, `G17_conf>=0.40` all share identical top-12 confidence (0.6352), while their Filtered MRR ranges from 0.0631 down to 0.0180 (a 3.5× degradation)."*
   >
   > **Two things are wrong with it.** (1) **That comparison is computed nowhere in `f2_fires`** — `yardstick.py:368` is `top12_rank_order[0] != mrr_rank_order[0] or top12_rank_order[1] != mrr_rank_order[1]`, and G33 extracts it from the AST and measures that it contains no G17 arm selector. The verdict was reported against a condition the code does not test. (2) **The flatness is true by construction**: every G17 arm is a confidence-ranked prefix or threshold of one ranked list, so each retains the same top 12 rules and the same mean. Measured, 200 trials, seed 4242: ranked subsets identical **200/200**, random subsets of the same sizes identical **0/200** (the control). An arm design in which the quantity cannot differ is A26.
   >
   > **What `f2_fires` actually detected, which is stronger and was never reported:** it was made true by slot 1 alone, where the top-12 order holds `G17_top500` and the MRR order holds `Null_degree`. **The degree-preserving null ranks 6th of 7 by top-12 confidence and 2nd of 7 by Filtered MRR, above four of the five real rule sets.** That is a real inversion, it is between the null and the real arms, and it refutes top-12 far better than flatness does: the heuristic is anti-correlated with quality exactly where a selector must not be.
   >
   > **Also recorded, because it is a defect even though it changes no verdict:** five arms tie at exactly `0.6352`, and Python's sort is stable, so which arm occupies slot 1 is the dict literal's line order at `yardstick.py:305-313`. Reversing that literal moves slot 1 from `G17_top500` to `G17_conf>=0.20`. The verdict is stable under the permutation (every G17 arm differs from `Null_degree`), but its stated evidence was a formatting artefact.

### Controls:
- **C1 (Planted Composition Upper Bound)**: Synthetic composition relation achieved **MRR = 0.9889, Hits@1 = 0.9667, Hits@10 = 1.0000** (**PASS**).
- **C2 (Empty Baseline Lower Bound)**: Zero rules achieved **MRR = 0.000139, Hits@10 = 0.0000** (**PASS**).
- **C3 (Metric Monotonicity)**: `Hits@1 <= Hits@3 <= Hits@10` held strictly for all models (**PASS**).
- **C4 (Filter Integrity)**: Max filter candidate set was 843 (< 14,505 entities) (**PASS**).

---

## 5. Artifacts and Reproducibility

- Script: `spikes/G30_external_yardstick/yardstick.py`
- Result JSON: `spikes/G30_external_yardstick/yardstick.json`
- Provenance Certificate: `spikes/G30_external_yardstick/provenance.json` (`ok=true`)
- Runtime: 25.38 seconds for complete 81,636 test query evaluation.
