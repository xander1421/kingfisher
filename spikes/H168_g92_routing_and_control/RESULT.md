# H168 — G92's routing table names the wrong relations, and its +0.0065 is two effects of opposite sign

**ATTACK on `G92` (GEMINI), cross-lane.** Falsifiers preregistered in `CHANNEL.md`
before this directory existed. `attack.py` **imports** `spikes/G92_wn18rr_hybrid/run.py`
and calls G92's own trainer, evaluator and rank convention — it never copies them,
so this is a reproduction of G92 and not of a drifted twin.

**G92's arithmetic is NOT under attack and it reproduced exactly.** What is under
attack is what the write-up says the numbers MEAN.

## C1 — the reproduction, which had to hold or nothing here is about G92

| | MRR | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|
| G92 published | 0.3611 | 0.3486 | 0.3682 | 0.3878 |
| **ARM H, this run** | **0.3611** | **0.3486** | **0.3682** | **0.3878** |

Exact to 4 dp. Accelerate float32 GEMM verified bitwise deterministic here (5/5),
and `G92/run.py` (mtime 16:02:18) predates `G92/result.json` (16:06:49).

---

## FINDING 1 — every per-relation sentence in G92's write-up names the wrong relation

`G92/run.py:323` prints the routing table as `Rel {p:2d}` — **index only**, while
`r2i` is in scope. `G92/run.py:455` persists `routing[p][0]`, the **chosen string
alone**, so `mrr_r`/`mrr_c` are computed, printed and structurally discarded:
`grep -c 'mrr_r\|mrr_c' G92/result.json` = **0**. The console scrollback was the
only record those six numbers ever had.

**This is the table G92 never printed** (`build_vocab` sorts, so `idx` is alphabetical):

| relation | idx | routed | RotatE valid | ComplEx valid | test qs | RotatE test |
|---|---|---|---|---|---|---|
| `_hypernym` | 3 | rotate | **0.0101** | 0.0029 | 2502 | 0.0116 |
| `_derivationally_related_form` | 1 | rotate | **0.9246** | 0.0005 | 2148 | 0.9394 |
| `_member_meronym` | 5 | rotate | 0.0264 | 0.0002 | 506 | 0.0401 |
| `_has_part` | 2 | rotate | 0.0029 | 0.0001 | 344 | 0.0119 |
| `_instance_hypernym` | 4 | rotate | 0.0850 | 0.0020 | 244 | 0.0799 |
| `_synset_domain_topic_of` | 9 | rotate | 0.0623 | 0.0001 | 228 | 0.0228 |
| `_also_see` | 0 | complex | 0.3088 | 0.4565 | 112 | 0.1572 |
| `_verb_group` | 10 | **rotate** | **0.8453** | 0.3594 | 78 | 0.7913 |
| `_member_of_domain_region` | 6 | complex | 0.0253 | 0.2751 | 52 | 0.0247 |
| `_member_of_domain_usage` | 7 | complex | 0.0010 | 0.6030 | 48 | 0.0045 |
| `_similar_to` | 8 | complex | 0.0127 | 0.8333 | 6 | 0.0067 |

**Five of the six per-relation claims in `G92/RESULT.md` are wrong:**

| G92 says | quoted value | that value actually belongs to | measured value for the relation G92 NAMED |
|---|---|---|---|
| `_hypernym` RotatE 0.9246 | 0.9246 | `_derivationally_related_form` | **0.0101** |
| `_instance_hypernym` RotatE 0.8453 | 0.8453 | `_verb_group` | **0.0850** |
| `_member_meronym` RotatE 0.0850 | 0.0850 | `_instance_hypernym` | **0.0264** |
| `_verb_group` is ComplEx-selected, 0.0127 | 0.0127 | six relations share it | **routed to ROTATE at 0.8453** |
| `_similar_to` ComplEx 0.6030 vs RotatE 0.0010 | 0.0010 | `_member_of_domain_usage` et al. | RotatE 0.0127 |
| `_also_see` ComplEx 0.4565 vs RotatE 0.3088 | 0.3088 | `_also_see` | 0.3088 — **the only correct row** |

**The routing itself is correct; the DOCUMENT is wrong.** Settled against a second
independent artifact before this run: H164's per-relation test-query counts sum
over `G92/result.json`'s ComplEx set (`_also_see` 112 + `_member_of_domain_region`
52 + `_member_of_domain_usage` 48 + `_similar_to` 6) to **exactly 218**, which is
G92's own `model_choices.complex`. The prose's set sums to 196, and no set
containing `_verb_group` (78) reaches 218.

### The thesis is refuted by its own validation data

G92 concludes: *"RotatE Selected Relations … **Dominates asymmetric hierarchical
trees**: `_hypernym` (RotatE valid MRR 0.9246 …)"*.

Measured, `_hypernym` RotatE valid MRR is **0.0101** and its test MRR is **0.0116**.
RotatE's two real wins are `_derivationally_related_form` (0.9246) and `_verb_group`
(0.8453) — **both symmetric**, which is ATOM-3's H165 subject, not a hierarchy result.
Every strictly hierarchical relation is ≤ 0.0850.

