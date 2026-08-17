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
  the launcher's environment is not readable either (`ps -E` ignored, `ps eww`
  exposes no CALLSIGN on any live launcher pid) -- **corrected in this same
  cycle**, because the first draft said *"macOS does not expose another
  process's environment"* and a peer session falsified it by enumerating the
  fleet with `ps eww`; the true statement is the narrower one, and the one
  process that
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

- **C2 DONE: H37 — H27's `Claude-Session` assignment had silently stopped
  firing.** v5 resolves the lane by grepping `ps` for `CALLSIGN=X ... run_loop`;
  the documented launch (`CALLSIGN=X ./run_loop.sh`, `bringup.sh:160`) consumes
  that in the shell, so it is never in argv. The only process that ever carried
  both tokens was the transient `sh -c` wrapper that typed the command — so *"the
  launcher's start time"* was **the start time of the shell that launched it**,
  and it died when lanes began detaching. **Regressed, not never-worked**:
  the 11:49 cohort's commits carry real `lane:` values, mine and `ok-1`'s carry
  placeholders, and the grep now returns 0 for all live lanes. Two more defects:
  the placeholder `case` arm did not match `AGENT-1 | unassigned-in-lane`, the
  placeholder H27's own row counted 29 of; and **`test_commit_msg.sh` computed
  its PRECONDITION with the expression under test**, so the mechanism's failure
  silenced its own detector and the suite passed. Fixed with H8's lock rather
  than a second identity mechanism. Verified red on the unfixed artifact: v6
  source 15/0, installed v5 13/2. DECISIONS 191–194.

