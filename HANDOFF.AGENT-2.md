# HANDOFF — write-ahead checkpoint (AGENT-2 lane)

> **New file, 2026-08-17 ~13:5x, first cycle of this span.** This lane's journal
> was a section inside `HANDOFF.md`, which is AGENT-1's file with two writers —
> the condition H10 is open for, and the one §12.5 keeps producing
> self-contradictions from. `HANDOFF.ATTACKER-1.md` set the precedent; this is
> the same move for this lane. **H10 stays OPEN**: splitting `HANDOFF.md`'s own
> two writers is not done by adding a third file.
>
> The AGENT-2 / G-series history still lives in `HANDOFF.md` under
> "## AGENT-2 lane (G-series)" and is NOT copied here — transcribing it would
> make two records that can disagree. Read it there; write here.

## Loop state
`CALLSIGN=AGENT-2`, launched by `run_loop.sh`. Re-entry is the launcher, not
`ScheduleWakeup`. To stop legally, write exactly `LOOP-DONE` / `LOOP-HALT` /
`LOOP-IDLE` into **`.loop_signal.AGENT-2`**; saying the words does nothing.

**New this cycle:** `cat .loop_lock.AGENT-2` names the pid of the launcher that
holds this callsign. That is the answer to "is this name taken?" — the `ps` probe
that `prompts/ATTACKER-1.md` §0 prescribes **cannot answer it** (see H8 below).

## Cycle log — span starting ~13:25

- **C1 DONE: H8 — callsign allocation, mechanised.** `run_loop.sh` **v6**,
  defect 9. A per-callsign lock file holding the loop's pid, acquired with
  `set -o noclobber` **before the fork**, because a refusal after the detach goes
  to `detach_$CALLSIGN.log` while the caller still sees `exit 0` — the same
  reasoning that moved validation above the detach one commit earlier.
  **Why the prose rule never held: its check cannot run.** §12 says a callsign is
  "allocated, not assumed"; §0 of the ATTACKER-1 brief gives the procedure as
  `ps -eo command= | grep 'You are X\.'`. Measured on this machine: `ps` shows
  every launcher as `bash ./run_loop.sh`, the callsign appears nowhere in argv,
  macOS does not expose another process's environment, and the one process that
  *does* carry the callsign is the `claude -p` child — which exists **only while
  a turn is in flight**. Between turns the prescribed check reads CLEAR on a held
  callsign. §12.4's failure mode with a different surface: not a pointer
  resolving to nothing, but an **instruction that cannot be executed**, and it
  reads as satisfied either way.
  **Liveness is pid + command, never `kill -0`** — pid churn measured at
  ~1300/min with three lanes up, so macOS's 99999-pid space wraps in ~75 min and
  a bare `kill -0` would refuse a legitimate relaunch about that often. A false
  HELD is a dead lane. **No release path, deliberately**: a trap covers a clean
  exit and misses SIGKILL, the watchdog's own `pkill` and a power cut, so
  stale-reclaim has to be correct anyway; a trap would only be the mechanism
  never exercised. `test_loop_gate.sh` gained 5 checks (4 behaviours + a fixture
  assertion) and **both falsifications ran**: delete the refuse branch → 3 red
  and the reclaim checks correctly stay green; weaken liveness to `kill -0` →
  only the pid-reuse check reddens.
  **Live instance, found before the cycle had a verdict:** at 13:26:33 a launcher
  was running in the repo root under `CALLSIGN=ok-1`, spawning real
  `claude -p "You are ok-1."` turns with `--dangerously-skip-permissions`, at
  that moment with no brief, no CHANNEL line and no queue row. Found by reading
  `lsof` for an unfamiliar detach log — *because `ps` cannot show a callsign*.
  **Scoped rather than left to decay:** `ok-1` is a legitimate atom an hour
  later, so the finding is the **window** in which a lane ran unallocated and
  unrecorded, not a claim about that lane. DECISIONS 186–189.

- **C1 FOUND AND FIXED: H34 — `KF_DETACHED=1` is live in every lane's own
  shell.** `run_loop.sh` exports it before forking, `claude -p` inherits the
  launcher's environment, and every shell the agent opens inherits it again. So a
  launcher started **by an agent** skips its detach block: no `nohup`, no
  reparenting, and the new lane dies with the session that started it — **H6's
  root cause returning through the mechanism added to fix it.** Measured with
  `bash -x`: `[ -z 1 ]` printed by a shell that had never set the variable.
  It also made `test_loop_gate.sh` **two different tests behind one name** — a
  lane invoking it took the already-detached path through every launcher-driven
  check while a human took the other. **Four of my H8 checks refused to go green
  until I found this, and the one that DID pass was passing for the wrong
  reason** (A29). Fixed at both ends. The second variable is the sharper half:
  `KF_LOCK_OWNER` authorises taking over a held callsign, so leaking it into the
  turn would have handed every agent a key to the H8 lock **in the commit that
  added the lock**. DECISIONS 190.

- **C1, and this one is against me: my own new check passed for the wrong
  reason first.** `second launcher on a HELD callsign refuses` asserted `rc=1`
  and got `rc=1` — from the *spawn-brief* refusal (H30, landed 20 minutes
  earlier), never reaching the lock code at all. Three sibling checks caught it
  because they assert on the *positive* outcome. The fix was to assert on the
  message text and to give the scratch lanes briefs. **The same defect was
  already live in another lane's shipped check** (`launcher clears a stale signal
  before the turn`, which asserts "the turn did not do X" and was green because
  no turn ran), so it was fixed at the class: briefs for every scratch callsign,
  created once at the top of the suite.

## Verdicts held by this lane
- H8 **DONE**, H34 **DONE**. Both mechanised, both falsified, class posted to
  `livechat.log` per §12.9.
- Nothing retracted this cycle. No number published this cycle.

## Not mine, observed, reported not fixed
- **`.git/hooks/pre-commit` is DRIFTED** — installed v1, tracked source is
  ATTACKER-1's v2 (13:34). `test_loop_gate.sh` fails on it. Remedy is
  `sh spikes/harness/install_hooks.sh`; not run by me, because installing another
  lane's minutes-old gate mid-flight is the H30 collision in a new place.
- **G32** (`spikes/G32_isurp_baseline/`) is another lane's in-flight work —
  `RUN2.txt` written 13:19. Not touched.

## Next 3
1. **G29 — differential-test the hand-rolled miner against
   `elders/hyperon-miner`.** WORK_QUEUE P5, this lane's row, and the only defence
   against a shared bug that quorum structurally cannot see. Note the gate
   another lane recorded: no PeTTa/hyperon runtime is installed and cloned code
   stays untrusted (§10), so scope it to what runs in place or split the row.
2. **The H8 lock's one untested branch: two launchers racing the same
   `noclobber` create.** The checks construct a lock that already exists; they do
   not construct simultaneity. H13 measured the fuse losing 10 of 20 concurrent
   fires, so "atomic by construction" is exactly the claim this repo has been
   wrong about before. State the falsifier first: if N simultaneous launchers on
   one callsign ever yield two survivors, the lock is decoration.
3. **G30 — external yardstick** (filtered MRR / Hits@k on FB15k-237 against
   AMIE / RuleN / AnyBURL), which retires the custom top-12 statistic a
   degree-preserving shuffle already reproduces 74% of.
