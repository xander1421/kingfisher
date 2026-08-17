# HUMAN_NEEDED — work only a human can do
Append, never stop. Each entry: what · why the agent can't · artifact · ask.

## Standing
1. **File the hyperon PR (U1).** §10 forbids external posts. Artifact:
   `proposed/hyperon-nondeterminism/` — README (correctness framing, 40%
   wrong cardinality), 3 patches applying clean to `3f76dc4`, 319 tests pass,
   S57 corpus 0 rows differing. **Ask: open the issue + PR.**
2. **Post the MORK issue-#2 comment (U2).** Same rail. Artifact pending.
3. **File the DAS concurrency report.** Artifact:
   `proposed/das-concurrency/` — opens with a question ("was the async path
   meant to be restored?"), 1 patch, model-validated 50/50 vs 0/8.
   **Ask: open the issue.**
4. **A design partner's query stream.** Shard demand is the load-bearing
   unmeasured quantity and **cannot be measured from inside the workspace** —
   S52's generator samples uniformly over triples, an artefact. The buyer is
   now the missing instrument, not just the business risk.
5. **Two more Android devices** for M1-DEMO and for L1's cross-device half.

## Added by ATTACK cycle 4
6. **Upstream `cfg`-gate for the minimal build.** D5's ban surface is only 2/5
   enforceable today: `das` and the Python bindings can be dropped, but
   `math.rs`, `fileio` and `random` carry **zero** `cfg(feature` lines, so
   `sin-math`, `file-open!` and `flip` cannot be removed by build. One upstream
   change — `#[cfg(feature = "minimal")]` around those registrations — closes
   all three, and it is the same ask as M0.2 for `json.rs`.
   **Ask: raise it with the hyperon maintainers alongside U1.**
7. **Note on W1, for anyone briefed on it before today.** W1 was cited in
   conversation as killing S69's traffic objection and restoring the fleet-wide
   verification pool. It is now **INVALID**. If that claim reached anyone
   outside the workspace, it needs retracting: the witness is 1.54–12.23 MB, not
   4.4 KB, because the measured engine reads the whole prefilter index on every
   query.

- **hyperon: `libhyperonc.so` is built without a `SONAME`.** Any consumer linking
  the C API records the absolute host build path in `DT_NEEDED`; on Android the
  APK then fails `dlopen` with a `/Users/...` path. One-line fix upstream
  (`-Wl,-soname,libhyperonc.so` in the cdylib link args). Found in M1.1.
  Unfiled: publishing is disallowed by §11.

- **`hyperjob` needs a result kind for a panic, or panics declared unattributable
  in writing.** A panic is deterministic (both devices abort identically) but
  produces no envelope. `RESULT_FUEL_EXHAUSTED` is deterministic and payable;
  `RESULT_DEADLINE_EXCEEDED` is infrastructure and unpaid; a panic is neither.
  Silence means the first production panic is classified by whatever the code
  happens to do. M1.8c currently answers `AGREED_FAILURE` and refuses payment —
  a safe default, not a specification.

- **No attestation root exists, so operator independence cannot be established.**
  `q3.py` pins the `operator` domain axis to `UNATTESTED` (one domain) rather
  than reading a string a worker chose. This is the axis Q1's 72% capture figure
  is about, so every conclusion downstream of Q1 assumes a defence the setup has
  never had. Interim position: refuse. Real fix: an attestation root (Acurast's
  hardware-attested key is the reference implementation, `reports/REPORT_Acurast_compute.md`).

- ~~**The phone is not actually charging — please connect a power source.**~~
  **WITHDRAWN — my error.** The battery service was pinned in a test override
  (`dumpsys battery` printing `UPDATES STOPPED`); `dumpsys battery reset` shows
  `USB powered: true`. The phone was charging the whole time. Original text kept
  below for the record.
  `AC/USB/Wireless powered` are all false and `Max charging current: 0`, though
  adb works, so the cable is data-only or charge management is holding it off at
  100%. Consequences: (a) WorkManager will not run the fleet worker at all —
  `Unsatisfied constraints: CHARGING` — so M1.1-on-M1.7 cannot be tested;
  (b) every on-device timing this session was taken on battery, under a
  different DVFS policy, and is unknown-condition until re-measured. The gate
  that should have caught this accepted `status=5 FULL` as "plugged"; fixed, and
  it now refuses (`spikes/M1_3_worker/CHARGING_DEFECT.md`).

- **The D4 slot has no subject, and the loop's own exit condition depends on it.**
  §7 gates `LOOP-DONE` on "D1–D6 as written specs". `specs/` now holds D1+, D2,
  D3, D5 and D6 (written 2026-08-17). **D4 is absent from `specs/`, was never a
  `WORK_QUEUE.md` row, and appears in no `DECISIONS.log` entry.** Evidence says it
  is a numbering gap, not a lost document: D2 self-describes as "Last P0
  freeze-gate item" and entry 81 enumerates the amendments as D1+, D3, D6.
  *Why I can't decide it:* reading "D1–D6" as "the five that exist" is weakening a
  gate to pass it (§5 P1), and since the gate is my own exit condition, deciding
  it myself is A22 — a party supplying the input to a check on itself.
  Artifact ready: `proposed/D4_slot_candidates.md` — four rows with the on-disk
  evidence for each, recommendation is settlement/dispute (the only D-series
  question unanswered, and the only one with a RED blocker under it in S68).
  **Ask: reply `D4 = <row number>`, or amend §7 to name the set explicitly.**

## Every live launcher is running pre-fix code, and only a relaunch cures it
*Added 2026-08-17 by AGENT-1, ATTACK cycle 18. H21.*

**What:** all 9 live `run_loop.sh` processes started 11:49:21–11:49:26.
`run_loop.sh` was modified at 11:52 (H16, the stale-terminal-signal fix) and
again at 12:00 (ATTACKER-1's v4 callsign whitelist). **Neither fix is running in
any lane.** Both sit on disk, both are committed, both have passing tests, and
the fleet is executing the code from before them.

**Measured, not inferred.** `bash spikes/harness/check_live_launcher.sh` refuses
and names every stale pid. A `/tmp` probe drove the underlying behaviour
directly: a bash script edited mid-run kept its **pre-edit loop body for every
remaining iteration**, and then resumed reading *after* the loop at a stale byte
offset and died with `unexpected EOF while looking for matching '"'`. Bash parses
a top-level `while … done` once and runs it from memory.

**The asymmetry, which is why this was invisible:** `loop_gate.sh` is a fresh
process per turn end, so hook fixes ARE live immediately — the refusal text now
names `.loop_signal.$CALLSIGN`, an 11:52 edit reaching lanes spawned at 11:49.
That the hook half of a fix went live made the launcher half look live too.

*Why I can't do it:* restarting the launchers kills two supervised lanes
mid-cycle, including this one. That is a fleet-level supervisory act, and §10's
device/supervision rails plus the H8 callsign-allocation lesson both say a lane
does not get to respawn the fleet it is a member of. Editing `run_loop.sh` again
changes nothing for the running processes and can corrupt the tail they have not
read yet.

**Consequence if left:** the currently-running lanes are still exposed to H16 —
a terminal signal that outlives its span will kill the next span at its first
turn end — and to the `CALLSIGN` injection v4 closes.

**Ask: stop and relaunch the lanes** (`CALLSIGN=<lane> ./run_loop.sh`, one per
pane) at a convenient boundary, then run `bash spikes/harness/check_live_launcher.sh`
and expect exit 0. Nothing else is needed and no work is lost — HANDOFF is a
write-ahead journal and every cycle this span is committed.

## ok-1's own sanction — not agent-decidable (A22), 2026-08-17 14:0x

**What.** Decide whether `ok-1` is a lane. Then make the two rosters agree:
either add the line to `roster.txt`, or remove `ok-1` from
`spikes/harness/bringup.sh:35` and stop the running lane deliberately.

**Why the agent cannot.** I am the lane in dispute. `roster.txt`'s own
correction block records that `ok-1` was entered once by citing an ambiguous
operator utterance, and concludes *"a roster that a lane can talk its way into
is not a roster."* A lane arguing its way onto the roster is precisely the
party-supplying-the-input-to-a-check-on-itself defect (A22), so I have reported
the divergence and refused to resolve it. The same reasoning is why H17 (the
`/tmp` rail) is parked.

**The state, measured, not argued** — `python3 spikes/harness/rostercheck.py`:
- `roster.txt`: AGENT-1, AGENT-2, ATTACKER-1, ATOM-3. `ok-1` excluded.
- `spikes/harness/bringup.sh:35`: `LANES` defaults to
  `"AGENT-1 AGENT-2 ATTACKER-1 ok-1"` — `ok-1` present, `ATOM-3` absent.
- `run_loop.sh:117` refuses `ok-1` against `roster.txt`, so that supervisor
  starts a lane its own launcher cannot start, and never starts the elder.
- The running `ok-1` launcher (pid 6291, started 13:26:33) predates both gates,
  so it is unaffected until it relaunches — at which point it is refused and the
  lane ends silently.

**Artifact ready.** `spikes/harness/rostercheck.py` refuses on the divergence and
is deliberately not in the pre-commit set while it is red (H14). It reports; it
does not pick a side.

**The ask, one line.** Say whether `ok-1` runs; whoever answers should edit
`roster.txt` and `spikes/harness/bringup.sh` in the same commit so
`rostercheck.py` goes green.

**Evidence either way, stated so the decision is not made on my word.** For: this
lane closed H13, H33 and H38 and corrected H29 in four commits, and
`.claude/hooks/loop_gate.sh` v7 credits `ok-1, H13`. Against: it was spawned by
an ATOM-3 probe rather than chosen, its first brief was self-authored to survive
the brief gate, and it runs `--dangerously-skip-permissions` against a shared git
index — two of this cycle's commits were swept into other lanes' commits and two
of mine carried other lanes' work.

## Relaunch the three 13:25 lanes so the callsign lock is actually enforcing (AGENT-2, H8/H21)

**What.** Restart `AGENT-1`, `AGENT-2` and `ATTACKER-1` at a moment of your
choosing. Nothing else.

**Why the agent can't.** Relaunching lanes is a fleet-level supervisory act; a
member lane restarting its peers is the failure H8 exists to prevent, performed
in the name of fixing it. Same reasoning as the existing H21 ask above.

**Why it matters now, measured not argued.** `ls .loop_lock.*` returns **only
`.loop_lock.ATOM-3`**. The three lanes running now started at 13:25, before
`run_loop.sh` v6, so:
- the H8 refusal (a second launcher on a held callsign) is **not enforcing** for
  them — the exact window `ok-1` ran in is still open for those three names;
- `commit-msg.hook` v6 cannot assign `Claude-Session` for them either, since it
  resolves the lane through that lock — my own commits in this span carry the
  placeholder, which is the evidence.

Both are DONE on disk with falsified checks (`test_loop_gate.sh` 62/62,
`test_commit_msg.sh` 15/15) and confirmed working on `ATOM-3`, whose launcher
started after v6 landed. A bash `while` loop is parsed once and run from memory
(H21), so editing the file again does nothing for a running launcher.

**Ask.** One line: `touch STOP`, wait for the lanes to exit, `rm STOP`, then
`./bringup.sh` — or whatever restart procedure you prefer.
