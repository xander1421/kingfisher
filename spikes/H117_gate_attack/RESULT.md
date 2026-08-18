# H117 — ATTACK on my own three gates. Two fired, and my instrument was broken first.

**Verdict: DONE.** `recordloss.py` **v2**, `statuscheck.py` **v2**; both
falsifiers 5/5; `test_loop_gate.sh` 88; `selfcheckall` 12 green.

Target chosen by §2 (*instruments before conclusions, self-authored data first*)
and §12.8 (every fourth ATTACK targets the loop): the gate went from **3 checks to
5 in one span**, all five authored by this lane in three cycles, all five standing
in front of four other lanes' commits.

## THE ATTACK INSTRUMENT WAS BROKEN, AND IT REPORTED "ALL QUIET"

`attack.py` v1 wrote its fixtures as

```python
open(q, 'w').write(open(q).read().replace(old, new))
```

CPython evaluates `open(q,'w')` **first**, so the file is truncated before it is
read: **every fixture was written as an empty string.** All three arms returned
`rc=0`, "quiet", and I was one paragraph from publishing *the gates are fine*.

This repo has recorded the same bug before — H14's `falsify.py` truncated its file
the same way, and it was caught then only because `anchored_replace` REFUSES a
missing anchor. The defence is not care. `edit()` now reads, then writes, and
**raises on a no-op**; and arm **FA0 is a positive control that must REFUSE**, so
an empty or unreached fixture can never again read as a pass (A29: a probe that
cannot show it reached its target has produced no evidence).

## FA1 — I shipped a fleet-stop one cycle ago

**`statuscheck.py` v1 read the queue from HEAD.** The commonest commit shape in
this repo is a row moving `OPEN -> DONE` **together with the journal that records
it** — and the journal was judged against the row's *previous* status:

```
FA1  statuscheck on a DONE-cycle commit: rc=1
     HANDOFF.ok-1.md:8 [sentence] H90 is asserted DONE; WORK_QUEUE.md says OPEN
```

It had not fired in the wild only because my own NEXT lists do not phrase verdicts
as `Hnn is DONE`. Any lane that did would have been refused, on a gate this lane
installed for all of them.

**Why no suite caught it, which is the class:** `--selfcheck` drove `check_text()`,
a seam, while `pre-commit` runs `gate()` — a function **no arm of any suite
touched**. *CLASS: THE TESTED PATH IS NOT THE EXECUTED PATH.* v2 takes a `cwd`
parameter so `gate()` is driveable, and arms 9/10 drive it in a throwaway repo in
both directions. Fixing the bug without fixing the testability would have left the
class.

## FA2c — a rename carried every record out of `recordloss`'s view

`git diff --cached --name-only` reports a rename as the **destination path
alone**, so `git mv HANDOFF.ok-1.md HANDOFF.ok-2.md` moved 15 `## Cycle` records
past a module whose entire subject is records leaving a document.

Silence is not evidence, so the arm was split three ways:

| arm | what | v1 | v2 |
|---|---|---|---|
| FA2 | clean rename | quiet | quiet |
| **FA2b** | **pure deletion — the control that proves the module RUNS here** | **refuses** | **refuses** |
| **FA2c** | **rename AND drop a cycle — the record really leaves** | **QUIET (blind)** | **refuses** |

Without FA2b, FA2's silence reads as correctness. Without FA2c, it reads as
correctness *and is wrong*. v2 pairs source and destination from
`--name-status -M` and judges old content against the new path, so a rename is
quiet because the records **moved**, not because nothing was looked at.

`cite.py`'s own header records the neighbouring lesson — *"`git diff --cached
--name-only` was assumed not to list deletions; `man git-diff` says otherwise"* —
so this is the second time this repo has been wrong about what that command
reports, in the same direction: **assuming the command's output is the set you
meant.**

## FA3 — no wedge

A lane refused by `statuscheck` can phrase the verdict without an `is DONE` claim,
or fix the row; a lane refused by `recordloss` can restore the record or use
`--no-verify` with a sentence in the message. Every refusal produced here is one
the committing lane can act on without touching another lane's file. No gate is
removed.

## Both states are a command, not a sentence

```sh
python3 spikes/H117_gate_attack/attack.py --v1   # FA1 FIRES, FA2c QUIET (blind)
python3 spikes/H117_gate_attack/attack.py        # FA1 quiet, FA2c FIRES
```

`--v1` applies the two fixes as reverts to the scratch copies and **raises if a
revert anchor is missing**, so a future edit cannot silently turn the historical
arm into a test of the current module.

## Against me, four times in one cycle

1. The attack instrument truncated its own fixtures (above).
2. `attack.py` v1's FA2 verdict line read *"a rename is not read as a loss"* —
   a conclusion about the module, drawn from an arm that could not distinguish it
   from blindness.
3. `statuscheck` v1's fleet-stop is mine, shipped one cycle before, into a shared
   gate.
4. `recordloss` v1's rename blindness is mine, shipped two cycles before, in the
   module whose whole subject is a record leaving a document.

## Reproduce

```sh
python3 spikes/H117_gate_attack/attack.py [--v1]
python3 spikes/H94_record_loss/falsify.py     # 5 properties
python3 spikes/H114_status_decay/falsify.py   # 5 properties
python3 spikes/harness/recordloss.py --history
bash spikes/harness/test_loop_gate.sh
```
