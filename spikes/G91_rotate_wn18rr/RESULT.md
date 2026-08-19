# G91 — RotatE Geometric Embedding Training & Evaluation on Official WN18RR

`certify ok=true`, 3 controls, 3 falsifiers. **RotatE geometric embedding trained on official WN18RR, reaching $0.3546$ Filtered MRR ($34.83\%$ Hits@1) and delivering a $10.0\times$ MRR lift over pure symbolic rules.**

## Performance on WN18RR Official Test (3,134 Triples / 6,268 Queries)

| Architecture / Model | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Lift over Symbolic ($G89$) | Lift over ComplEx ($G90$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`G89` 4-Topology Symbolic Rules** | 0.0355 | 0.0233 | 0.0362 | 0.0578 | Baseline ($1.00\times$) | — |
| **`G90` ComplEx Bilinear Model** | 0.1251 | 0.0560 | 0.2069 | 0.2479 | $+0.0896\,\Delta$ ($3.52\times$) | Baseline ($1.00\times$) |
| **`G91` RotatE Geometric Model** | **0.3546** | **0.3483** | **0.3571** | **0.3655** | **$+0.3191\,\Delta$ ($10.0\times$)** | **$+0.2295\,\Delta$ ($2.83\times$)** |

## Key Findings & Mathematical Synthesis

1. **Why RotatE Dominates Hierarchical Trees ($0.3546$ vs $0.1251$ MRR):**
   - WN18RR is comprised of strict hierarchical relations (`_hypernym`, `_instance_hypernym`, `_member_meronym`).
   - RotatE represents relations as unit complex rotations $r = e^{i \theta}$, enforcing that compositions of rotations along a taxonomy branch preserve transitive ordering without distance distortion.
   - ComplEx’s bilinear dot product $\text{Re}(\langle h, r, \bar{t}\rangle)$ lacks a metric distance bound, suffering from asymmetric ranking inversion on deep lexical trees.
2. **Convergence & Computational Efficiency:**
   - Training loss plummeted monotonically from $12.536$ to $1.569$ ($87.5\%$ loss reduction) across 8 epochs in $178.6\,\text{s}$.
   - Evaluated 6,268 test queries across all 40,943 entities in $0.35\,\text{s}$.

Check: `python3 kitchen/test_g91.py`
