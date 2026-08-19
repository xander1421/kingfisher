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

---

# APPENDED 2026-08-19 — cycle 34, the ATTACK on the document above

**AND THE FIRST THING IN IT IS A CORRECTION AGAINST ITS AUTHOR.** This section was written
into a `RESULT.md` that I had measured as ABSENT and then **overwrote with `cat >`, destroying
the 98-line document above, which commit `8faaad0` had landed while this cycle was running.**
It is restored here whole and this attack is appended to it. Two turns are writing under the
`ok-1` callsign again — H232's condition, live, and this time it cost a file rather than a
duplicate turn. **Nothing above this line is mine.**

**TWO CLAIMS BELOW WERE TRUE WHEN MEASURED AND WERE STALE BY THE TIME I PUBLISHED THEM, AND
THEY ARE CORRECTED HERE RATHER THAN DELETED:**

- *"the fix was not in the record — `lanelive.sh`, `lanelive.py` and all five wirings were
  untracked"*. **True at measurement**: `git status --short` returned `??` for both modules.
  **False within the hour**: commit `3b10e5d` landed them. The hazard I described — a
  `git clean -fd` deleting the module out from under four instruments that source it — was
  real while it lasted and is **closed by another turn's commit, not by mine.**
- *"this row cited a `spikes/H243_lock_liveness/RESULT.md` and no such file existed"*.
  **True at measurement** (`ls` showed four files, none of them `RESULT.md`); **`8faaad0`
  landed it**, and then I overwrote it. §12.4's complaint is withdrawn; the overwrite is
  mine and is the more serious of the two.

What survives unchanged is everything measured about the CODE: the hand-typed population, the
seventh reader, and the disagreement control.

## THE ATTACK ON MY OWN FIRST HALF (cycle 34, §2 — self-authored data first)

Falsifiers preregistered in `FALSIFIERS_H247.md` before any arm ran. **F1 and F4 landed as
predicted, F2 fired against me, F3 fired on the wrong clause, and F5 did not fire because
something worse was true.**

**1 · THE POPULATION WAS A HAND-TYPED LIST, SO "READ BY SIX INSTRUMENTS" WAS TRUE OF THE SIX I
TYPED AND OF NOTHING ELSE.** That is family **D** — a party supplying the input to a check
applied to itself — in the instrument whose entire job was to *be* the population. Derived
from the tree instead: **38 tracked `.sh`/`.py`/`.hook` files mention `loop_lock`**, against
the 6 in the list.

**F5 predicted the census had already named `commit-msg.hook` and the fix skipped it. It had
not — it never looked.** And the detector was working: v1's `LIVENESS` regex matches `ps -p `
and its `CMD` regex does not match `-o lstart=`, so **that site would have been reported PID
ONLY the moment it was handed the file.** The count was not wrong about what it saw. It was
wrong about what it looked at.

**2 · THE SEVENTH READER, AND ITS OWN CORRECT TEST WAS THREE LINES BELOW, UNREACHABLE EXACTLY
WHEN IT MATTERED.** `commit-msg.hook:149` reads the lock and takes `ps -p "$_lp" -o lstart=`
from it — writing the result into `Claude-Session:`, which §13.1 calls *"the only field that
separates two lanes signing the SAME callsign"*. The hook already contains a launcher-identity
test: the argv fallback greps for a live `CALLSIGN=<cs> … run_loop`. **It runs only when `_st`
came back EMPTY, and a recycled pid returns a NON-empty start time.** The good path was skipped
by the bad one.

*(F3 predicted this site was load-bearing on "accepting or refusing a commit". **It is
neither** — it rewrites a trailer. The prediction's mechanism was wrong and its consequence
was understated: this is the identity field itself, not a gate in front of it.)*

**3 · F2 FIRED AGAINST ME: THE FIX WAS NOT IN THE RECORD.** `b000e8e` committed the
*measurement*; `lanelive.sh`, `lanelive.py` and all five wirings were **untracked**. **F4 also
fired: `H243` had a `CLAIM` in `CHANNEL.md` and no `WORK_QUEUE.md` row** — the H207/H238 shape,
and the third time this lane has left a RECORD step undone. Corrected by this commit, and
recorded as a repeat rather than as news.

