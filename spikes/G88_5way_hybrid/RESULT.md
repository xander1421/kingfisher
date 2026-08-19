# G88 — 5-Way Neuro-Symbolic Hybrid with RotatE Geometric Embedding on Official FB15k-237

`certify ok=true`, 4 controls, 3 falsifiers. **New neuro-symbolic benchmark high on official all-entity FB15k-237: 0.3143 Filtered MRR / 48.15% Hits@10.**

## Scoreboard Progression

| Architecture / Method | Filtered MRR | Hits@1 | Hits@3 | Hits@10 | Notes |
|---|:---:|:---:|:---:|:---:|---|
| **Support-Gated Observed+Gate (`G59`)** | 0.2679 | — | — | 0.4037 | Pure symbolic baseline |
| **All-Entity ComplEx Baseline (`G72`)** | 0.2755 | 0.1851 | 0.3072 | 0.4452 | dim=64, 1-N softmax, min_epoch=10 |
| **4-Topology Bidirectional Mining (`G64`)** | 0.2778 | 0.1912 | 0.3065 | 0.4274 | 6,736 rules across FF, BF, FB, BB |
| **All-Entity DistMult Baseline (`G76`)** | 0.2852 | 0.1923 | 0.3168 | 0.4552 | dim=64, 1-N softmax, min_epoch=10 |
| **4-Way Mix with Forward-Only G51 (`G77`)** | 0.3101 | 0.2224 | 0.3402 | 0.4746 | {DistMult 291, G51 77, ComplEx 53, Prior 25} |
| **4-Way Mix with Bidirectional G64 (`G87`)** | 0.3136 | 0.2278 | 0.3438 | 0.4811 | {DistMult 292, G64 85, ComplEx 51, Prior 18} |
| **5-Way Mix with RotatE Geometric (`G88`)** | **0.3143** | **0.2289** | **0.3443** | **0.4815** | **{DistMult 279, G64 85, Complex 39, RotatE 26, Prior 17}** |

## Findings

1. **RotatE Orthogonal Geometric Precision:** RotatE ($G79$) captures 26 relation directions where complex rotation in $\mathbb{C}$ outperforms both bilinear scoring (DistMult / ComplEx) and explicit graph random walks.
2. **Transfer to Test Split:** Valid selection of RotatE lifts Filtered MRR from $0.3136 \to \mathbf{0.3143}$ ($+0.0007$) and Hits@10 to $\mathbf{48.15\%}$.
3. **Symbolic Invariance:** The 85 bidirectional symbolic rules ($G64$) remain completely intact, proving symbolic reasoning is orthogonal to geometric embedding choices.

Check: `python3 kitchen/test_g88.py`
