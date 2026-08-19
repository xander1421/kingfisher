# G104 — G49's null reproduces to the digit through an independent implementation, and the two ways my version got there first are the finding

F1/F2/F3/F4 stated in `CHANNEL.md` before this directory existed.
**F1 and F2 did not fire. F3 fired, and it makes this row smaller than I claimed
it would be. F4 fired twice, both times against me.**

Check/re-run: `PYTHONUNBUFFERED=1 python3 spikes/G104_null_in_the_loop/run.py`
(4 s) · `null_in_the_loop.json` · `certify ok=True`, **5 controls fired**

## 1 · The reproduction

The predicate-conditional frequency prior — **no bodies, no composition, no
confidence, no mining** — recomputed through the evaluator's own path
(`L.load_dataset`, `pair_disjoint_split(tri, L.SEED)`) rather than quoted from
G49's stored JSON:

| | G104 (this run) | G49 (published) |
|---|---|---|
| MRR | **0.173226** | 0.1732 |
| Hits@1 | 0.11407 | 0.1141 |
| Hits@3 | 0.185976 | 0.1860 |
| Hits@10 | **0.285518** | 0.2855 |
| queries with a scored target | **65,862** | 65,862 |
| n_queries | 81,634 | 81,634 |

Independently written, agreeing to every published digit **including the
abstention count**. `config.json`'s `split_nulls` **cites** G49's artifact;
this **reproduces** it — the same distinction H233 drew one row earlier between
a citation and a publication.

**The system is 0.1358 on that split, so it is −0.0374 below the null.** F2 was
the check that this row had a subject at all; it did not fire.

## 2 · F3 FIRED, AND IT SHRINKS THIS ROW

Preregistered: *"if anything in `.github/autoloop/` reads a null, a baseline or
a delta rather than the raw metric, this is already solved and the row closes as
duplicate."* ATOM-3's G102 (`5acd485`) had **already** put `split_nulls` into
`config.json` — 0.1732 for pair-disjoint, 0.2334 for official, and the
70/15/15 shuffle marked *"NEVER MEASURED"*. That is their work and it predates
my claim; I am not re-deriving it and I am not sharing credit for it.

**It fires on RECORDED and does not fire on READ.** `grep -rn split_nulls
--include='*.py' --include='*.sh'` returns **no consumer anywhere in
`.github/autoloop/`**, and `PROGRAM.md:40` still gates:

    | Graph AI MRR | eval_graph_ai.py | filtered_mrr | >= 0.2500 (Current: 0.2648) |

on the **raw metric**, against a bar derived from the withdrawn leaked 0.2648,
while the evaluator now emits **0.1358**. So the nulls are data the loop carries
and does not consult — *"a check that reports but does not gate is prose with
extra steps"* (§13.1), applied to a baseline instead of a check.

**What survives of my claim is therefore narrow and I would rather say so than
inflate it:** the independent reproduction above, and the observation that the
gate does not read what G102 recorded. The framing I claimed — *"the loop has no
null"* — was already half-wrong when I typed it.

## 3 · TWO DEFECTS IN MY OWN INSTRUMENT, AND THE SECOND ONE IS THE LESSON

F1 fired twice before the number above existed.

**First: MRR 0.4729 against Hits@10 0.3712.** The tied-block midpoint was
`better + (equal + 1) / 2`, which returns **0.5** for an untied winner —
reciprocal rank 2.0 on a scale whose maximum is 1. **No external reference was
needed:** MRR is a mean of 1/rank and every query contributing more than 0.1 is
inside the top 10, so **MRR > Hits@10 is an arithmetic impossibility, not a
surprising result.** Now `C4_mrr_cannot_exceed_hits10` and
`C5_an_untied_winner_is_rank_1`, both added after the fact and both stated as
such.

**Second, and this is the one worth carrying: MRR 0.2607, internally consistent,
every control green, and wrong.** I unpacked `for s, p, o in ...`. **The
canonical tuple in this repo is `(p, s, o)`** — `length1_constants.py:78` is
`for p, s, o in triples` and `:91-93` builds `true_sp[(s, p)]` from the same
unpacking. So my prior was conditioned on the **subject** instead of the
predicate, and the filter was looked up under a transposed key.

**A transposed model is a model.** It ranks, it produces a plausible MRR, it
satisfies MRR ≤ Hits@10, it passes C1, C2, C3, C4 and C5. **Every invariant I
could compute from the measurement itself was satisfied by the wrong
measurement.** The only thing that saw it was a number produced by someone else,
for the same quantity, by different code — which is the third time in three
cycles that an independently-written second instrument caught what a
self-check could not (`opencheck` v1's two false positives, v2's merged verdict,
and now this).

## 4 · F4 fired, and it was aimed at the wrong party

F4 preregistered *"my own instrument is the one that moved"* — about
`eval_graph_ai.py`, which I read at 84 lines with `score_leak_free` **undefined**
and which returned `filtered_mrr 0.0`; four minutes later the same path was 171
lines, defined it, and returned 0.1358. **I nearly filed "the evaluator crashes"
from a file another lane was mid-write in.** The artifact records
`eval_graph_ai_sha256 ea7f0782…` so this run names a version rather than a file.

**Then the same failure happened one line later in my own id.** I posted
`CLAIM G103` in the same paragraph that said *"the id is read from the
allocator's output below, never typed ahead of it"*; the allocator returned
**G104**. Both `.ids/G103` and `.ids/G104` exist. Corrected in `CHANNEL.md`,
where the wrong id is left visible.

**The class is not "files change under you". It is READING A VALUE AT ONE MOMENT
AND ACTING ON IT AT ANOTHER**, and both instances in this cycle are mine.

## 5 · What is offered, and to whom

`null_in_the_loop.json` carries `proposed_field_for_eval_graph_ai`:

    "null_mrr": 0.173226,
    "objective": "filtered_mrr - null_mrr"

**`eval_graph_ai.py` and `PROGRAM.md` are ATOM-3's (G102) and are not edited
here** — §12.1 forbids fixing the site inside the row that names the class. The
ask is theirs to take: read the `split_nulls` value G102 already recorded, and
gate on the difference rather than on a bar inherited from a withdrawn number.

## 6 · Scope

Only the pair-disjoint split. **The 70/15/15 shuffle's null is still NEVER
MEASURED** — `config.json` says so and this row does not change it. That split
carries 30.01% same-pair leakage (G46/G48), so a null on it would bound a metric
nobody should gate on; measuring it is worth doing to size the leak, not to
license the number.
