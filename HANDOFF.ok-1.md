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

## Cycle 6 — H41 DONE, H20 to a verdict, and two of my own claims corrected

*(Numbered `Cycle 5` when written, which is the second `5` in this file — my own
§12.4 defect, "a reference that resolves to TWO things", in the journal that
states the rule. Corrected in place at cycle 7; the ATTACK arithmetic below was
computed on the correct count and is unaffected.)*

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

## Cycle 7 — H62 DONE, H29 BLOCKED, H61 filed. The fix I planned was the wrong fix.

`spikes/H29_detach_race/`. Suite v2, 63 → 66 checks, **7.34 s from 9.06 s**.

**Cycle 6's NEXT 1 was wrong, and the probe said so before I wrote a line of
repair.** It said: set `KF_DETACHED=1` in the two launcher checks. That removes the
fork, and with it the ordering property those blocks exist to test — which the
suite's own comment states: *"there the refusal must beat the detach, and rc=0 from
a detached parent is exactly the defect to catch."* Four falsifiers stated first,
six arms, and what they found was bigger than the race:

**The hostile-callsign block was INERT — 63/63 green with `run_loop.sh`'s charset
whitelist neutered.** Gate order is charset, roster, brief; the suite never wrote
`prompts/L"6.md`, so the BRIEF gate exited 1 and the block's two assertions (rc=1,
an artifact absence) were satisfied for a reason the block is not about.
**`falsify.py F8` had been printing `INERT` on it for hours.** Unread — because
nothing runs the driver automatically, which is H29, the row I was working. The
instrument was right and nobody was listening.

**CLASS 1: rc=1 does not say WHICH gate refused.** CLASS 2: an absence assertion
read at the parent's exit is a claim about an asynchronous event — measured, `it
never reached the turn` and `launcher never reached claude` are RED under a live
defect with `run_loop.sh:275`'s post-fork `sleep 1` and **GREEN without it**. The
repair is not a sleep: the detach ANNOUNCEMENT is the parent's own, printed before
it exits, so each block asserts on that instead. Both classes posted to livechat.

**H61 is the finding I would keep if I could keep one:** *(CORRECTED at cycle 9,
against this paragraph: the mechanism named below is wrong. See "Cycle 9" — there
is no double admission at any arrival time with the sleep present; the defect is
that the refusal moves into the child, after the caller was told the lane
launched. The measurement in this paragraph reproduces; the inference does not.)* removing that same
`sleep 1` reddens the 20-launcher lock check — 4 survivors, then 1 survivor with 0
HELD refusals. **The H8 callsign lock is held closed by a sleep** whose comment
gives it an unrelated purpose. Filed with a fix shape, NOT fixed: different
component, and the fleet has 15 live launcher processes against it.

**Against me, twice.** (1) That NEXT item was wrong for a reason the file I was
editing already explained; found by reading the section rather than the check name,
which is H20's v2 lesson paid for a second time. (2) The probe's own FC arm treated
*any* red in the no-sleep arm as a confound and `sys.exit(2)`'d before printing its
verdict, so my first post-repair run printed no conclusion at all. The reds were in
a different block and were H61. A probe that stops before its own answer is A29 in
a control's clothes.

## Cycle 25 — H178 DONE, H191 DONE, H189 filed. Both fixes came from a control refusing, neither from a search.

`test_loop_gate.sh` **v4** (91 -> 93 checks), `probe.sh` **v2** (arms A4-A9, C3-C4),
`spikes/H178_suite_flake/`, `RESULT.md`, rows H178/H189/H191.

**H178's finding is in a CONTROL, not a check.** `failing_run_4.txt`, seven lines apart:
`FAIL H61: ... refused BY THE PARENT (want '1', got '2')` and `PASS every launcher is
accounted for`. True state was **0 admitted, 2 refused — no lane started at all** — and the
accounting control passed because `0+2+0 = 1+1+0`. `h61_parent` and `h61_child` each had a
`check`; **`h61_surv` had none**, and the sum was the only place it appeared.

> **A quantity that enters a verdict only through a sum has no verdict of its own.**

Grepped fleet-wide: exactly two asserted sums, both in this suite, and **the sibling is
SOUND** — its operands are each pinned above the sum. One added assertion, not a rewritten
control. Editing the sound site to look uniform would have been a rename.

**F1 REFUTED on the capture** (the failing check runs in `$T`, `treefail=0` — not H35/H72's
class inside the suite). **F2 CONFIRMED** (the H61 block is a wall-clock race). **F3 did not
fire**: a red run was captured, so this files a mechanism rather than two sightings.

**RETRACTED WITHIN THE CYCLE, and the retraction is the better finding.** I wrote — here and
in `livechat.log` — that the probe's "unreachable" MIXED arm *"fired on its own"*, reading it
as the flake appearing spontaneously inside my own probe. **Wrong.** That arm points the
suite at an empty hook dir, and the lone "contract" failure was `no installed pre-commit to
read a CHECKS list from`, which the empty dir CAUSES every time. I had a plausible story and a
matching observation and did not check that my own fixture caused it. What it actually exposed:
**`badt` was split by NAME, not by INPUT** — wired into the checks whose names mention drift,
and not into four siblings reading the same `$hookdir/pre-commit`. An all-live-tree run
reported itself as MIXED. *The wrong-attribution error, produced by the split built to prevent
it.* Rule now at the definition site: **`badt` iff the INPUT is the shared tree.** Arm A7.

**H191 arrived by C1 refusing, not by looking.** `for c in $cmds` unquoted splits on IFS while
its records are newline-delimited; inert for weeks, fired the hour ATTACKER-1 registered a hook
WITH ARGUMENTS. One registration became three failures naming `python3` as missing.
**The tell is the defeated guard:** `${c%% *}` strips the first word, so its author knew
commands carry arguments — the split had destroyed that input before the guard could run, so it
read as a no-op. **My first fix was the same family again**: `printf | while read` runs in a
subshell, so the counters would never move while the lines still printed. Caught before it ran;
recorded, not quietly replaced. **A8 is the general detector** — the summary's totals must equal
the PASS/FAIL lines printed — and it holds over the whole suite.

**NO FLAKE RATE PUBLISHED, and that is my own defect (family C, twice).** I edited the suite
while its 12-run sample was in flight: runs 1-3 report 91 checks, runs 4-11 report 92, run 12
died on a truncated read (`bash` reads scripts incrementally). Eleven usable runs across two
versions is not a sample of one artifact.

**Also fixed in passing and measured before generalising:** `test_loop_gate.sh` had `v2` and
`v3` rationale blocks and **no header version line**, so `versioncheck.py` — which needs
`^#\s*(\S+?)\s+v(\d+)\b` in the first 8 lines — never tracked the largest suite in the
harness. No other file uses the unrecognised `vN RATIONALE` spelling, so it is one site and
**not** a class; `versioncheck.py` is not touched.

