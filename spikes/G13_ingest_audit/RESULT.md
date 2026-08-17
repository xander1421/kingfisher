# G13 — the data has a 5% error rate, and the result survives it

**Verdict: SURVIVES.** The graph every G-result rests on was never audited. It is
regex over prose. Measured error is **5.0% on verdicts and 4.8% on citations**,
and at that rate the G10 attention-vs-control gap stays positive in every trial.

## Measured, not assumed

20 of 60 nodes sampled (seeded), every fact re-derived by a **different method**
than the ingest used — verdicts from the `**Verdict` line rather than the first
1200 characters, citations restricted to tokens outside code fences and file
paths naming a directory that exists.

```
verdict error    1/20                  = 5.0%
citation error   4 spurious + 0 missed = 4.8% of 83 edges
```

Zero missed edges. Every citation error is **spurious** — the ingest sees a
citation where the audit does not (`S72→S52`, `N1→S55`, `S5→S7`, `S32→S15`),
which is the expected failure of a regex that scans prose.

The one verdict disagreement is **S63**: ingest `INVALID`, audit `GREEN`. That
is a genuine ambiguity in the source, not a parse bug — a spike can carry one
verdict at write time and a different status after review. Which is right is a
question about the workspace, not about the parser.

## Sensitivity: does the finding survive its own data quality?

Perturb the graph at exactly the measured rates — flip 5% of verdicts to a
different value, drop or add citations at 4.8% — and re-run G10's loop, eight
trials:

```
unperturbed        attention 64%   control 16%   gap +47%

trial 0..7 gaps    +45 +47 +45 +48 +41 +42 +41 +39

perturbed          attention 59% (sd 3.9%)   control 16% (sd 2.7%)
                   gap +44%   worst trial +39%
```

**The gap never goes negative.** Absolute preservation falls about 5 points;
the comparison does not move materially.

That is the expected behaviour and it is now measured rather than argued:
**error that hits both arms equally cannot flip a comparison.** It is also the
reason the G-series reports gaps against a floor rather than absolute
percentages — a habit that turns out to have been load-bearing.

## What this does NOT cover, and it is the bigger gap

This validates that the **parse matches the source**. It says nothing about
whether the source is right.

G4 already found the labels partly encode *whether a claim was attacked* rather
than *whether it was wrong*, since "never attacked" and "attacked and survived"
are both recorded as live. That is label error at a level no parser audit can
reach, it is unmeasured, and it is larger than 5%.

So the honest statement is: **5% parse error, survivable; label validity,
unknown and unaddressed.**

## My own audit was wrong first

The first run reported 19 "missing" citations of 102 — 22.5% error. Every single
row listed its own id as missing, because the audit counted a spike naming
itself while the ingest correctly excludes self-citation.

A **uniform** shape across every row is the tell that it is the instrument, not
the data. Same signal as G9's flat verdict and N1c's inert control. Fixed, and
the real number is 4.8%.

## Reproduce

```sh
cd spikes/G13_ingest_audit && python3 audit.py
```

Sensitivity analysis inline in this file's git history; it perturbs
`G1_graph_ingest/graph.json` and calls `G10_closed_loop/loop.py` directly.
