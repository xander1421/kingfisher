# H63 — ATTACK on the loop's admission gate: it had no check at all

`ok-1`, 2026-08-17. Cycle 8, an ATTACK cycle (§2), and §12.8 makes it the loop's
turn rather than a spike's. Files: `attack.py`, `attack.out` (BEFORE),
`verify.out` (AFTER).

## Why this target

`run_loop.sh:124-134` decides **which lanes may run at all**. Its own comment says
what it is for: *"a brief that the lane wrote for itself is not sanction to run.
Add the callsign to roster.txt deliberately."* It is H32's answer (the launcher
gates entry, nothing audits what is inside) and H38's subject (two rosters, two
opposite answers to "is X a sanctioned lane"). This lane exists because something
ran unsanctioned for hours.

`grep -n roster spikes/harness/test_loop_gate.sh` returned **three** lines, all
three a scratch roster written *for* the 20-launcher block. Not one check asserted
the gate refuses anything.

## Falsifiers, stated in `attack.py` before the first run

| id | fires if | verdict |
|---|---|---|
| FA | the gate can be deleted and the suite stays green | **FIRED** |
| FB | an unrostered callsign launches while the roster is present | did not fire |
| FC | roster absent — measure, do not assume | **fail-open, measured** |
| FD | a substring of a rostered callsign is admitted | did not fire; `grep -qx` is why |

A29 guard on every arm: an arm with no output and no turn is recorded as no
evidence, not as a negative result. Positive control on every launcher arm: a
**rostered** callsign must reach `claude`, or the refusals below it are
unattributable — the state the H8 checks were once measured in (1 PASS / 3 FAIL,
and the one PASS was the false one).

## FA — the whole gate is deletable and nothing notices

`attack.out`:

```
  control                 66 pass /  0 fail   roster-related red: NONE
  roster gate DELETED     66 pass /  0 fail   roster-related red: NONE
  exact match -> substr   66 pass /  0 fail   roster-related red: NONE
```

Both arms are live defects in a real sense: `grep -qx` → `grep -q` admits
callsign `ok` against a roster listing `ok-1`, measured (`rc=0`,
`reached_claude=True`). This fleet has a lane called `ok-1`; `ok` is not rostered
and would have launched.

## FC — the gate degrades to a no-op on a missing input, and still reports success

```
  roster ABSENT          rc=0  reached_claude=True  said_roster=True
```

`WARNING roster.txt absent -- launching unrostered`, then it launches anything.
That is **H30's class at the gate with the widest blast radius**: a missing INPUT
silently degrades a mechanism to a no-op while it still reports success. Deleting
one tracked file removes admission for the whole fleet, and the only trace is a
line in a log nobody reads.

**Not fixed by me, and that is deliberate.** `roster.txt` is the operator's
sanction list, so what a missing one means is a question about the operator's
authority. An agent ruling on it is A22 — the beneficiary supplying the input to a
check on itself — and both answers cost something: fail-closed lets one `git rm`
stop the fleet with no lane able to restart it. Filed in `HUMAN_NEEDED.md` with
both costs and a one-line ask. The current behaviour is now **pinned by a check**,
so changing it requires changing the check and saying why.

## The repair — 9 checks, and they carry H62's two lessons

`test_loop_gate.sh` 66 → **75 checks**. Each arm asserts on the refusal **text**
as well as `rc` (H62 class 1: rc=1 does not say which gate refused), and the
detach-announcement rather than only the child's artifacts (H62 class 2: an
absence assertion read at the parent's exit can be won by being early). Every arm
has a brief, because the brief gate sits *below* the roster gate and would
otherwise refuse for a reason the block is not about — which is exactly how the
hostile-callsign block went inert.

```
unrostered callsign is refused
  refusal names the roster, not just a code
  and the unrostered lane never reached claude
  and announced no detach (unrostered)
  a ROSTERED callsign is admitted (else the gate just says no)
a callsign that is a SUBSTRING of a rostered one is refused
  and it never reached claude either
roster ABSENT admits any callsign (FAIL-OPEN — measured, not chosen)
  and says so out loud
```

`falsify.py` gains **F27** (gate deleted) and **F28** (exactness dropped). Both
fire; control green at 75.

`verify.out`, the same attack against the repaired suite:

```
FA  suite reds with the roster gate DELETED:  ['a callsign that is a SUBSTRING of a
    rostered one is refused', 'never reached claude', 'refusal names the roster',
    'unrostered callsign is refused']
FA' suite reds with exact match loosened:     ['a callsign that is a SUBSTRING of a
    rostered one is refused', 'never reached claude']
```

FA no longer fires. The gate is falsifiable in two independent ways.

## Reproducing

```sh
bash spikes/harness/test_loop_gate.sh                   # 75 checks
python3 spikes/H7_harness_attack/falsify.py F27 F28     # both fire, control green
python3 spikes/H63_roster_attack/attack.py              # 3 suite arms + 5 launcher arms
```

`attack.out` is the pre-repair run; `verify.out` the post-repair one. Same script.
