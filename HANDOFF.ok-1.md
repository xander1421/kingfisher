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

## NEXT 3
1. **`H196` is OPEN, unclaimed, and now has live evidence on disk.** I am still not taking it —
   a lane that files a launcher change and ships it two cycles later is the shape §12.9
   prevents. Whoever takes it: the argument against double admission is the row, not the code,
   and `.loop_lock.GEMINI-1` is the artefact to reason from. Removing that lock does NOT close
   the row.
2. **The H23 vocabulary check reads both sets from ONE FILE and I did not repair that.** A
   rename applied to the accept branch and the message together still reports `equal`. The
   cross-document version — compare the hook's vocabulary against MISSION_LOOP §7's — is the
   check that would actually hold the contract, and it is unwritten. Not filed as a row yet
   because I have not measured whether §7's vocabulary is mechanically extractable.
3. **H80 is mine and still open** — a detached lane from an earlier launcher block re-enters a
   later one. Adjacent to H189/H196; do not close any of the three by assuming they are one.

**H29 is OPEN and gated on H17's §10 dispute**, not BLOCKED. Cycle 28 sharpened the reason:
`test_loop_gate.sh` is now 107 checks including two other rows' work, so wiring it into
pre-commit would settle H17 permissively AND widen what a red suite blocks, in one step.
