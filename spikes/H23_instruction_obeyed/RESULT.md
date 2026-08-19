# H23 — an instruction the component does not obey. Three general detectors measured and rejected; the row's own F1 shipped.

ok-1, 2026-08-19. Row `H23` in `WORK_QUEUE.md`. Class **H**.

## The correction comes first, and it is against my own journal

`HANDOFF.ok-1.md` carried H23 in its NEXT block for three cycles as *"no mechanical detector
for a rationale block naming an absent path."* **That is a different row.** A rationale block
naming an absent path is a §12.4 dangling citation and `refcheck.py` check 4 already refuses
it. The row says:

> **CLASS: an interface removed or renamed in code while a surviving site still INSTRUCTS
> callers to use it.** Distinct from a dangling citation: this points at something that
> **exists and is wrong**, and it lives where nobody looks for rules — a runtime's own output
> string, a journal's "how to stop" line.

I read my own summary of the row instead of the row, three cycles running. That is H114's
lesson at my own site, and §6 of my brief exists because of the same failure.

## Why a string test cannot do this in general — measured, not conceded

The row states the difficulty: *"the distinguishing test is not the string, since rationale
blocks legitimately name what was removed; it is whether the sentence tells a reader what to
DO."* Three candidate detectors were run over all harness files **before** anything was
written (`measurements.out`, scripts committed beside it):

| | detector | hits | verdict |
|---|---|---|---|
| **1** | any repo path inside an emitted string must exist | 32 checked, **13 "missing"** | **41% false positives.** Every one is a suite's own scratch fixture — `prompts/RACE-2.md`, `spikes/Z7_on_disk_only`, `.github/workflows/x.yml`, `kitchen/test_b.py`. H14's named failure mode: a checker everyone learns to ignore. |
| **2** | a marker named in a message must appear in non-message code | 107 markers, **30 "orphans"** | **28 are hyphenated English** (`LIVE-TREE`, `SELF-REVIEW`, `FALSE-POSITIVE`, `NON-RUNNABLE`) or document names (`MISSION_LOOP`, `WORK_QUEUE`). |
| **3** | `<interpreter> <repo path>` inside a message — an instruction **by grammar**, not by keyword | **3 sites fleet-wide, 0 unresolved** | Real, and nearly empty. A detector with a regression record and no detection record. |

**Detector 2 also caught my own instrument, which is the more useful result.** One of its
"orphans" was `.claude/hooks/loop_gate.sh:155` — `echo LOOP-FUSE > "$EXIT_MARK"`. That is a
**file write**, and my classifier counted it as a message because it begins with `echo`. The
instrument could not tell its two inputs apart. Detector 3's first draft had the same shape
from the other end: `\b(sh|bash|python3)\s+(\S+)` matched `sh will`, `sh ---` and `python -c`
out of prose, because "the next word" is not "a path".

**None of the three ships.** Recording that is the deliverable: the next lane to reach for the
obvious generalisation now has the false-positive rate instead of the intuition.

## What ships: the row's own F1, at the site the row names

> **The hook's refusal message is an instruction, and the hook must obey it.**

`test_loop_gate.sh` **v5**, six checks, 93 → 99. Both sets are read out of the **same file**,
so they cannot drift apart without the suite going red:

- the markers the message promises (`grep '"decision":"block"'`) **equal** the markers the
  accept branch matches (`case … LOOP-DONE|LOOP-HALT|LOOP-IDLE)`);
- the vocabulary is **three** signals, and an empty grep is refused by name — two empty sets
  are equal, which is exactly how a check reports green after the thing it greps for is
  renamed (the `e3b0c442…` shape, an empty capture hashed as data);
- the signal **file** the message names is the one the hook reads (`SIGFILE in ".loop_signal.…"`);
- every `.md` artifact the message instructs a lane to refresh **exists**. These are not
  backticked, so `refcheck` check 4 — which matches backticked paths only — does not see
  them. If `HANDOFF.md` were renamed, the hook would go on instructing every lane to refresh
  a file that is not there.

**The control, with its input named** (§5: a control that cannot fail is not a control). A
copy of the hook has one marker removed from its accept branch by `sed`; the vocabulary check
must go **red** on it, and it does. The mutation is itself asserted — a `sed` whose anchor is
absent returns the input unchanged, which would leave the arm testing the unmutated hook.

## Scope, said rather than implied

- **This closes one instance, not the class.** The row's four historical sites were the hook's
  refusal message (this one), two in `HANDOFF.md`, and §13.1's hook path. The three prose
  sites are **not** covered by anything here, and the measurements above are the argument that
  they are not cheaply coverable — not a claim that they are gone.
- **The check is not wired into `pre-commit`.** `test_loop_gate.sh` is run by hand; wiring it
  in is `H29`, which is gated on H17's §10 dispute and must not be settled permissively by
  being done in passing.
- **Detector 3 is not shipped even though it is sound**, because 3 sites and 0 finds is a
  surface that does not justify a gate. It is committed as a script so the number can be
  re-measured when the harness grows, rather than re-argued.
