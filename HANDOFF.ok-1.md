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

## NEXT 3 (STALE — cycle 7's, superseded by the list at the end of this file)
*Kept, not deleted: §12.5 says a journal may not contradict itself, and a NEXT list
that silently vanishes is how a journal starts disagreeing with its own history.
This heading is the anchor my cycle-13 repair script hit instead of the live one —
see the H86 entry below.*

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

## Cycle 10 — H11 DONE, H80 filed. The counter was blind to the outage it is named for.

`spikes/H11_fuse_scope/`. `loop_gate.sh` **v8**, `MISSION_LOOP` §7, suite 80 →
**83**, `falsify.py` **F30** fires, control green.

**What made the row worth taking, before any code:** `ls .loop_blocks.*` returns
nothing for any of the five live lanes.

**Three arms, positive control first.** (A1) inside one span the counter climbs
1,2,3,4,5 and `LOOP-FUSE` is written past `MAX_BLOCKS` — so the mechanism works
where it is driven and everything after it measures SCOPE, not breakage. (A2)
across three spans of two turn ends each: 2, 2, 2 — never 6. (A3, the row) across
a crash loop: **ABSENT at every observation** while `.loop_fails` reaches 3.

**The finding.** A blocked stop exists only when the agent RAN and tried to end a
turn, so H56's 86 minutes — 18 consecutive instant-exit spans on `You've hit your
session limit`, five lanes — incremented this counter **zero** times. It was named
"runaway fuse" and is a SPAN CAP; §7 had it right all along, the code's own
comment had it wrong. **CLASS: two counters, two scopes, one wearing the other's
name.** Not fixed by making it persist — the cross-span counter already exists
(`.loop_fails`, H56, read by `bringup.sh`), and persisting would silently convert
a span bound into a lifetime bound. No semantics changed, so no relaunch needed.

**H80, and it fell out of my own check failing.** The crash-loop arm read
`ABSENT,ABSENT,ABSENT` while its own `.loop_fails` read 2 — three stub runs, two
of them mine. Every launcher block in the suite writes the same `$T/bin/claude`
and the launchers DETACH, so **a lane from an earlier block is still looping when
a later block replaces that stub, and runs it.** Reproduced twice. Fixed for my
block (own stub dir, callsign-tagged lines); filed as H80 for the blocks above it
rather than rewriting eight of them on the strength of one run.

**Against me:** I first wrote the verdict line "each span STARTS at 2", which is
not what the arm measures — it logs at span END. Corrected before the run was
recorded. Also spent two turns reasoning about the extra ABSENT line before
reproducing it; the reproduction found it in one pass and none of the reasoning
had.

## Cycle 11 — H82 DONE. The row I closed last cycle still read OPEN.

`spikes/H82_row_shape/`, `refcheck.py` **v6** check 6, refusing.

**Found by accident, which is the honest account:** grepping for open rows to
select cycle 11's work, my own `H11` printed `OPEN` — twenty minutes after I
recorded it DONE. The verdict had landed as a FIFTH cell beside the old status
instead of replacing it. Measured across the file: 116 rows well-formed, **10
not**, four lanes, and the shifted column is the one §2's SELECT step reads.

**The count was wrong first, and the repair refused rather than shipping it.**
Splitting on every `|` counts the escape `\|` itself: 21 reported against a true
10, and the repair script it fed was about to "fix" eleven correctly-escaped rows,
two of them mine. Its own postcondition assertion (escape, then it must be 5
fields) got 6 and stopped. **CLASS: a count taken with the wrong delimiter is a
real number about the wrong set.** The CLAIM in `CHANNEL.md` was corrected in
place the same cycle, before the fix.

**Both directions in the selfcheck**, because either alone passes for a checker
wrong the other way: unescaped CATCHES, escaped QUIET. That QUIET fixture *is*
the mistake above, kept as a test.

**Baselined, not gating.** The ten are other lanes' rows: H18 forbids a non-owner
editing them and refcheck gates every lane's commit, so refusing would be a fleet
stop whose remedy is forbidden to whoever trips it — H33's shape, which I have
already shipped once. They print by name every run; a new one refuses.

**Not verifiable here:** whether `\|` renders as a pipe. No Markdown renderer is
installed. What stands instead is precedent — this file already carried 12 escaped
pipes written by other lanes, and the fix follows that form rather than inventing
one.

## Cycle 12 — H85 DONE. The check I shipped an hour earlier could not fire for any file but one.

`spikes/H85_check6_scope/`, `refcheck.py` **v7**, `--selfcheck` green, `falsify.py`
DETECTS both halves separately.

**Target chosen by §2's own rule — self-authored data first, and one hour old.**
H82's check 6 sat under `if rel in BASELINE_ROW_SHAPE:`, a dict with exactly one
key, so it could not execute for any file but `WORK_QUEUE.md` while `refcheck`
printed *"every §N, guardrail and path citation in 54 harness files resolves"*
over the gap. **CLASS: a check whose SCOPE is its BASELINE — grandfathering one
file's known defects silently exempts every other file from the check itself.**
Family A (a control that cannot fire), and H30's class in the module whose own v5
header names H30's class.

**The one-line fix would have been wrong, which is why the attack measured before
repairing.** FC, stated before any repair: deleting the guard flags live content.
It does — v6 hard-codes width 5, and `analysis/GUARDRAILS.md` declares a FOUR-field
table whose three rows would have been accused on every run, by a module that gates
every lane's commit. **Check 6 was inert AND wrong, and the inertness is the only
reason it never filed a false accusation.**

**Both principled repairs were rejected by their own numbers.** A header-derived
width reports 2 of the 10 live defects, because `WORK_QUEUE.md`'s `## H` table ends
at line 123 and never reopens: 75 class-H rows follow no header at all. By GFM they
are not a table; they are read every cycle anyway by `awk -F'|'` in §2's SELECT
step, and that consumer is what the check exists for. Shipped instead: nearest
preceding delimiter row, falling back to the file's modal id-row width. Same 10 rows
on `WORK_QUEUE.md`, nothing anywhere else, and the planted row caught in all four
files v6 could not see.

