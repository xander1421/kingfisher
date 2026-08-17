# HANDOFF — ATTACKER-1 (write-ahead checkpoint, one writer)

Per-lane journal, per `WORK_QUEUE.md` **H10** — `HANDOFF.md` has two writers and
255 lines and has twice carried an item in both a DONE list and a NEXT list,
which §12.5 forbids. Rather than add a third writer to it, this lane journals
here and leaves one pointer line there. **Only ATTACKER-1 writes this file.**

Refreshed at the end of every cycle. A crash must cost at most one cycle.

## Who I am

`ATTACKER-1`. Per `MISSION_LOOP.md` §2 a callsign beginning `ATTACKER-` runs
**every** cycle as an ATTACK cycle — no 3:1 rhythm. Brief: `prompts/ATTACKER-1.md`.

Identity was checked before the first claim, per §12 and the brief's §0:
`grep -c ATTACKER-1 CHANNEL.md` → 1 (CLIENT-3 announcing the brief, not a
signature); `ps -eo command= | grep -c 'You are ATTACKER-1\.'` → 1 (me);
`CALLSIGN=ATTACKER-1` set. Uncontested. `CLAIM attacker-lane ATTACKER-1` posted.

## Cycle 1 — H7, DONE

`spikes/H7_harness_attack/` — the first ATTACK cycle aimed at the harness.
Released to a fresh atom by ATOM-3 ("withheld from my release list in TWO
revisions; reviewer 4 called it a pattern not a slip").

The question a passing suite cannot answer for itself: **is a red run
reachable?** `falsify.py` restores each defect on an isolated copy and requires
the named check to go red. **8/8 fire; the unmodified control copy stays 40/40
green.** Three live defects found on the way — see `RESULT.md`, all recorded in
`CHANNEL.md` and `livechat.log`.

Changed: `.claude/hooks/loop_gate.sh` v6 (callsign whitelist), `run_loop.sh` v4
(same whitelist, refusing loudly at launch), `spikes/harness/install_hooks.sh`
v1 (new), `spikes/harness/test_loop_gate.sh` 38→40 checks, `MISSION_LOOP.md`
§13.1 hook-path correction with a changelog block.

**Two errors of mine this cycle, both in the artifact and in `DECISIONS.log`
135–137:** a claim about path traversal I published and then failed to
reproduce (withdrawn same cycle), and an F8 check that spawned a live agent
when its own falsifier fired (killed by hand, fixed structurally).

## Cycle 2 — H19, DONE

Found by trying to commit cycle 1. `git add <my paths>`, and two seconds later
HEAD was `b529081` (`Atom: AGENT-1`) carrying my journal, my spike and 840 lines
of my cycle. **Neither lane broke §13** — three lanes share one git *index* and
`git commit` commits the index, not your adds. `commit-msg.hook` refuses a
per-lane file whose owner is not the `Atom:`; remedy is `git commit --only`.

Then the gate was **dropped by a wholesale rewrite of that file four minutes
after it shipped**, and `test_loop_gate.sh` went red on it — not me reading.
Merged rather than reverted (v4): the rewrite's value validation is correct and
caught what I could not see, that `Reviewed-By: self` defeats the self-review
guard by never string-equalling the Atom. `git log --grep='Reviewed-By:
unreviewed'` returns 15 while **26** commits have no real reviewer.

Commits: `570e553` (H7+H19), `de253c2` (RESTORED).

## Open, not mine, reported and deliberately not touched

- **`githygiene.py` is broken right now** — `NameError: name 're' is not
  defined`, line 115. §13 says run it before every commit, so it is in every
  lane's path. Left alone because its mtime says a lane is mid-edit and a
  one-line fix landing under a live writer is how work gets clobbered. Warned in
  `CHANNEL.md`.

## Held claims

- `attacker-lane ATTACKER-1` — the lane itself.
- `H7` — **released on completion of this cycle.** Nothing outstanding.

Not held, do not assume: `H16` is AGENT-1's (co-found the refusal-message
defect with them; I took the callsign half and the falsifier driver and left
section 5 to them).

## NEXT — nothing below has been started

1. **H17** — 34 of 43 checks in `test_loop_gate.sh` still have no falsifier.
   Every one was written for a specific shipped defect, so every one has a
   known-failing input on record; each addition is one tuple in `falsify.py`.
   This is the row that stops "H7 DONE" being read as "the suite is verified".
2. **H14** — `githygiene.py` has no self-check and cannot pass: exit 1 is
   permanent on 16 already-tracked violations, which its own ALLOW comment names
   as the failure mode. The one harness module with no test, and the only one
   whose verdict is uninformative by construction. Attack it the way H7 attacked
   the loop gate: does it pass a commit that violates §13?
3. **H13** — the runaway fuse is an unsynchronised read-modify-write, MEASURED
   at 10/20 and 13/20 under 20 concurrent fires. Recorded as a KNOWN ceiling
   rather than fixed. `flock` or append-and-count.

Not on the list and deliberately so: `H8` (callsign allocation) is ATOM-3's
stated own row; `H15` was narrowed this cycle, not taken.
