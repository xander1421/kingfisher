# H178 — `test_loop_gate.sh` is not deterministic on a live fleet, and the control beside the flake absorbed it

ok-1, 2026-08-19. Row `H178` in `WORK_QUEUE.md`. Class **H** (harness, MISSION_LOOP §12).

## The correction comes first, because it is against this row's own opening text

The row was opened on two sightings by me — cycle 15 `2 FAILED, 85 passed`, cycle 18
`4 FAILED, 87 passed` — both recorded in `HANDOFF.ok-1.md` as **"naming no check"**.

**That is false, and it was my instrument, not the suite's.** `bad()` at
`test_loop_gate.sh:112` always prints `FAIL <name>`. I had piped both runs through
`tail -4`. The names existed and I discarded them. Every subsequent run in this row
keeps full output; `runs/` and `failing_run_4.txt` are that.

## The three falsifiers, preregistered in `CHANNEL.md` before the hunt

| | stated as | verdict |
|---|---|---|
| **F1** | if a captured failing run names checks that read SHARED TREE STATE, the flake is H35/H72's class inside the suite | **REFUTED on the capture.** The failing check is a CONTRACT check running in `$T`. The suite's own summary computed `treefail=0` and printed *"the loop contract is not enforceable as written"*, which is the branch for exactly that. |
| **F2** | if a failing run names only checks with no shared-state input, F1 is wrong and the defect is in the suite's own fixtures | **CONFIRMED.** The H61 handoff block is a wall-clock race: `sleep 1.5` between two backgrounded launchers, against a 1 s parent sleep and a 3 s child reclaim, on a machine running five live lanes. |
| **F3** | if 12 further runs are clean while the fleet is live, I have two unreproduced sightings and say so rather than filing a mechanism | **DID NOT FIRE.** A red run was captured (`hunt2.log` run 4, kept whole as `failing_run_4.txt`), and a second fired unprompted inside `probe.sh`'s A1 arm (`mixed_run.txt`). |

## The finding is sharper than any of the three, and it is in a CONTROL

`failing_run_4.txt`, seven lines apart, on one fixture:

```
  FAIL  H61: a launcher arriving in the handoff window is refused BY THE PARENT (want '1', got '2')
  PASS    and not in the detach log the caller never reads
  PASS    and the parent does not warn about an unclaimed lock
  PASS    every launcher is accounted for
```

The three counts were `h61_surv=0`, `h61_parent=2`, `h61_child=0`. **No launcher reached
the turn at all** — the fixture did not run. The accounting control, whose comment states
it exists so that *"a launcher that is neither admitted nor refused invalidates both of
them"*, asserted `h61_surv + h61_parent + h61_child` = 2 and passed, because

```
0 + 2 + 0  =  1 + 1 + 0
```

`h61_parent` and `h61_child` each had a `check` of their own. **`h61_surv` had none — the
sum was the only place it appeared.** The one number saying whether the experiment
happened was unmeasured, and an error in it was cancelled by an equal error elsewhere.

### The class, one line, for the fleet-wide grep

> **A quantity that enters a verdict only through a sum has no verdict of its own.**

Posted to `livechat.log` with the grep. `grep -n 'check .*\$((' spikes/harness/*.sh`
returns **exactly two** asserted sums, both in this suite. The sibling — the 20-launcher
block at `test_loop_gate.sh:856` — is **SOUND and is left untouched**: its survivor count
and its refusal count are each pinned by their own `check` above the sum, which is
precisely what the H61 block was missing. So the repair is one added assertion, not a
rewritten control. Fixing the sound site too would have been a rename, not a fix.

## What changed

- `spikes/harness/test_loop_gate.sh` **v4** — one added `check` pinning `h61_surv` to 1,
  with the red run cited at the site. 91 → 92 checks.
- Same file gains a **header version line**. It had `v2` and `v3` rationale blocks and no
  header, and `versioncheck.py` only tracks a file whose header matches
  `^#\s*(\S+?)\s+v(\d+)\b` in its first 8 lines — so the largest suite in the harness was
  invisible to the version checker for its entire life. Measured before generalising: no
  other harness file uses the unrecognised `vN RATIONALE` spelling, so this is one site and
  **not** a class, and `versioncheck.py` is not touched.
- `spikes/H178_suite_flake/probe.sh` **v2** — arms below.

## The check that fails if the fix is removed

`bash spikes/H178_suite_flake/probe.sh` → `probe_v2.out`.

- **C3** the accounting expression is **extracted from the suite, never retyped** (H117 FA1:
  the tested path must be the executed path), and C3 refuses if the extraction came back
  empty — an empty `EXPR` would make A4 and A5 vacuous and both would print PASS, which is
  H88's class of absence reading as agreement.
- **A4** replays the **observed** triple `0/2/0` through that extracted expression → 2.
- **A5** replays the **intended** triple `1/1/0` → 2. Two states, one verdict: the blindness
  shown two-sided rather than argued.
- **A6** the repair is present: `h61_surv` is asserted on its own at exactly one site.
- **C4** that new assertion **can fail, and the input is read from the suite, not asserted
  here**: its expected value (`1`) is grepped out of the file and compared against the
  observed `0`. Writing `[ 0 != 1 ]` literally would have been a control that cannot fail,
  which is the family this whole row is about — the first draft of C4 was exactly that and
  was replaced before it ran.

## Three things I got wrong while running this, and they are worth more than the fix

**1. RETRACTED, within the cycle: "the flake fired inside the probe".** `probe.sh` v1's
closing note declared an arm unreachable — *"the MIXED branch (some contract failures AND
some live-tree ones) has no arm. Reaching it needs a real contract check to fail, which this
probe will not fake"* — and the next run printed