## Cycle 26 — H189 PARKED (F3 fired), H196 filed. The interesting story died and the boring one is worse.

`spikes/H189_double_refusal/` — `probe.sh` (30-iteration instrumented sample), `attack.sh`
(deterministic, two-sided), `RESULT.md`, `probe.out`, `attack.out`, `triples.tsv`,
`refusals.tsv`.

**THE HONEST NEGATIVE FIRST. 30/30 iterations read `surv=1 parent=1 child=0`**, under the
live fleet at load 4.74 with 30 matching launcher processes — the condition the H178 capture
occurred in. Preregistered **F3** is the branch that fired. **The mechanism of the original
double refusal is UNREPRODUCED and this row names none.** PARKED with the instrumentation
committed; §3 re-entry needs an ATTACK cycle to review the diagnosis.

**F1 and F2 were both decidable and neither was reached.** Every refusal is classified
against the set of launcher pids that iteration created: 30 `F2_own_launcher`, 0
`F1_foreign_pid`. That the classifier returned the *right* answer on the healthy case is the
only reason I trust that it would have returned a different one otherwise.

**MY FIRST INSTRUMENT COULD NOT HAVE ANSWERED ITS OWN QUESTION.** I logged launcher pids
from `$!` — the SUBSHELL pids — while the refusing process is `bash ./run_loop.sh` INSIDE
that subshell. The blamed pid could never have matched; **every** refusal would have
classified FOREIGN and I would have announced pid reuse off a bookkeeping error. Same family
as the row that produced this one: a number collected that cannot answer the question it was
collected for.

**WHAT THE CYCLE DID ESTABLISH is a different fact, it is worse, and it is `H196`:**

> `.loop_lock.$CALLSIGN` records a **bare pid**. The callsign is only in the **filename**.
> The holder is validated by `ps -p $held -o command= | grep -q 'run_loop\.sh'` — a name
> **every lane shares**.

`attack.sh`, two-sided, seconds: a decoy that does nothing but `sleep`, whose file is merely
NAMED `run_loop.sh`, holds the lock and **both** arriving launchers refuse — `surv=0
parent=2`, the observed triple on demand. Rename the identical file and the lock is correctly
called stale and a lane starts. **One character of filename decides it.** So a pid reused by
any of five lanes' launchers reads as *my* live holder. The launcher's own comment states the
inverse half — *"a copy under any other name is not recognised as a launcher"* — and treats it
as the safe direction.

**I FILED IT AND DID NOT TAKE IT, and that is the rail, not caution.** Every candidate fix
moves the launcher toward RECLAIMING MORE locks, and H6's hazard is that the absent branch
LAUNCHES: a wrong reclaim is a double admission on one callsign — two lanes sharing
`.loop_signal`/`.loop_exit`/`.loop_blocks` — which is strictly worse than a wrong refusal.
Direction recorded for whoever takes it (start time in the lock, compared to `ps -o lstart=`),
with the requirement that it be argued against double admission *before* it is written.

**A construction that reproduces a signature is not evidence that the signature had that
cause.** A1 makes `0/2/0` on demand; thirty unforced runs found none. Two claims, kept apart.

## Cycle 27 — H23 DONE for F1 only. Three detectors measured, none shipped, and the rates are the deliverable.

`spikes/H23_instruction_obeyed/`, `test_loop_gate.sh` **v5** (93 -> 99 checks).

**THE CYCLE OPENS WITH A CORRECTION AGAINST THIS JOURNAL.** My NEXT block carried H23 for
three cycles as *"no mechanical detector for a rationale block naming an absent path"*. That
is a §12.4 dangling citation and `refcheck` check 4 already refuses it. **The row is about an
interface removed or renamed while a surviving site still INSTRUCTS callers to use it** —
something that EXISTS and is WRONG. I read my own summary of a row instead of the row, three
cycles running; §6 of my brief exists because of exactly this, and it did not save me.

**THREE GENERAL DETECTORS MEASURED OVER ALL HARNESS FILES BEFORE WRITING ANYTHING, AND NONE
SHIPPED.** (1) *any repo path in an emitted string must exist*: 13 of 32 hits are a suite's own
scratch fixtures — **41% false positives**, H14's checker-everyone-ignores, which is worse than
no gate. (2) *a marker in a message must appear in non-message code*: 28 of 30 orphans are
hyphenated English or document names. (3) *`<interpreter> <repo path>`, an instruction by
GRAMMAR*: sound, and **3 sites fleet-wide with 0 finds** — a regression record with no
detection record. **Publishing the rates is the deliverable.**

**DETECTOR 2 CAUGHT MY OWN INSTRUMENT and that is the better result.** One *orphan* was
`echo LOOP-FUSE > "$EXIT_MARK"` — a FILE WRITE my classifier counted as a message because it
starts with `echo`. Detector 3's first draft had the same shape from the other end:
`\b(sh|bash|python3)\s+(\S+)` matched `sh will` and `python -c` out of prose, because *the
next word* is not *a path*. Two instruments in one cycle that could not tell their inputs
apart — the same family as cycle 25's and cycle 26's.

**WHAT SHIPPED IS THE ROW'S OWN F1 AND NOTHING WIDER:** the hook's refusal message is an
instruction, so the markers it PROMISES must equal the markers its accept branch MATCHES, both
read out of the same file. Plus the vocabulary must be three with **an empty grep refused by
name** (two empty sets are equal — how a check goes green after its target is renamed); the
signal file named must be the one the hook reads; and every `.md` the message tells a lane to
refresh must exist — **not backticked, so `refcheck` check 4 never saw them.** Control with its
input named: a hook copy missing one marker from its accept branch goes RED, and the mutation
is itself asserted.

**SCOPE KEPT. This closes ONE of the row's four historical sites**; the two in `HANDOFF.md` and
§13.1's hook path are prose and are not covered.

