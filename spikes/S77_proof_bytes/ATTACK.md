# ATTACK on S77's own instrument — S77 survives, and the attack found something better

**Verdict: S77 SURVIVES all three attacks. An independent recount from the key
sets alone, with no `pathmap`, no zipper and no Rust, reproduces its sibling
counts at 0.00% relative difference on all three sets. 3 controls, all fire,
`certify ok=true`. One of the attacks was built on a premise that the run proved
wrong, and that is recorded rather than edited out. The exactness of A1 is worth
more than the survival: if the number is computable from the key set alone, then
`pathmap` was never needed to measure it — and S75 and S76 spent two cycles
measuring a substrate to answer a question that was not about the substrate.**

Run: `python3 attack.py`. Artefacts: `attack.json`, `provenance.json`.

## Why S77 was the target

S77 retracted **two published spikes** on the strength of **one self-authored
measurement**: a Rust walk calling `child_count()` at each byte position. Its
validation was a two-key self-check and a 5–7% agreement with W2's prover — and
that second one is weaker than it looks, because if `child_count` systematically
under-reported branching, W2's own trie would still rank the sets the same way
and the agreement would survive intact. **A22: the party supplying the
measurement supplied the check on it.** §2 says ATTACK targets instruments before
conclusions and self-authored data first; this is the newest, most load-bearing,
most self-authored instrument in the lane.

## A1 — independent recount. **0.00% difference.**

The logical byte trie is fully determined by the key set: at a prefix `p`, the
children are the distinct bytes following `p` among keys starting with `p`. So
the siblings are recomputable in ~10 lines of Python that touch neither
`pathmap`, nor its zipper, nor any trie code in this project.

| key set | S77's `pathmap` walk | independent recount | difference |
|---|---|---|---|
| atoms, original | 45.658 | 45.658 | **0.00%** |
| atoms, interned | 56.356 | 56.356 | **0.00%** |
| triples | 70.194 | 70.194 | **0.00%** |

Two things follow. First, `child_count()` at a byte position returns the logical
child count, which is what a Merkle proof commits to — the zipper was read
correctly. Second, and larger:

> **The quantity that decides proof size is a property of the KEY SET, not of the
> data structure.** Node depth is substrate-specific — `pathmap` spends a node
> per byte, W2's trie spends one per unbranched run — and that is precisely why
> depth was never a proof size. S75 built a Rust probe against a real library to
> measure the wrong thing; S76 built a four-encoding sweep on top of it; the
> right number was available from the key files with a `defaultdict`.

## A2 — prefix keys. **Zero, and that is a recorded gap, not a pass.**

C4 of this project found a real soundness bug of exactly this shape: a key ending
*inside* another key's compressed span was reported present by both prover and
verifier. If a key were a proper prefix of another, its terminal position would
be both an end and a branch, and this walk might count it as neither.

Measured across all 6,588 keys in the three sets: **0 prefix-related pairs.** The
encodings are prefix-free in fact, not only by claim. **But that means the walk
was never exercised on the case** — recorded as an untested branch, which is what
A29 demands: a probe that cannot show it reached its target has produced no
evidence about the target.

## A3 — the root charge. The attack whose own premise was wrong.

S77 counts `child_count` *before* descending each byte, which includes the root.
A verifier already holds the root digest, so charging a proof for the root's
siblings may be an accounting error — and it would inflate the sets with the
widest roots most. If removing it made the sibling ordering agree with the depth
ordering, **S77's inversion would be an artefact and the retraction unfounded.**

It does not, and the premise was backwards:

| key set | root children | charge per key | siblings excl. root |
|---|---|---|---|
| atoms, original | 2 | 1 | 44.658 |
| atoms, interned | 2 | 1 | 55.356 |
| triples | **1** | **0** | 70.194 |

**The triples root has ONE child** — every triple key shares a leading byte — so
the set I expected to be overcharged most is charged nothing at all. The ordering
is identical with or without the root, and still the reverse of the depth
ordering. The wrong premise is left standing in the control's own text with a
note, because an attack whose stated mechanism is wrong is exactly what this
project keeps finding in its own controls (A25, A26, A30), and hiding it here
would be the same act.

## What this does not clear

- **A1 validates the walk, not the model.** Both the walk and the recount charge
  `(children − 1)` digests per branching position. If a real proof format carries
  something else — a 256-bit child mask, a full sibling map, per-node framing —
  every absolute byte figure moves together. The *ordering* and the inversion do
  not depend on that constant, and the ordering is what retracts S75 and S76.
- **Membership only**, one corpus, `pathmap` 0.3.0, no timings — carried forward
  from S77 unchanged.
- **This is still the author attacking his own work.** A1 removes the instrument
  from the loop, which is the strongest thing available inside one lane; it does
  not substitute for another lane reading it.
