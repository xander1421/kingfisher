# HANDOFF.ATOM-3.md — write-ahead journal, single writer: ATOM-3

Created 2026-08-17, cycle 1 of this span. Per H10 one journal per lane, one
writer each; `HANDOFF.md` is AGENT-1's, `HANDOFF.ATTACKER-1.md` is ATTACKER-1's,
`HANDOFF.AGENT-2.md` and `HANDOFF.ok-1.md` likewise. Refreshed at the end of
every cycle (§6): a crash costs at most one cycle.

**Read this file as suspect.** Four §12.5 violations stood in `HANDOFF.md` while
`journalcheck.py` ran green, because every one renamed the work between the NEXT
and the DONE (H5). Nothing below is renamed between the two lists; the ids are
`WORK_QUEUE.md` ids and `WORK_QUEUE.md` wins any disagreement (H28).

---

## Identity, settled before any work (brief §0)

`CALLSIGN=ATOM-3`, claude pid 44527, wrapper 44512 (ppid 1, self-detached),
`.loop_lock.ATOM-3` = 44512, live.

A peer reported that an interactive session (pid 2950) also identifies as ATOM-3
and that I was launched onto a held callsign — H8, caused by that peer, disclosed
by it. **Settled by the repo's own allocator, not by argument:** `run_loop.sh`'s
H8 block says *"the holder is RECORDED rather than inferred ... which is
`cat .loop_lock.AGENT-2` and needs no ps at all."* An interactive session holds
no lock. It is also the same identity's earlier session, which itself posted
`RELEASE ATOM-3 H-class -> ok-1` on the ground that it "cannot run cycles". Said
so rather than stopping; a dead lane has no next cycle.

**Two things in `prompts/ATOM-3.md` are stale and I am not the author, so this is
the changelog line the brief asks for:**
1. It says class H is mine as elder candidate. My candidacy was **REJECTED**
   (`CHANNEL.md:116`, two REJECT verdicts) and I **released** class H to ok-1.
   I took H6 under §12.9's "either rower may fix one", not by ownership.
2. Its §0 check `ps -eo command= | grep -c 'You are ATOM-3\.'` counts **turns in
   flight**, not holders — it reads clear on a held callsign between turns. The
   peer patched it to `.loop_lock.ATOM-3` with absence meaning UNKNOWN, never
   CLEAR. Confirmed correct; `MISSIONS.md` on disk already records both my
   rejection and the release, so the artifact is right and only prose about it
   was stale.

---

## DONE this span

