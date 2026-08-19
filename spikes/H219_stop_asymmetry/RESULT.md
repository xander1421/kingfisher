# H219 — the per-lane kill switch had two readers and the hook was not one of them

**ok-1, ATTACK cycle 30, 2026-08-19.** §12.8: at least every fourth ATTACK targets
the loop itself. My last three hit the commit/attribution path, so this one is the
loop. Target chosen from my own cycle-28 note: the H202 vocabulary check reads both
of its sets **out of one file**, so nothing in this harness compares a contract to
its implementation across documents. The stop switch is the smallest such pair.

## The finding

`STOP.$CALLSIGN` retires ONE lane. It was added by **H31** on 2026-08-17, taught to
`run_loop.sh:433`, to `bringup.sh`, to `spikes/harness/bringup.sh`, and written into
`MISSION.md:303` as the operator's documented way to retire a lane.

**It was never taught to `.claude/hooks/loop_gate.sh`, and the hook is the only
thing that ends a turn.** Section 1 read the fleet-wide `STOP` and that was the
file's *only* STOP read (1 of 1, grepped).

Measured, `probe_prefix.out`, hook `v8` at `5ea8435` (hook blob `e269f2fd79fc9adc`,
identical at `987470d`):

| input | hook verdict |
|---|---|
| no stop switch | `block` — the loop contract, correctly |
| fleet-wide `STOP` | `exit` — the turn ends on attempt **0** |
| `STOP.L1`, lane L1 | **`block`** — refused **20 of 20** attempts, span cap → **20** |
| `STOP.L2`, lane L1 | `block` — correct, and must stay that way |

**Why it costs a whole turn rather than a moment.** The launcher's *only* stop read
is its `while` condition (`run_loop.sh:433`, 1 of 1, asserted by probe arm C1), so
the switch is consulted **between** turns. The hook decides when a turn ends. A lane
under a per-lane stop was therefore told to run another cycle every time it tried to
stop, and the retirement arrived when `MAX_TURN`'s watchdog killed the turn —
default **3600 s** — logged as a wedged turn rather than as a retirement, with the
span cap climbing the whole time.

**The row is §12.2, the site and not the class, inside a row whose subject *is*
per-lane state.** H31 is `DONE` in `WORK_QUEUE.md` and its verification is recorded
as *"verified against the FILE, not against `CHANNEL.md:181`'s DONE line"* — the
right instinct applied to one of the two files that implement the switch.

## Preregistered falsifiers — posted in the CLAIM before the probe was written

| | if it fires | measured |
|---|---|---|
| **F1** | the hook already honours the per-lane form; row dies | **did not fire** — `block` |
| **F2** | the asymmetry costs nothing, the turn ends anyway | **did not fire** — 20 of 20 refused |
| **F3** | both spellings agree; no asymmetry to report | **did not fire** — `exit` vs `block` |
| **F4** | the suite already covers it | **did not fire** — HEAD's suite mentions `STOP.$CALLSIGN` only inside a *launcher span* fixture, never as a hook input |

## The repair, and the direction it must not take

`loop_gate.sh` **v9**: `[ -f "STOP.${LANE}" ] && exit 0`, placed **below** the
charset whitelist, because `$LANE` is interpolated into a filename here exactly as
it is into `EXIT_MARK` and `BLOCKS`.

**NOT a glob.** `STOP.*` would satisfy the headline check and let one lane's
retirement stop all five — H31's own defect restored from the other end. The
cross-lane arm (A4) and suite check 8b's second assertion exist for that, and
falsifier arm **M2** builds the glob and requires the suite to go red on the
cross-lane check *while the own-lane check stays green*, so the arm is specific.

## What can fail, and has

`spikes/harness/test_loop_gate.sh` **v7** (107 → 110 checks), section 8b: own-lane
STOP ends the turn / another lane's does not / the read sits below the whitelist.
`spikes/harness/test_h219_falsify.sh` reddens each of the three with its own mutant:

- **M1** the v9 line deleted — the exact pre-H219 hook; check 1 red.
- **M2** the read widened to a glob; check 2 red, check 1 still green.
- **M3** the read relocated above the whitelist — **behaviourally invisible**, since
  a refused callsign and an allowed stop are both `exit`; only the ordering check
  sees it. Had it not, that check would be decoration.

Every mutation asserts **that the edit applied** and that the mutant still parses,
per H217 — `cmp -s` and an anchor assertion agree on every successful edit and
disagree exactly when the editing tool fails. Two-sided: the same suite is green on
the shipped hook **and reports its check count**, because `rc == 0` is also what a
suite that never ran returns.

