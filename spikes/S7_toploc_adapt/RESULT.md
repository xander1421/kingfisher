# S7 — TOPLOC-style commitment adapted to INT8 hypervector similarity

**Verdict: GREEN** (stretch spike, implemented rather than pseudo-coded). A top-k Newton-polynomial commitment over S5's INT32 similarity scores works, is 34–514 bytes, catches a ±1 tamper every time, and costs ~0.1 % of what the verifier must spend anyway on recomputation. It also surfaced a latent bug in the upstream construction.

Code: `commit.py` (numpy + stdlib). Output: `result.json`. Workload is S5's exact encoding at D=1024, 100k triples, 20 queries.

## The adaptation, in one paragraph
TOPLOC commits to the top-k largest-magnitude bf16 *activations* and verifies with an **exponent-exact / mantissa-tolerant** comparison, because GPU float accumulation order varies across hardware. Our rung-2 output is INT8×INT8 → INT32; integer addition is associative and exact, so a correct device's scores are **bit-identical anywhere**. We therefore keep TOPLOC's compression — a Newton polynomial through `(triple_index, score)` over a prime field, 2 bytes per point — and delete its tolerance model, requiring exact equality.

## Measurements (D=1024, 100k triples, 20 queries)

| k | proof bytes | vs shipping all 100k scores (400 KB) | build ms/query | verify ms/query (excl. recompute) | honest accepted | ±1 tamper rejected |
|---|---|---|---|---|---|---|
| 8 | 34 | **11,765×** | 0.072 | 0.005 | 20/20 | 20/20 |
| 16 | 66 | 6,061× | 0.082 | 0.014 | 20/20 | 20/20 |
| 32 | 130 | 3,077× | 0.319 | 0.048 | 20/20 | 20/20 |
| 64 | 258 | 1,550× | 1.255 | 0.175 | 20/20 | 20/20 |
| 128 | 514 | 778× | 5.042 | 0.688 | 20/20 | 20/20 |

Proof layout: 2 B per coefficient + 2 B per node index + 2 B modulus.

## Verifier cost — the honest accounting
The commitment is free; **re-execution is the whole cost**. One query's matmul against the 100k-triple shard: **85 ms** on this laptop. Verifying the commitment on top of that: 0.005–0.688 ms, i.e. **0.006 %–0.8 %** of the recompute. So:

> Verifying a rung-2 job costs essentially exactly what running it costs. There is no cheap-verification magic here, and there was none in TOPLOC either — its "100× faster validation" comes from replaying an autoregressive decode as one batched prefill, a latency artefact of LLM generation that our workload does not have.

What the commitment *does* buy: the result envelope shrinks from 400 KB to 34 bytes, and the verifier can be a **random auditor rather than a mandatory second executor** — which is the actual economics (see `out/RISKS.md`, verification economics).

## The bug we found in the upstream construction
`toploc/poly.py:find_injective_modulus` walks **every integer** downward from 65497 and returns the first modulus under which the committed indices are distinct:
```python
for i in range(65497, 2**15, -1):
    if len(set([j % i for j in x])) == len(x):
        return i
```
It never checks primality — but `ndd.cpp` inverts denominators with Fermat's little theorem (`pow(denom, m-2, m)`), which requires a **prime** modulus. With a composite modulus the inverse is wrong or undefined and an **honest proof fails to verify**.

We hit it: at k=128, **1 of 20 queries** selected `m = 65496` (composite; the nearest prime the search should have taken is 65479), and that query's honest verification returned `False`. Adding a primality filter to the search made it 20/20 at every k.

TOPLOC is less exposed than we are — its activation indices are small enough that 65497 itself usually works, so the loop rarely descends. Our triple indices run to 100,000, always exceeding the modulus, so the search descends on every single commitment and eventually lands on a composite. **Anyone porting this construction to an index space larger than 2¹⁶ will hit the same thing.** Worth an upstream issue; it is a two-line fix.

## Design consequences for the hyperjob result envelope
1. `lsh_commitment` should be `{k, modulus: u16, nodes: [u16; k], coeffs: [u16; k]}` — 4k + 2 bytes, with k=16 a sensible default (66 B).
2. The modulus must be prime and must be **transmitted**, not assumed, because it is data-dependent.
3. Because our arithmetic is exact, the accept rule is equality, not a threshold — so the envelope needs no tolerance parameters and disputes have no grey zone. Rung 2 is, for this workload, just rung 1 with a smaller payload.
4. **Caveat that must be measured before this is load-bearing**: the exactness claim assumes the phone NPU performs true INT8×INT8→INT32 with no internal saturation, requantisation, or reduced-width accumulation. Some NNAPI/Core ML paths do not. If a real device turns out to be inexact, TOPLOC's tolerance model comes straight back and should be adopted as-is (it is MIT and 1,200 lines). This is a first-order question for the M2 device bring-up.
