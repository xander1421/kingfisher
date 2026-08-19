# G87 — 4-Way Neuro-Symbolic Hybrid with Bidirectional 4-Topology Mining ({DistMult, ComplEx, G64, Prior}) on Official FB15k-237

`certify ok=true`, 4 controls, 3 falsifiers. **New neuro-symbolic benchmark on official all-entity FB15k-237: 0.3136 Filtered MRR / 48.11% Hits@10.**

## Scoreboard Comparison

| Architecture / Method | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Notes |
|---|:---:|:---:|:---:|:---:|---|
| **Support-Gated Observed+Gate (`G59`)** | 0.2679 | — | — | 0.4037 | Pure symbolic baseline |
| **4-Topology Bidirectional Mining (`G64`)** | 0.2778 | 0.1912 | 0.3065 | 0.4274 | 6,736 rules across FF, BF, FB, BB |
| **All-Entity ComplEx Baseline (`G72`)** | 0.2755 | 0.1851 | 0.3072 | 0.4452 | dim=64, 1-N softmax, min_epoch=10 |
| **All-Entity DistMult Baseline (`G76`)** | 0.2852 | 0.1923 | 0.3168 | 0.4552 | dim=64, 1-N softmax, min_epoch=10 |
| **4-Way Mix with Forward-Only G51 (`G77`)** | 0.3101 | 0.2224 | 0.3402 | 0.4746 | {DistMult 291, G51 77, ComplEx 53, Prior 25} |
| **4-Way Mix with Bidirectional G64 (`G87`)** | **0.3136** | **0.2278** | **0.3438** | **0.4811** | **{DistMult 292, G64 85, ComplEx 51, Prior 18}** |

## Findings

1. **Increased Symbolic Capture:** Replacing forward-only 2-hop rules ($G51$) with full 4-topology bidirectional rules ($G64$) increases symbolic win rate from 77 keys to **85 keys** across relation directions.
2. **Transfer to Test:** Higher symbolic coverage lifts Filtered MRR from $0.3101 \to \mathbf{0.3136}$ ($+0.0035$) and Hits@10 from $47.46\% \to \mathbf{48.11\%}$ ($+0.65\%$).
3. **No Retraining Required:** Reuses frozen latent embeddings (`complex_emb.npz` and `distmult_emb.npz`).

Check: `python3 kitchen/test_g87.py`
