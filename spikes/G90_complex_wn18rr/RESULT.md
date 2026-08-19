# G90 — ComplEx Latent Embedding Training & Evaluation on Official WN18RR

`certify ok=true`, 3 controls, 3 falsifiers. **ComplEx continuous latent embedding trained on official WN18RR, achieving a $3.52\times$ MRR lift over pure symbolic rule induction.**

## Performance on WN18RR Official Test (3,134 Triples / 6,268 Queries)

| Architecture / Model | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Lift over Symbolic ($G89$) |
|---|:---:|:---:|:---:|:---:|:---:|
| **`G89` 4-Topology Pure Symbolic Rules** | 0.0355 | 0.0233 | 0.0362 | 0.0578 | Baseline ($1.00\times$) |
| **`G90` ComplEx Latent Embedding (dim=64)** | **0.1251** | **0.0560** | **0.2069** | **0.2479** | **$+0.0896\,\Delta$ ($3.52\times$)** |

## Key Findings

1. **Continuous Embedding Lift on Sparse Taxonomies:**
   - On WN18RR (where 1-hop inverse shortcuts were pruned by Dettmers et al. 2018), 2-hop symbolic paths only cover a tiny fraction of test queries ($0.0355$ MRR).
   - ComplEx projects the 40,943 lexical entities into $\mathbb{C}^{64}$, capturing asymmetric hierarchical semantics and lifting test MRR to **$0.1251$** ($24.79\%$ Hits@10).
2. **Speed & Efficiency:**
   - Trained across 8 epochs (86,835 triples per epoch) in $132.4\,\text{s}$ using pure vectorized NumPy AdaGrad.
   - All 6,268 test queries evaluated with full all-entity (40,943) filtered ranking in $0.22\,\text{s}$.

Check: `python3 kitchen/test_g90.py`