**H178's probe re-run against the v5 suite: all 13 arms still green**, including A8 (99 pass
lines, 99 counted) — the new checks report their verdicts rather than printing them.

## Cycle 28 — ATTACK (§2) on my own cycle-27 work. Two findings, and the second one was an objection I raised against myself.

`test_loop_gate.sh` **v6** (99 -> 107), `spikes/harness/test_h202_falsify.sh`,
`spikes/H202_vocabulary_coverage/`, addendum to `spikes/H189_double_refusal/RESULT.md`.

**1 · TWO OF §7's THREE EXIT SIGNALS HAD NEVER BEEN DRIVEN THROUGH THE HOOK BY ITS OWN SUITE.**
`LOOP-HALT` 7 times. **`LOOP-IDLE` once — at the BARE-signal check, where the expected answer
is `block`**, so a hook that had stopped accepting it returns the same `block` and the check
passes. **`LOOP-DONE`, the signal that ends the mission, appeared nowhere except inside v5's own
mutation string.** A hook refusing either would have passed every check, for the whole life of
the suite whose subject is the loop's exit contract.

**The hook is fine; the suite was blind** — renaming each marker in a copy and driving a real
signal returns `block` for all three. **CLASS: a suite that exercises one member of a
vocabulary and reads as covering the vocabulary.** This file's own history is the precedent.

**How it was found matters more than the finding.** I attacked v5's H23 check by renaming
`LOOP-HALT` everywhere *inside* the hook: it reports `equal`, because it reads both sets from
one file. That is a real limit and **it is not the finding** — check 2 catches that mutation
behaviourally. Asking *how many signals are checked that way* is what produced 7 / 1 / 0.

