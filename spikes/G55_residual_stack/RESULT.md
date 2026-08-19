# G55 — residuals stack; they do not replace

Question first: G51's +0.0542 is a residual on the frequency prior (G49/G50).
G54's type/analog arms *replace* G51. If the algebra is residual, type should
fill silent queries and stack on lift. Those two architectures did not exist.

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | silent-slice Δ(G51−prior) ≥ 0.02 → no hole | **did not fire.** silent Δ = **0.0000** |
| F2 | silent-fill ≤ G51 | **fired.** fill 0.2273 vs 0.2274 (−0.0001) |
| F3 | stack ≤ G51 | **fired.** stack **0.2228** vs 0.2274 (**−0.0046**) |

`certify ok=true`. C1 prior 0.1732. C2 G51 0.2274. C3 leak=0. C4 `(p,s,o)` max_p=236 < 237.

## Arms (81,634 queries, G48 pair-disjoint)

| arm | what | MRR | vs G51 |
|---|---|---:|---:|
| A prior | G49 frequency | 0.1732 | — |
| B G51 | published lift, β=0.10 | **0.2274** | 0 |
| C type-replace | prior + type, no lift | 0.1731 | — |
| D silent-fill | G51 if 2-hop fires, else type | 0.2273 | −0.0001 |
| E stack | G51 **plus** type | 0.2228 | **−0.0046** |

No test-grid β. DEV unused.

## The slice (this is the finding)

| slice | n | prior MRR | G51 MRR | Δ |
|---|---:|---:|---:|---:|
| 2-hop **fired** | 61,017 (74.7%) | 0.1472 | 0.2197 | **+0.0725** |
| 2-hop **silent** | 20,617 (25.3%) | **0.2502** | 0.2502 | **0** |

G51's aggregate +0.0542 is not a uniform lift. It is **+0.0725 on the
three-quarters of queries where a 2-hop fires, and exactly zero on the
rest.** Silent queries are the *easy* prior regime (0.2502), not a hard
hole. Type there is 0.2498 — the prior wearing extra clothes.

So:

1. **Type is not a new signal.** Replace = prior (−0.0001). Silent-fill
   collapses to G51 because on silent queries G51 *is* the prior.
2. **Stacking type on G51 hurts.** −0.0046 overall, −0.0060 on the fired
   slice (0.2137 vs 0.2197). Co-predicate overlap tracks frequency; it
   double-counts hubs the prior already ranked.
3. **Residuals do not automatically multiply.** G50's additive inertness
   and this stack loss are the same lesson: extra terms that correlate
   with P(c|p) are not lift.

## What we did not do

- Not G53. That spike is technique-first (softmax attention + test-grid
  β=0.08, γ=0.6). Its json gain vs G51 is **+0.0009**. Our F3 bar was
  +0.005; +0.0009 would not have cleared it. The note claimed 0.2284
  before `results_payload` existed in the first draft.
- Not G54 analog (GROK-2 is running that). Analog is the remaining
  candidate that is *not* a rewrite of the prior.
- Not a kernel change. G51 may rank. It may not enter F001.

Evidence: `stack.json`. Check: `python3 kitchen/test_g55.py`.
