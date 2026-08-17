# G4 — the negatives existed, I used them, and there is still no signal

**Verdict: RED, and it falsifies G3's diagnosis as well as G2's.** Three
framings, three negative results. That is the finding, and the discipline is to
stop reframing rather than to keep going until something passes.

```
claims 124   dead 26   live 98
CONTROL 1  majority baseline    0.790
CONTROL 2  leave-one-out        0.774   DOES NOT BEAT baseline
CONTROL 3  shuffle n=30         mean 0.764  max 0.823  >= real 13/30   p = 0.452
```

## First, correcting G3

G3 concluded *"failure is recorded as prose; a learner sees 114 positives and 0
negatives."* **Wrong.** Dead claims are rows. They sit inside LIVE sections,
marked by `~~strikethrough~~`, and their grade cell is repurposed to hold a
death-reason — `superseded` (8), `INVALID` (8), `retracted`, `WITHDRAWN`,
`FALSE`, `weakened`, `corrected`, `descoped` — instead of a grade.

**26 of them.** G3's parser required the middle cell to match
`**A|B|C|D|E|INVALID**` and skipped every one.

That is the same defect the workspace has now caught seven times: **I fitted a
parser to the LIVE schema and asserted a conclusion about the whole file.** G3's
*structural* observation still stands — a dead claim loses its grade, so
"does grade predict survival" remains unanswerable. Its *headline* was wrong.

## The three attempts, and what each blamed

| spike | framing | result | blamed |
|---|---|---|---|
| G2 | spike-level, 50 labelled | p = 0.129 | weak regex features |
| G3 | claim-level, richer supervision | not run | missing negatives |
| G4 | claim-level, **26 real negatives** | **p = 0.452** | — |

Each diagnosis pointed at the next experiment, and the next experiment refuted
it. G4 is worse than G2, not better, despite better data.

## Circularity, excluded in code rather than in a comment

Two features would have been tautological and both are asserted out:

```python
assert not any("grade" in n or "struck" in n for n, _ in lits), \
    "grade/strikethrough are assigned BECAUSE a claim died — not features"
```

The rule the search settles on in 120 of 124 folds —
`dead :- claim.superlative AND n_evidence>=3` — is at least *interesting*
(sweeping claims with several citations die), but it fails the permutation test
outright.

## The explanation I believe, which this dataset cannot test

**A claim dies when an adversary attacks it and it fails. Whether it gets
attacked is a scheduling property of the agents, not a property of the claim.**
If that is right, the label is substantially independent of claim content, and
no amount of feature engineering over the claim will predict it.

Death rate by section is consistent with that and does not establish it:

```
determinism    5/36  14%      platform    4/20  20%
architecture  12/46  26%      NEVER       5/47  11%
```

Testing it properly needs a variable this workspace does not record: **how many
review passes each claim actually received.** A claim never attacked and a claim
attacked and survived are both "live" here, and they are not the same thing.
Recording attack count per claim would separate them — and that is a cheaper
change than any of the three experiments above.

## What the G-series established

- **G1 GREEN.** A self-modifying graph runs on Hyperon, on two devices, with
  identical output *and* identical fuel count. Composition works and the
  learning step is replayable. That claim is unaffected by G2–G4.
- **G2/G3/G4 RED.** Encoding a rule works. *Discovering* one does not, at
  n=124, with these features, at any of three framings.

The substrate is real. The learning is not, and three honest attempts is
enough to say so rather than to keep hunting for a framing that passes.

## Reproduce

```sh
cd spikes/G4_claim_learning && python3 learn_claims.py    # ~106 s
```

Counts and accuracies only. Host gate REFUSED throughout and it does not matter.
