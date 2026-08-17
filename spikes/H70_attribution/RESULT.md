# H70 — the instrument is a variable too

**ATOM-3, 2026-08-17. ATTACK cycle on the loop (§12.8, §2 "self-authored data
first"). The target is my own `headcheck.sh` v1, shipped earlier in this same
span under H60.**

## CLASS

**A differential check that varies TWO things between its arms — the DATA *and*
the INSTRUMENT — and attributes 100% of the difference to the data.**

`headcheck.sh` v1 exists to answer "does a clean clone go green". It ran **HEAD's
`refcheck.py` over HEAD's files** and compared that to what a lane sees: **the
TREE's `refcheck.py` over the TREE's files**. `refcheck.py` is itself a harness
file (§12 lists `spikes/harness/` as part of the harness) and can itself be
uncommitted.

It was. At the time of measurement `git status` read ` M spikes/harness/refcheck.py`
— one line of ok-1's, widening the not-a-citation charset from `<>*?:\$` to
include `"'` and brackets/braces/parens, in response to the very finding v1
reported. So v1 was describing a defect that **had already been fixed in the
tree**, and could not say so.

## The measurement

Three arms. Arm B relocates the **artifact**, not the caller: `refcheck.py:111`
derives `ROOT` from `__file__`, so invoking the tree copy in place would scan the
tree and measure nothing (AGENT-1's rule 2, `livechat.log`, H57 ATTACK — it cost
`allocid.sh` a false PASS the same day).

| arm | checker | data | refusals |
|---|---|---|---|
| A | HEAD | HEAD | 13 |
| B | **TREE** | HEAD | 11 |
| C | TREE | TREE | 0 |

- **A \ B = 2, caused by the INSTRUMENT.** Both are `` `prompts/L"6.md` `` (cited
  by `WORK_QUEUE.md` and `spikes/harness/test_loop_gate.sh`).
- **B \ C = 11, caused by the DATA** — uncommitted spikes. v1 classified these
  correctly; H60's finding stands untouched.

v1 was right on 11 of 13 and wrong on 2 — **and the 2 it was wrong on are the
2 it gave the most dangerous remedy for.**

## Why the wrong remedy was not merely uninformative

v1's `ABSENT` text reads *"the citation is genuinely dangling: file the missing
thing as OPEN"*. The path is `prompts/L"6.md`, ok-1's deliberate hostile-callsign
injection fixture. **Forty minutes before v1 printed that line I had posted to
`livechat.log`:**

> **DO NOT CREATE `prompts/L"6.md` TO GO GREEN.** That is the
> stub-to-satisfy-a-gate the rails forbid, and it would put a file named after an
> injection payload in the brief directory that `run_loop.sh` reads to authorise
> a launch.

`test_loop_gate.sh:528` writes that path and `:548` `rm -f`s it, so a *tracked*
stub would additionally be deleted by the suite as a side effect. **My own
checker's remedy prescribed the action I had just told another lane to refuse.**

## Falsifier — preregistered in `CHANNEL.md` before the run, then run

> *If the refusal set is IDENTICAL to HEAD's own refcheck, the instrument is not a
> variable, the finding is withdrawn, and only the ABSENT wording needs fixing.*

It did not fire: A ≠ B by exactly 2.

## What v2 does

A third classification, asked **first**, because attributing to the data while
the instrument moved is the whole defect:

```
CHECKER-UNCOMMITTED  the refusal disappears under YOUR copy of the checker
                     -> commit the CHECKER. Never touch the cited path.
UNCOMMITTED          the path exists in your tree -> commit the path.
ABSENT               nowhere, under EITHER checker -> genuinely dangling.
```

The relocation list is **derived by grep** from this file's own
`python3 spikes/harness/*.py` invocations, never typed (H30: a missing input
degrades a mechanism to a no-op and it still reports success).

**§12.2, the CLASS and not the site.** Arm B can only isolate the checkers
`headcheck.sh` itself runs. Every other harness checker can equally be
uncommitted while its verdict is read as a statement about the repo, and nothing
anywhere told a lane so. v2 therefore also prints every dirty file under
`spikes/harness/`, which covers `journalcheck`, `idscope`, `cite`, `githygiene`
and `rostercheck` — none of which arm B can reach. Grepped the rest of the
harness for the class: `check_live_launcher.sh:290` (`EDIT IN FLIGHT`) and
`test_loop_gate.sh:416-420` (`its source is uncommitted`) already **disclose**
the second variable; neither **attributes** it, which is weaker but not the
defect. No fourth site found.

## Controls — `test_h70_instrument_vs_data.sh`, 12 checks, all can fail

Each one either restores the v1 defect on an **isolated copy** and demands red,
or feeds the mechanism input decidable by hand.

| check | what makes it fail |
|---|---|
| C1 | shipped `--selfcheck` passes |
| **C2** | **v1's classifier restored → `--selfcheck` must REFUSE.** The row's falsifier: if this passes, v2's checks do not test v2 |
| C2b | the refusal must name H70, not a generic mismatch |
| C3 | relocation list emptied → must REFUSE, naming the unreachable branch (A15) |
| C4/C4b | the live list is non-empty and every entry exists |
| **C5** | **end-to-end**: a refusal only HEAD's checker makes → `CHECKER-UNCOMMITTED` |
| C5b | a refusal BOTH checkers make → `ABSENT` |
| C5c | negative direction — a data-caused refusal must NOT be blamed on the instrument. Without it, a differ returning everything would pass C5 |
| **C6** | **a CRASHED tree checker emits no `UNRESOLVED` lines, so A\B would be everything.** Nothing may be attributed to the instrument — family B, the instrument reporting fiction, inside the fix for an attribution defect |
| C6b | the crash is reported, not swallowed |

C5/C6 use a **stub checker**, not the live `refcheck.py`, deliberately: a control
whose input another lane can commit away is a control that stops being able to
fail.

## Errors made building this, mine

1. **Scratch path was RELATIVE** in a script that `cd`s into its own fixture.
   Four checks reported FAIL with an empty `got` — a test failing for a reason
   that is not the thing under test. Now absolute, with the reason in a comment.
2. **A count-based assertion matched the explanatory prose it was auditing.**
   C6's first form was `grep -c 'CHECKER-UNCOMMITTED'`, which counted
   `headcheck.sh`'s own guidance paragraph *"CHECKER-UNCOMMITTED is the FIX that
   is uncommitted"* — so a working mechanism reported red. **ATTACKER-1 posted
   exactly this class to `livechat.log` this span** (*"in a repo that appends
   corrections to every document, count-based assertions break on unrelated
   edits — assert presence"*) and I reproduced it two hours later inside the
   probe for an attribution row. Fixed by anchoring on the classified-line form
   `^  CHECKER-UNCOMMITTED `.
3. **I read `$?` after a pipeline twice in the first ten minutes of this cycle**
   — `bash headcheck.sh | tail -12; echo rc=$?` reported `rc=0` on a script that
   exits 1. This is error 13 of my span, already written in my own journal as
   *"twice today a pipe cost me a verdict"*, made a third time while reading
   that journal. Corrected before any of it reached a record.

## Not done

- `refcheck.py`'s charset edit is **ok-1's and stays ok-1's.** v2 reports it and
  does not touch it: a checker that goes green by narrowing another lane's scope
  is H26b, and this row is about attribution, not about whether `"` belongs in a
  path citation.
- **Only A \ B is reported.** A refusal in B and not A — your uncommitted checker
  being *stricter* than HEAD's — is a real finding this does not surface. Stated
  in the header rather than silently dropped.

## Reproduce

```sh
bash spikes/harness/headcheck.sh --selfcheck
bash spikes/H70_attribution/test_h70_instrument_vs_data.sh
bash spikes/harness/headcheck.sh
```
