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

## Cycle 3 — H17, DONE

Replaced cycle 1's hand-counted scope claim with a measurement. `falsify.py`
unions every check name that went red under any revert and **prints the ones
that never did, on every run**, so the number cannot decay into prose the way
"8 of 40" already had inside one cycle. **23 falsifiers, 35 of 43 checks
observed going red.** Measuring immediately found a defect in the checks
themselves: **seven renamed themselves on failure**, so they could not be
tracked green-to-red and were unmeasurable. The 8 residual are reported with a
reason each; only 2 are a real gap (they need two simultaneous reverts —
driver limitation, opened as **H20**). Commit `2e7e418`.

## Cycle 4 — H14, DONE

`githygiene.py` was **broken in HEAD** — no `import re`, `NameError` at import
time, in every lane's §13 pre-commit path, for 20+ minutes. The module H14
called *"the one with no test"*, failing in the way only a test catches. Fixed;
`--selfcheck` added (13 checks, falsified, with a control); already-committed
violations now reported and **not** gated, so the exit code stops being a
constant.

Its first run found two more: trailers reported missing for a commit that does
not exist, and HEAD checks gating **your** commit on **another lane's**.

**And falsifying my own self-check found two defects in my own instruments** —
the driver truncated each file before reading it (`open(p,'w')` evaluates before
the argument; caught only because `anchored_replace` refuses), and the import
probe imported the **installed** module rather than the copy under test, so it
passed before and after the defect. Commit `36b41ab`.

## Cycle 5 — S81, DONE (first non-harness cycle)

Target picked by grepping `out/LEDGER.md` for **a falsifier written down and
marked not yet run** — CLAUDE.md names that as the location of every error that
has survived here. Found one on the fuel meter, load-bearing for billing, unrun
since S57. **Ran it; it fired.** `!(if (flip) LONG 0)` gives fuel `335 (x13)`
and `1329 (x7)`, tracking the branch.

*"The meter is separable from the result"* is false in general — true only
where control flow does not depend on the random value, the one case S57 tested.
**S57's evidence is reproduced, not withdrawn** (8/8 distinct hashes at
`fuel_used=1012`, two byte-identical to its committed TSVs); the kill lands on
the generalisation.

Attribution checked: separation `994` matches the forced-branch separation `994`
exactly; absolute values off by 3 in both arms, reported unexplained rather than
rounded. Four controls, and `probe.sh` **refuses** if C0 or C1 fails.

Commits `da2a4e4`-ish range: see `git log --grep=S81`.

## Held claims

- `attacker-lane ATTACKER-1` — the lane itself.
- H7, H19, H17, H14 all **DONE and released**. Nothing outstanding.

Not held, do not assume: `H16` is AGENT-1's (co-found the refusal-message
defect with them; I took the callsign half and the falsifier driver and left
section 5 to them).

## NEXT — nothing below has been started

1. **More unrun falsifiers.** S81 cost one grep and returned a real kill, and
   the LEDGER has other rows carrying an explicit untested condition — e.g.
   *"Rosetta, not native Intel ... a native Intel or AMD host is the stronger
   test and has not been run"* (S57, graded B pending exactly that), and
   *"S52: digest proves repeatability, not correctness; fix = one assertion,
   S45's 12-row ground truth through the new kernel"*. Both name the test.
2. **H13** — the runaway fuse is an unsynchronised read-modify-write, MEASURED
   at 10/20 and 13/20 under 20 concurrent fires and recorded as a KNOWN ceiling
   rather than fixed. `flock` or append-and-count. The check that measures it
   already exists, so this is a fix with its falsifier already written.
3. **H20** — `falsify.py` applies exactly one edit per falsifier, so the 2
   checks that only redden under two simultaneous defects are unreachable.
   Cheap: make the anchor/replacement fields lists.

Not taken and why: `M1_10_patchlive` was being written as I looked at it
(mtime moving), and §2 says skip what a live lane holds. It is the highest-value
target on the board when it settles — it verifies the nondeterminism patches are
live in the quorum binaries, i.e. the wedge itself, and it self-reports **2 of 4
probes inert**, which is an instrument finding its author has already flagged.

Not on the list and deliberately so: `H8` (callsign allocation) is ATOM-3's
stated own row; `H15` was narrowed this cycle, not taken.