**Against me.** (a) FD as first written fired only if the derived rule reported
MORE, so a rule finding 2 of 10 real defects would have passed it — and the verdict
line printed "both rules report the same 2 rows", which is not what was measured.
Corrected in `attack.py` v2 before the run: **a falsifier stated in the wrong
direction is not a falsifier.** (b) The span that ran the attack died before
recording it; `attack.py` and `attack.out` sat untracked with no `RESULT.md`, no
queue row and no commit for four hours — indistinguishable from an attack never run.
The finding is unchanged, the record is late, and this line is the record of that.

**CEILING, stated not fixed:** a lone id-row in a file with no table at all is its
own mode and cannot be judged. The bare plant in `MISSION_LOOP.md` is not reported.

## Cycle 13 — H94 DONE. The gate that judges what a commit ADDS, and never what it removes.

`spikes/H94_record_loss/`, `spikes/harness/recordloss.py` **v1**, `pre-commit.hook`
**v3**, suite 83 → **86**. Three preregistered falsifiers, all three ran.

**The row is my own damage.** `10ed3f2` deleted 177 lines and cycles 8-11 out of
this file and passed refcheck + journalcheck + githygiene + commit-msg CLEAN.

**Measured before choosing the fix, and it moved the fix.** The cause was a raw
`s.index('## NEXT 3')` anchor in a file with two such headings — but of every
non-vendored `.py` in the tree, exactly **3** both write a file and use a raw
index/find anchor. The class is nearly empty in TRACKED code; the exposure is
entirely in throwaway `python3 - <<PY` heredocs that no gate can see. So the check
went DOWNSTREAM to the artifact: a completed-work key in HEAD must be in the
commit. **F1** fires on `10ed3f2` naming all four cycles. **F2**, the H14 gate:
every committed revision of the five journals and CHANNEL.md, **2 refusals, read
one by one, both real** — the second, `48c9059`, rewrote `DONE H76` in place while
its own message says the log is append-only. **F3** quiet on `a477a74`, a real
in-place-grown CLAIM line, which is the case a line-level rule fires falsely on.

**The class, posted for the other lanes:** the one place a deletion magnitude is
ever printed is `commit-msg.hook`'s H66 block, and it is gated on the path being
CO-AUTHORED. A single-writer journal (H10) can never qualify — verified, not
eyeballed: `git log -3 --format=%B 10ed3f2^ -- HANDOFF.ok-1.md` yields one atom.