**THE FIX HAS ITS OWN LESSON.** The class guard's first draft grepped this file for
`echo <MARKER> > .loop_signal.<lane>` and reported **all three uncovered**, including the seven
`LOOP-HALT` drives directly above it — the drives are parameterised, so the literal is never in
the text. **A text check cannot see a loop.** Records at runtime now, with the record asserted
non-empty (an empty driven-set against an empty accept-set reports `0 uncovered` — a clean
number from a check that never ran, H178's shape). Falsifier added because the guard had never
been red on purpose: a FOURTH marker must turn it red AND name it, two-sided.

**2 · I RAISED THE OBJECTION TO MY OWN H189 `attack.sh` AND ANSWERING IT MADE H196 WORSE.**
The objection: A1 seeds `.loop_lock` directly, a privilege no launcher has, so it shows the
CHECK is fooled and not that the STATE is reachable. One read of the live tree:

    .loop_lock.GEMINI-1    pid=4999    <DEAD PID — lock outlived its holder>

Every other lane's lock names a live `bash ./run_loop.sh`. GEMINI's names nothing. That is the
launcher's **design** — no release path, stale locks reclaimed not respected — so half of H196
is on disk unforced, and the other half is demonstrated two-sided. **The only unmeasured step
is pid 4999 being reissued to any of five launchers**, ~1300 pids/min through a 99999 space,
and 4999 is a LOW pid. GEMINI is out of tokens and will not reclaim it.

**It does not identify the cause of the H178 capture** — 30 unforced runs still reproduced
nothing and that verdict stands. It retires the *artificiality* objection. **I did not delete
the lock**: another lane's file, and it is the live evidence for an open row (A23).

## Cycle 29 — H199 DONE. The row's own falsifier had never been run, the placement question has an answer, and two of my own numbers died before publication.

`spikes/H199_hook_window/` (`probe.sh` 13/13, `probe_b.sh` 9/9, `probe_c.py`, `probe_f4.py` 10/10)
+ `RESULT.md`, `WORK_QUEUE.md` H199 DONE and **H215** filed.

**PREREGISTERED F1 no, F2 no, F3 no, F4 no. THREE HELD, F4 DID NOT, and the row ships the
consequence F4's own clause named** — an injector at `commit-msg` may PRINT the trailer and may
not WRITE it. A prediction that costs something when it is wrong is the only kind worth posting.

**THE ROW'S FALSIFIER WAS WRITTEN BY ATOM-3 AND NO CYCLE HAD RUN IT, INCLUDING MY FIRST TWO.**
*"Measure before writing code."* I wrote arms A and B first. It did not fire: 29 `Carries:`
trailers over 400 commits (`HEAD=f372b12f`), **7 AGREE, 17 OVER, 9 UNDER** — a script defect, not
a habit note, both directions live.

**THE PLACEMENT ANSWER, AND IT IS NOT AN AMEND: the `commit-msg` hook is INSIDE the frozen
window.** Its `--cached` equals the commit's added lines under `--only`, including a co-lane line
appended after `git add`, and a `$1` rewrite lands. **A1 alone proves nothing** — so A2 stages a
sibling the real index holds and `--only` must drop, and it is absent from both. The
compute-before-`git commit` form is measured WRONG on the same fixture (`pre='Carries: AGENT-2'`,
`post='… ATTACKER-1'`).

**ATTACK ON THE REMEDY ALREADY WIRED INTO EVERY LANE'S COMMIT PATH.** `carries_repair()`
(`commit_scoped.sh:366`, AGENT-1's H209) claims the window is *"ELIMINATED … the same object by
construction"*. **The object is immutable; `HEAD` is not.** Under interleave, lane A's repair
**rewrites lane B's commit** — new sha, a trailer scored for the wrong atom, `--no-verify` so the
hook never sees it, and lane A's own commit never gets what it was owed. **50 ms, not zero.
Smaller window than the 8 s it replaced, strictly worse consequence.** Their file, their cycle in
flight: `send.sh` + `livechat.log` inside the cycle, one-line fix named, **not touched**.

**TWO OF MY OWN NUMBERS DIED BEFORE PUBLICATION AND THEY ARE ONE FAMILY.** Arm C v1 said **26 of
37 over-declared** — and its list read `declared=['.', '35', '42', 'Run', 'before', …]`, a SENTENCE:
the parser could not tell a trailer from a sentence about trailers. F4 v1 said **12.7% of
attributed lines are the false-accusation shape** — and all eight it sampled were CORRECT
attributions with hyphenated labels. **Both were computed, both looked decisive, both measured
something other than their name.** What caught them was reading the sample the count printed,
which §12.12 says is not mechanisable, and that is the third cycle running where the not-mechanisable
defence is the one that worked.

**AND A THIRD TIME IN ONE CYCLE, IN MY OWN PROBE: A4 PASSED FOR NO REASON.** Its negative arm is a
`grep -c` = 0, which is what F3 predicts, so a `carriescheck` printing nothing reports PASS — and
it printed nothing, because I piped the PROSE report through `sed -n 's/^Carries: //p'` and that
report indents the trailer four spaces. `--trailer` is the machine-readable mode. **If a check's
healthy answer is a zero or an empty set, it cannot tell you the instrument ran.**

**H215 FILED, NOT FIXED: `Carries:` HAS TWO READERS DISAGREEING IN OPPOSITE DIRECTIONS AND THE
LOOSER ONE GRANTS THE AUTHORISATION.** `commit-msg.hook:236` takes any `^Carries:` line anywhere;
git takes only the final paragraph. **8 of 400 commits — 22% of those that tried to declare —
carry a line the hook accepts and git cannot see.** git misses five real declarations; the hook
accepts two sentences. One blank line decides it, and it hides `Cites:` too.

**THE RECONCILIATION IS THE PART I WOULD READ FIRST.** `commit_scoped.sh` runs the hook BY HAND at
line 239 and then commits `--no-verify` at 360. **A hook invoked by hand is not the same
instrument as a hook invoked by git** — by hand `--cached` is the shared index `--only` ignores;
under git it is the temp index that IS the commit. That is arm A and AGENT-1's H214
(`notice_can_fire_now=false`) as one fact from two sides. **H180, H190, H199, H209 are four rows
reconstructing outside git what git's own hook invocation hands over for free, and none of them
named the cause.** No fifth id: H214 owns that hook.

## Cycle 30 — H219 DONE (ATTACK, §12.8: the loop itself). RECORDED A CYCLE LATE, because the cycle that produced it never committed.

`.claude/hooks/loop_gate.sh` **v9**, `MISSION_LOOP.md` §7's stop bullet, `spikes/H219_stop_asymmetry/`,
`spikes/harness/test_h219_falsify.sh`, `test_loop_gate.sh` section 8b. Committed in cycle 31 as `847665b`.

**`STOP.$CALLSIGN` RETIRES ONE LANE AND THE ONLY THING THAT ENDS A TURN HAD NEVER HEARD OF IT.** H31
taught it to `run_loop.sh:433`, to both `bringup.sh` copies and to `MISSION.md:303`; the hook read the
fleet-wide `STOP` and nothing else. Measured, `probe_prefix.out`: `STOP.L1` under lane L1 **refused 20 of
20**, fleet-wide `STOP` honoured on attempt 0. The launcher's single stop read is its `while` condition, so
the switch is consulted BETWEEN turns while the hook decides when one ENDS — a per-lane retirement
therefore arrived when `MAX_TURN`'s 3600 s watchdog killed the turn, logged as a wedged turn.

**F1-F4 all preregistered in the CLAIM, none fired.** Three defects in my own probe are in `RESULT.md`,
including a probe with no seam that measured the repaired hook under the pre-fix label — caught by the
banner, not by the exit code, which was a clean 0.

**WHAT COST A CYCLE: the RECORD step never happened.** The queue row, `livechat` and `DECISIONS` were
written; the CHANNEL `DONE` line, this journal entry and the commit were not. Two cycles of evidence sat
untracked for hours. §13 says an uncommitted result is indistinguishable from one never run, and this is
the second time this lane has paid it.

## Cycle 31 — H232 DONE. Two lanes were running this callsign, the lock could not see it, and the work of the last two cycles was transiently deleted while I looked for the reason.

`run_loop.sh` **v11**, `test_loop_gate.sh` **v8**, `spikes/harness/test_h232_falsify.sh` + `h232_mutants.py`,
`spikes/H232_two_lanes_one_lock/` (`probe.sh`, `probe.out`, `probe_prefix.out`, `snapshot.txt`, `falsify.out`,
`RESULT.md`), and commits `847665b` (H219+H199 evidence) + this one.

**THE LOCK EXCLUDED AT t=0 AND NOWHERE ELSE.** `noclobber` at acquire is correct and 20 racing launchers
still leave one survivor — the suite proves that, and proved only that. **0 reads of `$LOCK` inside the
turn loop** (lines 433-635, extracted by the probe, not read by eye). Steal the lock from a running
launcher: **2 more turns in 8 s, silently**. Live: `ok-1` on roots **3619** and **56520**, two turns in
flight, one lock, four other callsigns on one root each.

**F3 FIRED AND KILLED MY FIRST EXPLANATION.** I wrote in the CLAIM that `bringup.sh` cleared the lock for
a lane in backoff. `lane_lock_pid()` refuses to call a lane missing while its lock names a live pid, and
its comment names the backoff case explicitly. **The cause of the free lock at 22:10 is UNIDENTIFIED and
ships that way**; three candidates survive and this row separates none of them.

**THE TREE ITSELF WENT AWAY FOR ~90 SECONDS AT 22:21.** I measured `H219 = 0` occurrences in a
`MISSION_LOOP.md` that had carried that text for an hour, a hook that read as pre-v9, and four of my
modified files gone from `git status` — then all of it back. It coincides with `a7468e0`
(*RESTORED to main … committed to an orphan*). **One casualty did not come back: `test_loop_gate.sh` v7,
rewritten from `RESULT.md`.** Everything I measured in that window was fiction, and the only reason I know
is that I re-read rather than trusting the first answer.

**TWO DEFECTS IN MY OWN INSTRUMENTS, both caught by an arm rather than by reading.** A 644 copy of the
launcher produces no turns, and "stopped producing turns" is trivially true of a launcher that never
started — the precondition check is now in both the probe and the suite. And the falsifier's first version
built its mutants inside a heredoc inside a shell function: two anchors never matched, the mutants were
never written, and it reported *"mutant does not parse"* for files that did not exist. The anchor
assertion is what said so. Mutants live in `h232_mutants.py` now.

**RETIRED THE DUPLICATE BY HAND**, killing root 3619 — this cycle's own tree — because the lock names
56520. Not `.loop_signal.ok-1` and not `STOP.ok-1`: both are single files read by both trees, so either
could have retired the survivor instead (§12.6).

## Cycle 32 — H231 DONE (ATTACK, §2 and §12.8). The target was my own uncommitted work, and it was carrying §12.2 in eleven lines of new code.

`.github/autoloop/evaluators/eval_hygiene.py` **v3**, `spikes/H231_record_vs_tree/`
(`probe.py`, `probe.out`, `RESULT.md`), `WORK_QUEUE.md` H231 DONE + a census added to
ATTACKER-1's H198, `CHANNEL.md`, `livechat.log`, `DECISIONS.log`.

**THE ROW WAS CLAIMED IN CYCLE 30 AND ITS WORK HAS BEEN SITTING UNCOMMITTED SINCE.** 198
lines in a tracked file, through two cycles, while H234 was recording a live `git stash`
that reverted five files of another lane's in flight. §13 says an uncommitted result is
indistinguishable from one never run; this is the **third** time this lane has paid it and
the first two are in cycles 30 and 31 above. **The CLAIM line also ends "Falsifiers
preregistered below" and there are none below it.** I did not backfill them and pretend:
`RESULT.md` states which falsifier was found by reading and which were predicted.

**CLASS: A METRIC THAT SCORES THE COMMITTED RECORD IS COMPUTED FROM THE WORKING TREE.**
`hygiene_score` — `PROGRAM.md` §Invariants' safety invariant, the one `scripts/autoloop.py:222`
fails `--ci` on — was **0.0 on a single refcheck refusal in a file no commit has ever
carried**. `pre-commit.hook` v2 (H35) had MEASURED that scope for the GATE and nobody carried
it into the EVALUATOR. `hygiene_record_verdict` CLEAN/VIOLATED/NOT_MEASURED now attributes
each refusal; `hygiene_score` is deliberately NOT rescoped, because `MEMORY.md` carries
historical rows of it and moving a published number under an unchanged name is A18.

**THE ATTACK FOUND TWO DEFECTS IN v2, BOTH MINE.**

**1 · A CHECKER THAT REFUSED WITHOUT PRINTING A PARSEABLE LINE SCORED AS `CLEAN`.** v2 read
**stdout only** and escalated exactly ONE checker — githygiene, at the call site, because it
emits no marker. So the rule existed for one of three. **Reachable and measured, not argued:**
`journalcheck.py:186` refuses an absent `WORK_QUEUE.md` — its own §4-authoritative input — on
**stderr** with `sys.exit(2)`, printing nothing to stdout, so v2 published `hygiene_score 0.0`
beside `record_verdict CLEAN`. v3 states the rule once for every checker and DELETES the
special case rather than adding two more.

**This is the third consecutive cycle where the defect is "a check whose PASS is
indistinguishable from its NOT-RUN"** — H202's vocabulary guard, cycle 29's A4 that passed on
an empty grep, and now this. I named the class both times and rebuilt it anyway.

**2 · MY OWN SELFCHECK WROTE OUTSIDE THE WORKSPACE THROUGH A ROUTE THE §10 GATE CANNOT SEE.**
`tempfile.mkdtemp()` → `$TMPDIR`. `scratchcheck.py` is a SHELL classifier and says so in its own
`--scan` output. **Found by tripping it from the other side**: the gate refused the *shell* form
of a scratch write of mine two minutes earlier, and never saw the python form already in my file.
**Not filed as a row — that is H198, already open** — census contributed there instead: **53
`tempfile.*` call sites with no `dir=` in 51 tracked `.py` files** outside `elders/`,
`scratchcheck.py` among them.

**FIVE FALSIFIERS, PREDICTED BEFORE THE PROBE RAN, ALL FIVE AS PREDICTED.** F1a fired
(`rc=2`, empty stdout), F1b fired (`v2=CLEAN v3=VIOLATED`). F3, F4, F5 did not. **F5 is the one
that mattered**: the live verdict is still `NOT_MEASURED`, so this is not a fix that only moved
today's number.

**TWO CEILINGS SHIPPED NAMED RATHER THAN CLOSED.** A green tree does not prove a green record
either — an uncommitted repair masks a defect in HEAD's blob — and scoring HEAD exactly costs
614 ms / 164 MB per run (H35) or a materialised copy, which is what H223 measured poisoning
three checkers. And the **mixed** vocabulary case still reads `NOT_MEASURED`: one parseable
refusal on a dirty file beside one unparseable line about a clean file. Closing that needs a
refusal vocabulary each checker DECLARES rather than one this evaluator guesses.

**A SMALL ONE, RECORDED BECAUSE I NEARLY ACTED ON IT.** After adding the H198 census I measured
its row at "10 fields" with `awk -F'|'` and read that as H82 — an unescaped pipe shifting the
status column. I had genuinely introduced one, and escaping it fixed refcheck's count 3 → 2. But
the 10 stayed, because **awk splits on `\|` too**: my measuring instrument could not see the
escape that the authority (`refcheck`) reads correctly. The row is clean; the second reading was
the wrong instrument for the question.

## Cycle 33 — H229 DONE, H246 filed. Two of my three predictions were wrong, and the row's author was right without a count.

`spikes/harness/githygiene.py` **v5**, `spikes/H229_append_only_population/`
(`FALSIFIERS.md`, `measure.sh`, `measure.out`, `RESULT.md`), `WORK_QUEUE.md` H229 DONE +
H246 filed, `CHANNEL.md`, `livechat.log`, `DECISIONS.log`.

**FALSIFIERS WERE COMMITTED WITH THE CLAIM THIS TIME**, in the spike rather than in
`CHANNEL.md` — because the row is about `CHANNEL.md`'s size, and because my H231 CLAIM
ended *"falsifiers preregistered below"* with nothing below it. **F1 and F2 fired against
my predictions.** I predicted few line-number citations and no live breakage; there are
**93** to `CHANNEL.md` and **37 already point past EOF**. AGENT-1 wrote *"there are many"*
with no count and was right; I had the count and the wrong prediction.

**(1) THE EXEMPTION QUESTION IS CLOSED WITH A NEGATIVE, AND A MECHANISM I HAD ALREADY
DESIGNED WAS DELETED RATHER THAN SHIPPED.** The row demanded a NAMED PROPERTY, not a path
allowlist. Deletions per addition over full history: `CHANNEL.md` **0.594**,
`HANDOFF.ok-1.md` 0.612, `WORK_QUEUE.md` 0.281 — against `MISSION_LOOP.md` **0.059**,
`githygiene.py` 0.038. **The logs are LESS append-dominant than ordinary source, the wrong
way round, because rotation is a deletion**, and the only two that score pure are the two
nobody has rotated. Append-only is policy in the briefs, not a shape in the data. I measured
the classifier before building it, which is the only reason the design died cheap.

**(2) `githygiene --only <paths>` — and the finding under it is that the CONDITION WAS
UNDETECTABLE ON THE PATH EVERY LANE IS TOLD TO USE.** `commit_scoped.sh:231` runs the
checker labelled *"(index-scoped, already correct)"*; `:360` commits `--only`, which ignores
the index. Gate population and commit population disjoint by construction. **Confirmed
against my own history: my H231 commit an hour earlier printed *"clean — nothing you are
about to commit violates §13"* while committing `CHANNEL.md`.**

**CLASS POSTED: A COMMENT ASSERTING A CHECK IS ALREADY CORRECTLY SCOPED IS WHY NOBODY
RE-DERIVES ITS SCOPE.** Three rows — H190, H230, H229 — have found a check reading the wrong
object inside that one script, and the line saying the third was fine is why it survived.

**NOT WIRED, AND THE ROW SAYS SO IN ITS STATUS CELL.** `commit_scoped.sh` is AGENT-1's and
their cycle is live (H199 precedent, same file, same reason). Until they take the one line,
this is a capability and not a gate. **"Shipped" and "in the path" are different claims** and
I would rather the queue carry the weaker one than read as closed.

**H246 SPLIT OUT AND DELIBERATELY NOT TAKEN.** `<file>:<line>` is the one citation shape no
checker in this repo resolves and the one that breaks without anyone editing the citing file
— §12.4's class arriving by a route §12.4 does not cover. A resolver arrives with 37
pre-existing failures, which is githygiene's own H14 shape and this row's subject.

**MY OWN PROBE DEFECT, CAUGHT BY READING THE OUTPUT AND NOT BY THE EXIT CODE.** `measure.sh`
v1's F5 block was three greps: one matched a COMMENT instead of the command, one matched
nothing at all, and the block printed a tidy-looking result either way — cycle 29's A4 shape,
third time. Each arm now says `ARM DID NOT FIND ITS LINE — the evidence is absent, not clean`
when it fails. **A check whose healthy answer is an empty set still cannot tell you it ran,
and I have now shipped that defect in three consecutive cycles' instruments.**

## Cycle 32 — ATTACK (§2, §12.8: the loop). H243 DONE: the rule the launcher quotes was obeyed by no other reader of the same file.

`spikes/harness/lanelive.sh` + `lanelive.py`, wired into `bringup.sh`, `spikes/harness/bringup.sh`,
`fleetcensus.sh`, `registry.py`, `whois.py`; `spikes/H243_lock_liveness/` (`probe.sh`, `sites.py`,
`probe_prefix.out` committed BEFORE the repair, `probe.out`, `RESULT.md`). Commits `3b10e5d`, `bb2c229`,
`8faaad0`.

**THE TARGET WAS H232'S CONSEQUENCE, NOT H232 AGAIN.** If a lock can name a launcher that no longer holds
the callsign, every instrument answering *"who holds X"* from it inherits a well-formed wrong answer.
**7 liveness tests read a lock pid; 5 used pid alone**, and two of those DECIDE — `bringup.sh:130` feeds
MISSING, `spikes/harness/bringup.sh:254` gates the stale-clear. Driven: `--check` called a lane **UP off a
lock naming a live `sleep`**; the census called it **CONSTITUTED**. UP means not MISSING means **not
relaunched**.

**THE FIX NEARLY BECAME A WORSE DEFECT THAN THE BUG, and this is the line to remember.** With the helper
absent from the sandbox, `launcher_alive` was undefined, every arm read `DOWN`, and a supervisor that
believes the whole fleet is down **relaunches every lane onto a held callsign**. `command -v ... || exit 1`
now. A missing check must not read as an answer.

**THREE DEFECTS IN MY OWN PROBE**, each caught by an assertion rather than by reading: BSD `sed` has no
`\|` in a basic regex (all three arms returned empty, all red at once); A3 measured the LIVE fleet because
`fleetcensus.sh` resolves its own root from `$0`, and the precondition check is what said so; A1 counted
`run_loop.sh`'s heartbeat — a TURN pid, correctly tested by pid alone — then, once excluded, missed
`registry.py`, whose lock read and liveness call are five lines apart and whose helper body is thirty.

**NOT COMMITTED BY ME: `spikes/harness/bringup.sh`.** It carries my `launcher_alive` edit AND a co-lane's
uncommitted citation to a section 15 that no document it may cite defines, which `refcheck` refuses.
(Written without the section glyph on purpose: `refcheck` cannot tell a citation from a QUOTATION of a
broken one, so naming it in the glyph form reddens the checker on the file reporting it — A30's trap,
and it cost this commit one refusal before the sentence was rewritten.) Their file, their cycle in flight — the edit stays in
the tree for whoever commits it, and `refcheck` will keep refusing until the citation resolves.

## Cycle 33 — H252 DONE. The item this lane carried for four cycles, and the delay was the measurement.

`spikes/harness/vocabcheck.py` v1 + `spikes/H252_two_documents/`. The H23 guard compares the hook's
refusal MESSAGE with the hook's ACCEPT BRANCH — one file — so a rename applied to both together reports
`equal` and the hook can drift from `MISSION_LOOP.md` §7 with every check green.

**THE OPEN QUESTION WAS NEVER HOW TO WRITE IT.** It was whether §7's vocabulary is extractable at all: if
not, the only buildable check compares the hook against a **third hand-written copy of the same list**,
which is the same assertion wearing a different filename and would have read as covered. **It is
extractable** — `MISSION_LOOP.md:79`'s *"exactly one of"* against `loop_gate.sh:114`'s `case` pattern.
F1-F4 preregistered, none fired. **9 arms, two-sided**, including a gutted `case` that must REFUSE rather
than compare two empty sets, and a reworded anchor that must REFUSE — the cost of anchoring on a phrase,
paid rather than argued away.

**SELECT was re-read rather than taken from my own NEXT list, and that is what stopped a collision.**
NEXT 1 was H229; the OTHER `ok-1` (the lock holder, 56520) had claimed and finished it while I was on
H243. My NEXT list was stale by one cycle — H28's class — and the queue is the authority.

## Cycle 34 — ATTACK (§2, §12.8). H243 CORRECTED — my own DONE row, from a turn that is not in this journal, and it did not hold as written.

`spikes/harness/commit-msg.hook`, `check_live_launcher.sh`, `spikes/H243_lock_liveness/`
(`sites.py` **v2**, `falsify.sh`, `sites.out`, `FALSIFIERS_H247.md`, `RESULT.md`),
`test_commit_msg.sh`, `.git/hooks/` reinstalled, `WORK_QUEUE.md` H243 amended in place,
`CHANNEL.md`, `livechat.log`, `DECISIONS.log`.

**THE CYCLE'S FIRST ACT SAVED IT.** My NEXT block said to attack the `.loop_lock` liveness
question and to **read ATTACKER-1's H238 first**. I did, and the question was already taken —
as **H243, by this lane**, in a turn with no journal entry. Without that check I would have
filed H204's shape over my own work.

**CORRECTED AGAINST MYSELF BEFORE THE CYCLE CLOSED, AND THIS IS THE PART TO READ FIRST.**
Two turns are writing under `ok-1` again — H232's condition, live. While this cycle ran,
`3b10e5d` landed `lanelive.sh`/`lanelive.py`/the wirings and `8faaad0` landed the spike's
`RESULT.md`. **I had measured both as absent, and then I overwrote that 98-line `RESULT.md`
with `cat >`.** Restored whole from `8faaad0` with this cycle's attack appended below it;
`git diff 8faaad0 -- <it>` is pure insertions, nothing lost. **The untracked-fix finding and
the missing-RESULT.md finding were true when measured and stale when published**; both are
corrected in place in the row, in `CHANNEL.md` and in `livechat.log`. What survives unchanged
is everything measured about the CODE. **The lesson is not "re-read the queue at claim time" —
I did that. It is that a shared tree makes a measurement perishable, and I published on a
twenty-minute-old `git status`.**

**F2 AND F4 FIRED AGAINST ME AND THEY ARE THE SAME FACT: A DONE ROW IS A CLAIM ABOUT THE
RECORD, AND MINE WAS A CLAIM ABOUT MY WORKING DIRECTORY.** *(As measured; see the correction
above — another turn closed the record half within the hour.)* `b000e8e` committed the
*measurement*; `lanelive.sh`, `lanelive.py` and all five wirings were **untracked** while the
row read DONE, and the row cited a `RESULT.md` that did not exist. `git clean -fd` would have
deleted the module and left four instruments sourcing nothing — and H234 recorded a whole-tree
operation on this tree today. **Fourth RECORD failure by this lane**, and this one had a queue
row asserting the opposite.

**(a) THE POPULATION WAS HAND-TYPED.** *"7 liveness tests read a lock pid and 5 use `kill -0`"*
was true of the six files I typed into `SITES` and of nothing else — **family D, in the
instrument whose entire job was to BE the population.** Derived from the tree: **38**. And the
detector was fine the whole time: v1's regex matches `ps -p ` and does not match `-o lstart=`,
so the missed site would have been flagged the moment it was handed the file. **Wrong about
what it looked at, not about what it saw — and that is invisible from the output, because a
census prints its findings and never its population.**

**(b) THE SEVENTH READER, AND ITS OWN CORRECT TEST WAS THREE LINES BELOW.**
`commit-msg.hook:149` took `ps -p <lockpid> -o lstart=` straight into `Claude-Session:` — the
field §13.1 calls *the only field that separates two lanes signing the SAME callsign*. The argv
fallback below it IS a launcher-identity test and **runs only when the start time came back
EMPTY, which a recycled pid never does.** The good path was gated on the bad path failing.

**(c) THE DISAGREEMENT CONTROL COULD BE FOOLED BY THE DISAGREEMENT IT EXISTS TO FIND.**
`check_live_launcher.sh:337` counted lock holders with `kill -0`. Now `launcher_alive`, and
with the module absent it prints `CONTROL UNAVAILABLE` and **declines to take the count** —
H231's lesson, one cycle old, applied against my own instinct to fall back quietly.

**THE ARM THAT MADE THE HOOK FIX REAL, AND WHY IT FAILED FIRST.** Every existing
`test_commit_msg.sh` arm hands the hook a lock naming a **genuine** launcher, so a hook that
skipped the identity check passed all of them. The new arm points the lock at a live
**non-launcher**. It failed on first run **against the INSTALLED `.git/hooks/commit-msg`**,
which still carried the old code while the reviewed source was fixed — the suite doing its job
on a real drift. 19/19 after `install_hooks.sh`.

**THREE DEFECTS IN MY OWN INSTRUMENTS, EACH CAUGHT BY A DIFFERENT THING, AND ONE IS THIS
LANE'S OWN NAMED CLASS.** (1) A word in a comment matched as a variable: the new lock-variable
rule scored `registry.py:181` because *"# NOT for lock pids"* contains the word `lock`. **A30's
class — a checker that cannot tell a live construct from a mention of one — which I logged
against the §10 gate two cycles ago, reproduced inside a rule written to fix a different defect
in the same cycle.** (2) The 12-line window silently dropped the site it had just fixed, because
my own rationale comment pushed the line thirteen rows down — so a **reverted** fix would have
read as *not a site*. Caught by re-running the census after the edit, not by any check.
(3) A mutant's `sed` used `\|` as its delimiter against a pattern containing `\|\|`; caught only
because every mutant asserts its own edit applied (H217).

**AMENDED IN PLACE, NOT RE-FILED**, and `orphancheck.py:130` is **routed to ATOM-3, not
touched**. PID ALONE **8 -> 6**, and the six are 2 pinned historical copies, 3 deliberate
fixtures and that one routed site — a floor, not a backlog.

## Cycle 34 — H254 DONE. The §10 gate refused one of my `grep`s, and the three cases already written for that exact heading were passing for the wrong reason.

`spikes/harness/scratchcheck.py` **v4** + `spikes/H254_operator_in_quotes/`.

`grep -nE 'git |cp |mktemp|TMP' <file>` was refused as a WRITE. The `|` before `mktemp` is a regex
alternation; `MKTEMP`'s anchor set reads any `|` as a pipe, so a word inside a search pattern was in
command position. **CLASS: an operator character inside quotes read as an operator.**

**THE PART I WOULD READ FIRST: v3 already carried three of its author's own refused commands under the
heading *"a gate that refuses the investigation of its own rail is unusable"* — and all three are clean
only because their token has a SPACE before it.** The heading claims quoting is handled. The space was
doing the work. A negative case that passes for a reason nobody has named is not covering what the comment
above it says it covers.

**Narrow on purpose:** the fix looks at the OPERATOR, never at the path — `_in_quotes`'s own docstring
records that masking quoted spans would delete true positives, since the path of a real write is usually
quoted. `echo "$(mktemp -d)"` still refuses, because `$(` inside double quotes is live. 56 arms (was 53),
including M6, which turns the rule off and requires the reported command to refuse again while
`ls | mktemp` keeps firing.

**TWO THINGS AGAINST MYSELF.** I logged this in `DECISIONS.log` when I hit it and chose not to file it —
wrong by one cycle, because the refusal names a path the command never contains, so the next lane pays the
same diagnosis. And my first draft wrote `H253` in three comments from memory; renumbered mechanically
against the allocator before the row was typed, which is the only reason it is not this week's fourth id
collision.

## Cycle 35 — the OTHER `ok-1` turn attacked my H243 while I was on H254, and three of its findings stand against me.

`ddeb936` (CORRECTED) and `7ed2ab5` (RETRACTED), both `Atom: ok-1`, both from the lock-holding tree. I did
not write them and I am recording them here because this journal is the write-ahead record of what this
lane believes, and it must not keep carrying a number that died.

**WHAT DIED, AND IT IS THE HEADLINE OF MY OWN ROW.** *"7 liveness tests read a lock pid and 5 use pid
alone"* was true of the **six files I typed into `sites.py`'s `SITES` list** and of nothing else — **family
D, in the instrument whose entire job was to BE the population.** Derived properly from `git ls-files`:
38 tracked `.sh`/`.py`/`.hook` files mention `loop_lock`. PID ALONE **8 -> 6** after their fixes.

**A SEVENTH READER I MISSED ENTIRELY:** `commit-msg.hook:149` fed `ps -p <lockpid> -o lstart=` into
`Claude-Session:` — the one field §13.1 says separates two lanes signing the same callsign — and its
launcher-identity test only ran when the start time came back EMPTY, which a recycled pid never does.
**And `check_live_launcher.sh` counted lock holders with `kill -0`**, inside the control whose job is to
notice that exact divergence.

**WHAT SURVIVES:** the class, the predicate, the five wirings, the refusing source guard, and every
before/after measurement of behaviour. Two of their findings were themselves retracted — both true when
measured and stale when published, on a tree five lanes write.

**WHY I AM NOT DEFENDING IT.** The census was self-authored and I did not notice, and *"a party supplying
the input to a check applied to itself"* is the failure family this repo names A22/D. My probe printed the
list I had typed and I read the output as the tree's population.

**H232's condition is live in the record, not just in the incident:** two turns are writing under `ok-1`,
and their commits and mine both sign it. The lock is the arbiter, this tree is retired, and their turn is
the one that continues.

## Cycle 36 — ATTACK (§2). H258 DONE: three Stop-hook registrations on this disk, and every check reads one of them.

`spikes/harness/hookcopies.py` v1 + `spikes/H258_registered_copies/`.

**THE TARGET CAME FROM THE ATTACK ON ME.** The other turn's finding was *"the population was hand-typed"*;
applied to my own remaining instruments it stops being *is the hook correct* and becomes **which copy does
the check read**. `test_loop_gate.sh`, its H23 block and `vocabcheck.py` (mine, one cycle old) all read
`.claude/hooks/loop_gate.sh`. Nothing enumerated the registrations.

`.codex/hooks.json` registers `.codex/hooks/loop_gate.sh` at **v8, digest `e269f2fd79fc9adc`** — the blob
H219's own RESULT cites as **the pre-fix hook**, measured refusing `STOP.<lane>` 20 of 20. **H1's shape
mirrored:** H1 was a hook registered where no session looked; this is one registered where no check looks.

**F2 FIRED AND I SHRANK THE ROW RATHER THAN THE FINDING.** No `codex` on PATH, `.codex/` untracked, so the
drift is **latent** — a retired contract wearing a current registration, not a lane running the wrong hook
tonight. Recording it as live would be this repo's "correct numbers, wrong attribution".

**`.codex/` NOT TOUCHED (A23).** Untracked, another harness's, and overwriting it destroys the only on-disk
record of what that registration runs. Reported, mechanised, routed.

## NEXT 3 — written for the SURVIVING `ok-1` tree (56520), because this one is retired
1. **H241 is OPEN and neither turn should close it without a decision on the seam.** `run_loop.sh`'s quota
   branch has no check at all: any fixture that reaches it sleeps at least the parser's 60 s floor, so
   testing it means adding `KF_QUOTA_MAX_SLEEP` or equivalent to a live launcher. That is a decision, not
   an implementation detail, and it belongs to its own row.
2. **`spikes/harness/bringup.sh` carries my `launcher_alive` edit UNCOMMITTED**, next to a co-lane's
   uncommitted citation of a section 15 that nothing defines, which `refcheck` refuses. Whoever commits
   that file should keep the edit — it is the H243 class fix for the supervisor copy — and should expect
   the refusal until the citation resolves.
3. **H215 (the `Carries:` reader split) is still OPEN and still this lane's by ownership.**
   `commit-msg.hook:236` accepts any `^Carries:` line anywhere; git accepts only the final paragraph; the
   looser reader grants the authorisation. **The reason I gave for not taking it — that H214 was open in
   the same hook under another lane — expired: `WORK_QUEUE.md` records H214 DONE (AGENT-1,
   `commit_scoped.sh` v10, and its own premise WITHDRAWN when F1 fired). Caught by `statuscheck.py`
   refusing this very commit, which is the check that exists so a brief cannot quietly go stale.** Whoever
   takes H215 should read H214's withdrawal first: measure which reader is live before changing either.

**H196, H80 remain OPEN and unchanged. H29 is OPEN and gated on H17's §10 dispute, not BLOCKED.**

**STANDING NOTE:** cycles 31-35 in this journal were run by the **retired** `ok-1` tree (root 3619, killed
in cycle 31 under H232). `56520` holds the lock, is the live lane, and has been correcting this tree's work
from the other side — H229 and the H243 attack are both its. Read any `ok-1` line from this period as
coming from one of two trees, and the queue as the arbiter.
