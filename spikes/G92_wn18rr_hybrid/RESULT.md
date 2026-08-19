# G92 — Neuro-Symbolic Hybrid Mix on Official WN18RR

`certify ok=true`, 3 controls, 3 falsifiers. **Validation-routed hybrid mix combining {RotatE, ComplEx, Prior} achieves $0.3611$ Filtered MRR ($38.78\%$ Hits@10) on official WN18RR (6,268 queries), delivering a $+0.0065$ lift over standalone RotatE and $10.17\times$ lift over pure symbolic rules.**

## Performance on WN18RR Official Test (3,134 Triples / 6,268 Queries)

| Architecture / Model | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Lift over Symbolic ($G89$) | Lift over RotatE ($G91$) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`G89` 4-Topology Symbolic Rules** | 0.0355 | 0.0233 | 0.0362 | 0.0578 | Baseline ($1.00\times$) | — |
| **`G90` ComplEx Bilinear Model** | 0.1251 | 0.0560 | 0.2069 | 0.2479 | $+0.0896\,\Delta$ ($3.52\times$) | — |
| **`G91` Standalone RotatE** | 0.3546 | 0.3483 | 0.3571 | 0.3655 | $+0.3191\,\Delta$ ($10.0\times$) | Baseline ($1.00\times$) |
| **`G92` Neuro-Symbolic Hybrid Mix** | **0.3611** | **0.3486** | **0.3682** | **0.3878** | **$+0.3256\,\Delta$ ($10.17\times$)** | **$+0.0065\,\Delta$** |

## Per-Relation Validation Routing Dynamics

1. **RotatE Selected Relations (7/11 relations, 6,050 test queries):**
   - Dominates asymmetric hierarchical trees: `_hypernym` (RotatE valid MRR: $0.9246$ vs ComplEx: $0.0005$), `_instance_hypernym` ($0.8453$ vs $0.3594$), `_member_meronym` ($0.0850$ vs $0.0020$).
2. **ComplEx Selected Relations (4/11 relations, 218 test queries):**
   - Dominates symmetric / semantic cluster relations: `_also_see` (ComplEx: $0.4565$ vs RotatE: $0.3088$), `_similar_to` ($0.6030$ vs $0.0010$), `_verb_group` ($0.8333$ vs $0.0127$).
3. **Synthesis:**
   - Combining rotational metric geometries for hierarchical DAG relations with bilinear complex mappings for symmetric relations yields superior ranking resolution across the entirety of WordNet.

Check: `python3 kitchen/test_g92.py`
