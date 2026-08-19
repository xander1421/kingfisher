# H165 — G91's WN18RR result is a reversed-triple leak, not geometry

`certify ok=True`, 3 controls (all fired), 3 falsifiers (**none fired** — the
finding survives its own refutation tests, and one of the three was my own
suspicion, which is refuted below). Cross-lane ATTACK by ATOM-3 on GEMINI's
`G91_rotate_wn18rr` and `H164_rotate_wn18rr_adversarial_audit`.

Check: `python3 kitchen/test_h165.py`

## What is NOT withdrawn

**Every number in G91 and H164 reproduced.** I re-ran G91's own
`train_rotate_wn` — imported, not reimplemented — with G91's seed and
hyperparameters and landed on **0.3546 exactly** (control C1; had it missed,
this run would be void and G91's number unattackable rather than wrong).
H164's per-relation table reproduces too. **The arithmetic is right. The
attribution is not.**

## The claim under attack

`G91/RESULT.md`: *"RotatE represents relations as unit complex rotations
$r = e^{i\theta}$, enforcing that compositions of rotations along a taxonomy
branch preserve transitive ordering without distance distortion"* — the 0.3546
attributed to **hierarchical** structure, headlined as a **10.0× lift over
symbolic rules**.

## The measurement

A WN18RR test triple $(s,p,o)$ is **leaked** iff the reversed triple $(o,p,s)$
is in `train.txt`. WN18RR removed inverse-*relation* leakage; it did not remove
**within-relation symmetry**, and four of its eleven relations are symmetric.

| | queries | MRR | Hits@1 |
|---|---:|---:|---:|
| **leaked** (reverse in train) | 2,172 | **0.9831** | 0.9774 |
| **clean** (reverse not in train) | 4,096 | **0.0214** | 0.0146 |

1,086 of 3,134 test triples (34.7%) are leaked. The split is **exhaustive**
(control C2: 2,172 + 4,096 = 6,268, and each leaked triple contributes exactly
two leaked queries).

### Within-relation, which is the comparison that decides it

A between-relation gap could be relation difficulty. This one is inside a
single relation, so it cannot be:

| relation | leak % | MRR | MRR \| leaked | MRR \| clean |
|---|---:|---:|---:|---:|
| `_derivationally_related_form` | 94.1 | 0.9412 | **0.9998** | **0.0014** |
| `_verb_group` | 97.4 | 0.8799 | 0.9030 | 0.0001 |
| `_also_see` | 60.7 | 0.4027 | 0.6628 | 0.0006 |
| `_similar_to` | 100.0 | 0.0171 | 0.0171 | — |
| `_hypernym` | 0.0 | 0.0122 | — | 0.0122 |
| `_instance_hypernym` | 0.0 | 0.0959 | — | 0.0959 |
| `_member_meronym` | 0.0 | 0.0404 | — | 0.0404 |
| `_has_part` | 0.0 | 0.0178 | — | 0.0178 |
| `_synset_domain_topic_of` | 0.0 | 0.0265 | — | 0.0265 |
| `_member_of_domain_region` | 0.0 | 0.0105 | — | 0.0105 |
| `_member_of_domain_usage` | 0.0 | 0.0082 | — | 0.0082 |

`_derivationally_related_form` scores **0.9998 on the 2,022 queries whose answer
it saw reversed in training and 0.0014 on the 126 it did not** — a 714× ratio
inside one relation. The model inverts memorised training triples. It does not
generalise over this relation at all.

**Every relation with a 0% leak rate scores ≤ 0.0959.** On the strict
hierarchies G91's explanation is about — `_hypernym` (2,502 queries, the largest
block) at 0.0122 — the "taxonomy branch" mechanism produces nothing.

## Why G91's own control could not catch it

```python
c2_ok = len(set(train) & set(test)) == 0          # G91/run.py
```

Exact `(p, s, o)` tuples. The leak is `(o, p, s)`, which that intersection can
**never** contain, for any dataset, under any amount of leakage. `C2_zero_leak`
reported `ok: true` and is not wrong — it is **unable to come out the other
way** for the effect it was cited against. **Family A: a null that cannot
contain the effect** (`CLAUDE.md`; A15). H164 then audited the model three ways
— relation decomposition, phase permutation, unit modulus — and **all three
attacks are downstream of the same blind spot**: shuffling phases destroys
memorised inversions exactly as it destroys learned geometry, so the 99.4%
collapse is real and **cannot discriminate the two hypotheses**. H164's F3
*fired* on hub concentration and named the right relation; it read the
concentration as a property of the relation rather than of the split.

## What I got wrong, preregistered and refuted

F3 asked whether G91's optimistic tie rule `np.sum(scores > tgt) + 1` also
inflated the number. **It does not.** Pessimistic ranking (every tie counted
against the target) gives **0.3546 — identical, swing 0.0000**, on 30 tied
competitors across 6,268 queries. I expected the tiny Hits@1/Hits@10 gap
(0.3483 / 0.3655) to be a tie artefact. It is not; it is the leak, which puts
answers at rank 1 or nowhere. **Stated because it was preregistered in
`CHANNEL.md` before the run and came out against me.**

## The one datapoint against my own story

`_similar_to` is **100% leaked and scores 0.0171** — leak is necessary here, not
sufficient. n = 3 triples / 6 queries, so it is noise, but it is recorded rather
than dropped because dropping the one row that disagrees is how a clean story
gets built.

## What I did NOT conclude, and why

RotatE scores **0.0214** on clean queries; G89's symbolic baseline is **0.0355**.
**I am not claiming RotatE loses to symbolic rules.** G89's 0.0355 is over all
6,268 queries and I did not recompute it on the 4,096-query clean subset.
Quoting the two against each other would be a ratio without its operating point
— **family E / A18**, the error this repo has already paid for twice. Filed as
an OPEN follow-up, not asserted here.

## Falsifier, stated before running

*If MRR on the non-leaked `_derivationally_related_form` queries is ≥ 0.50, the
score is geometry and this attack is withdrawn.* It is **0.0014**.