## The class, and the sweep for it

> **A per-lane state name taught to one reader while a second reader of the same
> state keeps the global-only spelling.**

Third recorded instance. The first two are in the hook's own header: bare
`.loop_signal` (v5 — either lane could consume the other's exit) and one shared
`.loop_blocks` (two lanes, one span cap, each lane's `rm -f` resetting the other's).

Swept mechanically, arm C3, over eight per-lane state names across six readers:
**0 live bare sites.** One raw hit, printed with its text rather than counted:
`bringup.sh:618` is `.loop_launcher` inside a **message string**, not a read. Both
numbers are on the page because a bare count of 1 reads as a live second site.

`STOP` was the only live instance, and the documentation half of it is repaired in
the same edit: **MISSION_LOOP §7's stop bullet named only the fleet-wide spelling**,
and it was the only place the contract told a lane what a stop looks like — so a
lane resolving it mechanically checked `STOP` and never its own.

## Three defects in my own instrument, and one of them is the reason the seam exists

1. **v1 of the probe had no seam.** `KF_TEST_GATE=<HEAD's hook> probe.sh` silently
   measured the **working tree** hook — the one I had already repaired — and printed
   *"F1/F3 FIRED … the row dies here."* The pre-fix run reporting the post-fix hook
   under the pre-fix label. **What caught it was the banner still reading v1**, not
   the exit code, which was a clean `0`.
2. **A5 built its fixture with `: > 'STOP.../etc'`**, which cannot be created —
   `No such file or directory` — so the arm PASSED with no fixture present (A29). It
   could not have discriminated anyway: a hostile callsign and an allowed stop are
   both `exit`. Split into A5 (artifacts) and A6 (order, read out of the file).
3. **The class sweep printed `bare-spelling reads: 0` eight times** because the local
   `grep` is `ugrep`, which rejected the `\{` in the pattern outright: eight clean
   zeros from a regex that never ran. Rewritten in python, no shell regex dialect.

And twice in a row the banner misidentified its own subject — `sed -n 2p` printed
`v8` for the v9 hook, then `grep '^# v[0-9]' | tail -1` printed `v6`, because this
hook's rationale blocks are in file order and v9's note sits above v3/v5/v6's. It is
`max`, by number, now.

## Reproduce

```sh
bash spikes/H219_stop_asymmetry/probe.sh                    # the shipped hook: 9/9
git show 5ea8435:.claude/hooks/loop_gate.sh > .scratch/h219_prefix_gate.sh
KF_TEST_GATE="$PWD/.scratch/h219_prefix_gate.sh" \
  bash spikes/H219_stop_asymmetry/probe.sh                  # pre-fix: 6 pass, 3 fail
bash spikes/harness/test_h219_falsify.sh                    # 3 mutants, 3 checks red
bash spikes/harness/test_loop_gate.sh                       # 110 checks pass
python3 spikes/H219_stop_asymmetry/certify_run.py
```

`.scratch/` is gitignored, so the pre-fix gate is not committed — it is reproduced
from the commit above, whose hook blob is `e269f2fd79fc9adc`, and the probe prints
the version of whatever gate it was handed.

## What this row does NOT close

The check that started it. **The H202 vocabulary guard still reads both of its sets
out of one file**, so a rename applied to the hook's accept branch and its refusal
message together still reports `equal`. H219 is one *hand-built* cross-document
comparison — contract §7 against hook v9 — not a mechanism that would find the next
one. Whether §7's vocabulary is mechanically extractable is still unmeasured, and
filing a row whose feasibility is unknown is how H23 sat mis-summarised for three
cycles.

**Do the live lanes obey v9?** The hook is read from disk at every stop, so the
hook half applies to the next stop of every lane. The launcher half was already
theirs: `bash spikes/harness/check_live_launcher.sh` run for this row reports
**all 6 live launcher processes at or newer than `c41deaa`**, the newest commit
touching `run_loop.sh`.

I drafted this paragraph carrying H21's caveat — *"20 of 21 live launchers predate
the current `run_loop.sh`"* — from `WORK_QUEUE.md`'s H31 row. **It is stale; the
fleet has relaunched since.** I ran the checker instead of quoting the row, and the
number moved from 20-of-21 to 0-of-6. That is claim decay caught at the only point
it can be caught (§12.12): the row was right when written and is a different fact
now, and re-running its instrument costs one command.

Its own control disagrees in the same run — **5 live lock holders vs 6 selected
launchers** — and the checker refuses to resolve it. Recorded, not smoothed over:
one of the six has no lock, and this row does not say which or why.
