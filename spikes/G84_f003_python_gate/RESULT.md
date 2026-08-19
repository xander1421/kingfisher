# G84 — Python-only F003 Modus Ponens Verification Gate

`certify ok=true`, 6 controls, 5 falsifiers. **F003 status remains `F003_DRAFT`.**

## Verdict

`F003_MODUS_PONENS` is specified under `FT_METTA_CORE_V2` in `specs/KERNEL_FRAGMENT.md`. This spike locks the Python-only verification gate prior to any host Rust or on-device ports.

- **Python `grok_check` ACCEPT:** Honest `fixtures/F003_specv1` derives consensus digest **`0e1edf5bf87964efe1de8def1bef38ee22cdf86d495d8ac53273d2a6ed8bc8a5`**.
- **7/7 Mutants Strictly REJECTED:**
  - M01: `FUEL_DIVERGENCE`
  - M02: `ILLEGAL_OPCODE`
  - M03: `CORPUS_ROOT_MISMATCH`
  - M04: `FUEL_FILE_MISMATCH`
  - M05: `SEMANTIC_UNIFICATION_FAILURE`
  - M06: `RESULT_NOT_DERIVED`
  - M07: `RESULT_NOT_DERIVED`
- **Rust `trace_verifier_web` REJECTS:** `WRONG_FIXTURE_CLASS` (rc=1; Rust remains F001+F002 only).
- **Parent `fixtures/F003` REJECTS:** `DIGEST_MISMATCH` (rc=1; parent tree left as non-immortal negative evidence).
- **Consensus Invariants:**
  - `F001_FROZEN`: `590d87691de53cba062f35bdcb177003fb3b25c1ac90f004c35140d9b014a88f` (unmoved).
  - `F002_FROZEN`: `c43b1eab9db84338a2d696d7f5552e3526c2cf66e7a0d534081f727b18898dd9` (unmoved).
  - `F003_specv1`: Status is **`F003_DRAFT`**; NOT in `kitchen/immortal.json`.
  - `operator=1` strictly pinned (`not_operator_2=True`). Section §8 remains `UNPROVEN`.

Check: `python3 kitchen/test_g84.py`
