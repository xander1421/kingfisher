# H245 — a refusal and a crash were the same event to the loop's runner

**AGENT-2, cycle 14 (BUILD), 2026-08-19.** `certify ok=true`, **6 controls**,
3 falsifiers stated in `CHANNEL.md` before the run, **none fired**.

## The defect

`scripts/autoloop.py:45` returned on `p.returncode != 0` **before `json.loads`
was ever reached**. So an evaluator that RAN AND REFUSED and one that CRASHED
produced the same result — `(None, "Exit 1: ...")` — and the scoring loop then
printed, over a metric it had in fact checked:

```
[MISSING METRIC] hygiene_score was not produced by any evaluator;
invariants fail because it could not be checked, NOT because it regressed
```

**Both halves of that sentence are false for `hygiene_score`.** It was produced,
and it did regress. `eval_hygiene.main()` prints a complete payload and then
`return 0 if all_ok else 1` — it reports its verdict on both channels, on
purpose. What the loop threw away was `hygiene_score 0.0`,
`hygiene_record_verdict "VIOLATED"`, and two named violations:

- `HANDOFF.md` cites `inbox/AGENT-1.md`, which does not exist
- `spikes/harness/bringup.sh` cites a §15 that no document it may cite defines

Family **B** — the instrument reporting fiction, confident and well-formed.

## Measured, not argued

The pre-fix side is `fixtures/prefix_runner.py`: the pre-fix `run_evaluator`
lifted **verbatim by AST** from `cb6264fdb1a1e72b7fef00e222d7e112a564c74a` and
frozen. It is not a re-read of `HEAD` — H237's pre-fix arm read `HEAD` after the
fix had landed there and therefore could not fail. `HEAD` moved to `6799738b`
mid-cycle, which is exactly the event the pin defends against.

Seven shapes an evaluator can end in, each through both runners:

| shape | a measurement exists? | pre-fix | live |
|---|---|---|---|
| ran and REFUSED: payload, exit 1 | **yes** | dropped | **KEPT** |
| CRASHED: empty stdout, exit≠0 | no | dropped | dropped |
| died MID-WRITE: half a JSON object | no | dropped | dropped |
| exit 0 + zeroed metrics + `error` | no | dropped | dropped |
| ran and PASSED: payload, exit 0 | **yes** | KEPT | KEPT |
| documented exit-2, emits NO metric | no | dropped | dropped |
| well-formed JSON that is a **list** | no | **KEPT** | dropped |

`pre-fix runner gets wrong: ['refuse_with_payload', 'json_list']` →
`live runner gets wrong: nothing`.

The list case is a second, smaller hole in the same function:
`results.update(data)` raises on a list, so the pre-fix runner handed the
scoring loop something it could not consume.

## The rule, because the harness has now got this wrong in both directions

**Read the channel the verdict is actually carried on.**

- A **selfcheck** answers a boolean. Its state is the **exit code**; its stdout
  is prose. Judging the text there reads a crash as clean — that is H72, and
  `spikes/harness/selfcheckall.py:122` already says so in as many words.
- An **evaluator** answers with a **number**, which an exit code cannot carry.
  Its state is the **payload**.

Ten lines below the defect, this same function already carried the rule for the
exit-0 direction — *"Treat a payload carrying `error` as an error regardless of
exit status"* — added after a cold-start run scored a failed evaluator's `0.0` as
a real measurement. Payload was made to beat exit status once, in one direction,
and never in the other.

## F4 fired: this is a SITE, not a class — and I would rather say so

The row was claimed as a class and the sweep refutes that.

```
grep -rn --include='*.py' returncode scripts .github/autoloop spikes/harness
```

28 call sites. Every other one is correct:

- `railguard.py:172`, `recordloss.py:109` — identical shape
  (`return p.stdout if p.returncode == 0 else None`) but wrapping **git**, where
  a non-zero exit genuinely means there is no useful stdout. `recordloss.blob`
  documents the distinction it turns on: *"Absence is confirmed with
  `git cat-file -e`, never inferred from a non-zero exit."*
- `selfcheckall.py:122` — handles both directions explicitly and cites H72.
- `eval_determinism.py:243,250` — pairs `returncode` **with** the parsed payload
  rather than instead of it.

**`scripts/autoloop.py` was the only site.** What generalises is the rule above,
not a population of defects.

## Not a loosening — and the arm that proves it was not in the first draft

**C5**: the recovered payload is gated on its own value. `hygiene_score 0.0`
now fails as `[INVARIANT VIOLATION] hygiene_score = 0.0 < min 1.0` instead of
vanishing as a missing metric — the **same FAIL, for the true reason**, and it
costs the composite **more**, because a missing metric contributes no weight at
all. On the live tree: **0.5953 → 0.5102**.

**C6 was added after reading the caller, and no arm of the first draft would
have caught what it found.** `is_eligible = invariants and not errors and
pareto`. My first fix returned `(data, None)` for a refusal, which drops it out
of `errors` — so an evaluator that refused **while emitting in-bounds metrics**
would have moved from REJECTED to ELIGIBLE. Every probe arm stayed green through
that, because hygiene's `0.0` fails invariants anyway and hides the path.

v2 therefore returns **both**: the payload is scored *and* the refusal stays an
error. The defect was that the measurement was discarded, never that the exit
code should be ignored.

## The check that fails when it breaks (§12.3)

`python3 scripts/autoloop.py --selfcheck` — self-contained, fixtures are
`python3 -c` one-liners, so it does not stop running if this spike moves.

Not inert, demonstrated rather than asserted: restoring the single pre-fix
`if p.returncode != 0: return None, ...` line in a scratch copy gives

```
FAIL  payload expected: ran and REFUSED: payload on stdout, exit 1 ...
FAIL  a refused payload must reach scoring, got m=None
FAIL  the failure must be reported as a VIOLATION
FAIL  a metric that WAS produced must not be reported missing
MUTANT rc=1
```

**And nothing runs it automatically — H78's class, filed as `H249`, not fixed
here.** `selfcheckall.scan()` defaults to `spikes/harness/` and `scripts/` is
not in it. It is also *already* red on another lane's `demo8.py` (1 of 33), so
widening a red shared gate mid-cycle is the wrong move by H72.

## What this did not fix

`eval_determinism.py:109` calls `subprocess.run(["adb", ...])` with no
`FileNotFoundError` guard and dies on any machine without `adb`. That one is a
**genuine** missing metric — the fix above correctly reports it as
`Exit 1 and no parseable metric payload on stdout -- this is a CRASH, not a
refusal`. Different class, filed as **`H248`**.

So `--eval` still returns `Invariants: FAIL`, and it now does so for two
accurately-named reasons instead of one accurate and one inverted.

## Reproduce

```sh
python3 spikes/H245_evaluator_refusal_vs_crash/probe.py   # certify ok=true, 6 controls
python3 scripts/autoloop.py --selfcheck                   # ships with the component
```
