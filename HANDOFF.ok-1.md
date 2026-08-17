# HANDOFF — ok-1 (harness lane)

Write-ahead journal, single writer (H10). Refreshed at the end of every cycle
(§6). A crash must lose at most one cycle.

Started 2026-08-17 ~13:27. Lane exists by accident: ATOM-3 probed `run_loop.sh`
with `ok-1` as the *valid* control while testing hostile-callsign refusal, the
launcher launched, and killing the `claude` child did not kill the detached
wrapper (H31), which respawned it. `prompts/ok-1.md` carries the full account and
is written by another lane, not by me.

## Cycle 1 — DONE. H13, H33, and a correction to H29.

**H13 — `loop_gate.sh` v7, the runaway fuse counts under concurrency.**
The row's defect was in the SUITE, not the hook: `test_loop_gate.sh` check 11 was
a `KNOWN` line, not a check — it printed the undercount and passed either way, so
the suite's exit code could not tell a fixed fuse from a broken one (A28 in a test
file). Hook half locks the increment with `mkdir`, fail-open after ~1 s.
Append-and-count, the row's other suggestion, is the wrong one: it changes the
file format and breaks checks 6, 7 and 12, each encoding a defect that shipped.
Measured before: 12/13/14 of 20 across three runs, 28 of 60.
Falsifier: `bash spikes/harness/test_h13_falsify.sh` — broken copy FAIL, control
PASS.

**H33 — `refcheck.py` v4, a template path is not a citation.** Check 4 skipped
`$` only as a leading character. **This was a live fleet-stop**: `pre-commit.hook`
gates refcheck, so three correct citations of `prompts/$CALLSIGN.md` refused every
lane's commits at rc=1. Found by tripping it — I wrote the third one.

**H29 — CORRECTED, against my own justification.** Its stated blocker (H13's race
makes the suite unsafe under three lanes) is false: the suite `mktemp -d`s,
rewrites the hook's pinned `ROOT` with an anchor assertion, and runs launcher
copies from there. Three concurrent runs: 44/44 each, rc=0 each, no
`.loop_blocks.*` at the repo root. What stands instead: `/tmp` writes decide
H17's undecided §10 rail by default, and both launcher checks run `run_loop.sh`
with `KF_DETACHED` unset so the assertion races a detached child, in the
direction where the PASSING answer is the free one.

**Also mine, and reported as a defect rather than a result:** my first hook copy
did not isolate `ROOT`, so 60 fires wrote to the live repo root and landed on 28.
`.loop_blocks.L9` removed.

**H19 — evidence row added, no fix proposed.** Its gate refuses a commit carrying
another lane's PER-LANE files; a shared harness SOURCE file is not on that list.
Both halves of this cycle were swept: the `test_loop_gate.sh` check-11 edit into
`15ee371` (`Atom: AGENT-1`), and the `livechat.log` / `DECISIONS.log` /
`WORK_QUEUE.md` record into `829d57b` (`Atom: AGENT-2`). Both commits passed the
gate correctly by its own contract. The work is in history; the attribution is
not. Commits of mine: `2c9d277` (code), `a62248c` (correction + evidence rows).

## Held claims
- H13 DONE, H33 DONE, H29 corrected-in-place and still OPEN. All three have their
  evidence in `WORK_QUEUE.md` rows, `CHANNEL.md` DONE lines, and `livechat.log`.
- No claim here rests on a number I did not run this cycle.

## Open against this lane
- **`prompts/ok-1.md` has two writers.** I wrote it to stop `run_loop.sh` v6
  defect 8 from refusing this lane at its next relaunch; another lane rewrote it
  wholesale minutes later with a better-informed account. Not contested — their
  version is the one to read. The one measurement of mine it dropped (the
  three-way callsign shape disagreement) was moved to `WORK_QUEUE.md` under H8,
  where the class lives, rather than re-added to a file I am not the only writer
  of.
- **This lane's callsign is lowercase and only commits because
  `commit-msg.hook` upper-cases the value before checking it.** Sign `Atom: ok-1`
  consistently; the gate will not catch a case mix.

## Cycle 2 — DONE. H38: the harness has two lane rosters.

`spikes/harness/rostercheck.py` v1, refusing. `roster.txt` names four lanes and
excludes `ok-1`; `spikes/harness/bringup.sh:35` hard-codes a fifth list that adds
`ok-1` and drops the elder `ATOM-3`, and launches each through the launcher that
refuses `ok-1`. Falsifier stated first and run: `grep -n roster
spikes/harness/bringup.sh` is empty, so it stands.

**I am the lane in dispute and did not decide it.** The checker reports the
divergence and refuses to pick a side; the ask, with the evidence both ways, is
in `HUMAN_NEEDED.md`. Not wired into pre-commit while red (H14).

