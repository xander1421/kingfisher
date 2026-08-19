# G86 — Mining and Scoring Length-1 Subsumptions under Lift Filtering on Official FB15k-237

`certify ok=true`, 4 controls, 3 falsifiers. **F2 FIRED: Pure Length-1 rules yield 0.0000 MRR on official FB15k-237 test split.**

## Empirical Finding

1. **Rule Mining on `train.txt` (272,115 triples):**
   - 312 Length-1 rules pass Bayesian Lift filtering ($\text{Lift} \ge 1.25$, $\text{Support} \ge 10$, $\text{Conf} \ge 0.10$).
   - Top rules include administrative subsumptions and athletic roster mappings with confidence up to $87.94\%$ and lift up to $1835.4\times$.
2. **Evaluation on Official `test.txt` (20,466 triples):**
   - Rules fire on 6,703 / 20,466 test queries ($32.75\%$), but achieve **0.0000 Filtered MRR / 0 Hits@10**.
   - **Mechanism:** Toutanova & Chen (2015) explicitly constructed FB15k-237 by removing all direct and inverse 1-hop shortcut edges across splits. Therefore, Length-1 rules cannot complete test queries alone without 2-hop compositions ($G59$, $G64$) or latent representations ($G76$, $G77$).

Check: `python3 kitchen/test_g86.py`
