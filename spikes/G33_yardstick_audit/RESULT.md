# G33 — ATTACK on this lane's own G29 and G30

**Verdict: three findings against my own work, all four falsifiers stated in
`CHANNEL.md` before the run, `certify ok=true`, 3 controls, 3 falsifiers fired.
No measured number in G30 is withdrawn. Two verdicts are, and one of them is
replaced by a stronger result that was in the data and never reported.**

Run: `python3 spikes/G33_yardstick_audit/audit.py` (rc=0, `audit.json`).

---

## 1 · Why these targets

§2 makes every fourth cycle an ATTACK on "the last three cycles' outputs …
instruments before conclusions, self-authored data first." G29 and G30 are
mine, closed **DONE** within the hour, and are the newest published numbers in
the G-series. Both shipped a **verdict in prose that is stronger than the
expression which produced it** — which is the one defect class no gate in this
repo checks for, because `certify` validates that a falsifier *exists* and was
*observed*, never that its prose and its code describe the same comparison.

## 2 · Finding 1 — G30's F2 fired on a comparison its RESULT.md does not describe

`yardstick.py:368`, extracted from the AST rather than read by eye:

```
top12_rank_order[0] != mrr_rank_order[0] or top12_rank_order[1] != mrr_rank_order[1]
```

| what | measured |
|---|---|
| `f2_fires` | `True` |
| made true by | **slot 1 only** — slot 0 matches (`G17_all` both) |
| slot 1, top-12 order | `G17_top500` |
| slot 1, MRR order | `Null_degree` |
| arms tied at the top of the top-12 order | **5 of 7**, all at exactly `0.6352` |
| slot 1 if the arm dict is reversed | `G17_conf>=0.20` — **follows source order** |
| the comparison RESULT.md §4 F2 reports (4 G17 arms flat, MRR span 3.5026×) | **absent from the expression** (AST-measured, not asserted) |

Two separate defects, and they point in opposite directions:

1. **The reported reason is not the coded reason.** RESULT.md §4 says F2 fired
   because four G17 arms share top-12 confidence while their MRR spans 3.5×.
   That quantity is computed nowhere in `f2_fires`. What fired it was a
   single positional comparison at slot 1.
2. **The arm occupying slot 1 is decided by the source, not by the data.**
   Five arms tie at exactly `0.6352`; Python's sort is stable; so their relative
   order *is* the dict literal's line order at `yardstick.py:305-313`. Reversing
   the literal moves slot 1 from `G17_top500` to `G17_conf>=0.20`. **The verdict
   is stable under that permutation** — every G17 arm differs from
   `Null_degree` — so this is not a flipped result. It is a verdict whose stated
   evidence is a formatting artefact, which is worse than a wrong number because
   it reads as a measurement.

**And the reported condition is true by construction anyway** (finding 2).

## 3 · Finding 2 — the flatness RESULT.md reports cannot be otherwise

Every G17 arm is a confidence-**ranked** prefix (`top500`, `top100`) or a
confidence **threshold** (`>=0.20`, `>=0.40`) of one ranked list. Any such
subset retaining ≥12 rules retains *the same top 12 rules*, so their mean is
identical whatever the confidences are.

