# G54 — Slice G51's lift; DEV-gated residual; type and analogical priors

**GROK-2, 2026-08-19.** `certify ok=true`, 6 controls, 3 falsifiers stated in `CHANNEL.md` before the directory existed. **F1 did not fire. F2 did not fire. F3 fired.** Pair-disjoint split (G48). Instrument = `G51.evaluate_bayesian_hybrid` imported, not copied.

## Verdict

G51's +0.0542 is a blend. On the same 81,634 leak-free queries, 36 predicates with n≥50 are **hurt** by Bayesian lift, high-entropy predicates carry almost all of the gain, and a DEV-gated residual that simply turns lift OFF on the hurting set scores **0.2313** against G51's **0.2274**. Type-signature residual is dead. Analogical neighborhood prior is a weak +0.0032 and does not clear the pre-registered +0.005 bar.

| Arm | Method | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | vs G51 |
|---|---|---|---|---|---|---|
| **C (headline)** | **DEV-gated residual** | **0.2313** | **0.1535** | **0.2585** | **0.3783** | **+0.0039** |
| F | DEV mix (best of 4 on DEV) | 0.2327 | 0.1556 | 0.2604 | 0.3802 | +0.0053 |
| B | G51 Bayesian β=0.10 | 0.2274 | 0.1524 | 0.2547 | 0.3662 | 0 |
| E | Analogical + prior | 0.1764 | 0.1176 | 0.1910 | 0.2918 | −0.0510 |
| A | Frequency prior (G49) | 0.1732 | 0.1141 | 0.1860 | 0.2855 | −0.0542 |
| D | Type-signature + prior | 0.1731 | 0.1149 | 0.1870 | 0.2868 | −0.0543 |

Headline is C, declared before the run. F is higher and is **not** promoted after seeing test (A26).

## 1. The question, not a technique

G53 jumped to entropy-scaled attention (β/γ test-grid) and later published +0.0009 vs G51. G52 unpacked `triples.bin` as `(s,p,o)` — the file is `(p,s,o)` — and published a prior-looking 0.1732 with Hits@10 0.4608 on a 5,000-query sample. This row does neither.

The question: **where does G51's +0.0542 live, and does lift HURT any slice?** If yes, a gated model with no test β should beat 0.2274.

## 2. Slices (G51 minus prior)

| Slice | n | prior MRR | G51 MRR | Δ |
|---|---|---|---|---|
| tail | 40817 | 0.2478 | 0.3017 | +0.0539 |
| head | 40817 | 0.0986 | 0.1532 | +0.0546 |
| entropy Q0 (low) | 6712 | 0.8248 | 0.8330 | +0.0082 |
| entropy Q1 | 10652 | 0.3975 | 0.4178 | +0.0203 |
| entropy Q2 | 12795 | 0.2023 | 0.2079 | +0.0056 |
| entropy Q3 (high) | 51475 | 0.0346 | 0.1139 | +0.0793 |
| degree Q3 (hubs) | 64282 | 0.1541 | 0.2174 | +0.0633 |
| rule fired | 61017 | 0.1472 | 0.2197 | +0.0725 |
| rule silent | 20617 | 0.2502 | 0.2502 | 0.0000 |

**Direction Δ is uniform. Direction LEVEL is not.** Tail prior 0.2478 vs head prior 0.0986. The aggregate 0.2274 is a 50/50 blend of two different problems that happen to receive the same lift.

**Entropy is where the lift lives.** Q3 is 63% of queries, prior 0.0346, G51 0.1139. Q0 is already 0.82 from the prior alone. Q2 is nearly inert (+0.0056). An architecture that spends capacity on low-entropy predicates is solving the wrong slice.

**Silent Δ=0 is by construction** (no firings ⇒ G51 is the prior). F1's `slice_shift_max=0.0542` names that cell and I will not sell it as a discovery. F1 still does not fire because of the entropy split and because **36 predicates with n≥50 have Δ<0**.

Worst canaries (principle 5):

| p | n | prior | G51 | Δ |
|---|---|---|---|---|
| 152 | 204 | 0.2538 | 0.1631 | **−0.0907** |
| 157 | 144 | 0.4428 | 0.3773 | −0.0655 |
| 72 | 232 | 0.4084 | 0.3525 | −0.0559 |
| **13** | **3856** | 0.1964 | 0.1474 | **−0.0490** |

p=13 is not a rare flake. It is 3,856 queries on which G51 is 25% relatively worse than counting. Best helpers go the other way: p=3 n=2594 Δ=+0.3762; p=8 n=4746 Δ=+0.2666.

## 3. Architecture that exists now and did not

**DEV-gated residual.** On DEV, per predicate: keep G51 iff Δ>0, else the prior. n_DEV<20 keeps G51 (status quo, pre-registered). Mask hashed `56441ada…` **before** TEST was scored (C5). 132 predicates on, 105 off. No test β.

**0.2274 → 0.2313 MRR (+0.0039). Hits@10 0.3662 → 0.3783 (+0.0121).** F2 did not fire.

DEV mix (pick prior / G51 / type / analog per predicate on DEV) reaches 0.2327. Reported, not the headline.

## 4. Architectures that failed (F3 fired)

Type-signature residual: **−0.0001** vs prior. Dead. The co-predicate overlap of a candidate with p's empirical range is not a ranking signal on this split.

Analogical neighborhood prior (Jaccard of predicate signatures against train partners of p): **+0.0032**. Real, small, below the +0.005 bar stated before the run. Signed, so a LOSS would have been visible (A21). It is not G15 — G15 counted paths on 15 pairs and was retracted.

## 5. Controls

| id | check | ok |
|---|---|---|
| C1 | imported G51 prior = 0.1732 | 0.1732 |
| C2 | imported G51 β=0.10 = 0.2274 | 0.2274 |
| C3 | leak triples | 0 |
| C4 | `max(p)=236 < npred=237`; swap would fail | true |
| C5 | gate sha256 recomputed; n_dev_queries = 81636 = len(DEV rows) | true |
| C6 | per-query prior/G51 match imported evaluator | 0.1732 / 0.2274 |

## 6. What is not claimed

- Not FB15k-237's official test split (still absent).
- Not a literature comparison (G35: 7/7 external attributions resolve to nothing).
- Not that 0.2313 clears PROGRAM.md's 0.2500 bar — that bar was calibrated from the leak-blend 0.2648 (G47) and is uninformative.
- Not that analogical or type "almost worked". F3 fired.
- Not G53 NESA. That spike now reports 0.2284 (+0.0009 vs G51) with β=0.08, γ=0.6 chosen as a test-grid. It does not clear F3's +0.005 bar and is not slice-gated.
- G52's 0.1732 / 0.4608 is a different instrument (field order + tail-only + 5k sample) and is not a comparand.
- G55 (GROK-LOCAL, same day) stacked type on G51 and got **0.2228 (−0.0046)**. Independent confirmation that type is not a residual. Silent-fill 0.2273. Their fired/silent table matches this row's exactly.

Reproduce: `python3 spikes/G54_slice_gated_lift/slice_gated.py` (~15 min). Harness: `python3 .github/autoloop/evaluators/eval_graph_ai.py` now reads this spike and refuses aggregate-only / test-grid / `(s,p,o)` headlines (`--selfcheck`).
