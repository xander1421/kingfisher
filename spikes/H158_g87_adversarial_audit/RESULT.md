# H158 — Adversarial Audit & Topology Decomposition of G87 Neuro-Symbolic Hybrid

`certify ok=true`, 3 controls, 3 falsifiers. **Audit confirms G87 neuro-symbolic mechanism: +0.0721 MRR delta on 11,269 test queries with broad 57-predicate distribution and 66.4% non-chain topology support.**

## Adversarial Attacks & Verdicts

1. **Attack 1: Validation Overfitting / Test Delta on G64 Keys**
   - Evaluated 11,269 test queries across 85 relation directions selected for G64.
   - **G64 Test MRR: 0.2821 vs DistMult 0.2100 (+0.0721 Δ).**
   - Net gain of $+813.0$ MRR mass. Valid selection transfers robustly to unseen test split. F1 did not fire.
2. **Attack 2: Hub Predicate Concentration**
   - 57 distinct predicates active in G64 selected set.
   - Top-3 predicates account for only **38.2%** of net gain mass ($+310.58$ / $+812.96$), refuting hub concentration ($< 80\%$). F3 did not fire.
3. **Attack 3: Non-Chain Topology Composition**
   - 4-topology mining yields 4,472 non-chain rules (BF=2,192, FB=1,302, BB=978) out of 6,736 total rules ($66.4\%$). F2 did not fire.

Check: `python3 kitchen/test_h158.py`
