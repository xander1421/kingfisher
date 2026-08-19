# H201 — a control whose verdict is a literal, and there are twelve of the same one

`certify ok=True`. 4 controls, all fired. 3 falsifiers preregistered in
`CHANNEL.md` before the run; **none fired**, and each could have killed the row.

Run: `python3 spikes/H201_literal_verdicts/sweep.py` · Check: `sh spikes/H201_literal_verdicts/check.sh`

## What this row is NOT

S91's seat-level defect — five seats that are one computation — is **AGENT-1's
H188, already DONE**, and is not re-litigated here. H188 proved 0 seat reads, max
1 distinct digest per job, a wrong pin leaving adjudication byte-identical, and
an axis audit that responds only to the literal roster. This row is the thing
H188 did not test: **whether S91's controls could fail at all.**

## The defect

`S91/run.py:242`:

    c3_ok = True
    ...
    controls[2].observe(c3_ok, {"f001": PIN_F001, "f002": PIN_F002})

on `Control("C3_pins_intact", why="F001 and F002 pins remain invariant",
can_fail_because="pin drift")`. **No input to that program makes `c3_ok`
anything but `True`.** It fired; `certify` recorded `ok=True`; and the claim it
stands behind is that the frozen benchmark pins are intact.

**It is not one spike.** At `503231f8`, 487 `.py` files scanned:

| | |
|---|---:|
| LIVE literal verdicts | **31** |
| …of which are the *same copied* `C3_pins_intact` control | **12** |
| fixtures inside `demo()` / `selfcheck()` (not defects, printed anyway) | 11 |
| unparseable | 0 |
| trees skipped (each named on request) | 98 |

The twelve: `G86`, `G87`, `G88`, `G89`, `G90`, `G91`, `G93`, `H157`, `H158`,
`H159`, `H164`, `S91`. That is the whole WN18RR/hybrid thread, **three
adversarial audits**, and a distributed run — a template travelling by
copy-paste. Every one declares `can_fail_because="pin drift"` and none can
observe drift.

## The guard that exists for this cannot reach it

`Control.observe` already flags constant observations — *"a control whose
observations are all identical distinguished nothing"* — but only when
`len(values) > 1` and every value is equal. Measured:

    observe(True, {"f001": ..., "f002": ...})  ->  constant = False
    observe(True, [True])                      ->  constant = False
    observe(True, [1, 1, 1])                   ->  constant = True

So a dead control with a rich-looking observation dict reads as a healthy one.
**The flag inspects the OBSERVATIONS; the defect is in the VERDICT.** That is F1,
and it did not fire.

## Not all 31 are dead controls, and the tool does not claim they are

`H89`, `H194`, `H200` write

    c1.observe(True, [2, 0], 'exit 2 on `echo x > /tmp/y`; exit 0 on `echo x > out/y`')

The verdict is a literal, but the **discriminating values are recorded beside
it** and the `can_fail_because` names them: *"if the permitted case also exited 2
… these two values would be equal."* A third party can recompute that. It is
weaker than deriving the verdict in code — a mistyped observation would not be
caught — but it is not the pins shape, where the observation is the two pin
constants and nothing in the program compares them to anything.

**Both are reported; only the second is called a dead control, and that reading
is prose here, not a verdict of the tool.** A source-level detector cannot tell
transcription from fabrication, and pretending otherwise would be the
wrong-attribution failure this repo names as unmechanisable.

## Method — AST over source, bounded on purpose

`constcheck.py` flags a `.observe(` whose first positional argument is a literal
constant, **or a name bound exactly once in that scope to a literal**. Any second
binding of the name — augmented assignment, loop target, `with … as`, walrus,
`global` — disqualifies it. That is not dataflow analysis; it is "this name is a
constant in this scope, by construction", and the bound is what keeps the false
positive rate at zero. `c1.observe(len(ROSTER) == 5, …)` is derived and must
never be flagged; that arm is C1's second half and F3.

Fixtures are split by the **enclosing function chain** (`demo` / `selfcheck`),
mechanically and not by a file name list — `provenance.py`'s own `demo()` builds
`c_dead.observe(False, …)` deliberately to prove `record()` refuses it, and
flagging that would make this module report the test written for the thing it
reports. Nested helpers count: `provenance.py`'s `_c` sits inside `demo`.

## Two defects this row found in its own detector

**v1 could not see the instance that motivated the row.** It flagged only a
literal *first argument*; S91 writes `c3_ok = True` and passes a `Name`. v1's
tree-wide sweep returned 23 hits with **S91 not among them** — and v1's own
header argued the gap was a design virtue, which is how a scope narrows itself
green (H26b). C2 is the mutation that keeps it honest: delete the
name-resolution branch and S91 disappears from the sweep (1 → 0), so the branch
is load-bearing rather than decoration.

**v1 counted 11 fixtures as defects**, including `provenance.py`'s own
deliberately-dead controls. A checker red on its own fixtures is one everybody
learns to ignore (H14).

## And C4 fired against this spike, on the first run

C4 scans **this file with the module it ships**. On the first run it fired:
`certify` refused with *"CONTROL reporter_is_not_the_reported DID NOT FIRE — run
is VOID"*, because my F1 probe replayed S91's shape as
`dead.observe(True, {...})` — a literal verdict, in a spike whose subject is
literal verdicts.

**Repaired by removing the literal, not by exempting myself.** `observe()`
computes `constant` from `self.values` alone and never reads the verdict, so the
literal was irrelevant to what F1 measures; the probe now passes
`len(shape) == 2`. A reporter that special-cases itself is the failure this row
is about, and the alternative — adding `H201_` to a skip list — was available and
is exactly what C4 exists to make visible.

## Falsifiers

| | preregistered before the run | outcome |
|---|---|---|
| F1 | if `Control.observe`'s `constant` flag already catches S91's C3, the premise is false and this row closes WRONG | **did not fire** — `constant=False` on S91's exact shape |
| F2 | if S91 is the only site, this is a spike bug and no checker should ship | **did not fire** — 31 live, 12 of them one copied template |
| F3 | if the detector flags a DERIVED verdict it is not shippable, and the false-positive rate is the result rather than the count | **did not fire** — 0 on `len(R) == 5` |

## Filed, not fixed

**I change no other lane's spike.** The twelve pins controls belong to their
authors. `certify` is **not** changed to refuse a literal verdict either, and
that is a decision rather than timidity: retro-refusing would invalidate records
already on disk across six lanes and turn a shared gate red for work nobody can
clear alone — H14's shape, where the bypass then covers the real cases.

`constcheck.py` reports and is wired into `bringup.sh`'s reporting block beside
`idscope` and `stalecheck`, on the same grounds: report only, never gating a
lane launch.

**The open question, for whoever owns `provenance.Control`:** should
`can_fail_because` be checkable at all? Today it is prose a third party reads and
the module cannot test. This row makes the *source-level* form observable; it
does not make the promise enforceable, and I have no measurement of what
enforcing it would cost.
