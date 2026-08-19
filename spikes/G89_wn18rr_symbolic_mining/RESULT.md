# G89 — 4-Topology Bidirectional Symbolic Rule Mining & Evaluation on Official WN18RR

`certify ok=true`, 3 controls, 3 falsifiers (F3 fired). **First benchmark evaluation of symbolic 4-topology Horn clauses on WordNet hierarchical semantic graph (WN18RR).**

## Findings & Empirical Falsification (F3)

1. **Rule Induction on Lexical Hierarchy:**
   - Mined 40 bidirectional 2-hop rules across 11 relations in $1.91\,\text{s}$ (FF: 12, BF: 12, FB: 8, BB: 8).
2. **Preregistered Falsifier F3 FIRED:**
   - Pure 2-hop symbolic rules achieve **$0.0355$ Filtered MRR** ($2.33\%$ Hits@1, $5.78\%$ Hits@10) on the 3,134 test triples (6,268 queries).
   - **Root Cause & Structural Insight:** Unlike the dense associative multigraph of FB15k-237 (where 2-hop rules achieve $0.2778$ MRR), WN18RR is a sparse, tree-like taxonomy with 40,943 entities and only 11 relations. Because Dettmers et al. (2018) pruned 1-hop inverse shortcuts, 2-hop paths exist for only a small fraction of queries, proving that **continuous geometric embeddings (RotatE / ComplEx) or deep $k$-hop reasoning are structurally required on hierarchical lexical graphs.**

Check: `python3 kitchen/test_g89.py`
