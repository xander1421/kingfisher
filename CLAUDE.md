# OPERATION KINGFISHER — working rules

Read `HANDOFF.md` for state. This file is the *discipline*, and it is loaded
automatically, so it is the one place a rule will actually be seen.

## Before you believe a number, run the checks

```python
import sys; sys.path.insert(0, '<repo>/spikes/harness')
from kfcheck import certify, Control

ok, problems = certify(
    spike_dir, deps=[...], artifacts=[...],
    controls=[Control(name, why, null_must_contain=..., can_fail_because=...)],
    measurements=[{'name':..., 'points':[(x,y)...], 'as_rate':True}],
    captures=[('result_hash', h)],
    instrument_texts=[('dumpsys battery', text)],
    falsifier='what result would have refuted this claim')
```

`certify` **refuses**; it does not warn. It is cheap and it has caught real
errors in this repo, including in the code that added it.

## Five failure families — every error here has been one of these

**A. The instrument cannot produce the answer.** (A15 / A20 / A21)
A control that cannot fire; a null that cannot contain the effect; a test that
cannot express its verdict. *Decidable from the design, before the run.*
→ `Control(can_fail_because=...)`, `power.check()`

**B. The instrument is reporting fiction.**
A frozen override (`UPDATES STOPPED`); an empty capture hashed as data
(`e3b0c442…`); a gate testing the wrong condition (`status=5` means FULL, not
plugged). *Confident, well-formed, wrong.*
→ `instrument.check_not_frozen / check_nonempty / check_semantics`

**C. The artifact is not what you think.** (A24)
A dirty tree claimed as a commit; a binary predating its source; the correct
sha256 of the *wrong* binary; an APK never installed; a Cargo feature moving
`fuel_used` 107→580.
→ `provenance.record` (mtime vs source, manifest hashes)

**D. Self-reported or self-flattering inputs.** (A22)
A party supplying the input to a check applied to itself. Four domain keys have
now overstated their own independence.
→ observe or attest, never declare. `DOMAIN_AXIS_LIMITS.md`

**E. The number is real, the model is wrong.** (A18)
One point extrapolated as a rate; an affine model that does not hold; harness
cost published as system cost; a ratio quoted without its operating point.
→ `units.fit_or_refuse / check_affine / attribute_intercept /
ratio_with_operating_point`

## Three things no tool will catch
Each of these was caught by reading, and pretending otherwise is its own error:

1. **Claim decay across documents** — "404s" → "deleted" → "the project failed".
   Cite the ledger row and its scope; re-verify anything load-bearing.
2. **Correct numbers, wrong attribution** — every figure reproduced, pointing at
   the wrong site. Precision is not evidence of correct cause.
3. **The right measurement of the wrong question** — uniform demand hid the
   regime that mattered.

The only defence is: **state the falsifier before running, then run it.** Every
error that survived here is one whose falsifier was written and marked "not yet
run". Every one that was caught is one where it was run.

## Editing
Use `edits.anchored_replace` / `patch_file`. `str.replace` returns the string
unchanged when the anchor is absent — a silent no-op edit was shipped that way
and found only because the resulting flag was inert.

## Correcting yourself
Correct in the LEDGER, in place, with what was withdrawn and why. Several
findings here got *better* when their falsifier fired. A retraction that
improves the result is the normal case, not an embarrassment.

## Safety rails (MISSION_LOOP §10 devices/keys, §11 publishing) — non-negotiable
No publishing: no pushes, PRs, package uploads, issue comments, posts. External
artifacts go to `proposed/` for a human. No wallets, keys, seed phrases, tokens,
mainnets or testnets. No miners. Device jobs honour charging + idle + UNMETERED,
and the gate must *refuse*, not warn. Cloned code in `elders/` stays untrusted:
build and test in place, never pipe curl to a shell. Nothing is written outside
the workspace.
