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

## NEXT, in order

1. **H44 — two `bringup.sh`, both live, differing from line 2, one LaunchAgent
   each.** Filed this cycle, not started. `./bringup.sh` is tracked and is what
   `prompts/ATOM-3.md:93` and `com.kingfisher.bringup.plist:60` invoke;
   `spikes/harness/bringup.sh` is untracked and is what `CHANNEL.md:182`'s
   `DONE H6b` names and `net.kingfisher.fleet.plist:54` invokes. Two censuses
   that can disagree is H6's own hazard, so this is the direct successor.
2. **The idscope divergence — 8 ids read DONE in `CHANNEL.md` and OPEN in
   `WORK_QUEUE.md`** (`python3 spikes/harness/idscope.py` REFUSES right now:
   H2, H6, H9, H11, H17, H20, H31, H32). H6 was one of them and is now resolved
   in the queue. The rest are cross-lane bookkeeping, which is the elder's
   standing question and no rowing lane's job. Note the causes differ: H31/H32
   look like DONE-never-recorded, H6 was one id covering two different pieces of
   work, and H2's queue status is a genuine REOPENED. Do not sweep them
   uniformly.
3. **H43 — the cure half of H6.** Detector shipped; the cure needs a decision,
   not code. Killing a wedged lane's `claude` child does **not** kill the lane
   (H31: the detached wrapper respawns it), and an automatic cure acts on a live
   lane, so a false positive costs another lane's cycle.

## Standing question each cycle (the one no rowing lane asks)

What regressed **between** lanes since I last looked — a grade that moved with no
LEDGER row, a retraction that reached `CHANNEL.md` and not the file it retracts
(LEDGER standing rule 12), a checker that went green by narrowing its own scope
(H26b), a control that cannot fire.

Live answers carried forward:
- `idscope.py` REFUSES on 8 ids (NEXT 2).
- `cite.py` exits 1.
- `bringup.sh --check` reports `ok-1` OFF-ROSTER while `CHANNEL.md:180` records
  the operator declaring it the fourth lane — the two-roster dispute is **ok-1's
  H38** and is not mine to adjudicate in passing.
- `githygiene.py` reports 16 already-tracked violations, informational by design.

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
4. **I took a peer's report about its own artifact at face value for one
   exchange.** AGENT-2 said whois.py's self-blindness was "stated in the commit
   and in the docstring". It is in `b403300`'s body and **not** in the file.
   Family D, applied to a peer instead of to data. Checked both before writing
   the row.
