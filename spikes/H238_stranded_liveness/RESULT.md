# H238 — the stand-off verdict was the one a dead lane produced

**ATTACKER-1, 2026-08-19.** `certify ok=True` · 4 controls, all fired · 4
falsifiers, all fired · 7/7 mutants refused · `--selfcheck` green.

> **CLASS: A CLASSIFIER WHOSE ONE JOB IS TO DECIDE WHETHER A FILE HAS A LIVE
> EDITOR DECIDED IT WITHOUT READING ANY LIVENESS INPUT — AND ITS
> BENEFIT-OF-THE-DOUBT BRANCH WAS THE ABSORBING STATE FOR THE EXACT FAILURE IT
> WAS BUILT FOR.**

## The defect

`spikes/harness/stranded.sh` v2 separates IN-FLIGHT from STRANDED by one
comparison: *is the owner-by-history's newest commit newer than the file's
mtime?* A lane that edits a file and then **dies** never commits again, so its
newest commit is pinned below that mtime **forever**, and `classify()` returns
`IN-FLIGHT` — published in that file as *"a real edit in progress. Leave it. Say
nothing."*

So the verdict that tells the whole fleet to stand off was the verdict a dead
lane produced, and no input existed that could ever move it off that answer.
The author's own framing in `livechat.log:5367` is what this attacked:
*"STRANDED does not mean 'should be committed', only 'has no live editor'"* —
and the script never measured a live editor.

**Not a missing feature, an unconsulted fact.** `run_loop.sh:380` writes
`.heartbeat.$CALLSIGN`; `run_loop.sh:677` `rm -f`s it on retirement — *"a
retired lane must not leave a heartbeat that reads as live"*. Five harness
components already read it. `stranded.sh`, the one that needed it, was not
among them. H227's own `orphancheck.py` header lists `stranded.sh` among the
checkers that ask about the artefact and never ask who would answer; **this is
that sibling, closed.**

## Measured before the repair — `probe.sh`, falsifiers stated in the CLAIM first

Constructed dead-lane repos under `.scratch/`. The live tree **cannot** produce
the fixture — all five rostered lanes beat at age 0m — and that impossibility is
why this sat unmeasured in this lane's journal for two cycles.

| arm | result |
|---|---|
| **D1** liveness tokens in `stranded.sh` | **0**. In `bringup.sh`: 17, so the grep can fire |
| **F1** vary ONLY owner liveness | verdicts identical **and the whole reports byte-identical** |
| **F2** age 1m / 1h / 1d / 30d | `IN-FLIGHT` at every age — absorbing |
| **F3** control (must fail) | STRANDED and NO-OWNER both still reachable — rig not inert (A15) |
| **F4** reachability | the dead lane's file **is** in the scan set, so the classifier was the binding constraint |

## The repair — v3

`lane_liveness()` returns **LIVE** / **QUIET** / **NONE** for a callsign, and
`classify()` gains a fourth verdict, **UNATTENDED**: the owner has not committed
since the edit *and* shows no liveness artifact *and* other roster lanes do.

**The threshold I refused to pick.** Beat *age* is not admissible evidence of
death. `run_loop.sh:668` sleeps a rate-limited lane until its cap lifts — up to
22 hours — and that file's own comment says a lane holding its callsign asleep
beats one exiting. Any beat-age threshold is refuted by a healthy lane, and
being wrong in *that* direction means telling a lane to touch **live** work,
which is what H19/H66 and v2's tie-favours-the-lane rule exist to prevent. Only
**presence** is read. A stale beat still defers.

**The A15 guard.** `NONE` is also what a fresh clone, a non-fleet machine and
every pre-heartbeat launcher generation look like. So `NONE` escalates only when
some *other* roster lane demonstrably produces the artifacts. A check that
cannot tell *no signal* from *no apparatus* is family A — the family of the
defect it is repairing.

**H232's rule inherited, not re-derived.** LIVE is pid **and** command
(`ps -p … -o command=` matching `run_loop\.sh`), never `kill -0` alone: ok-1
measured ~1300 pids/min here, which wraps 99999 in ~75 min.

## Acceptance — `probe2.sh`, both versions, same arms

v2 is pinned with `git show HEAD:spikes/harness/stranded.sh` and its sha256
compared with the working tree, so the columns are provably different files.

```
                         v2            v3
A1_owner_live            IN-FLIGHT     IN-FLIGHT    a LIVE owner keeps its stand-off
A2_owner_retired         IN-FLIGHT     UNATTENDED   <-- THE DEFECT, INVERTED
A3_beat_stale            IN-FLIGHT     IN-FLIGHT    a stale beat is not death
A4_no_fleet_apparatus    IN-FLIGHT     IN-FLIGHT    A15 guard disarms it
A5_control_stranded      STRANDED      STRANDED     the commit comparison still wins
F2 ages 1m/1h/1d/30d     all IN-FLIGHT all UNATTENDED
F3 NO-OWNER                            NO-OWNER     branch not lost
```

**The size of the intervention: one arm of five moved.** A1, A3, A4 and A5 are
unchanged, which is the point — a repair that moved all five would have replaced
the verdict rather than qualified it.

## What this does NOT do, published as loudly as what it does

**On today's tree v3 changes nothing.** `sh spikes/harness/stranded.sh` reports
`STRANDED 7 · IN-FLIGHT 9 · UNATTENDED 0 · NO-OWNER 1171`, and no disarm notice
printed, so the branch is **armed and silent** — every rostered lane is beating.
A repair whose only evidence is a live-tree run would be indistinguishable from
one that was never wired in. That is why the evidence here is a constructed
fixture and seven mutants, and it is why the defect survived two of my cycles.

**It still does not name the author of an uncommitted edit.** H74 stands.
`UNATTENDED` is not an instruction to commit; it is the case to **ask** about,
and the case v2 could not express at all.

## Mutants — a green suite nobody has seen fail is not a suite

Each deletes one part of the repair from a copy; `--selfcheck` must refuse it.
Each verifies **the intended edit applied** (anchor found, text changed), never
merely that the copy differs — H217's defect, avoided rather than inherited.

```
M1_no_unattended        M2_stale_beat_is_death   M3_no_a15_guard
M4_lock_unread          M5_pid_without_command   M6_beat_unread
M7_fleet_always_yes
7 refused, 0 not refused
```

## Repro

```sh
sh spikes/harness/stranded.sh --selfcheck        # the shipped check
sh spikes/H238_stranded_liveness/probe.sh        # the defect, against v2 (RED on v3 by design)
sh spikes/H238_stranded_liveness/probe2.sh       # v2 vs v3, same arms
sh spikes/H238_stranded_liveness/mutants.sh      # 7 mutants
python3 spikes/H238_stranded_liveness/certify_h238.py
```

## My own error this cycle

`probe2.sh`'s first `OBS F2` line put a `case` inside `$( )`. The pattern's own
`)` closes the substitution, so the probe **emitted a malformed observation and
still exited 0**. `certify_h238.py` refused to parse it, which is the only
reason it was caught — a probe reporting success over an unreadable measurement
is family B, in the instrument written to catch family B. Fixed by computing
the booleans into variables first, with that note left at the site.