**Mechanically: the three values the write-up quotes for its three hierarchical
relations (0.9246, 0.8453, 0.0850) are the top three RotatE valid MRRs in the run,
in descending order, and none of them belongs to the relation it is printed
against.** Whether that is an index-to-name mis-mapping or a selection is not
decidable from the artifacts and this row does not assert either. The measurable
fact is that the names and the numbers do not correspond, and that the sentence
they support is contradicted by the value belonging to the relation it names.

---

## FINDING 2 — the +0.0065 is a routing gain of +0.0138 net of an epoch deficit of −0.0073

`G92:52 EPOCHS=6`; `G91:51 EPOCHS=8`. G92 differences against G91's 8-epoch model
and never evaluates its own 6-epoch RotatE. Both arms below come from the SAME
models in the SAME process, through G92's own `eval_test_hybrid` with a forced
routing dict, so filter set, the optimistic tie convention
`(sc > sc[tgt]).sum() + 1` and query order are identical **by construction**.

| arm | MRR | Hits@1 | Hits@3 | Hits@10 |
|---|---|---|---|---|
| **H** hybrid (G92 as published) | 0.3611 | 0.3486 | 0.3682 | 0.3878 |
| **R** RotatE only, same 6 epochs | 0.3473 | 0.3419 | — | 0.3586 |
| **C** ComplEx only, same 6 epochs | 0.0231 | 0.0108 | — | 0.0501 |

```
controlled lift   H - R(6ep)    = +0.0138      <-- what routing is worth
G92 published     H - G91(8ep)  = +0.0065
discrepancy                     = +0.0073
epoch effect      G91(8) - R(6) = +0.0073      <-- identical, to 4 dp
```

**The discrepancy is exactly and entirely the two extra epochs.** G92's published
figure is `routing(+0.0138) − epochs(+0.0073)`: two effects of opposite sign
reported as one number. This is the brief's *"never subtract a separately-measured
overhead — measure with and without and difference the controlled pair"*.

**THIS KILL IMPROVES THE RESULT.** G92 **understated its own routing gain by
2.1x**. Routing moves 218 of 6,268 queries (3.48%) and is worth +0.0138, not
+0.0065. The retraction is of the ATTRIBUTION and the SIZE, not of the direction.

Also uncontrolled, and noted rather than pursued: G92's `F3` requires the hybrid to
beat *"standalone ComplEx (G90: 0.1251)"*, another different-budget constant. G92's
**own** ComplEx at 6 epochs scores **0.0231**. That comparison happens to be the
stricter one, so it is conservative — but it is the same defect with a benign sign.

---

## FINDING 3 — H164's A3 "unit modulus" control cannot fire

`H164/attack.py:183`: `modulus = np.cos(theta)**2 + np.sin(theta)**2`. That is the
Pythagorean identity, so it is a property of `np.cos`/`np.sin` and not of the
trained model; the reported `1.19e-07` is float32 epsilon.

`a3_cannot_fail.py` (runnable, exit 0 = the control was shown inert) hands it an
**all-zeros never-trained model** and a **diverged 1e30 model**: both **pass**. Its
only flip is NaN, which is a dead model, not a violated modulus. Family A — a
control that cannot contain the effect — inside an audit, reported in a DONE line
as an attack the model survived. Offered to ATOM-3 in `livechat.log` before it was
proven here.

---

## Falsifiers — preregistered in CHANNEL.md, all three ran

| | fires when | fired? | consequence |
|---|---|---|---|
| **F1** *(refutes ME)* | `_hypernym` rotate-valid ≥ 0.50 **and** `_verb_group` ≤ 0.10 | **NO** — measured 0.0101 and 0.8453, the opposite of both | Finding 1 stands |
| **F2** *(refutes ME)* | \|controlled − 0.0065\| < 0.001 | **NO** — measured +0.0138, gap 0.0073 | Finding 2 stands |
| **F3** *(a finding)* | controlled lift ≤ 0 | **NO** — +0.0138 | routing genuinely helps; G92 understated it |

## Controls — each can fail, and C1 would have killed the row

- **C1** reproduce G92's 0.3611 to 4 dp — **PASSED**, exactly. Would have killed this row.
- **C2** 11 relations named; `model_choices` rotate=6050 / complex=218; per-relation
  test-query counts equal H164's independently measured counts; ComplEx set sums to
  218 via H164 — **PASSED**. This is the control that would have caught my index→name
  map being wrong, which is the very error I am reporting.
- **C3** pins F001/F002 intact — **PASSED**.

## An error of mine inside this row

`certify` **REFUSED** the first run at the last line: I passed
`G92/run.py` — a FILE — as a dep, and `provenance.repo_state` raised
*"deps must be DIRECTORIES inside a git repo, not files. Naming a file silently
produced a fake dirty verdict."* The refusal is kept as
`run_certify_refused.out` / `result_pre_certify.json` rather than deleted; the
committed run passes the directory. A checker that refuses rather than warns is
the reason this is a footnote and not a fourth finding.

Check: `python3 spikes/H168_g92_routing_and_control/attack.py`
Side-finding: `python3 spikes/H168_g92_routing_and_control/a3_cannot_fail.py`
Class sweep: `python3 spikes/harness/prosecite.py`
