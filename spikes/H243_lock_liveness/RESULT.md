# H243 — a pid is not an identity: the callsign lock's readers, and the census that missed one

`ok-1`. Filed and fixed across two cycles; **cycle 34 is an ATTACK on the first half**, and
the row is written from the attacked state, not the claimed one.

```sh
python3 spikes/H243_lock_liveness/sites.py .     # the census, population derived from the tree
bash    spikes/H243_lock_liveness/falsify.sh     # every guard removed in an isolated copy
bash    spikes/harness/test_commit_msg.sh        # 19/19, incl. the behavioural arm below
```

## THE DEFECT

`.loop_lock.<CALLSIGN>` records the launcher pid, and readers asked `kill -0` — *is some
process alive with this number*. **A pid is not an identity.** This fleet burns ~1300
pids/min through a 99999-pid space, so it wraps in about 75 minutes and a dead lane's
recorded pid becomes somebody else's process. `run_loop.sh`'s acquire path says exactly this
in its own comment and was the only reader that acted on it.

Measured before the fix (`probe_prefix.out`): `bringup.sh --check` reported a lane **UP** off a
lock naming a live `sleep`, and `fleetcensus.sh` scored the same lock **CONSTITUTED**. The
supervisor's UP means *not MISSING*, which means **not relaunched** — a dead lane with a
recycled pid is never restarted, and a dead lane has no next cycle.

`launcher_alive` (`spikes/harness/lanelive.sh`, and `lanelive.py` for the two python readers)
is the predicate `run_loop.sh` already used: **pid + command**, never pid alone.

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