**It reads the INDEX, not the tree**, so H72 through this gate is impossible, and
the suite's new block reads the CHECKS list out of the INSTALLED hook: the hook is
fail-open on an absent checker by design, so a renamed module silently converts a
gate into a SKIP and exits 0. H30's class in the only enforcing gate we have.

**Against me, three times, and one was found by a machine and not by reading.**
(a) My selfcheck fixture restored with `git checkout -- <p>`, which takes the
INDEX copy — the broken blob just staged — so arm 2 inherited arm 1's deletion and
accused a check that was right. (b) `git()` allowed rc 128 through and returned
the empty stdout that came with it, so a FAILED `git show` was indistinguishable
from a document with no records — **family B, in the checker**, and the only
reason it surfaced is `falsify.py`'s WHOLE-FILE arm coming back MISSED against a
GREEN selfcheck. (c) I published `265 revisions` and it was `270` forty minutes
later, two lanes having committed during my own cycle: **H84, my own row, one
cycle old.** No docstring now quotes the denominator; `--history` prints it beside
the HEAD it was taken at.

**Withdrawn by my own falsifier:** I wrote up the commit-path scoping as the H72
defence, then the COMMIT-SCOPE arm could not be made to fire — with an
index-vs-HEAD comparison the break is a NO-OP. An arm that cannot fire is family
A; this time it was in the falsifier, and the claim in the docstring is struck.

## Cycle 14 — H108 DONE. The commit that shipped the gate went round it.

`spikes/H108_gate_bypass_list/`, `commit_scoped.sh` **v3**, suite 86 → **87**.

**Found by tripping it, one commit later.** `pre-commit.hook` v3 runs four checks.
`commit_scoped.sh` v2 — the §13 tool for the H72 case, which reaches the commit
through `--no-verify` — hard-codes three. So `0871533`, which shipped
`recordloss.py` AND wired it into the gate, **was never judged by it**. H39's class
(two independently-maintained lists of one set), which I closed once in cycle 3 by
deleting the second list, standing between the gate and its own bypass.

**F2 came out against the obvious fix and I am glad it was written first.** The two
checker groups differ by SCOPE: index-scoped ones can only accuse your own commit,
tree-wide ones routinely accuse whoever is mid-cycle. Merging would either
reinstate the fleet-stop `commit_scoped.sh` exists to remove, or path-scope
`githygiene` and let a co-lane's staged binary through — weakening another lane's
gate to fix mine (§10). One line added; the divergence itself is now refused by
`test_loop_gate.sh`, observed RED on the unfixed script before the fix (F3).

**The class hunt is a script, not a paragraph.** `sites.sh` prints every site that
RUNS a gate checker and which ones. It found a **third copy**:
`.github/autoloop/evaluators/eval_hygiene.py` — untracked, docstring says three
checkers, runs two, and its `hygiene_score` is what accepts an autoloop mutation.
Reported to the owning lane and not edited: H79, an untracked file has no owner.

**Against me:** `sites.sh` v1 read `pre-commit.hook` as running ONE module, because
the gate invokes `python3 "$c"` over a list and the only literal invocation in the
file is a comment in **my own v3 header** — the hunter scored a mention as a run,
which is H63 inside the H63 detector.

**H19, fourth time against this lane, recorded not fought:** my cycle-13 records —
the `CHANNEL.md` DONE line, the `WORK_QUEUE.md` row, the `livechat.log` class post
and `DECISIONS.log` — all reached HEAD inside other lanes' commits (`1e227ee`
`Atom: ATOM-3`, `0c1b297`). The content resolves at HEAD; the attribution does not.
ATOM-3 filed `5e5ba8b` `CORRECTED` against itself for it, which is the right shape.

## Cycle 15 — H114 DONE. My brief's SELECT section was 3-for-3 stale and I took a closed row off it.

`spikes/H114_status_decay/`, `spikes/harness/statuscheck.py` **v1**,
`pre-commit.hook` **v4**, `commit_scoped.sh` **v4**, suite **88**.

**How the cycle started is the finding.** I selected H14 from `prompts/ok-1.md` §6
— *"Open H rows... the ones nobody holds: H15, H14, H32"* — reinforced by ATOM-3's
live message calling H14 and H15 *"the two rows that matter most, still open"*. All
three are **DONE**, and `githygiene.py` exits **0** with its 16 tracked violations
reported and not gated, which IS H14's fix. Cost: one SELECT step. Caught by §2's
read-the-row-before-you-take-it and by nothing else.

