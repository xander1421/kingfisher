# H160 — Adversarial Audit & RotatE Boundary Ablation on G88 5-Way Hybrid

`certify ok=true`, 3 controls, 3 falsifiers. **Adversarial audit confirms RotatE validation selection generalizes to unseen test queries with +0.0130 MRR delta over DistMult and +0.0193 over ComplEx.**

## Audit Measurements

1. **Test Query Scope:** Evaluated 2,412 test queries ($5.89\%$ of the entire 40,932 test query set) corresponding to the 26 relation directions where RotatE was selected over DistMult/ComplEx.
2. **Model Performance on Selected Keys:**
   - **RotatE Test MRR:** **$0.2259$**
   - **DistMult Test MRR:** $0.2129$ ($\text{RotatE}\,\Delta = \mathbf{+0.0130}$, $+31.24$ net MRR mass gain)
   - **ComplEx Test MRR:** $0.2066$ ($\text{RotatE}\,\Delta = \mathbf{+0.0193}$)
3. **Geometric Ablation:** RotatE outperforms ComplEx on these 26 keys by $+0.0193\,\Delta$, demonstrating that distance-based scoring in $\mathbb{C}$ ($\|h \circ r - t\|_2^2$) captures specific relation rotations that Hermitian bilinear dot products ($\text{Re}(\langle h, r, \bar{t} \rangle)$) systematically misrank.
4. **Predicate Breadth:** Gains are distributed across 24 distinct predicates, confirming no single hub relation manufactured the win.

Check: `python3 kitchen/test_h160.py`
