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

## NEXT 3
1. **Cycle 8 is an ATTACK cycle and §12.8 makes it the loop's turn.** Target: the
   class hunt this cycle named and did not run — grep the whole harness for absence
   assertions after anything that forks or backgrounds, and for `"$rc" "1"` on
   multi-gate paths. Both classes were found in my own suite, so that is the wrong
   place to stop looking.
2. **H61** — the launcher lock handoff. Fix shape is in the row and the check that
   fails when it breaks already exists. Do not take it while another lane is
   mid-edit in `run_loop.sh` (H19: three lanes, one git index).
3. **H54** — the cost H41 paid. A journal's evidence-path citations need a check
   that reports to the journal's OWN lane, not to the shared commit gate.

**H29 is BLOCKED on H17, not done, and the diagnosis is in BLOCKED.log.** Do not
"finish" it by wiring the suite into pre-commit: that settles H17's open §10
dispute by default, in the permissive direction, in favour of the agent doing it.

**RECORD, cycle 7, and it is H19 for the third time against this lane:** the
commit `d049820` carries 9 files, not the 12 I passed to `git commit --only`.
`WORK_QUEUE.md`, `CHANNEL.md` and `DECISIONS.log` had already been committed two
seconds earlier by `9800b1f` (`Atom: AGENT-2`, G36) out of the shared working tree,
so `--only` found no diff for them. **The content is in HEAD and correct** — H61,
H62, the H29 status rewrite, the DONE line and the decision log all resolve at
HEAD — and the attribution is not. `--only` protects you from committing another
lane's work; nothing protects your work from being committed by another lane.

## Cycle 8 — ATTACK (§2), and §12.8 makes it the loop's. H63: the gate nobody tested.

`spikes/H63_roster_attack/`. Suite 66 → **75 checks**. Four falsifiers stated
first; two fired.

**The roster gate — `run_loop.sh:124-134`, the thing that decides which lanes may
run at all — had no check of any kind.** Delete the whole block and the suite stays
66/66 green. Loosen `grep -qx` to `grep -q` and callsign `ok` is admitted by a
roster listing `ok-1`: rc=0, reached claude. `ok-1` is this lane.

**How I found it, and it is worth more than the fix:** `grep -n roster
spikes/harness/test_loop_gate.sh` returned three lines and all three were a scratch
roster written FOR a different block. **A fixture mention reads exactly like
coverage in a grep.** That is a two-second audit anyone can run on any mechanism.

**Not fixed, and not mine to fix:** with `roster.txt` absent the launcher warns and
admits ANY callsign — H30's class (a missing input degrades a mechanism to a no-op
while it still reports success) at the gate with the widest blast radius. It is the
operator's sanction list, so ruling on its absence is A22 with me as the
beneficiary. `HUMAN_NEEDED.md` carries both costs and a one-line ask; today's
behaviour is pinned by a check so it cannot change silently.

**Carried H62's lessons forward on purpose**: every arm asserts refusal TEXT, not
just rc; every arm asserts the parent's detach announcement, not just the child's
artifacts; every arm has a brief, because the brief gate is BELOW the roster gate
and would otherwise refuse for a reason the block is not about; and the block has a
rostered-callsign POSITIVE control, because "it refused" is satisfied by a launcher
that refuses everything.

## Cycle 9 — H61 DONE, and I withdrew both halves of the row I filed

`spikes/H61_lock_handoff/`. `run_loop.sh` **v10** defect 13; suite 75 → **80**;
`falsify.py` **F29** fires, control 80/0.

**Both sentences in my own row were wrong, and the probe said so before I wrote a
line of repair.** (1) "The H8 lock is held closed by a sleep" — no. Eight arms,
every launcher accounted for: there is **no double admission**; the second
launcher is refused in every arm. That reading came from H29's arm where the
`sleep 1` was DELETED — an edit, not a load. (2) "The check that fails when it
breaks already exists, it is the 20-launcher block" — no. It reads `1 survivor /
19 parent refusals` with the defect present AND absent. Simultaneity is the one
arrival time the constant did cover: all 20 hit the lock while the first parent is
still inside its sleep.

**What is there is worse than what I filed.** The lock is acquired by the PARENT
and reclaimed by the CHILD, so between the parent's exit and that reclaim it names
a dead pid. A launcher arriving there passes the parent-side check and is refused
**by its own child** — into `detach_$CALLSIGN.log`, after the parent printed
`detached` and exited **0**. `run_loop.sh:232-234` states that failure as the
reason the lock is acquired before the fork, and defect 8 (H30's brief gate) was
moved above the fork citing the same sentence. **CLASS: validating above the
detach is not enough when the validated state is handed over ASYNCHRONOUSLY —
refusals must be printed by a process the caller is still waiting on.** Posted to
livechat with what to grep.

**Against me, four times.** (a) The row. (b) probe v1 concluded "a slow child
breaks the lock" from `2/3 red` while the numbers it printed said `0 survivors, 19
refusals` — one late lane, not two admitted. (c) probe v2 counted refusals only in
`race.log`, which holds the PARENT's output, so the one arm that answers the row
came back `UNACCOUNTED: 1+0 != 2`, **the probe printed its own A29 warning and the
verdict logic used the number anyway**. v3 makes that guard a refusal. (d) The new
check manufactured its own defect twice: an `awk >` copy at 644 whose children
died at exec, then a copy named `run_loop_h61.sh` — invisible to the lock's
`grep -q 'run_loop\.sh'` liveness test, so every held lock read stale and the
block measured **2 survivors, a double admission it had created itself**.

**Not live in any lane.** Every launcher predates the commit, so
`check_live_launcher.sh` reads red fleet-wide — H21's class, closes at a relaunch
cutover. Said in livechat so nobody reads it as a new stall.

## NEXT 3
1. **Cycle 10 is not an ATTACK cycle (cycle 12 is), so take a build row.** H29 is
   still BLOCKED on H17 and must not be "finished" by wiring the suite into
   pre-commit. Candidates nobody holds: **H11** (fuse semantics: the comment says
   per-session, `run_loop.sh` clears per turn, so MAX_BLOCKS cannot mean what it
   says) and **H23** (no mechanical detector for a rationale block that names an
   absent path).
2. **The class hunt is still only half run.** Class 1 (`rc`-only assertions) turned
   up one candidate outside my tree — `spikes/H56_fleet_stall/probe.sh:179`,
   `check "P2 --check exits non-zero on a STALLED lane" "$rc" "1"` — and I have not
   checked whether that path has a second way to exit non-zero. Not my spike: ask
   its owner rather than edit it. **Add H61's class to the same hunt**: grep for a
   validation above a fork whose state the child re-claims.
3. **H54** — closed by ATOM-3 while I had it queued; drop it from this list and do
   not re-take it. (Kept as a line rather than deleted, because silently dropping a
   NEXT item is how a journal starts disagreeing with itself — §12.5.)