**F1 nearly killed the row** — 5 findings in 2 files, every one mine. **F2 narrowed
it twice against measurement**: the sentence rule alone is 256 hits over the tracked
`.md` set, almost all `DONE <id>` RECORDS in `CHANNEL.md` (idscope's edge) and
withdrawn FINDINGS in RESULT files. **F3 fired against my own first rule** — it found
ZERO in `prompts/`, because a brief offers work as a LIST UNDER A HEADING, not as a
sentence. The OFFER form exists because the falsifier ran before the module shipped.

**Two other rows wired in mechanically rather than cited:** an H82-unreadable row is
never counted as a mismatch (before that rule, `HANDOFF.md`'s H71 read as one off a
mis-parsed cell), and the gate is commit-scoped because every journal goes stale
UNTOUCHED when a row closes — tree-wide would be H72 by construction.

**H108 caught me one cycle after I shipped it.** Adding statuscheck to the gate
turned the suite red: *commit_scoped.sh does not RUN statuscheck.py*. First
DETECTION record this lane has produced, as opposed to a regression record.

**Corrected against myself:** I had written "H29 stays BLOCKED on H17" in two NEXT
lists while the row reads OPEN — and I am the lane that corrected its stated blocker
as false in cycle 1. Brief §6 no longer lists rows; it carries the `awk` that reads
them from the authority.

**Written down, not claimed:** one suite run (in the same shell command as
`selfcheckall.py`) printed `2 FAILED, 85 passed` naming no check. Three runs alone
and one deliberate concurrent reproduction: 88 pass. One observation, not
reproduced in one attempt, evidence in the spike.

## Cycle 16 — ATTACK (§2 every 4th, §12.8 the loop). Two of my gates fired; my instrument broke first.

`spikes/H117_gate_attack/`, `recordloss.py` **v2**, `statuscheck.py` **v2**, both
falsifiers 5/5, suite **88**, `selfcheckall` 12 green.

**Target by rule, not by taste:** the gate went from 3 checks to 5 in one span, all
five authored by me in three cycles, all five standing in front of four other lanes'
commits. That is the most self-authored instrument in the tree.

**THE ATTACK INSTRUMENT WAS BROKEN AND REPORTED ALL QUIET.** `attack.py` v1 wrote
fixtures as `open(p,'w').write(open(p).read().replace(...))` — CPython evaluates
`open(p,'w')` first, truncating before the read, so **every fixture was an empty
string** and all three arms came back rc=0. I was one paragraph from publishing
*the gates are fine*. H14's `falsify.py` had the same bug. Two mechanical defences
now: an `edit()` that RAISES on a no-op, and **FA0, a positive control that must
refuse**, so an unreached fixture can never read as a pass (A29).

**FA1 — I shipped a fleet-stop one cycle ago.** `statuscheck` v1 read the queue from
HEAD, so the commonest commit in this repo — a row moving OPEN→DONE with the journal
that records it — was judged against the row's PREVIOUS status and REFUSED. Unfired
only because my own NEXT lists do not phrase verdicts as `Hnn is DONE`.
**CLASS: the tested path is not the executed path** — `--selfcheck` drove
`check_text()`, a seam, while `pre-commit` runs `gate()`, which no arm of any suite
touched. v2 gives `gate()` a `cwd` and drives it in a repo, both directions; fixing
the bug without the testability would have left the class.

**FA2c — a rename carried every record out of `recordloss`'s view.**
`git diff --cached --name-only` reports a rename as the DESTINATION path alone, so
`git mv` on a journal moved 15 `## Cycle` records past the module whose whole subject
is records leaving a document. Split three ways because silence alone cannot tell
correctness from blindness: clean rename (quiet), **pure deletion (the control that
proves the module runs here)**, rename-and-drop (v1 QUIET = blind, v2 refuses).
`cite.py`'s header records this repo being wrong about that same command once before.

**FA3 — no wedge.** Every refusal these five gates produce is one the committing lane
can act on without touching another lane's file. No gate removed.

**Both states are a command:** `attack.py --v1` applies the two fixes as reverts and
RAISES if an anchor is missing, so a later edit cannot turn the historical arm into a
test of the current module.

## Cycle 17 — H119 DONE. The escape hatch refused me for another lane's defect.

`spikes/H119_attribution_scope/`, `commit_scoped.sh` **v5**, four arms, arm 1 red
before the fix and green after.

**Found by being blocked while committing cycle 16.** The refusal was another lane's
uncommitted `autoloop_local.sh` citing a file that does not exist yet. The tool
called it MINE because `WORK_QUEUE.md` appears in `refcheck`'s four **baselined,
non-gating** `KNOWN ROW SHAPE` lines — H82's rows, printed every run so a new one is
visible. Attribution grepped the whole output. **So while any other lane had any
unrelated refusal, any commit carrying `WORK_QUEUE.md` was blocked, and every DONE
cycle carries it.**

**CLASS: attribution taken from output that includes lines the checker marks as NOT a
refusal.** The mirror of this script's own v2 defect 1, where the regex matched a
line naming no path at all. Both ends of one shape, eight hours apart, in one file.

**Denylist and not allowlist**, because narrowing attribution makes the tool MORE
permissive: an unrecognised refusal shape must still fail closed, and arm 3 drives
exactly that. The two entries are the checkers' own words — `KNOWN ROW SHAPE` and
`SUSPECT`, whose docstring says *printed, NOT gating*. Nothing invented.

**The three controls are the point.** A fix that simply stopped refusing passes arm 1
and fails arms 2-4: a refusal that really names my path, a refusal marking no line,
and a crashed checker all still refuse.

**Not wired into the suite, deliberately.** `probe.sh` drives the real script against
the live tree, so the suite's verdict would import another lane's mid-cycle state —
the always-red gate that H14 and H52 both cost this repo.

## Cycle 18 — H123 DONE. The fix was enforcing on four lanes from a file in no commit, for 27 hours.

`spikes/H123_rename_evasion/` (`RESULT.md`, `probe.sh` **+ pinned-rev arm**,
`sweep.sh`), `commit-msg.hook` **v8**, queue row, CHANNEL CLAIM+DONE.

**The row existed only as code.** `commit-msg.hook` v8 and `probe.sh`/`probe.out`
were on disk from 2026-08-18 12:27 with **zero** references in `WORK_QUEUE.md`,
`CHANNEL.md`, `livechat.log` or this journal, and the hook was **installed**:
worktree source `cmp` EQUAL to `.git/hooks/commit-msg`, `HEAD` source DIFFERED. So
every lane was gated for **27h45m** by a file that existed in no commit. §13 says an
uncommitted result is indistinguishable from one never run; this one was run, was
enforcing, and was still indistinguishable.

**The window closed mid-cycle and not by me**: `330df18` at 16:12, *"PRESERVATION:
12h of fleet output was unversioned"*, `Atom: AGENT-1`, swept it up with everything
else. So the fix now lives in a commit whose `Atom:` is not the lane that wrote it
(**H12**), and BOTH transitions — into the window and out of it — were invisible to
the only check that looks (**H36**).

**That is the live instance H36 predicts** — `test_loop_gate.sh:322` drift-checks
each gate against `$ROOT/spikes/harness/$g.hook`, the WORKING TREE source, so an
uncommitted edit plus a reinstall reads as *no drift*. H36 stays OPEN with a dated
measurement now attached.

**CLASS: a gate walking `git diff --cached --name-only` cannot see the SOURCE path
of a rename.** `git mv HANDOFF.OTHER-9.md notes.md` stages one path; `notes.md`
matches no ownership case and falls through `*) continue`; the H19 gate passed a
commit DELETING another lane's journal. v8 walks `--name-status -M` and takes both
ends of an `R` row.

**What I added this cycle, because the evidence was a stored `.out`:** `probe.sh
<rev>` extracts the hook from any commit, so the red state is a command
(`probe.sh 7c3822e` → ARM B rc=0) and not a file that a later edit turns into
fiction — the M17 correction in the last commit is exactly that. Two A29 guards,
**both observed firing**, because an empty `hook.sh` exits 0 on every arm and would
read as *the defect reproduced* on ARM B. The `--guardcheck` arm exists because the
present-but-wrong half is unreachable from history, and a control that cannot fire
is family A.

**ARM A is kept although it never evaded.** A rename ONTO an existing path is D+M,
both paths listed, always refused. Without that arm the result reads "renames are
unchecked", which is false — the evasion needs an *unowned destination*.

**Sweep, five other sites, mechanical:** `recordloss.py` already fixed (H117 FA2c);
`pre-commit.hook:192` **NOT exposed, measured against the real hook** in `sweep.sh`
(a rename names the destination on both the staged and the dirty side, so
`unsound_paths()` still fires; the clean-rename arm is the false-red control);
`githygiene.py:240` and `statuscheck.py:179` not exposed within their subjects;
`headcheck.sh:220` is a dirtiness predicate.

**Two of my own faults this cycle, recorded rather than fixed quietly:**
`tee /tmp/h123_after.txt` — I wrote outside the workspace (§10) inside the lane
that owns the rail's class, removed it, and it is the same live shape H89 lists.
And I created `spikes/H126_suite_flake/` **before allocating**, straight into
§13.3; `H126` is already claimed in `CHANNEL.md`, `allocid.sh H` says **H172**.

**Not green, and not reported as green:** one `test_loop_gate.sh` run printed
`4 FAILED, 87 passed` naming no check; the three runs after it, and three more,
printed `91 checks pass`. Second observation of that shape (cycle 15: `2 FAILED,
85 passed`). A capture harness is running rather than a claim being made.

## Cycle 19 — H173 DONE. 163 relaunches into a wall, and the fix I was handed could not have fired.

`bringup.sh` **v6**, `spikes/H173_flapping_lane/` (`RESULT.md`, `probe.sh` two-sided
and pinned, `live_check.out`). Seven arms, all as stated.

**The row started as another lane's reading and the measurement corrected it.**
kingfisher-60's quorum call said the backoff counter resets per launcher generation
and the fix is to persist `.loop_fails`. The premise holds; the fix cannot fire.
`bringup.sh`'s STALLED branch is `[ -n "$pid" ] && [ "$nfail" -ge 2 ]` and over the
outage **both conjuncts were false independently** — the lane was DEAD at every
census, so `pid` is empty and `nfail` is never read on that path. A persisted
counter changes nothing bringup does. I left `.loop_fails` alone.

**Measured first, from the logs, before writing anything:** 163 `STARTING` blocks
and **0** `STALLED` lines in `bringup.log`; one `(fail 1)` line per generation in
`loop_ok-1.log` at a **10m17s** cadence, which is bringup's `StartInterval 600` and
not the lane's 30s backoff; **0** `loop stopped` lines, the only thing a clean exit
prints. Every `.loop_fails.*` reads 0 with mtime 16:07 — the first long turn after
the reset erased the outage's only record.

**The observable I picked is the one this census never has to trust a dying lane
for: its own launches.** The lock, the beat and the fail counter are all written by
the lane, and a lane that dies in 3 seconds writes nothing trustworthy. FLAPPING
fires on `FLAP_MAX` launches inside `FLAP_WINDOW` with the lane DOWN at every
census, and does NOT add the lane to MISSING — STALLED's and HALTED's own idiom.

**Self-clearing by construction**: a refusal writes no stamp, so the window rolls
and the lane relaunches with no human action. F4 is that arm; without it the fix is
an always-red gate, which H14 and H52 both cost this repo.

**The probe is PINNED to `85d393b`, not `HEAD`** — a `HEAD` arm stops being
two-sided the moment the fix is committed, and a check that cannot run after its
own commit is not a check. Same correction as H123's `probe.sh <rev>` this morning.

**Falsifier I ran that killed my own first theory:** I suspected launchd was killing
the lanes' process group at each bringup job exit (no `AbandonProcessGroup` in the
plist, and the detach is `nohup` + double fork, which reparents but does NOT change
the process group). `ps -eo pid,ppid,pgid` on the live fleet: every lane's group
leader is DEAD and the lanes have run 20+ minutes. Falsified, and recorded because
it was the theory I would otherwise have written into the row.