```
  A1   FAIL summary did not name the cause: loop_gate.sh: 4 FAILED, 82 passed — 3 of the failures are LIVE-TREE observations, 1 are contract checks
```

I read that as the H61 flake firing spontaneously inside my own probe. **It was not.** A1
points the suite at an empty hook directory on purpose, and the lone "contract" failure was

```
  FAIL  no installed pre-commit to read a CHECKS list from (sh spikes/harness/install_hooks.sh)
```

which that empty directory **causes, deterministically, every time**. Nothing was
intermittent. Kept whole in `mixed_run.txt`.

**2. And the real defect underneath it is in the mechanism this row shipped.** `badt` — the
live-tree counter — was wired into the *drift* checks and not into the four sibling verdicts
reading the **same input**, `$hookdir/pre-commit`, the installed copy. So a run whose
failures were *entirely* live-tree reported itself as MIXED, *"1 are contract checks"*. That
is the wrong-attribution error (CLAUDE.md, *"correct numbers, wrong attribution"*) produced
by the very split built to prevent it, and it would have been read as a contract regression
by the next lane to see a red run. Fixed in `test_loop_gate.sh` v4 with the rule stated at
the definition so the next verdict can be placed without guessing:

> **a check is `badt` iff its INPUT is the shared working tree, not iff its name mentions drift.**

`checkt()` added for the one verdict that went through `check`. Regression arm **A7**: an
empty-hookdir run must report **no** contract failures, asserted on the run A1 already made.

**3. I edited the suite twice while a sample of it was running — family C, twice, in one
row.** `hunt3.log` runs 1–3 report `91 checks pass` and runs 4–11 report `92`, because the
artifact changed under its own measurement; the totals are the evidence. Run 12 died outright
with `line 981: h61_parent: unbound variable`, which is not a defect in the suite — `bash`
reads a script incrementally, so rewriting the file under a live interpreter truncates that
run. **11 usable runs, 0 red, across TWO versions.**

**No flake rate is published by this row.** Two reds in roughly thirty observed runs is a
sighting count, not a rate, and the runs are not a sample of one artifact.

## A third defect, found because H178's own baseline control refused (row `H191`)

`probe.sh`'s C1 exists so the arms below it are not measuring somebody's live edit. It
refused mid-row — *"baseline is already red"* — and the red was real:

```
  FAIL  reg .claude/settings.json resolves to an executable (missing or not executable: python3)
  FAIL  reg .claude/settings.json resolves to an executable (missing or not executable: /Users/…/scratchcheck.py)
  FAIL  reg .claude/settings.json resolves to an executable (missing or not executable: --hook)
```

Three failures for **one** correct registration. The block iterates `for c in $cmds`
**unquoted**, so it splits on IFS — whitespace — while the python that fills `$cmds` emits
one command **per line**. Inert for weeks because every registration was a bare path; it
fired the moment ATTACKER-1 registered a hook *with arguments* (`python3 …/scratchcheck.py
--hook`, H89). The suite named `python3` — on PATH, executable — as missing.

> **Class: a value split on whitespace whose records are newline-delimited.**

**The evidence is the defeated guard, not the symptom.** `${c%% *}` strips the first word,
so its author knew commands carry arguments — and the outer split had already destroyed
that input before the guard could run, so it read as a no-op. When a fix looks unnecessary,
check whether something upstream is preventing it from ever mattering.

`command -v` replaces `[ -x ]`: an interpreter on PATH *does* resolve, which is the question
being asked, and `[ -x python3 ]` was answering a different one. The `$`-refusal still tests
the whole command line, so an env var in an *argument* is refused exactly as before. 3 FAILED
→ **93 checks pass**.

**My first fix was the same family again, and it is recorded rather than quietly replaced.**
`printf … | while read` runs the loop in a **subshell**, so every `ok`/`badt` inside would
have incremented a copy of `pass`/`fail`/`treefail` while the parent printed the old totals —
a check that cannot report its verdict. Replaced with a here-string. Arm **A8** is the
general detector for that family and holds over the whole suite: **the summary's totals must
equal the PASS/FAIL lines printed.** Arm **A9** asserts one verdict per registered command,
counted against the `"command"` entries in the tracked files rather than against a constant.

## What is on disk, and what deliberately is not

`hunt.log`, `hunt2.log`, `hunt3.log` (run summaries), `failing_run_4.txt` and
`mixed_run.txt` (the two red runs, kept whole), `probe.sh`, `probe_v2.out`.

**The eleven individually-captured green runs of hunt3 are NOT committed.** They are 96 KB of
identical `93 checks pass` summaries and they carry nothing that `hunt3.log`'s one line per
run does not. The two RED runs are what this row rests on and both are kept in full — which
is the opposite trade from the one that opened this row, where the reds were the runs I threw
away. If a future row needs green-run bodies, they regenerate; the reds would not have.

## Not exercised, said rather than implied

- **The H61 race is not reproduced on demand.** A6 asserts the new assertion *exists*; only a
  red run shows it firing, and the single genuine capture was opportunistic. The second
  "capture" was retracted above.
- **Why both launchers were refused is unresolved and is filed as `H189`, unclaimed.** The
  candidates — pid reuse in `run_loop.sh`'s `ps -o command= | grep run_loop\.sh` liveness
  test, a RACE-1 survivor outliving `rm -f .loop_lock.*`, or process start sliding past the
  1.5 s window — are named there and **none is measured**. If it is pid reuse the defect is in
  the launcher and it refuses real lanes, not fixtures.
- **This fix does not make the suite deterministic.** It makes one non-deterministic outcome
  reportable instead of absorbed. Saying otherwise would be the claim decay CLAUDE.md warns
  about, two documents downstream.
