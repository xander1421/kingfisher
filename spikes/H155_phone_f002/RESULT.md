# H155 — Phone F002 Execution on Samsung Galaxy S25 Ultra (Snapdragon 8 Elite)

`certify ok=true`, 3 controls, 5 falsifiers. **Gate 4 is CLOSED on silicon.**

## Verdict

The native aarch64 Android binary was rebuilt directly from `fixtures/verifier/trace_verifier.rs` (`4,517,840` bytes) and executed on the attached Samsung Galaxy S25 Ultra (`R5CY93675MK`, Snapdragon 8 Elite).

On physical hardware:
- **`F001` ACCEPTED:** Derived fuel `400`, witness `112f7e8c…`, consensus digest **`590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f`**.
- **`F002_specv1` ACCEPTED:** Derived fuel `400`, witness `2271d062…`, consensus digest **`c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9`**.
- **7/7 F002 Mutants REJECTED on Silicon:** M01 `FUEL_DIVERGENCE`, M02 `ILLEGAL_OPCODE`, M03 `CORPUS_ROOT_MISMATCH`, M04 `FUEL_FILE_MISMATCH`, M05 `SEMANTIC_UNIFICATION_FAILURE`, M06 `RESULT_NOT_DERIVED`, M07 `SEMANTIC_UNIFICATION_FAILURE`.
- **Gemini `fixtures/F002` REJECTED:** `FUEL_TABLE_MISMATCH` (rc=1).
- **`fixtures/F003_specv1` REJECTED:** `WRONG_FIXTURE_CLASS` (rc=1).

---

## Device Telemetry (`quiet.sh --device`)

- **Device:** Samsung Galaxy S25 Ultra (`SM-S938B`, `R5CY93675MK`)
- **SoC:** Qualcomm Snapdragon 8 Elite (aarch64)
- **Quiet Before:** CPU busy $0.4\% < 15\%$, thermals $36.3^\circ\text{C} < 45^\circ\text{C}$, charging `true` (level 100).
- **Quiet After:** CPU busy $0.7\% < 15\%$, thermals $36.6^\circ\text{C} < 45^\circ\text{C}$, charging `true` (level 100).

---

## Provenance & Gate Status

- **Gate 3:** CLOSED (`F001_FROZEN` accepted across Python, host Rust, and Android silicon).
- **Gate 4:** **CLOSED** (`F002_FROZEN` accepted across Python, host Rust, and Android silicon; 7/7 mutants rejected; Arm B noninterference certified in G70).
- **Section §8:** `operator=1` remains strictly pinned (`not_operator_2=True`). Section §8 remains `UNPROVEN` (0 multi-operator live network jobs).

Check: `python3 kitchen/test_h155.py`