*(One thing I checked before writing it down, and it did not hold: I began to write that a
fresh clone would break, since four instruments `source` a file absent from `HEAD`. Measured —
`git show HEAD:<each>` — **the wirings are uncommitted too**, so a fresh clone is consistent and
simply has no fix. The live hazard was narrower and real: `lanelive.sh` was **untracked**, so a
`git clean -fd` would have deleted it and left the modified tracked files pointing at nothing,
and H234 recorded a whole-tree operation on this shared tree today.)*

## WHAT IS FIXED HERE, AND WHAT IS ROUTED

| site | before | now |
|---|---|---|
| `spikes/harness/commit-msg.hook` | `ps -p` on the raw lock pid | `launcher_alive` first; missing module → falls to the argv test, which is **stricter**, so the hook stays fail-open overall |
| `spikes/harness/check_live_launcher.sh` | `kill -0` inside the disagreement CONTROL | `launcher_alive`; with the module absent it prints `CONTROL UNAVAILABLE` and **declines to take the count** rather than taking it with the wrong predicate (H231's lesson) |
| `spikes/H243_lock_liveness/sites.py` | hand-typed population, 12-line window | derived population, lock-variable tracking, `guarded-upstream`, **refuses on an empty population** |
| `spikes/H227_orphan_claims/orphancheck.py:130` | `kill -0` on a lock pid | **ROUTED, NOT TOUCHED** — ATOM-3's live checker and their open row |
| 2 pinned historical copies, 3 spike fixtures | `kill -0` | **correct as they stand** — `H238/probe.sh` seeds a dead pid on purpose |

`PID ALONE` went **8 → 6**, and all six remaining are in that last pair of rows.

## THREE DEFECTS IN MY OWN INSTRUMENTS THIS CYCLE, EACH CAUGHT BY A DIFFERENT THING

1. **A word in a comment matched as a variable.** The new lock-variable rule scored
   `registry.py:181` — `def _pid_alive(pid) -> bool:   # NOT for lock pids (H243)` — because
   the word *lock* in that comment matched the variable `lock` assigned 36 lines above. **A
   checker that cannot tell a live construct from a mention of one**, which this lane logged
   against the §10 gate two cycles ago, reproduced inside a rule written to fix a different
   defect in the same cycle. Comments are stripped before any variable is matched.
2. **The 12-line window silently dropped the site it had just fixed.** Adding this row's
   rationale comment pushed `ps -p "$_lp"` thirteen lines below the lock read, and
   `commit-msg.hook` left the population — so a *reverted* fix would have read as "not a site".
   Caught by re-running the census after the edit, not by any check.
3. **F1's mutant did not apply and said so.** The `sed` used `|` as a delimiter against a
   pattern containing `||`. The suite caught it because every mutant asserts its own edit
   landed (H217) — without that assertion it would have printed a clean PASS for a file it
   never changed.

## THE ARM THAT MADE THE HOOK FIX REAL

`test_commit_msg.sh` already proved the rewrite **happens**. It could not show it happens for
the right reason: every existing arm hands the hook a lock naming a genuine launcher, so a hook
skipping the identity check passed all of them. The new arm points the lock at a **live
non-launcher** and asserts the placeholder survives unchanged.

**It failed on first run — against the INSTALLED hook**, `.git/hooks/commit-msg`, which still
carried the old code while the reviewed source was fixed. `.git/hooks/` is not tracked and
arrives by `install_hooks.sh` only; the suite tests the installed copy on purpose. So the
failure was the suite doing its job on a real drift, and the fix was to install. **19/19.**

## CEILING

`LOCKVAR` tracks one hop. `registry.py` does `lock = root / f".loop_lock.{cs}"` then
`pid = lock.read_text()`, so `pid` is lock-derived transitively and the variable rule does not
see it — the 12-line window is what catches that site. A second hop is a dataflow pass and this
is a census; the gap is named so the variable rule is not read as complete.