**Standing hazard for whoever reads this next:** this lane is OFF-ROSTER. The
running launcher (pid 6291, 13:26:33) predates the roster gate, so `ok-1` is
unaffected until it relaunches — at which point `run_loop.sh:117` refuses it and
the lane ends with no alarm. `.heartbeat.ok-1` is already gone. If this journal
stops, that is the reason, and the work to date is in commits `2c9d277`,
`a62248c`, `d6b390c` and the H38 commit.

## Cycle 3 — IN FLIGHT. H39 (found by tripping it), H20 blocked behind it.

**H39 — the falsification driver was dead and nothing reported it.**
`python3 spikes/H7_harness_attack/falsify.py` could not build a scratch tree at
all: `build()` runs `install_hooks.sh` with `check=True`, that installer's loop
is `for h in commit-msg pre-commit`, and falsify's `TREE` restated the list with
only `commit-msg.hook`. So it raised `CalledProcessError` before one falsifier
ran, and had done since H15 landed `pre-commit.hook`. **This is the instrument
that answers H7's question — is a red run reachable — and H22's 35-of-43
coverage number was measured with it.** That number is now unreproducible until
this is fixed; I am NOT claiming it was wrong, it was measured before the break
and I have not re-measured it.

Same class as H38 one hour later: two independently-maintained lists of the same
set with nothing comparing them. Fixed by deleting the second list —
`installed_hooks()` parses the installer's own loop and REFUSES rather than
falling back, because a silent fallback is how it would go quiet again.
`TREE` verified to derive both hooks. **Full driver pass not yet observed** —
running when this checkpoint was written.

**H20 is CLAIMED and NOT started.** Its falsifier needs the driver, so it is
blocked behind H39. Two probe attempts recorded rather than hidden: the first
hand-rolled its own scratch tree and reported "neither" for all four arms
INCLUDING A+B, i.e. it could not show it had reached the checks — A29, no
evidence rather than a negative result. The second reused `falsify.build()` and
is what surfaced H39. The two checks H20 names still exist, at
`test_loop_gate.sh:155` and `:162`.

**A count I got wrong and corrected inside the cycle:** `pgrep -f run_loop.sh`
read 395 while four suite arms were in flight; the steady-state measurement is
15 — five lanes at three processes each (supervisor, turn, watchdog). Not a
fork storm. Recorded because a transient taken as a level is E-family, and I
nearly acted on it.

## Cycle 4 — ATTACK (§2). Target: my own instrument. It lost.

`spikes/H38_attack/attack.py`, three falsifiers stated first, all three fired
against a live control: `rostercheck.py` v1 matched only a double-quoted scalar,
so a bash array, a python list and a single-quoted scalar were invisible. v2
catches all four forms; the CALLSIGN shape guard is unchanged, so the syntax
loosened and the test for what counts as a lane did not.

**The finding worth more than the fix: my first repair fixed two of three and
presented as complete.** Only re-running the attack found the python-list case
still blind. A partial repair reads exactly like a whole one.

**H38's live divergence is CLOSED by another lane** — `bringup.sh` now agrees
with `roster.txt`, scan green. That expired my own stated reason for keeping the
checker out of the pre-commit set; corrected in place with a changelog line, and
the remaining reason (a shared gate rewritten within the hour) offered to its
owner in livechat rather than acted on.

Commits: `90e3b68` (attack + v2), `bc6cbfa` (H39).

**Still open from cycle 3:** the repaired `falsify.py` run has not returned after
~20 min. Not hung — python block-buffers stdout when piped, so `| tail` shows
nothing until exit. **No verdict claimed for H39 beyond "it builds and runs";
H20 stays claimed and unstarted behind it.**

## Cycle 5 — DONE. H45: allocation is a race, and the correct grep loses.

`spikes/harness/allocid.sh`. `refcheck.py` check 5 enforces id uniqueness in the
WORK_QUEUE **table** — where an id lands *after* the work — while allocation
happens in `CHANNEL.md` minutes earlier and is not atomic. Measured on CHANNEL
claims: `H20 H30 H38` collided, and **in every case both lanes ran a correct
grep**, minutes apart, with neither row published at the other's read. TOCTOU,
so grepping more files cannot fix it — which is what was tried all five times.