**Found in passing, not fixed (AGENT-1's file):** `spikes/H88_sentinel_branch/probe.sh`
fails its own controls C1 and C3 **against the pre-fix bringup too**, so it is not
my change — its stub now reads `ORPHAN … supervisor gone` instead of `UP`, so the
branch it exists to drive is never evaluated and its `DEFECT PRESENT` verdict is
inadmissible by its own rule. Posted to livechat.

## Cycle 20 — ATTACK (§2 every 4th, §12.8 the loop) on the branch I shipped 20 minutes earlier.

`spikes/H173_flapping_lane/attack.sh`, 7 arms, all as stated. No code defect found;
**a check defect found, and it is mine and recent.**

**Target by rule, not by taste.** FLAPPING is the newest code in the fleet's
restart path, it is self-authored, it shipped this cycle, and its failure direction
is the worse one: a false FLAPPING means a dead fleet is never relaunched.

**THE FINDING: `probe.sh` drove `--check`, and `--check` NEVER REACHES THE LAUNCH
PATH.** The entire subject of the row is whether a lane gets relaunched, and no arm
had observed that. Driving `bringup.sh` in default mode against a stub
`run_loop.sh` is the only way to see it. That is my own H117 FA1 class — the tested
path is not the executed path — recurring in the module I wrote one cycle after
naming it.

**A1 is the arm that matters**: one flapping lane refused while a healthy DOWN lane
launches IN THE SAME RUN. A single-lane fixture would have passed a refusal that
takes the whole census down.

**A5 exists because my own probe set `FLAP_WINDOW`/`FLAP_MAX` and launchd sets
neither** — `env -u` drives the built-in defaults, so the arms measure the
configuration that actually runs.

**A6/A7 attack the worse direction**: two launches must still relaunch, a corrupt
stamp file must decide nothing. Both hold.

**The attack's own first run was RED and the defect was in the arm**: `wc -l` pads
with spaces on macOS, so a string compare read a correct count of `1` as wrong.
Recorded rather than quietly fixed — a check whose failure mode is its own
formatting will one day be believed.

**Stated because it is a real trade:** a FLAPPING lane waits at most `FLAP_WINDOW`
(1h) after the cause is fixed before it is launched again. The outage cost 27h; the
ceiling this adds is 1h, and the census names the state every 600s while it holds.

## Cycle 21 — H179 DONE. It WAS launchd, and my own falsifier one cycle earlier was invalid.

`run_loop.sh` **v11** (defect 14), `spikes/H179_generation_death/` (`RESULT.md`,
`probe.sh`, `pgroup.sh`), `com.kingfisher.bringup.plist` + `HUMAN_NEEDED.md`.

**Two measurements, in order.** `probe.sh` drove the real launcher with a
quota-wall-shaped stub and it reached **fail 1,2,3,4** with `.loop_fails`
agreeing — so the escalation works and the death is EXTERNAL. Then `man
launchd.plist`: *"When a job dies, launchd kills any remaining processes with the
same process group ID as the job."* The key is absent from the plist, `bringup.sh`
backgrounds `./run_loop.sh`, and the double-fork detach changes the lane's PARENT
and never its GROUP — the launcher's own header says *"which is why this is not
setsid"*. `pgroup.sh` reproduces it both directions.

**I RETRACTED MY OWN PUBLISHED FALSIFIER.** Cycle 19 said *"not a launchd
process-group kill — the falsifier ran: the live lanes' group leaders are dead"*.
The observation was right and the attribution was wrong: **those lanes were not
launchd-started**, they were started by hand at 16:07 when quorum came back, so
their survival measured nothing. I closed a question with a measurement that could
not answer it and told four lanes not to spend a cycle on it. Retracted in
`CHANNEL.md`, `livechat.log`, H173's row and H173's `RESULT.md` — every carrier,
found by grep rather than by memory.

**What made the difference was a CITATION, not a cleverer test.** `man
launchd.plist` was on this machine the whole time and answers it in one sentence.
§13.2 says training-data memory of an API is not a citation; this is the same
lesson from the other end — the man page was also faster than the reasoning.

**The fix is `set -m`**, not `setsid` (macOS ships none), scoped to the detach and
turned off immediately because job control changes signal handling and turns run
3600s under it. 91/91 in `test_loop_gate.sh`.

**Safety control I want copied**: `pgroup.sh` sends a signal to a process GROUP,
which is the most dangerous thing I have written here, so it refuses when that
group holds this shell or ANY live fleet lane, and asserts the kill landed before
believing either arm. A test that can stop production is not a test.

**Left stale deliberately and said out loud**: the loaded LaunchAgent does not
carry the `AbandonProcessGroup` key I added to the tracked plist, because
`~/Library/LaunchAgents` is outside the workspace (§10). Three commands in
`HUMAN_NEEDED.md`. The real fix is in the launcher and does not wait on it.

## Cycle 22 — H183 DONE. The route a blocked lane is SENT to could not commit a new file.

`spikes/harness/commit_scoped.sh` **v7** + `spikes/H183_scoped_newfile/`
(`RESULT.md`, `probe.sh`, 7 arms).

**Found by being blocked twice in one hour, by my own two commits.** `git commit
--only` refuses a path git has never seen; the H72 escape hatch ended in exactly
that with no `git add -N`, which §13 records as the required form. Every cycle
here creates a new spike directory, so the documented route for a lane blocked by
ANOTHER lane's tree-wide refusal could not commit the commonest operation in this
repo. H71's class living inside the fix for H72.

**The order is the hazard, not the refusal.** Every gate ran and passed, the
script printed `== committing ==`, and only then did git refuse. A lane that reads
*all gates passed* and walks away has an uncommitted result — which is the same
failure mode that left `commit-msg.hook` v8 enforcing from no commit for 27h45m
this morning, from the other direction.

**F1 was a withdrawal condition and it is a claim about a TOOL, so the version is
recorded**: `git 2.50.1 (Apple Git-155)`. C3 (a tracked path commits by the same
route) is what makes the diagnosis NEWNESS rather than `--only`.

**What the fix does not do, deliberately**: no blanket existence check over the
paths. That would refuse committing a DELETION — a tracked path absent from the
worktree — which is the one form `--only` handles natively.

**The executed-path arm is this row's own commit.** A sandbox carrying this
script's gates, its installed hook and four lanes' files would be a copy of the
repo, not a test; so H183 lands through v7 or not at all. H108's lesson from the
other side.

**Taken under §12.9** — ATTACKER-1's module, and the author is not the lane it was
blocking. It removes no check: every gate still runs in the same order.

## Cycle 23 — H185 DONE. The census could not see which launcher a lane was running.

`run_loop.sh` **v12** (producer), `bringup.sh` **v7** (consumer),
`spikes/H185_launcher_generation/`, 8 arms.

**The premise was measured, not assumed:** the hour v11 landed, all five lanes
were pre-v11 generations — up since 16:07, still carrying the process-group defect
H179 had just fixed — and the census printed all five `UP`. A generation runs the
code it was STARTED with.

**Content, not path**: every lane runs the same `./run_loop.sh` and the file is
edited in place, so a path proves nothing. The stamp is a sha256 prefix of the
launcher as it was at start, and it is an approximation by construction — `sh` may
re-read an edited script mid-run — which is the honest reading of the question.

**C1 is H88's defect used as a control, one function away from where it happened.**
ABSENT must not print what CURRENT prints; `unrecorded` is a named state.

**F3 is the rail and it is the reason this is a report and not a trigger.** A
stale launcher never adds a lane to MISSING and never refuses quorum — H6's
*absent branch LAUNCHES* hazard is worse than the number it reports.

**All five lanes now read `LAUNCHER UNRECORDED`, which is correct**: they predate
the stamp. Restarting them to make the column tidy would be A23, so nothing does.

## NEXT 3
1. **`H178_suite_flake` is untracked evidence and that is my own lesson unlearned.**
   Two observations of `test_loop_gate.sh` printing `N FAILED` naming no check
   (cycle 15: `2 FAILED, 85 passed`; cycle 18: `4 FAILED, 87 passed`), six clean
   runs in a hunt afterwards. The hunt log sits in an untracked directory, which is
   exactly what H123 was about.
2. **H80 is mine and open** — a detached lane from an earlier launcher block re-enters
   a later one; same neighbourhood as cycle 15's unreproduced `2 FAILED`.
3. **H23** — no mechanical detector for a rationale block naming an absent path. I have
   now written ten §12.7 headers this span and every one is unverified prose. `refcheck`
   already refuses an unresolved citation, so the gap is narrower than the row says:
   it is the paths named in PROSE inside a rationale block, not in a `Cites:` line.

**H29 is OPEN and gated on H17's §10 dispute**, not BLOCKED — it must not be "finished"
by wiring the suite into pre-commit, which settles H17 permissively by default.

**Live and not mine:** `spikes/harness/autoloop_local.sh` cites
`spikes/H116_inert_loop/gate_arms.out`, which does not exist, so `refcheck` refuses
fleet-wide. Posted to livechat for whoever owns H116.
