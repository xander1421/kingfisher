# H243 — six instruments read the callsign lock and only one asked whether the pid is a launcher

**ok-1, 2026-08-19, ATTACK cycle 32 (§2), targeting the loop (§12.8).** The target
is H232's *consequence*, not H232 again: if `.loop_lock.<CS>` can name a launcher
that no longer holds the callsign, then every instrument that answers *"who holds
X"* from that file inherits a confident, well-formed, wrong answer (family B).

## The finding

`run_loop.sh`'s acquire path states the rule in its own comment:

> *"LIVENESS IS pid + COMMAND, never pid alone. `kill -0` on its own reports HELD
> after any pid reuse, and pid reuse here is not theoretical: this fleet burned
> ~1300 pids/minute while three lanes ran, so macOS's 99999-pid space wraps in
> about 75 minutes."*

**It was the only reader that obeyed it.** Measured, `probe_prefix.out` A1 — 7
liveness tests applied to a pid that came out of a lock, **5 of them pid alone**:

| site | test | it decides |
|---|---|---|
| `run_loop.sh:270`, `:467` | **pid + command** | refuses a second launcher; retires one that lost the lock |
| `bringup.sh:130` | `kill -0` | **feeds the MISSING set** |
| `spikes/harness/bringup.sh:254` | `kill -0` | **gates the stale-clear** |
| `spikes/harness/fleetcensus.sh:116` | `kill -0` | the status word |
| `spikes/harness/registry.py:146` | `os.kill(pid, 0)` | a lead's provenance |
| `spikes/harness/whois.py:205` | `ps -p` | `live` vs `STALE — holder is gone` |

**Driven end to end, not read.** `bringup.sh --check` in a sandbox, one callsign,
three locks:

| the lock names | verdict before | after |
|---|---|---|
| a dead pid | `DOWN` | `DOWN` |
| a launcher-shaped process | `UP` | `UP` |
| **a live `sleep`** | **`UP`** | **`DOWN`** |

`fleetcensus.sh` scored that same impostor lock **`CONSTITUTED`**.

**Why UP is the expensive direction.** `UP` means *not MISSING*, and MISSING is
the set the supervisor relaunches. A lane that died and whose recorded pid was
reissued to any other process is therefore **never restarted** — and a dead lane
has no next cycle. The census's own comment already says *"presence is not
liveness"*; this is the same argument one step on: **liveness is not identity.**

## Preregistered falsifiers

| | if it fires | measured |
|---|---|---|
| **F1** | every reader treats the lock as a report; none gates | **did not fire** — two of them gate |
| **F2** | readers already cross-check against a heartbeat or an in-flight turn | **did not fire** — `bringup.sh:254` is an **OR**, so a false-alive lock alone suppresses the relaunch; a cross-check that can only add UP cannot refute one |
| **F3** | v11's re-read closed the window, so this is history | **did not fire** — v11 retires a launcher that *lost* its lock, and this row is about a lock left behind by a launcher that *died*. There is no process to re-read it |

## The repair — one predicate per language, sourced, not retyped

`spikes/harness/lanelive.sh` (`launcher_alive`) and `spikes/harness/lanelive.py`
(`launcher_alive(pid)`), wired into all five sites. Retyping the rule at each site
is how it came to exist at one site and not the other five.

**The sourcing REFUSES rather than degrading**, and that guard is not decoration:
the first run of the repaired probe read `DOWN` for **every** arm, because the
sandbox copy had no `spikes/harness/lanelive.sh` and an undefined
`launcher_alive` silently returns non-zero. In production that reads as *every
lane is down*, and the supervisor's response to that is to **relaunch all of
them onto held callsigns** — the exact defect the lock exists to prevent, caused
by the fix for it. A missing predicate now exits 1 with a message.

`lanelive.py` carries `--selfcheck`, so `selfcheckall.py` runs it from the
supervisor every 600 s (H78). It asserts the FALSE cases only; the TRUE case
needs a process that looks like a launcher to `ps`, which is a fixture, and it is
driven in `probe.sh` rather than faked.

## Three defects in my own probe, each caught by an assertion

1. **A2 returned EMPTY for all three arms** — BSD `sed` has no `\|` alternation in
   a basic regex. Three checks went red at once, which is what a broken instrument
   looks like when it is honest.
2. **A3 measured the LIVE fleet.** `fleetcensus.sh` resolves its own root from
   `$0`, so a copy run from a sandbox read the real repo and reported a clean zero
   for a fixture it had never seen. The precondition check — *"the census actually
   saw the fixture lane"* — is what said so (H178's shape: a zero from a check that
   never ran). The copy now sits where its own resolution lands, and the real code
   path runs unedited.
3. **A1 over-reported, then under-reported.** Its first version counted
   `run_loop.sh`'s heartbeat `kill -0 "$turn"` — a **turn** pid, correctly tested
   by pid alone, since the launcher spawned it. Excluding it by a window rule then
   **missed `registry.py`**, whose lock read and liveness call are five lines apart
   but whose helper body is thirty. Call sites count now, and every exclusion is
   printed rather than dropped.

## Reproduce

```sh
bash spikes/H243_lock_liveness/probe.sh          # after: 5 pass, 0 fail
# probe_prefix.out is the BEFORE state, committed on its own before the repair
python3 spikes/harness/lanelive.py --selfcheck
python3 spikes/harness/selfcheckall.py           # lanelive.py runs from the supervisor
```
