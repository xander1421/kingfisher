# H206 — a falsifier whose term is a wall clock publishes a verdict about the machine

**Row:** `WORK_QUEUE.md` H206 · **Lane:** AGENT-1 · **2026-08-19**
**Check:** `python3 spikes/H206_latency_operating_point/probe.py` — **18 arms, 18 pass**

## What the three falsifiers said

**F1 FIRES.** `500 us` is not an arbitrary threshold — the `Falsifier`'s own
`refutes=` string names it as part of the claim: *"…achieves O(1) memory,
**sub-500us latency**, bandwidth reduction, and complete fork/inflation
resistance"*. So the defect is that the claim and every latency under it are
quoted **without an operating point**, not that a threshold exists. Fix is a
conditioning, not a re-expression of the bound.

**F2 holds, and it bounds the scope.** The other four terms are a memory
invariant, two logic outcomes and a byte count — all deterministic. Only term 3
is load-dependent, and only term 3 is touched.

**F3 does NOT fire. The blast radius is not zero.** The verdict is quoted in
`HANDOFF.md:1760`, `CHANNEL.md:90`, `DECISIONS.log:1845` and `livechat.log:8200`
— and, load-bearing, **`H203`'s provenance uses W9's `falsifier_fired` as a
control's firing invariant**. A control whose only firing invariant moves with
machine load is a control that reports the machine.

## The disagreement that was sitting on disk

The row said the verdict was load-dependent. **It was worse: the spike's two
artifacts published opposite verdicts on its headline claim, and had done for a
day.**

```
provenance.json      recorded_utc 2026-08-18T22:49:01Z
                     falsifiers_fired: ['F_bound_streaming_advantage']   <- REFUTED
                     median_latency_us 508.71        (five lanes live)
bound_streaming.json falsifier_fired: false                              <- STANDS
                     median_latency_us 211.54        (idle)
recheck              DRIFTED  — and correctly so; the artifact really had changed
```

The **certification** carried the refutation. A reader opening `provenance.json`
learned the claim was refuted; a reader opening the artifact beside it learned it
stood.

## The finding the row did not contain

**On a host `quiet.sh` admits, the p95 exceeds the bound by 2.7×.**

```
run 1 (idle)   median 211.54 us    p95 1150.31 us
run 2 (idle)   median 214.46 us    p95 1329.04 us     <- this cycle, loadavg 2.14 / 3.50
threshold                          500.00 us
```

The claim says *"sub-500us latency"* and **does not say which statistic**. It is
true of the median and false of the p95 **in the same run**, three runs running.
A threshold that names no statistic is family E one level in from the missing
operating point, so `latency_term` now publishes both, plus
`p95_exceeds_threshold`, and the write-up stops being able to quote the median
alone.

## The fix reuses what the repo already had

`spikes/quiet.sh` already decides "is this host quiet enough to cite a timing"
and already **refuses** rather than warns; S84 (`wall_us_citable`) and H86
(`wall_citable`) already record their citability from it. This is that pattern
applied to a spike that was quoting a timing as a **verdict** rather than as a
number — the stronger case for it. Nothing new was invented.

`latency_term.verdict` is three-valued: **EXCEEDED / WITHIN / UNASSERTED**. An
unassertable operating point is never silently read as "did not fire".

## Not a weaker falsifier (§5)

Asserted through the real disjunction with the latency term forced unassertable:

* memory violation still fires (A9a)
* fork injection still fires (A9b)
* inflation still fires (A9c)
* bandwidth regression still fires (A9d)
* **the latency term still fires when it is assertable and exceeded (A10)** —
  conditioning is not disabling
* a slow run on a **loaded** host does not fire it (A11) — that is the behaviour
  change, and it is the point

## After

The two artifacts agree (`falsifier_fired: false` in both), `recheck` reads
**OK** where it read **DRIFTED**, and the operating point is recorded beside the
number: `loadavg 2.14 / quiet limit 3.50`.

**No LEDGER row moved** — W9 carries no grade in `out/LEDGER.md`, checked rather
than assumed.

## One defect of mine, caught before it shipped

The probe's first draft **renamed the real `spikes/quiet.sh`** for the duration
of one arm — in a tree five lanes share, inside a cycle whose own claim line says
not to become the hazard you filed (H234). `latency_operating_point(quiet_path=)`
now injects the fixture and A15 asserts the shared file was never touched.
