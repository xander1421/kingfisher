# H20 — two unreachable checks, and only one of them was the row's defect

**Verdict: DONE.** `falsify.py` v3 (multi-edit falsifiers, shared apply site, id
filter) and `test_loop_gate.sh` section 9b. Suite 62 → 63 checks.

## The row

> `falsify.py` applies exactly ONE edit per falsifier, so any check that only goes
> red under two simultaneous defects is unreachable and its PASS is unmeasurable.
> Two named: `writes no 'unknown' marker` and `lane signal untouched`.

**Falsifier, stated in the CLAIM before any code was written:** *if either named
check goes red under a SINGLE revert, the row misdiagnosed it and I withdraw that
half — the test is to try each single revert alone before writing any list
support.* Run: `probe.py`, four arms, all four falsifiers passed.

| arm | pass/fail | target checks red |
|---|---|---|
| control | 62 / 0 | neither |
| A — LANE default restored | 56 / 6 | neither |
| B — glob signal read restored | 59 / 3 | neither |
| A+B | 55 / 7 | `lane signal untouched` |
| control + plant in section 9 | 62 / 0 | neither |
| A + plant in section 9 | 60 / **2** | `writes no 'unknown' marker` |

## Half the row was right, and the other half was a different defect

**`lane signal untouched` — the row is right.** Red under the pair, quiet under
either alone. Consuming lane `L1`'s signal from a callsign-less session needs the
LANE default *and* the glob read: with the default alone the hook looks for
`.loop_signal.unknown` and there is none; with the glob alone it never reaches the
lookup. A driver applying one edit per falsifier could not construct it.

**`writes no 'unknown' marker` — not a two-revert check at all.** It lived in a
section that opens `rm -f .loop_signal*`, and the hook writes `.loop_exit.<LANE>`
only after consuming a signal. **No combination of hook defects can redden it**;
it is A15, an instrument that cannot produce the answer, and the fix is a
precondition rather than driver support.

## The obvious fix for that half is wrong, and the probe measured it

Planting the signal *inside section 9* makes the hook exit legally under the
LANE-default defect, so `no callsign is not gated` stops firing on the very defect
it exists for: **that defect reddens 6 checks, and 2 with the plant folded in.**
A repair that raises one check's coverage by disarming five reports better and
tests less. The plant went into a new **section 9b** instead. Verified: A still
reddens 6.

## Fixing the class, not the site

The row named this itself — *"the driver has two apply sites, the F-series and the
G-series, and a fix at one is the defect this repo has paid for at every version
of §12.2."* Both loops now call one `apply_edits()`, and both take the same
optional extra-edits field, so a two-defect githygiene falsifier costs nothing.

Also v3: **`falsify.py F24 G2` runs a subset.** A full pass is 25 scratch trees at
~3 min of suite each — over an hour — so there was no way to exercise one
falsifier while writing it. The instrument that answers *"is a red run reachable"*
was itself unreachable during the work that needed it. A filtered run **refuses to
print coverage**: a subset ratio in the shape of a full pass is family B.

## What runs

```sh
python3 spikes/H20_multi_revert/probe.py    # the row's own falsifier, 6 arms
python3 spikes/H20_multi_revert/verify.py   # the repair's, 4 arms / 5 falsifiers
python3 spikes/H7_harness_attack/falsify.py F24   # F24 alone through the real driver
```

`verify.py`, stated before running — V1 control all-green, V2 marker reds under
the single revert, V3 signal reds under the pair, V4 signal quiet under either
alone, **V5 the LANE-default defect still reddens ≥ 6 checks** (the disarming
test, which the obvious fix fails). Run: 5/5 PASS, control 63/0, A reddens 6.

## Two errors of mine, recorded rather than smoothed

1. **`probe.py` v1 named the wrong partner defect** — F5's bare-signal form, which
   `.loop_signal.L1` matches under no hook at all. The A+B arm would have reported
   "row does not stand" over a defect of my own. Found by reading the section the
   check lives in instead of the check's name.
2. **My cycle-4 note that the driver was "not hung, python block-buffers stdout"
   was wrong.** It is simply over an hour long. The run I left in flight was also
   *unobservable* — stdout to a pipe whose reader died with the session — so its
   result could never have been read whatever it said. That is what the id filter
   and running detached to a file are for.

**What this does not construct:** any check needing three simultaneous defects,
and any two-defect case in the G-series — the field exists and has no user, so it
is untested there.
