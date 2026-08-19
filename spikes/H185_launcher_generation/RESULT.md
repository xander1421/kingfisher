# H185 — a lane runs the launcher it was started with, and nothing recorded which

**ok-1, 2026-08-19.** `run_loop.sh` **v12** (producer), `bringup.sh` **v7**
(consumer), 8 arms.

## CLASS

> **The census reports a lane as UP without knowing which launcher it is running,
> so a fix to `run_loop.sh` is invisible until something else kills the lane.**

Measured live, the hour it mattered: `run_loop.sh` **v11** — H179's process-group
fix — landed at 17:0x, and **all five lanes were pre-v11 generations**, up since
16:07, still carrying the defect that had just been fixed. `bringup.sh` printed
all five `UP` with turn ages and CHANNEL distances, because it had no column for
this.

Same family as **H21** (*a wrapper still running a generation that predates the
beat*), which was recorded as a four-state observation in prose and never made
observable.

## Two sides, and they fail differently

**Producer — `run_loop.sh` v12, defect 15.** At launcher start:

```sh
printf '%s %s\n' "$(shasum -a 256 "$0" | cut -c1-16)" "$(date +%s)" > "$GENFILE"
```

**Content, not path.** Every lane runs the same `./run_loop.sh` and the file is
edited in place, so a path proves nothing. It is an approximation by construction
— `sh` may re-read an edited script mid-run — and the honest reading is *what this
generation was STARTED with*, which is exactly the question.

**Consumer — `bringup.sh` v7, `lane_launcher()`.** Three states, each named:

| state | line |
|---|---|
| current | *(nothing — quiet when there is nothing to say)* |
| stale | `LAUNCHER STALE -- started with <had>, tree has <now>; picks up the fix at its next relaunch` |
| unrecorded | `LAUNCHER UNRECORDED -- generation predates the stamp (H185); not stale, UNKNOWN` |

## The two rules this row is built to obey, both earned in this same file

- **C1 — ABSENT is not CURRENT.** H88's defect was `lane_fails` returning `-1` for
  absent and being read by a branch that could not tell it from healthy, so the
  census printed **byte-identical lines** for a missing counter and a healthy one.
  That is one function away from this one. `unrecorded` is a named state and the
  probe asserts it is not silence.
- **F3 — reported, never acted on.** A stale launcher must never add a lane to
  MISSING or refuse quorum. Relaunching a healthy lane because its launcher is old
  is H6's *absent branch LAUNCHES* hazard, and worse than the number it reports.

## Arms

```sh
bash spikes/H185_launcher_generation/probe.sh
```

```
  C2   PASS sandbox drives the live bringup.sh AND run_loop.sh
  P1   PASS the launcher stamped its OWN content (fca18af466d57ca7)
  P2   PASS and when it started (1787154991)
  C3   PASS census sees PROBE-7 UP, so the launcher note is reached
  A1   PASS current launcher prints no note (quiet when there is nothing to say)
  A2   PASS stale is NAMED and quotes both hashes
  C1   PASS ABSENT is NAMED, not silent -- H88's defect not re-earned
  F3   PASS stale launcher: still UP, not MISSING, quorum untouched (EXIT=0)
```

`P1` is the arm that would catch the commonest way to get this wrong: stamping the
hash of *some* file rather than of the launcher that is running. `C3` is A29 — if
the census did not see the lane UP, every consumer arm below it would be measuring
the DOWN path.

## The live fleet, immediately after

```
  AGENT-1      UP   pid 32211 (loop) turn age 1s, last CHANNEL line 7 back LAUNCHER UNRECORDED -- generation predates the stamp (H185); not stale, UNKNOWN
  …
  quorum: 5/5
```

Every lane reads UNRECORDED, which is **correct and is the point**: they were
started before the stamp existed. They read `current` after their next relaunch,
and nothing here hurries that — restarting a healthy lane to make a number tidy is
A23, the instrument perturbing what it observes.

## ATTACK, one cycle later, on this row's own consumer (cycle 24)

`bash spikes/H185_launcher_generation/attack.sh` — 7 arms, two-sided, pinned to
`29aee62`.

**THE PROBE ABOVE ASKED WHETHER `unrecorded` IS SILENT. THE ATTACK ASKED WHETHER
IT IS TRUE.** v7 returned `unrecorded` for **three different causes**:

1. no stamp file — the intended meaning, a fact about the lane;
2. a stamp present but empty or garbage — a corrupt stamp, a different fact;
3. **`./run_loop.sh` unreadable from the census's cwd — a fact about the CENSUS**,
   which prints for **every lane at once** and reads as *an old fleet*.

That is **H88's class re-earned inside the control written to prevent it**. C1
asserts `unrecorded` is not silence, and it passes just as happily when the reason
is that the census is standing in the wrong directory.

`bringup.sh` **v8** names all three:

```
  AC    PASS census sees PROBE-6 UP (arms are not vacuous)
  A0    PASS valid stamp: quiet
  A1    PASS names the CENSUS's own inability (UNCOMPARABLE)
  A2    PASS names a corrupt stamp (UNREADABLE), distinct from old
  A3    PASS no stamp still reads UNRECORDED (the intended meaning survives)
  A4    PASS still UP, not MISSING, quorum untouched
  B1    PASS pre-fix: a missing ./run_loop.sh DID read as 'the lane is old' -- the defect was real
```

**A3 is the arm that stops the fix from being a rename**: the intended meaning has
to survive the split. **B1 is the two-sided half** — it drives the pinned pre-fix
rev and its verdict is inverted, because there the conflation MUST appear; a
one-sided green proves only that today is green.

**This matters beyond a label.** `bringup.sh` runs from launchd with
`WorkingDirectory` set, and there are **two `bringup.sh` in this repo** (H44). A
census run from the wrong directory would have reported the entire fleet as
*generations that predate the stamp* — a sentence about five lanes, produced by a
fact about one missing file.

Regression over the change: `test_loop_gate.sh` **91 checks pass**,
`test_h44_check_is_readonly.sh` **15 passed** (the census stays a reader — this
adds one more thing it reads), `spikes/H173_flapping_lane/probe.sh` all arms.
