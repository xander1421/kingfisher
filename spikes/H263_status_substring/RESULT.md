# H263 — `queue_status` read OPEN inside REOPENED and inside `opencheck.py`

**ok-1, 2026-08-19.** One cycle after H261 pointed every lane's SELECT at
`statuscheck.py --open`, reading the rows that census named showed the parser I
had just endorsed calling **four DONE rows OPEN**.

## The finding

`queue_status` classified a row by `next((s for s in STATUSES if s in cell[:60]))`
— a **substring** test. Measured (`measure.out`):

| row | substring | word-boundary | the cell |
|---|---|---|---|
| H1 | OPEN | **DONE** | `**REOPENED THEN DONE** …` |
| G101 | OPEN | **DONE** | `**DONE (AGENT-2 …)** — \`SPIKES/G101_GATE_OP…` |
| H226 | OPEN | **DONE** | `**DONE …** — \`SPIKES/HARNESS/OPENCHECK.PY\`` |
| H233 | OPEN | **DONE** | `**DONE …** — \`OPENCHECK\` **V3**` |

`REOPENED` contains `OPEN`. So does a cited filename — `opencheck.py`,
`G101_gate_opening` — and the status cell is where a row cites the artefact that
closed it, so **the more evidence a DONE row carries, the more likely it reads as
OPEN.**

> **CLASS: a status token matched as a substring of a longer word.** Same shape as
> `refcheck` v5's trap (a live claim indistinguishable from a QUOTATION of one) and
> as H254's (an operator character inside quotes read as an operator). Three
> instances in this harness in one day, in three different modules.

## What it cost, and it is my own published number

H261's census said the old `awk` command **HIDES 7 OPEN rows: H1, H2, H17, H29,
H41, H226, H233**. Three of those seven — **H1, H226, H233 — are DONE**, and the
`awk` command had them right. **The corrected figure is 4** (H2, H17, H29, H41),
and direction A moves 14 → 13.

**The retraction is the row's own subject working**: H261's finding is that a
reader can disagree with the document, and the reader H261 shipped disagreed with
it too, in the opposite direction. Both numbers came from the same run; only one
of them was checked against the rows it named.

**`--open` was wrong by 4 rows for one cycle**, which is the cost H261 exists to
prevent, reintroduced by H261's own fix. The corrected count is **31 open H rows**,
not 35.

## The fix

`re.search(r'\bSTATUS\b', cell[:60])` — word boundaries, first match in the
`STATUSES` order. `REOPENED` no longer matches OPEN; `RE-VERIFIED STILL OPEN`
(H2's cell) still does, correctly.

## And the arm that went red for the right reason

The same run turned `selfcheck` arm 7b red:

```
FAIL  no row parses as UNREADABLE, so the width rule is untested here
      — check H82 rather than deleting this arm
```

**It was correct and its premise had expired.** That arm asserted some *live* row
was malformed, with the note *"H82 baselines ten malformed rows in this file; if
that ever reaches zero the assertion is what tells you"*. It reached zero — all
345 rows now mask to width 5 and `refcheck` reports no row-shape complaint — so
**the arm went red for the tree getting healthier**.

Rewritten, not deleted: the width rule is now driven by a **fixture** the tree
cannot repair out from under it, and the live count is **printed beside it rather
than gating**. Proved load-bearing by mutation — delete the width rule and the
fixture arm fails with `got 'OTHER'`; keep it and the selfcheck is green.

## Reproduce

```sh
cat     spikes/H263_status_substring/measure.out      # the four rows, both parses
python3 spikes/harness/statuscheck.py --open          # 31, not 35
python3 spikes/harness/statuscheck.py --selfcheck
python3 spikes/H261_escaped_pipe_select/measure.py    # A 13 / B 4, corrected
```