- **H6 (detector half)** — `spikes/H6_liveness/`, `RESULT.md` + 9 checks.
  **CLASS: a census that cannot see its own observer.** `man pgrep` (-a) excludes
  the caller *and all its ancestors*; a lane running a census is always that
  census's ancestor. Measured from inside ATOM-3: `./bringup.sh --check` printed
  `ATOM-3 DOWN`, `quorum: 3/4`, exit 1, with pid 44527 live. Four sites fixed in
  two `bringup.sh` copies; the fifth (`whois.py:74`, AGENT-2's) left RED in C4b
  rather than whitelisted. Second half of the finding: the row's own premise —
  `.heartbeat.$CALLSIGN` "exists to watch" — could not detect lane death at any
  threshold, because the beat is written once per turn and a turn is legal to
  `MAX_TURN=3600`. Liveness moved to `ps` + `.loop_lock` (no threshold); the beat
  repurposed to watchdog-failure detection. `test_loop_gate.sh` 62/62 after.

- **H53** — the CHANNEL/QUEUE status divergences, verified one at a time against
  the artifact. Six were **three different defects wearing one uniform**, which
  is why none had been cleared: 2 genuinely stale and now closed (**H31**,
  **H32** — each a live SELECT hazard), 1 one-id-two-works (**H11**, stays OPEN,
  `run_loop.sh:316` still clears the fuse per turn), 2 renumbered ids the checker
  cannot follow (**H17**→H22, **H20**→H25), and **H2** re-verified still open and
  wider — `check_live_launcher.sh` REFUSES, 20 of 21 live launchers predate
  `run_loop.sh`, so every launcher fix made today is in no running lane. All four
  residual rows now carry their adjudication in the row itself.
- **H60** — `spikes/harness/headcheck.sh`. **`refcheck.py` refused on HEAD for
  hours while every lane's local run was green**, because the checkers read the
  working tree and each lane's tree contains its own uncommitted work — so the
  lane causing a refusal is the one lane that cannot see it. H35's class, 5th
  site. **All six unresolved paths existed on disk and had never been committed;
  none was a dangling citation, and two are FINISHED SPIKES** (S85 15:32, W6
  16:11). I committed only my own (`net.kingfisher.fleet.plist`, 7→6) and
  reported the rest per owner — H19 is the recorded cost of sweeping another
  lane's work. `refcheck.py` untouched and un-narrowed (H26b). Commits
  `59c7168`, `a8ff03e`.
- **H52 filed** (not fixed, another lane's file): a checker with a permanent
  non-zero floor is read as background noise, and that floor is what hid H31 and
  H32.
- **`prompts/ATOM-3.md` §0 guarded**, with a changelog line: it prescribed
  `./peers.sh` UNGUARDED — the section a lane runs before anything else, telling
  it to run a script that did not exist (H23's class). `peers.sh` landed at 14:15
  and refcheck is green again.

- **H44** — `spikes/H6_liveness/test_h44_check_is_readonly.sh`, 15 checks, C1 is
  the falsifier. **Which of the two `bringup.sh` is real was decided by MEASURING
  launchd, not by choosing**: one job is loaded and its `ProgramArguments` names
  `./bringup.sh`; the fleet plist naming the other copy was never installed. So
  *"two live LaunchAgents"*, the premise of my own CLAIM line, was false. Two real
  defects found while measuring, both mine, both in `spikes/harness/bringup.sh`:
  `--check` — documented "verify only" — **reinstalled `.git/hooks` for every lane
  in this working tree and deleted loop state**, because `CHECK_ONLY` was tested
  at one site out of three; and the stale-signal sweep took **every** lane's
  `.loop_exit.*`, so a live lane could lose its own terminal signal in the window
  between the Stop hook writing it and `run_loop.sh` reading it — H16 inverted,
  and silent where H16 is loud. **CORRECTED, three false facts in my own row**:
  `163 lines`, `228 lines`, `UNTRACKED`; the second copy has been TRACKED since
  `600d138` (13:56), 28 minutes before I wrote UNTRACKED, and the counts were 230
  and 273. Also `H55`, cited in both headers as the consolidation row, was never
  a row — refiled as **H58**. Commit `c6439ae`.

- **H59 (ATTACK, the loop — §12.8)** — `check_live_launcher.sh` **v2**. The
  component that decides whether any harness fix is RUNNING compared a process's
  start against the launcher's **working-tree mtime** while printing the verdict
  `running PRE-FIX code`. A touch, a checkout or a lane mid-edit moved the first
  and not the second, so the fleet read STALE one second after anyone opened the
  file. **Contradicted by an observable, not by argument:** v1 refused 25 of 25
  while `cc1da90` — H48's mid-turn beater, `BEAT_EVERY=30` — was demonstrably
  running, every heartbeat under 30s. Fixed by comparing against the newest
  COMMIT; uncommitted edits reported, not counted; no write of any kind.
  `--selfcheck` now calls the same `launcher_ref()` the body does and goes red on
  a revert (verified). **Both historical verdicts re-decided and NOT retracted** —
  the defect made GREEN unreachable, it did not make those alarms false.
  **Consequence for the fleet, and CORRECTED within the hour:** at 16:08 the
  check exited 0 — the cutover was complete *for `cc1da90`, as of 14:29:16*. I
  published that as "the H21 cutover is DONE", undated, and `90decab` (H56,
  `run_loop.sh` v9) landed at 16:15:42 and made it false. **The fix is working
  and this refusal proves it**: v2 gave opposite, both-correct verdicts eight
  minutes apart — `EDIT IN FLIGHT` + exit 0 for an uncommitted edit no process
  could carry, then a refusal on a committed fix that genuinely is not running.
  v1 could not have told those apart. Commit `f9d1e86`.

- **H43** — `bringup.sh` **v3** + `spikes/H6_liveness/test_h43_work_signal.sh`,
  7 checks. **The cure for the wedged lane had a trigger that cannot fire for
  it**, decidable from the code with no run: `.loop_fails` climbs only where
  `elapsed < 60` and STALLED needs `nfail >= 2`, so a lane with slow
  unproductive turns resets the counter every turn and reports plain UP. Wider
  half: **nothing in the harness observed WORK** — every signal watched the
  supervisor, the turn boundary, or the turn's duration, which is H56's own
  class inside the fix for it. Fixed with §14.2's observable, as a column with
  **no threshold** (C5 fails if it ever gates quorum). **Not commit recency** —
  ok-1 measured at 16:25 with a 2h-old commit while writing its journal.
  **F2 fired against my own first fix**: a distance from the end of an
  append-only file freezes on a silent fleet, so an absolute fleet-output age
  was added. Commit `5437981`.

- **H36** — `test_loop_gate.sh`'s gate-drift block compared the WORKING TREE and
  reported *"gate matches its tracked source"*. Instance 3 of H35's class, open
  since midday, unclaimed. **Only the word was wrong, and the falsifier decided
  that rather than my preference**: `install_hooks.sh:35` copies from the tree,
  so the comparison is a tree question — had it read HEAD, the comparison would
  have been the defect and the message fine. Messages corrected, plus an `info`
  line per gate answering what the old wording claimed (is the ENFORCED gate in
  any commit), **informational and never a verdict** — a bare HEAD compare
  reddens the suite for any author with an uncommitted hook edit installed, which
  is H52's floor. Both of the row's recorded blockers re-checked and cleared
  first; the live instance had also cleared and I did **not** close it on that.
  Falsified two-sided on the real installed gate. Commit `c8e1f50`.

- **H66 filed, and it is a DISCLOSURE against me.** `c8e1f50` carried **78 lines
  of ok-1's in-flight H63 work** under `Atom: ATOM-3`. I used `git commit --only`
  exactly as §13 prescribes and `git status --porcelain` on the file was EMPTY
  before I edited it. **CLASS: `--only` protects against the shared INDEX, not
  against a shared FILE** — it commits the working-tree content of the paths you
  name, so a concurrent writer's bytes ride along. H19's remedy is complete for
  the defect H19 measured and silently incomplete for this one. **The only thing
  that caught it was the commit stat** (112 insertions against ~30 written) —
  second time today the stat was the sole instrument. Two more the same turn in
  the benign direction: two `--only` commits landed **0 changes** because another
  lane had already committed the file carrying my lines, and *that* direction is
  the one nobody notices. No history rewritten (§13); handed to the commit-gate
  owner rather than fixed by me.

## NEXT, in order

1. **H58 — the two `bringup.sh` are still two implementations.** Filed, not
   started. H44 settled which is the entry point and made them agree
   about the fleet; it did not merge them. Merging means one script with a mode
   flag, and H44's own finding is that this file's last mode flag wrote to
   `.git/hooks`. Any merge that moves the entry point goes to `proposed/` (§10).
2. **A turn-level productivity test in `run_loop.sh`.** H43's residual, recorded
   in `DECISIONS.log` rather than left implied: the `elapsed >= 60` reset is the
   natural site for "did this turn produce anything", and today was the wrong
   day to edit that file — three lanes touched it this hour and H59 measured 25
   of 25 processes predating the current commit. Needs a fleet-quiet moment.
3. **`headcheck.sh` is still red on five paths owned by other lanes** (H60).
   Not mine to commit; re-check it each cycle and chase if it persists.

## Standing question each cycle (the one no rowing lane asks)

What regressed **between** lanes since I last looked — a grade that moved with no
LEDGER row, a retraction that reached `CHANNEL.md` and not the file it retracts
(LEDGER standing rule 12), a checker that went green by narrowing its own scope
(H26b), a control that cannot fire.

Live answers carried forward, re-measured at 16:08 this cycle:
- **H48's mid-turn heartbeat is now LIVE in all five lanes** — every
  `.heartbeat.*` reads ≤9s old. Its own DONE line recorded it as "DONE ON DISK
  AND INERT FOR EVERY SPAN NOW RUNNING (H21's class)", so that caveat is spent
  and the beat is no longer the 2500s-stale signal I misread the fleet as dead
  on. This is the answer to the standing question this cycle: the thing that
  changed between lanes is that an H21-flagged inert fix became real.
- **`check_live_launcher.sh` is the answer; no sentence of mine is.** It read 0
  at 16:08 (all 25 at or newer than `cc1da90`) and 1 at 16:2x (all 25 predate
  `90decab`, H56's v9, committed 16:15:42). Both correct. **A fleet-state fact
  has a shelf life of minutes here — run the check.** *Superseded within the cycle: this
  entry first read "REFUSES (exit 1) — 25 of 25", which was the v1 defect fixed
  under H59 below, not a fleet stall.* The original reading: The launchers started 15:56:02–15:56:08; the file
  is dated 16:04:09, and the newest COMMIT touching it is `cc1da90` at 14:09,
  so a lane is sitting on an UNCOMMITTED `run_loop.sh` edit right now. The
  checker compares process start against the launcher's CURRENT MTIME, so **any
  lane editing that file makes the entire fleet read STALE within the second**
  — H52's class (a checker with a permanent non-zero floor is read as
  background noise) at a second site. REPORTED, NOT FIXED: the file has a live
  editor in it, and the module is not mine.
- I first read this checker as exit 0 while it printed `REFUSE`. It did not:
  I piped it through `tail` and read **`tail`'s** status. `$?` after a pipeline
  is the last command's. Family B, on the instrument reading the instrument.
- `idscope.py` REFUSES on 5 ids and CANNOT reach zero (H52). Four are correct
  by its own design; the fifth is mine — `DONE H50 ATOM-3` in the append-only
  log against AGENT-1's OPEN `| H50 |` row. Adjudicated in the H53 row, not
  clearable.
- `cite.py` exits 1.
- `refcheck.py`, `journalcheck.py`, `githygiene.py`, `rostercheck.py` all exit 0
  after this cycle's edits.
- `bringup.sh --check` reports `ok-1` OFF-ROSTER while `CHANNEL.md:180` records
  the operator declaring it the fourth lane — the two-roster dispute is **ok-1's
  H38** and is not mine to adjudicate in passing.

## Errors this span, mine, every one (§14.5: not a representative sample)

1. **I read the whole fleet as dead** on a 23-minute-stale `.heartbeat.*` at the
   top of the cycle. Three lanes were healthy mid-turn. Corrected by `ps` before
   acting; it is why H6 was taken, and it is in `RESULT.md` and `CHANNEL.md`
   rather than only here.
2. **The H6 control failed to fire twice, and both failures looked clean.**
   (a) the marker sat past macOS `ps` line truncation, so *both* arms read empty
   — including the positive control (A29); (b) the search was `grep -v grep` and
   the target's own argv contained `grep`, so the filter deleted the target —
   one-sided, so it read as confirmation. Same family as the defect under test.
   Caught by me, before publishing, only because the arms disagreed with the
   four-lane observation.
3. **I nearly built the wrong instrument twice.** First a poll loop touching the
   beat during a turn — abandoned after observing that `claude -p` buffers, so
   `loop_$CALLSIGN.log` grows only at turn end (mine was 0 bytes 24 minutes in):
   a control that cannot fire. Then a pidfile — abandoned on finding
   `.loop_lock.$CALLSIGN` already in the tree from AGENT-2's H8. Both avoided by
   checking, neither by foresight.
4. **I allocated another lane's id and my DONE line closed their OPEN row.**
   `H50` is AGENT-1's. I allocated with `grep ... | sort | tail` over a namespace
   three lanes are writing — stale the moment it returns — while
   `sh spikes/harness/allocid.sh H` had existed since 14:06, six minutes earlier.
   `idscope.py` went 4 → 5 divergences **on my own edit**, and it is H11's shape
   (one id, two pieces of work) reproduced inside forty minutes of my writing the
   queue row that documents it. Renumbered myself to H53, and my H51 row to H52
   after finding `CLAIM H51 AGENT-1` predated it. Caught by reading the commit
   stat — `1 file changed, 1 insertion` when I had edited five rows — not by any
   check.
5. **I took a peer's report about its own artifact at face value for one
   exchange.** AGENT-2 said whois.py's self-blindness was "stated in the commit
   and in the docstring". It is in `b403300`'s body and **not** in the file.
   Family D, applied to a peer instead of to data. Checked both before writing
   the row.
6. **THREE FALSE FACTS IN THE HEADER OF THE ROW ABOUT THOSE TWO FILES** (H44).
   `163 lines`, `228 lines`, `UNTRACKED`. Measured once, early, then restated
   unchanged in four documents over half an hour, one of them written 28 minutes
   after the fact stopped being true. **CLASS: a prose header asserting a
   checkable fact about another artifact, with nothing checking it.** Caught by
   me, this cycle, only because H44 forced me to resolve the citations
   mechanically — not by any check, and not before I had published three of the
   four sites. Fixed by DELETION where the fact carries nothing (`wc -l` gives it
   free) and by C10/C11/C12 where it decides something.
7. **I invented an id in prose.** Both headers cited `H55` as the consolidation
   row; H55 was never a row, and by the time I resolved it `.ids/` showed
   H55–H57 belonging to other lanes, so the invented id had become someone
   else's real one. §12.4 exactly: a citation to a missing artifact reads as
   satisfied. Refiled as H58 through `allocid.sh` — the mechanism that already
   existed when I made my *previous* id error (§14.5: same error, not paid for
   twice, except I did).
8. **Four of my own checks failed before they passed, each in the family it was
   built to catch.** C7 could not express its verdict (`eval` + `exit 1` kills
   the command substitution, so only the non-exiting arm could report — A29's
   direction). C10 and C12 fired on the CORRECTION BLOCK quoting the text they
   hunt, which is ATTACKER-1's H48 class and makes §5 and the gate contradict
   unless the gate is scoped. C11 matched a path out of a plist COMMENT and
   reported launchd running it. All four caught by running them, none by
   foresight.
9. **I stated a checkable fact I had not checked, three times in one turn, in
   the rows I filed to name that exact defect.** (a) H44's header: "UNTRACKED,
   228 lines" about a file tracked for 28 minutes. (b) H60's CLAIM line: "4
   absent from disk too", marked *Already run*, when I had `ls`-ed three paths
   and asserted about seven — all four existed, so the error made my own finding
   look weaker than it was, which is not the direction wishful thinking pushes.
   (c) H59's DONE: "the H21 cutover is DONE, exit 0", published undated, false
   ninety seconds later when `90decab` landed. **CLASS: a statement about an
   artifact that nothing re-derives from the artifact.** All three corrected in
   place; none caught by a check, all three caught by re-measuring for the next
   row. The mechanisms now exist at all three sites (C10/C11/C12,
   `headcheck.sh`, and "run the check, do not quote a sentence about it").
10. **I committed another lane's in-flight work under my Atom trailer** —
    `c8e1f50`, 78 lines of ok-1's H63. I used `git commit --only` exactly as §13
    prescribes and `git status --porcelain` on the file was empty before I
    edited. **CLASS: `--only` protects against the shared INDEX, not against a
    shared FILE.** Caught by the commit stat and by nothing else — second time
    today the stat was the sole instrument (error 4 was the first). Disclosed in
    `CHANNEL.md`, filed as H66, handed to the gate's owner, no history rewritten.
11. **I finished H36 and left it uncountable for twenty minutes.** Recorded in
    `WORK_QUEUE.md` and in the commit, no `CHANNEL.md` DONE line — and §14.2
    makes that line the definition of a big cycle, so
    `grep -c '^DONE' CHANNEL.md`, the number the operator watches, did not count
    it. Caught by my own end-of-turn check that every line I posted is in HEAD,
    which I ran only because H66 had just taught me that a successful commit is
    not evidence the record landed. **The check that caught it existed because of
    the error before it**, which is the only reason it was caught at all.
12. **§10 rail slip, mine.** My first falsification probe ran in `mktemp -d`,
   i.e. `/tmp` — outside the workspace, which is H17's open row — while working a
   harness row. No workspace-external file survived, and both permanent artifacts
   scratch inside the tree, but the slip is in `DECISIONS.log` rather than
   nowhere.
