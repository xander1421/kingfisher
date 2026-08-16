# S17 — I attacked S11 and failed. The failure is worth more than the attack.

**Verdict: GREEN for S11, RED for S11's cutoff rule, and M4 comes out stronger.**

I set out to break my own strongest result. The attack was declared in advance in
`chat.log` and in this spike's docstring: S11 clustered by `(pred, subj)` and
queried by `(pred, subj)`, which is close to circular, so a multi-pattern
workload should collapse it and take M4's last justification with it.

It did not collapse. Instead the experiment found a defect in **my own S11
cutoff rule**, and once that was fixed the conclusion inverted into something
more useful than what I was attacking:

> **Layout does not buy recall. Layout buys CPU work at fixed recall.**
> Unshaped bundling reaches the same recall — by making the CPU exactly-match
> **78% of the store**. Shaped bundling reaches it at **22%**.

Code: `multipattern.py`. Output: `multipattern_sqrt.json`, `multipattern_B.json`,
`multipattern.log`, `multipattern_B.log`, `c3_cutoff_sweep.log`.
D=1024, B=16, 100k triples, 100 queries per pattern.

## Method

One store, built once under a fixed layout, then queried with **every** exact
pattern class S10 validated (m ≥ 2 of 3). A shard is built once and serves many
query shapes, so the honest test is one store against many patterns — not one
store per pattern, which is what S11 accidentally measured.

Five layouts: `random` (the no-shaping control), `by_pred_subj` (S11's),
`by_pred_obj`, `by_subj`, and `interleaved` (a deliberate compromise, alternating
runs of both sort orders).

## Round 1 — with S11's cutoff, the attack looked like it landed

Using S11's rule `2·nnz(Q)/sqrt(B)` unchanged:

| layout | C1 `(p s ?o)` | C2 `(p ?s o)` | C3 `(? s o)` | C6 `(p s o)` |
|---|---|---|---|---|
| random | 0.6936 | 0.6856 | 0.0200 | 0.4800 |
| **by_pred_subj** | **1.0000** | **1.0000** | 0.6850 | **1.0000** |
| by_pred_obj | 1.0000 | 1.0000 | 0.7200 | 1.0000 |
| by_subj | 0.9924 | **0.0192** | 1.0000 | 1.0000 |
| interleaved | 1.0000 | 1.0000 | 0.1700 | 1.0000 |

Two things already contradicted my prediction. `by_pred_subj` held **recall 1.0
on C1, C2 *and* C6** — three of four — so it was not circular in the way I
claimed. And `interleaved`, the honest compromise, was **worse** than committing
to either single key (C3: 0.17 versus 0.685).

Only C3 `(? s o)` failed. I was about to write that up as "no single layout
serves all patterns" when the CPU column made it suspicious: C3 was checking
**0.08%** of the store. Almost nothing was passing the cutoff. That is the
signature of a threshold that is too strict, not a layout that scatters answers.

## Round 2 — the confound was real, and it was mine

Sweeping the cutoff divisor for C3 under `by_pred_subj` (`c3_cutoff_sweep.log`):

| divisor | recall | perfect | CPU % |
|---|---|---|---|
| 2.00 | 0.0600 | 6/100 | 0.00 |
| 4.00 (= √B) | 0.6750 | 66/100 | 0.08 |
| 8.00 | 0.9700 | 97/100 | 0.59 |
| 12.00 | 0.9900 | 99/100 | 3.88 |
| **16.00 (= B)** | **1.0000** | **100/100** | 9.26 |

C3's "layout failure" was a **cutoff calibration failure**. S11 flagged
`sqrt(B)` as "a guess above B=1" and noted the CPU plateau was "evidence the
cutoff is far too permissive" — that reading was backwards. It is too *strict*
for patterns not aligned with the layout, and the correct divisor is ~B, not √B.

## Round 3 — the corrected matrix, and the real finding

Re-running everything with the calibrated cutoff `2·nnz(Q)/B`:

| layout | worst recall | recall-1.0 on | **worst CPU %** |
|---|---|---|---|
| random | 0.9976 | 3/4 | **78.04** |
| **by_pred_subj** | 0.9700 | 3/4 | **21.88** |
| by_pred_obj | 0.9800 | 3/4 | 22.26 |
| by_subj | 0.6741 | 2/4 | 34.41 |
| interleaved | 0.9000 | 3/4 | 22.30 |

**Random bundling now reaches essentially the same recall as shaped bundling.**
It gets there by handing the CPU 78% of the store — an exact-match pass over
three quarters of the shard, which is a full scan wearing a pre-filter costume.
Shaped bundling reaches the same recall at 22%: **3.6× less exact-match work**.

And layout still matters directionally: `by_subj` is a *bad* layout and is
punished on both axes at once — recall 0.6741 on C2 and 34.41% CPU.

## What this changes for M4

`analysis/GAP_MATRIX.md` row 17 and `out/PORT_PLAN.md` M4.2 justify the shaping
job class with S3's sparse/dense density crossover. S13 showed that crossover was
measured against a baseline 15× below the machine floor. S11 replaced it with a
recall argument. **This spike shows the recall argument was also wrong** — recall
is recoverable by loosening the cutoff, on any layout.

The surviving claim is better than both:

> Shaping's product is **exact-match work per query at fixed recall**. It is
> measurable before and after on the shard alone, it needs no SpGEMM benchmark
> and no crossover, and it is denominated in exactly the unit `PORT_PLAN.md`
> M4.2 already says shaping should be priced in — "shaping makes *future* jobs
> cheaper, so the marketplace should pay it out of a levy on the jobs that
> subsequently run on the shaped shard."

That is a cleaner basis for M4 than anything the workspace had, and it is the
one thing a verifier can check cheaply: recompute rows-checked on the output
shard for a fixed query set. No replication, no challenge, no bisection.

## Corrections owed to S11

1. **The cutoff rule is wrong.** `2·nnz(Q)/sqrt(B)` should be `2·nnz(Q)/B` for
   patterns not aligned with the bucket sort key. S11's headline numbers (64× at
   recall 1.0000, 11.82% CPU) were measured on the *aligned* pattern, where the
   stricter cutoff is both sufficient and cheaper — so **those numbers stand**,
   but only for the aligned case, and S11 should say so.
2. **The right rule is per-alignment, not global**: aligned → `√B` (~10% CPU),
   unaligned → `B` (~22% CPU). That is a real design knob and neither spike had it.
3. **S11's circularity caveat was overstated by me.** `by_pred_subj` serves C1,
   C2 and C6 at recall 1.0. The predicate is doing the work — it appears in three
   of the four patterns, and `by_subj` (no predicate in the sort key) is precisely
   the layout that collapses C2. The design rule is **cluster on the slots most
   commonly bound across the workload**, not on any single query's key.

## What this does NOT show
- One synthetic uniform graph, one B, one D. The cutoff calibration (`B` vs `√B`)
  is fitted on this data and is not derived; there is probably an analytic form
  and I did not find it.
- `interleaved` is one naive compromise construction. Its failure is evidence
  that *this* compromise is worse than committing, not that no compromise exists.
- C3 `(? s o)` still lands at 0.97 under `by_pred_subj` with a 0/100 minimum,
  i.e. at least one query loses everything. Worst-case recall, not mean recall,
  is what a verification protocol has to care about, and no spike has tuned for it.