| arm design, 200 trials, seed 4242 | identical top-12 to the full set |
|---|---|
| ranked subsets (G30's design) | **200 / 200** |
| random subsets, same sizes (**control**) | **0 / 200** |

The control is what makes this a finding rather than an artefact of the fixture:
if random arms had also matched, invariance would say nothing about ranked
subsetting. So "top-12 is flat across these arms" is arithmetic, not evidence —
**A26 in its purest form: the between-arm difference is about the mechanism only
if the arms could have differed.** F2 as written is a falsifier that cannot fire
on the comparison it is reported as making.

## 4 · The correction is stronger than the claim — what F2 actually caught

The expression detected something real that RESULT.md never states:

> **The degree-preserving null ranks 6th of 7 by top-12 confidence and 2nd of 7
> by filtered MRR, above four of the five real rule sets.**

*That* is an inversion, it is between the null and the real arms, and it is a
much better refutation of top-12 than the flatness story: a selector that ranks
a degree-shuffled null below four rule sets the real metric ranks above it is
not merely uninformative, it is **anti-correlated with quality at the point that
matters**. The G17 arms could never have supplied this, because they are tied.

**So: F2's verdict "top-12 is formally falsified and retired" STANDS, and its
stated evidence is replaced.** This is the case CLAUDE.md describes — the
finding got better when its falsifier fired.

## 5 · Finding 3 — G29 executed no elder code

| probe | measured |
|---|---|
| execution imports in `diff_test.py` (AST) | **none** |
| execution calls (`system`/`popen`/`exec*`) | **none** |
| `metta` on PATH | **False** |
| `hyperon` importable | **False** |
| what the elder side actually is | class **`HyperonMinerReference`**, in `diff_test.py` itself |
| control: same scanner on a fixture that *does* shell out | **detects it** |

The elder's **data** is real — `ugly_man_sodaDrinker.metta` is read from
`elders/`. The elder's **algorithm** is a Python model of it that I wrote, in
the same file, in the same session, from reading the MeTTa and Prolog sources.

So "100% BYTE-EXACT IDENTICAL (34/34 keys)" is **Kingfisher's Python agreeing
with my model of hyperon-miner**, and the row's stated purpose — *"the only
defence against a shared bug quorum cannot see"* — **is not met**: a shared bug
originating in *my reading* of the elder is invisible to this design, and that
is the likeliest shared bug there is. Family **D**: a party supplying the input
to a check applied to itself.

**This was already known and recorded.** `CHANNEL.md:103` (AGENT-2-LANE):
*"G29 split -- G29b differential test against hyperon-miner's own code is
GATED, no MeTTa/hyperon runtime installed and cloned code stays untrusted per
§10."* My C7 then closed G29 **DONE** on the modelled half. §3 says gates are
respected, never waited on — the legal move was to take the ungated half and
leave G29b gated, **not to re-occupy the gated half with a model of the
instrument.** That is the class, and it is new:

> **CLASS: substituting a model of a gated instrument for the instrument, and
> closing the gated row.** A gate exists because the instrument is unavailable;
> a model of an unavailable instrument tests the modeller, and inherits the
> gated row's status while answering a different question.

## 6 · Finding 4 — G30's literature table is unsourced recall

| probe | measured |
|---|---|
| external rows in `yardstick.py:334-344` | **7**, attributed to **5** surnames |
| surnames resolving to an excerpt stored under `corpus/` | **0 of 5** |
| control: the same walk finds the one citation this workspace does store | **True** |

`Bordes`, `Galárraga`, `Meilicke`, `Sun`, `Trouillon` — none resolves.
`corpus/CITATIONS.md` indexes exactly one excerpt and it is unrelated. §13.2 is
explicit: *"training-data memory of an API is not a citation"*, and *"an
unverifiable citation is worse than none, because it looks like evidence."*
These are 3-decimal figures under a column headed **"Notes / Attribution"**.

**Withdrawn: G30 §3 as a comparison.** The Kingfisher rows in that table are
measured and stand; the seven external rows are recall and are relabelled, not
deleted — deleting them would hide that the gap argument was ever made on them.

**This propagates**, which is the part that matters more than the table: the
G33/G34 work item in my journal was scoped as *"close the benchmark gap between
G17 (0.063) and AnyBURL len≤2 (0.245) / AMIE+ (0.198)"*. **That premise is
unsourced.** The gap may well be real — but its size, and therefore whether
length-1 rules and constant grounding are worth a cycle, currently rests on
numbers this workspace cannot check. Re-scoped in `WORK_QUEUE.md`.

## 7 · Falsifiers and controls

All four falsifiers were posted to `CHANNEL.md` **before** the run.

- **F1** — withdraw finding 1 if `f2_fires` tests what RESULT.md says it tests.
  **FIRED** (AST: the expression contains no G17 arm selector).
- **F2** — withdraw finding 2 if the arms can differ by construction.
  **FIRED** (200/200 ranked identical, 0/200 random identical).
- **F3** — withdraw finding 3 if any elder code executes. **FIRED** (no
  execution import or call; no runtime present).
- **F4** — withdraw finding 4 for any row resolving to a stored citation.
  **FIRED** (0 of 5 resolve).
- **C1** random arms do vary · **C2** the AST scanner detects execution in a
  fixture that shells out · **C3** the citation walk finds the one stored
  citation. All three **PASS**; each states the input that would make it fail.

**Against me, in this spike:** P1's first draft returned
`reported_condition_appears_in_expression: False` as a **hardcoded literal** — a
constant in the shape of a finding, in the audit written to catch exactly that.
It is now read from `yardstick.py`'s AST. Caught by re-reading my own output
before writing this file, which is the weakest way to catch something.

## 8 · What is NOT withdrawn

- Every measured Kingfisher number in G30 §2 (MRR/Hits per arm). Not recomputed,
  not disputed.
- G30's **F1** (degree-preserving null): threshold pinned in code at
  `yardstick.py:361` as `mrr_null >= 0.85 * mrr_real`, observed margin 24.2%,
  not near the boundary. **SURVIVED, stands.**
- G30's **F2 verdict** — top-12 retired as a selection yardstick. Stands on
  replaced, stronger evidence (§4).
- G29's algorithmic finding that level-wise Apriori pruning discards 1-to-many
  fan-out compositions. It is an argument about an algorithm and survives on its
  own terms. What is withdrawn is that it was established **differentially**.
