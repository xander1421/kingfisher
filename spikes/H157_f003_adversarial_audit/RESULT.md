# H157 — Adversarial Audit on Modus Ponens Verification & FT_METTA_CORE_V2 Soundness

`certify ok=true`, 3 controls, 3 falsifiers. **All 4 adversarial attacks strictly REJECTED.**

## Attack Results

1. **Attack A1 (Fuel table downgrade — V1 table on V2 fixture):**
   - Result: `REJECTED: ILLEGAL_OPCODE` (rc=1). Opcode `MODUS_PONENS` is missing in `FT_METTA_CORE_V1`.
2. **Attack A2 (Unbound consequence variable injection):**
   - Result: `REJECTED: RESULT_NOT_DERIVED` (rc=1). Unbound variable `$y` cannot unify with the claimed ground result.
3. **Attack A3 (Premise mismatch):**
   - Result: `REJECTED: RESULT_NOT_DERIVED` (rc=1). False premise `(Dog Kermit)` does not satisfy rule antecedent `(Frog $x)`.
4. **Attack A4 (Tampered step cost):**
   - Result: `REJECTED: FUEL_DIVERGENCE` (rc=1). Step fuel 100 diverged from declared cost 150.

Consensus digests and pins `F001_FROZEN` (`590d8769…`) and `F002_FROZEN` (`c43b1eab…`) remain completely invariant.

Check: `python3 kitchen/test_h157.py`
