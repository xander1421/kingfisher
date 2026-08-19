# G83 — F003_DRAFT is named, not frozen, not rust

`KERNEL_FRAGMENT.md` Gate 4 no longer says phone F002 is open. It names
S25 + pin `c43b1eab9db84338…`. It also names `fixtures/F003_specv1` as
**F003_DRAFT** (modus ponens, `FT_METTA_CORE_V2`) and says it is **not a
legal class**. `certify ok=true`. **F1–F3 quiet.**

This row does not freeze F003. It does not teach rust F003. It does not
write `kitchen/immortal.json`.

## Verdict

Python `grok_check` ACCEPT `0e1edf5b…` on the sidecar (already true;
not a new checker). Host rust REJECT `WRONG_FIXTURE_CLASS`. F003 is
absent from immortal.json. F001 `590d8769` / F002 `c43b1eab9db84338`
unmoved. Spec 103 lines (bar 120). V1 table is not hot-patched.

Parent `fixtures/F003` stays a different encoding (`544aea51`,
query=prefix). Quote the sidecar.

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | rust ACCEPT F003_specv1 | WRONG_FIXTURE_CLASS | quiet |
| F2 | F003 in immortal.json | absent | quiet |
| F3 | F001 or F002 pin missing | both present | quiet |

C1 spec names DRAFT + not a legal class. C2 Gate 4 S25 + real pin.
C3 python 0e1edf5b. C4 rust WRONG_FIXTURE_CLASS. C5 pins. C6 nlines≤120.

Do not start rust F003. Do not freeze. operator=1. Gate 4 (this S25) closed.

Reproduce: `python3 spikes/G83_f003_draft/draft.py`
Check: `python3 kitchen/test_g83.py`
