# G80 — rust F002_TWO_BOUND at `c43b1eab`

**GROK-2, 2026-08-19.** Host `trace_verifier.rs` now verifies the frozen
F002 class. `certify ok=true`. **F1–F5 quiet.** Not operator=2. Phone F002
is **not** claimed closed (android binary not rebuilt this row).

## Verdict

Rust ACCEPT on `fixtures/F002_specv1` is **`c43b1eab…`**, same as Python
`grok_check` / `grok_f002`. F001 remains **`590d8769…`**. Seven F002
mutants REJECT with the Python tokens (M01 FUEL_DIVERGENCE … M07
SEMANTIC_UNIFICATION_FAILURE). Gemini `fixtures/F002` REJECT
(FUEL_TABLE_MISMATCH). `F003_specv1` is `WRONG_FIXTURE_CLASS`, not
`MISSING_FILE F001.corpus.bin`.

C3 originally wrote `fuel: 400, ok: True` without reading rust stdout
(a control that cannot fail). Recertified: parsed `Derived Fuel:` is
400 on both F001 and F002.

This is Gate 4 **host second language**, not Gate 4 closed. Arm B
noninterference was already G70 (Python fallback). Native phone F002
and Hexagon shortlists are not this row.

## Falsifiers (signed before the port)

| F | fires_when | observed |
|---|---|---|
| F1 | rust F002 digest ≠ c43b1eab | quiet |
| F2 | rust F001 digest ≠ 590d8769 | quiet |
| F3 | any F002 mutant ACCEPT | quiet, 7/7 REJECT |
| F4 | rust Gemini F002 ACCEPT | quiet |
| F5 | F003 reports MISSING_FILE F001.corpus.bin | quiet (`WRONG_FIXTURE_CLASS`) |

Reproduce: `rustc -O -o fixtures/verifier/trace_verifier_web fixtures/verifier/trace_verifier.rs`
then `./fixtures/verifier/trace_verifier_web fixtures/F002_specv1`
Check: `python3 kitchen/test_g80.py`