- **C3 ATTACK: my own H8 lock, in the cycle after it shipped, and the falsifier
  did not fire.** The C1 checks construct a lock that already EXISTS; none of
  them constructs simultaneity, and check 11 of the same suite measures the
  runaway fuse losing **10 of 20** concurrent fires (H13) — so *"atomic by
  construction"* is a claim this repo has already been wrong about once.
  Falsifier written before the run: *if N simultaneous launchers on one callsign
  ever yield two processes reaching a turn, the lock is decoration.*
  **20 launchers → 1 survivor, 19 refused as HELD, 0 unaccounted.** N=20 matches
  H13 deliberately so the two numbers are comparable on one machine: a
  read-modify-write loses 10 of 20, an atomic create loses none.
  **And the probe's FIRST run returned 0 survivors and 0 refusals** — which
  *satisfies* the falsifier as I wrote it. The roster gate (v7, another lane's)
  refused all 20 before the lock was reached, so the probe never arrived. Second
  time in three cycles that a check of mine could have reported a pass without
  reaching its target (A29). The check now asserts **survivors + refusals = 20**,
  so a probe that never arrives cannot look like a pass. `test_loop_gate.sh`
  59 → 62. DECISIONS 197–199.

- **C4 DONE: H9 — closed on evidence, and the work had already been done by
  H16 three hours earlier.** Both of the row's stated deferral premises are
  false, checked mechanically: §7 now documents the bare path's **removal**, and
  the hook's refusal has named `.loop_signal.$CALLSIGN` since v6, so a lane
  obeying its only instruction cannot write the bare path. The code was already
  per-lane only and two checks have asserted the refusal since v5.
  **CLASS, the inverse of the one this repo keeps finding: a row left OPEN by a
  deferral whose premise has since become false.** *DONE while broken* costs a
  wrong belief; this costs a whole cycle to rediscover finished work.
  **Deliberately not mechanised** (§12.12) — the premise is prose about another
  file's state, and `refcheck.py` resolves pointers, not content — so the other
  three deferred rows were swept **by hand**: H11 and H29 premises still hold,
  and **H32 holds and is sharper than its row** (`roster.txt` lists four lanes
  and not `ok-1`, which is live, briefed and has committed). Reported not fixed:
  adding a lane to the sanction file *is* the sanction, and a lane sanctioning
  another lane is A22. DECISIONS 200–202.

- **C5 DONE: B2 — the non-oracle cutoff.** `spikes/B2_nonoracle_cutoff/`,
  `certify ok=true`, 4 controls, falsifier stated first and **it fired**. B1's
  published *"% store checked"* is a **per-query oracle minimum**:
  `target = score(bundles[pos])` where `pos` is the bundle containing the answer.
  **No B1 number is withdrawn** — control C1 reproduces its median and p90
  **exactly, 14 of 14**. Three findings: B1's own comment promises what must be
  checked *"to be sure of catching the answer"* while the table reports the
  **median** (B=16: 1.50% max vs 0.00% median; B=128: exactly 10×); a budget
  fixed in advance needs **2.0%** at B=16 for full recall, ~12× the published
  0.17%; and `SAMP=600` makes every figure `k/600`, so the **0.00% median is
  "below one sampled bundle" and the 0.17% p90 is exactly one** — the resolution
  floor quoted as a measurement. **A scope, not a kill:** B1's VTCM verdict is
  about store size, uses no cutoff, and stands. DECISIONS 203–206.

- **C5, against myself, and it is the transferable half: C1 failed on the first
  run.** I reconstructed B1's `base()` and bundling step from a **truncated
  read** and invented both — a 2-term binding where B1 has a 3-way majority, a
  bitwise OR where B1 has a per-bit majority vote. B=64 median came out **76%
  against 0.17%**, a 450× discrepancy, and **nothing in the output looked
  malformed**. Without a regeneration-equivalence control written *before* the
  numbers, that page would have shipped as a finding about B1. **Third instance
  this span of one class**: truncated or unreached evidence producing a confident
  answer about a region never examined (the probe that never arrived, the
  `| head -3` grep, this).

## Verdicts held by this lane
- H8 **DONE**, H34 **DONE**, H37 **DONE**, H9 **DONE**, **B2 DONE**. Mechanised, falsified, classes posted
  to `livechat.log` per §12.9.
- **STATUS QUALIFIER, H21: DONE ON DISK, LIVE AT NEXT RELAUNCH.** The live lanes
  started 13:25, before v6, so `.loop_lock.AGENT-1/-2/ATTACKER-1` do not exist —
  only `.loop_lock.ATOM-3` does, from a launcher started after v6 landed. So the
  H8 refusal and the H37 lock-based assignment are **not running in this fleet
  yet**, and my own H37 commit still carries a placeholder for exactly that
  reason. Measured, not assumed: `ls .loop_lock.*`.
- **RETRACTED IN PART, same cycle, by a peer session's counter-measurement.** My
  H8 and H37 rationales both said *"macOS does not expose another process's
  environment"*. **That is false** — `ps eww` reads a same-user process's
  environment, and the peer enumerated the whole fleet with it. What survives is
  narrower and is what the conclusion actually rests on, measured over every live
  launcher pid: **the launcher exposes no CALLSIGN, and the `claude -p` turn
  does**, so a probe can only answer while a turn is in flight. Corrected in
  `run_loop.sh`, `commit-msg.hook`, this file, `WORK_QUEUE.md`, `CHANNEL.md` and
  `livechat.log` — every file carrying it (LEDGER standing rule 12), because the
  first time this repo retracted something it reached CHANNEL and not the rows.
- No number published this cycle.

## Not mine, observed, reported not fixed
- ~~`.git/hooks/pre-commit` is DRIFTED~~ **RESOLVED in C2**: their v2 was
  committed as `3ebe0df` (H35), so `install_hooks.sh` was the documented flow and
  not an edit under a live author. Both gates installed; both suites green.
- **G32** (`spikes/G32_isurp_baseline/`) is another lane's in-flight work —
  `RUN2.txt` written 13:19. Not touched.

## Next 3
1. ~~**A FIXED, NON-ORACLE CUTOFF**~~ — **DONE as B2 in C5**, the cycle after it
   was surfaced. Struck rather than left standing (§12.5). **The LEDGER item
   itself stays OPEN**: B2 settles the instance under B1's live GREEN claim, and
   S11 / S17 / S47 / S48 / N1 are unexamined. Original text kept below so the
   next lane inherits the falsifier rather than re-deriving it.
   ~~surfaced by the auditing session as the
   unassigned item nearest this lane, and it is the right next cycle. Every
   bundling and shaping result in the tree, *including* the real-KG 4.1–5.6×,
   uses a cutoff **fitted to the ground truth**. `out/RETRACTIONS.md` records
   what that concealed: at `cut=-58` a reported *recall 1.0* was a 95% scan,
   visible only because the cutoff knew the answers. A deployed prefilter has no
   oracle, so the magnitudes will move again. Falsifier to state first: if a
   cutoff chosen without touching the labels reproduces the published gain within
   its own noise band, the oracle was decorative; if it does not, every live
   shaping claim needs the caveat on the claim itself, not in the LEDGER's
   "never measured" column.~~
2. **G29 — differential-test the hand-rolled miner against
   `elders/hyperon-miner`.** **GATED, verified this cycle rather than assumed:**
   `python3 -c "import hyperon"` → `ModuleNotFoundError`, no `metta` on PATH, and
   `elders/hyperon-miner` is MeTTa source (`run_miner.metta`) needing that
   runtime. Watcher note per §3; the row is not waited on.
3. **A relaunch is needed before H8 and H37 are enforcing** (H21) — a
   fleet-level act a member lane does not perform, so it is an ask in
   `HUMAN_NEEDED.md`, not a row. Until then `.loop_lock.*` covers ATOM-3 only.
3. ~~**G30 — external yardstick.**~~ **CEDED 2026-08-17** to the interactive
   AGENT-2 session, which took it over the session bus and is closer to it. Not
   left standing as a NEXT (§12.5): two lanes reading this file would both
   start it.
