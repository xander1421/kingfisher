# G3 — the workspace records success as data and failure as prose

**Verdict: RED for the experiment, and the RED is a finding about the instrument
rather than about the graph.** G2 concluded its features were too weak and
pointed at the LEDGER's 108 graded claim rows as better supervision. They are
better — and they are **all positives.**

```
section                                    rows  prose
LIVE — determinism                           36      0
LIVE — architecture requirements             46      0
LIVE — platform                              20      0
LIVE — magnitude survives                     3      0
LIVE — shaping, oracle labelled               7      0
LIVE — residency                              2      0
DEAD — added this round                       0      2
DEAD                                          0      2
NEVER MEASURED                               47      0

LIVE claims as structured rows: 114
DEAD claims as structured rows:   0
```

**Every surviving claim is a table row with a grade. Every dead claim is a
paragraph.** A learner reading `out/LEDGER.md` sees 114 positives and zero
negatives.

## Three consequences, in ascending order of importance

**1. G2's diagnosis was right but shallow.** G2 blamed weak regex features. The
deeper cause is that the failure data is not recorded in a learnable form
*anywhere*. Better features would not have helped; there were no negatives to
fit them against.

**2. The grading scheme cannot be validated against its own record.** The
obvious question — *does grade A actually predict survival?* — is unanswerable
from the LEDGER, because **claims lose their grade when they die.** They move
from a graded row into prose. LEDGER v2 already deleted *"nothing at grade A has
fallen"* as circular; this shows the file's schema makes the non-circular version
unaskable too.

**3. The one structured failure record uses a different schema.**
`out/RETRACTIONS.md` has **29 parseable rows** of `| claim | spike | why |` —
real, adversary-assigned, with stated causes. But no grade, no section, and no
key linking a retraction row back to the LEDGER row it killed. Two records of
the same events that cannot be joined.

## The circularity trap, checked rather than assumed

`INVALID` is assigned *because* a claim died, so using it to predict death is
tautological — the shape of S70's `4R`. Asserted in code:

```
circularity check: INVALID rows 9, of which in DEAD 0
  -> INVALID EXCLUDED from predictors
```

Note what the check itself revealed: all 9 INVALID rows sit in **LIVE**
sections. So `INVALID` is not even the DEAD marker — it is a live row carrying a
do-not-cite flag. Two different notions of "dead" coexist in one file.

## The fix, and it is small

**Record dead claims as rows, in the same schema, carrying the grade they held
when they died.**

```
| claim | grade-at-death | killed-by | why |
```

That single change:
- gives any learner negatives (currently zero),
- makes *"does grade predict survival"* falsifiable for the first time,
- lets RETRACTIONS join to the LEDGER on a key rather than on prose similarity.

It costs one column and it is the difference between a changelog and a dataset.

## What was built

```
ingest_claims.py   parses LEDGER rows + RETRACTIONS rows, emits atoms
claims.metta       108 claims -> 455 MeTTa atoms
claims.json        rows, retractions, conditions block
```

The graph is real and loads; there is simply nothing to learn from it yet.

## What this does NOT say

- Not that the LEDGER is badly kept. It is unusually well kept **as a document
  for humans.** The asymmetry is invisible when you read it and fatal when you
  parse it, which is exactly why it survived 113 commits.
- Not that 29 retraction rows are useless — they are the best failure record in
  the workspace. They are just too few, and unjoinable to the graded set.
- No learner was run. Running one on 114 positives and 0 negatives would have
  produced a number, and that number would have been meaningless. Declining to
  produce it is the result.
