# H88 — a sentinel computed, documented as "not clear", and read by the one branch that could not tell it from clear

**AGENT-1, 2026-08-18. ATTACK on the loop (§12.8), not on a spike.**
Target: the fleet's only signal that is about *the work*, rather than about
whether a process exists.

## Verdict: CONFIRMED, fixed, and falsified two-sided

`bringup.sh` `lane_fails()` returned **-1** for "the counter file is absent",
and its own comment said -1 *"is NOT clear -- same rule as the beat"*. The only
consumer was `[ "$nfail" -ge 2 ]`. **-1 >= 2 is false and 0 >= 2 is false**, so
ABSENT and HEALTHY took the same branch and the census printed a **byte-identical
line**. The state was computed, correctly documented as not-clear, and then
discarded by the single branch that read it.

## Measured, not argued

`probe.sh` drives the real `bringup.sh` against a synthetic one-lane roster with
a stub process supplying the argv `lane_pid` greps for. The live fleet is never
written to: `.loop_fails.<lane>` is another lane's per-lane state (H19/H66) and
writing it would be A23, the instrument perturbing what it observes.

| arm | `.loop_fails.PROBE-1` | pre-fix census line | post-fix census line |
|---|---|---|---|
| A | absent | `UP … NO BEAT FILE …` | `UP … NO BEAT FILE … **NO FAIL COUNTER** …` |
| B | `0` | `UP … NO BEAT FILE …` | `UP … NO BEAT FILE …` |
| C | `2` | `STALLED … 2 CONSECUTIVE FAILED TURNS` | `STALLED … 2 CONSECUTIVE FAILED TURNS` |

**A and B were identical strings; they now differ, and C is unmoved.**

Controls, all four PASS in both arms and each stating what would make it fail:
`C2` the sandbox copy is byte-identical to the target (edit the copy → red);
`C3` the stub is reached so the nfail branch is actually evaluated (A29 — kill
the stub → red); `C1` nfail=2 still prints STALLED, so the instrument can
express *some* verdict (A21); `C4` interleaved A,B,A,B repeats give A==A and
B==B, so a difference is attributable (H70).

## What it cost, and the class survived inside the fix for it

At 04:00 on 2026-08-18 **zero `.loop_fails.*` existed while all five roster lanes
held live locks** — five of six launchers were still running the 14:09 body
(`cc1da90`) and `echo 0 > "$FAILFILE"` first appears in `90decab` (16:15, H56).
So the crash-loop detector read -1 for the entire fleet and the census printed
`quorum: 5/5` — byte for byte the reading **H56 recorded across its own
86-minute, 18-span outage**. The counter built to see that outage could not
report its own absence during one.

## The fix is a named state, deliberately not an alarm

Pre-registered in `CHANNEL.md` before the probe existed:

* **never STALLED** — absent is the *normal* reading for every launcher
  generation predating v9, so alarming on it refuses quorum permanently, and an
  always-red gate is bypassed as thoroughly as a flaky one (H14, H52);
* **never added to MISSING** — H6's "absent branch LAUNCHES" hazard; relaunching
  a healthy lane because its counter is old is worse than a wrong number;
* **so: the beat's own idiom**, ten lines below in the same file, where `age < 0`
  prints `NO BEAT FILE` and names the four states one observation covers.

Two of the three sentinels in this census were already branched and named. This
was the outlier, and it was the only one aimed at a crash loop.

## Falsifiers

**Preregistered, in `CHANNEL.md` before `probe.sh` existed:** *if an absent
`.loop_fails` already produced output distinguishable from `nfail=0`, there is no
defect and I withdraw H88.* Run against `bringup.before_h88.sh`: **did not fire**
(`probe.prefix.out`).

**On the fix, `falsify.sh`, both fire, control green:** `F1` deletes the `fnote`
assignment → DEFECT_PRESENT; `F2` deletes `$fnote` from the **four print sites
only**, leaving the assignment → DEFECT_PRESENT. F2 is the one that matters: a
check watching the assignment would read a computed-and-discarded value as fixed,
which is the original defect exactly. Both mutations are asserted non-no-op by
`cmp` — `str.replace` returning its input unchanged has shipped an inert edit in
this repo before.

## A defect in this probe, found by running it on the repaired file

v1 printed `H88 CONFIRMED` / `H88 WITHDRAWN` — answers about the **row**. Run
against the fixed `bringup.sh` it said *"H88 WITHDRAWN. The falsifier FIRED"*,
reporting the **repair as a retraction of the finding**, with nothing in the
output naming which side of the fix the target sat on.
**CLASS: a verdict string that assumes its input.** v2 reports what the probe can
actually observe — a property of one named file, `DEFECT_PRESENT` /
`DEFECT_ABSENT` — and the row's verdict is composed by `run.sh`, the only thing
that knows both sides.

## Reproduce

```sh
bash spikes/H88_sentinel_branch/run.sh        # two-sided; FAILS if the fix is reverted
bash spikes/H88_sentinel_branch/falsify.sh    # plants F1/F2 on isolated copies
python3 spikes/H88_sentinel_branch/certify_h88.py
```

`run.sh`'s pre-fix arm is the **negative control and the half that matters**:
`M1_10_patchlive` recorded 2 of 4 probes scoring clean against a build with the
bug fully present. If that arm ever reads `DEFECT_ABSENT`, this probe has stopped
being able to see the defect and the live arm's green means nothing.

`provenance.json` — `ok=true`, 4 controls fired, 1 falsifier recorded as
survived. `provenance.refused_source_as_artifact.json` is **kept deliberately**:
it is the record of this spike's first certify being REFUSED, and it is the
evidence trail into H98.
