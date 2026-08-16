# REPORT: TOPLOC

## 1. Identity
- URL: https://github.com/PrimeIntellect-ai/toploc
- Commit: `7ab7bcd6a4459ba4400fd41e4636bbeed7438997` (2025-04-10)
- License: **MIT**, © 2024 Prime Intellect. Gate: **PORT allowed with attribution.**
- Paper: arXiv 2501.16007, *"TOPLOC: A Locality Sensitive Hashing Scheme for Trustless Verifiable Inference"*.

## 2. Shape
Tiny and clean: 29 files. Python 11 files / **1,191 LOC**, C++ 3 files / 777 LOC (pybind11 extensions), plus `.pyi` stubs. Build: `pyproject.toml` + `setup.py`.

| path | role |
|---|---|
| `toploc/poly.py` (189) | the whole public API: `build_proofs{,_bytes,_base64}`, `verify_proofs{,_bytes,_base64}`, `batch_activations`, `find_injective_modulus` |
| `toploc/C/csrc/ndd.cpp` | Newton divided-difference interpolation and Horner evaluation, **mod 65497** |
| `toploc/C/csrc/poly.cpp` | `ProofPoly` (coeffs + modulus, serialise to bytes/base64), `VerificationResult` |
| `toploc/C/csrc/utils.cpp` | `get_fp_parts` — split bf16 into exponent and mantissa |
| `bench/`, `tests/` | benchmarks and unit tests |

## 3. Entry points
Library only: `from toploc import build_proofs_bytes, verify_proofs_bytes`.

## 4. The commitment construction (the extraction target)

**Build** (`poly.py:build_proofs`):
1. Flatten a batch of activations (prefill treated as one batch; decode grouped by `decode_batching_size`).
2. `topk_indices = flat.abs().topk(topk).indices` — the *k largest-magnitude* activations. This is the locality-sensitive part: the identity of the top-k coordinates is stable under small numeric perturbation, unstable under a changed model, prompt, or precision.
3. Interpolate a **Newton polynomial through the points (index, value)** over the prime field **mod 65497** (`ndd.cpp:5 constexpr int MOD_N = 65497`), where the y-values are the bf16 bit patterns reinterpreted as `uint16`. `find_injective_modulus` searches downward from 65497 for a modulus that keeps the indices distinct.
4. The proof **is** the coefficient vector: `k` values < 65497, i.e. **2 bytes per point**. The README's 10-byte proofs are k=4.

**Verify** (`poly.py:verify_proofs`):
1. **Re-run the computation** to obtain your own activations.
2. Take *your* top-k indices; evaluate the committed polynomial at those indices (`evaluate_polynomials`, Horner mod 65497) to recover the committer's claimed values.
3. Split both into exponent and mantissa (`get_fp_parts`). Return a `VerificationResult{exp_mismatches, mant_err_mean, mant_err_median}`: **exponents must match exactly; mantissas are allowed to differ**, and the mean/median mantissa error is the accept/reject statistic. If every exponent mismatched, error is set to 2⁶⁴ (hard fail).

**What it requires of the computation:**
- Approximate reproducibility — the *same* top-k coordinates and the *same* exponents on different hardware; only the low mantissa bits may drift.
- A meaningful magnitude ordering (activations have heavy tails; top-k is stable). This is precisely why it does not transfer to computations whose outputs are flat or uniformly distributed.
- The verifier must **re-execute**. The 100× speedup claim comes from re-running an autoregressive decode as a **single batched prefill** — verification is cheaper than generation only because generation is latency-bound, not because the commitment avoids work.
- Storage win is real and separate: 2k bytes instead of the full activation tensor (the "1000×" claim).

## 5. ≤10-line note: adapting TOPLOC to INT8 hypervector similarity

Our rung-2 outputs are **INT8 × INT8 → INT32 dot products**. Integer addition is associative and exact, so *there is no accumulation-order drift to tolerate*: a correct device produces bit-identical scores, on any hardware, always. The mantissa-tolerance machinery — the entire reason TOPLOC exists — is therefore **unnecessary for us**, and rung 2 collapses into rung 1 (plain hash equality). What we should still borrow is the *compression*: an envelope must not carry 100k scores. Commit to the top-k `(triple_index, score)` pairs as a Newton polynomial mod a prime > max score, exactly as `ndd.cpp` does; the proof is 2k bytes and the verifier recomputes and evaluates at its own top-k indices, requiring **exact** equality rather than a mantissa-error threshold. One caveat that could reintroduce TOPLOC proper: if a phone NPU quantises or saturates internally (some INT8 paths accumulate in INT16, or clamp), outputs stop being exact and the tolerance machinery becomes necessary again — so the S2/M2 device bring-up must *measure* bit-exactness before we commit to the strict rule. Full treatment in `spikes/S7_toploc_adapt/RESULT.md`.

## 6. Verdict for the mission
MIT, 1,200 lines, one idea, cleanly implemented — the easiest PORT in the elder set if we need it. But our workload is a strictly easier verification problem than theirs, and the honest finding is that we probably need only its *serialisation trick*, not its *tolerance model*. That is worth stating loudly in the proposal: our chosen workload makes a whole rung of verification nearly free.