`set -o noclobber` (AGENT-2's own H8 primitive): 20 concurrent allocations → 20
distinct ids; **negative control**, the count-then-write method it replaces
driven identically → **7 distinct of 20**. Without that control the positive
result says only that this box serialises.

**The sixth collision happened while I was committing the fix**: a duplicate
`H42` (ATTACKER-1's liveness row vs AGENT-1's provenance row) took
`pre-commit.hook` to rc=1 and refused **every lane's commits**, my own H45 row
included. I did not renumber either — H18 records that a renumber by a non-owner
turns an ambiguous citation into a confidently wrong one. Reported to AGENT-1
over the bus; another lane resolved it; gate green again.

Commit: `H45` + `.ids/`. Not wired into any gate, and nothing forces a lane to
use it — it is cheaper than grepping and that is its only enforcement.

## Cross-lane, this session
- Corrected kingfisher-60's credit: I did **not** build `roster.txt` or
  `bringup.sh` — both are AGENT-1's, zero commits of mine touch them. The wrong
  credit turned out to live only in cross-session prose; `MISSIONS.md` had it
  right. The message decayed, the artifact did not.
- Corrected their correction: my work is **H38**, not H40. H40 is ATTACKER-1's
  identity-check row, renumbered under H18's first-come rule. Had they "fixed"
  it, the file would have credited me with someone else's finding.
- `PEERS.md`: the session-name column cannot be self-filled — `ListAgents`
  excludes self, so the name is assigned and visible only to the receiver. H27's
  shape one artifact later. Both other lanes reached the same conclusion.

## Cycle 5 — H41 DONE, H20 to a verdict, and two of my own claims corrected

**H41 — `refcheck.py` v5. The row named one of two defects and the one it named
catches nothing alone.** Measured on all 45 harness files BEFORE writing the
repair: fence half 0 flagged, dot-slash half 2, both 4, zero false positives at
either half, all four the same real absent file. The row's own cited live
instance survives the fence fix, because check 4 skips any token whose first path
segment is not a top-level entry and the first segment of a dot-slash token is
`.`. Falsifier stated first and run: `spikes/H41_fenced_paths/falsify.py` reverts
each of v5's three changes on an isolated copy — 3 of 3 caught, control green.
Commit `1f5f6ab`.

**Against me, three times in one row.** v5's first run flagged its OWN source
three times: a rationale block naming an absent path is indistinguishable from a
broken citation of it — the trap `selfcheck()` builds every fixture from string
parts to avoid, in a comment I had read minutes earlier. It then caught me twice
more, in the queue row and in the header I wrote to describe the first three.

**Scope narrowed, cost filed as H54 rather than buried.** Per-lane journals left
refcheck's PATH check: 3 of the 4 red sites were lanes REPORTING this defect, one
inside a journal H10 forbids me to write to, so the block's only remedy was
forbidden to every lane that could trip it. Given up: a journal claiming evidence
at a path that does not exist is now unchecked.

**The live instance was closed by another lane mid-cycle** — `peers.sh` created
14:16. So the green tree is not evidence for v5 and I do not cite it as such; the
selfcheck is the evidence.

**H20 — HALF THE ROW IS WRONG, measured.** Probe `spikes/H20_multi_revert/probe.py`,
four falsifiers stated first, all four passed. `lane signal untouched` reds only
under the PAIR (LANE default + glob read) — list support justified. `writes no
'unknown' marker` stays green even under the pair: its section opens
`rm -f .loop_signal*` and the hook writes an exit marker only after consuming a
signal, so no combination of hook defects could redden it. **Not a two-revert
check — a check whose own section deletes its precondition (A15).**

**And the obvious fix for that half is wrong, which the probe also measured.**
Folding the plant into section 9 lets the hook exit legally under the LANE-default
defect: that defect reddens 6 checks, and 2 with the plant folded in. So the plant
went into a NEW section 9b. A repair that raises one check's coverage by disarming
five reports better and tests less.

**My own probe v1 named the wrong partner defect** — F5's bare-signal form, which
`.loop_signal.L1` matches under no hook at all, so the A+B arm would have reported
"row does not stand" over a defect of mine. Found by reading the section the check
lives in rather than the check's name.

**Corrections to my own cycle-4 notes.** (1) `falsify.py` was not hung and does
not block on buffering — the suite is ~3 min per run and a full pass is 25 trees,
over an hour. (2) The run I left in flight was UNOBSERVABLE: its stdout went to a
pipe whose reader died with the session, so its result could never have been read.
Killed and re-run to a file. `falsify.py` now takes an id filter so one falsifier
can be exercised without an hour's wait.

**Cycle-2 standing hazard is CLOSED.** `roster.txt` now carries `ok-1`, sanctioned
by the operator on a checkable record, and `rostercheck.py` is green over
`bringup.sh` and `send.sh`. This lane will not be refused at its next relaunch.

## NEXT 3
1. **H29** — the decidable half: set `KF_DETACHED=1` in the two launcher checks
   so the assertion observes the process it is asserting about (A29). The `/tmp`
   half is H17 and is not agent-decidable — §10 is an absolute rail and an agent
   narrowing a rail it operates under is A22.
2. **H54** — the cost H41 paid. A journal's evidence-path citations need a check
   that reports to the journal's OWN lane, not to the shared commit gate.
3. **H23** — a stale instruction at a surviving call site, no mechanical
   detector. Read it before taking it: the row states the distinguishing test is
   whether the sentence tells a reader what to DO, which may not be mechanisable
   at all (§12.12). If it is not, the honest verdict is to say so in the row.

**Cycle 6 is not an ATTACK cycle; cycle 8 is, and §12.8 makes it the loop's turn
— at least every fourth ATTACK targets the harness rather than a spike.**
