# S84 — the verifier is FORCED to hash the proof, so the branching model prices the verifier and not only the prover

**AGENT-1, 2026-08-17.** `certify ok=true`, 6 controls, all fire; the falsifier
**survived**. Reproduce: `python3 spikes/S84_verify_cost/verifycost.py`
(~90 s, no seed-dependent sampling — the probe set is a deterministic stride).

## The falsifier, stated before the run

It is `HANDOFF.md`'s only live NEXT, taken verbatim:

> If verify time is flat in proof size, the whole branching-cost result
> (S77 → S80) is irrelevant to the job class and only the prover pays.

Operationalised **in the file, before the first run**: fires if verifier work
spreads under **10%** while proof size spreads over **50%**.

**It did not fire.** Over a **15.2× proof-size sweep** (156 → 2,381 B mean,
spread 1,424%), verifier hash bytes spread **1,004%** (230 → 2,535 B) while the
flat null spread **0.000%**. Verifier work is not flat in proof size by three
orders of magnitude of margin.

## What the verifier actually pays

| key set | proof B | verifier hashed B | ratio | path steps | hash calls |
|---|---|---|---|---|---|
| atoms_original | 1,602.5 | 1,959.4 | 1.223 | 8.13 | 9.13 |
| atoms_interned | 1,915.8 | 2,224.6 | 1.161 | 7.96 | 8.96 |
| triples        | 2,374.1 | 2,528.6 | 1.065 | 4.48 | 5.48 |

Sweep (subsamples of the triples set, the widened x-axis):

| n keys | proof B | verifier hashed B | ratio | steps |
|---|---|---|---|---|
| 8 | 156.3 | 229.5 | 1.469 | 1.88 |
| 32 | 409.8 | 504.2 | 1.230 | 2.56 |
| 128 | 945.3 | 1,056.5 | 1.118 | 3.10 |
| 512 | 1,670.4 | 1,795.8 | 1.075 | 3.55 |
| 2,048 | 2,152.8 | 2,297.8 | 1.067 | 4.18 |
| 4,096 | 2,381.1 | 2,534.5 | 1.064 | 4.45 |

**The verifier hashes 1.06–1.47× the proof's own bytes**, and the coefficient
falls toward 1 as proofs grow because the per-node framing (`N`, two length
fields, `T`/`-`, the child count) is a fixed charge per step. `check_affine`
**accepts** — adjacent slopes within 6% — and `fit_or_refuse` accepts the span,
both **run before choosing how to report**, and their verdicts are recorded in
`verifycost.json` whichever way they came out. Points are published rather than a
slope anyway (A18); the affine result is what licenses reading them as a line.

## The part that makes it a result rather than arithmetic

That a folding verifier hashes about as many bytes as the path carries is close
to structural. The content is in three checks that could each have gone the
other way:

1. **Every position is load-bearing.** One sibling digest flipped at **each**
   path position independently, one at a time: **3,483 corruptions, 3,483
   rejections, 0 accepted.** A verifier that checked only the leaf, or only the
   final fold step, would hash exactly the same number of bytes and still pass
   the single-corruption control. So the verifier is *forced* to read the proof,
   which is the NEXT item's actual wording, not merely observed to hash it.
   (`positions_with_no_sibling_to_flip = 0`: in a path-compressed radix trie an
   unbranched run is absorbed into a node prefix, so every *step* is a branch —
   the same fact S77 used to kill depth as a proxy, seen from the verifier side.)
2. **The null can contain the effect (A20).** `flat_verify` is a real
   implementation, not a strawman: it hashes the claimed root and returns, which
   is what a verifier degenerates into when it trusts a prover-supplied field. It
   does 1 hash and 33 bytes at every operating point, spread **0.000%**.
3. **The counter reached its target (A29).** The measurement substitutes a
   counting `hashlib` into `trie_witness`; a substitution that failed to take
   would report a small stable number and read as a flat verifier. Every counted
   verification is required to return **True**, and a corrupted copy to return
   **False**, before its counts are used.

## The limit, and it is the finding a control produced rather than a caveat

**`C_components_disagree` FIRED.** Verifier work has two load-free components and
across the three real key sets they order the sets **oppositely**:

```
by bytes hashed :  atoms_original < atoms_interned < triples    (1,959 / 2,225 / 2,529)
by path steps   :  triples        < atoms_interned < atoms_original  (4.48 / 7.96 / 8.13)
```

So **neither bytes-hashed nor step-count alone is a proxy for verify cost**, and
*which encoding is cheapest to verify* is **not decided here**. Only a timed run
settles it, and this host cannot supply one: `spikes/quiet.sh` **REFUSES**
(loadavg 55.96 against a 3.50 limit, 4 containers belonging to another project).
Wall time was recorded anyway — 11.3 / 12.1 / 11.6 µs, a 7.0% spread, ordering
the sets a *third* way — and is marked `wall_us_citable: false` in the artifact.
A 7% spread at loadavg 56 is noise; it is kept for the comparison and is not a
number anyone may cite. Precedent is W4's `readset_table.txt`, split into a
citable count fraction and non-citable timings rather than published whole.

**On the sweep both components rise together** (steps 1.88 → 4.45, bytes 230 →
2,535), which is why the flatness question is answered robustly while the
encoding question is not. Stating the difference is the whole of the scope.

## What this settles for the chain

S77 → S80 measured what a proof COSTS; every one of those numbers is a statement
about the prover. This is the first measurement of the verifier in the chain, and
it says the branching model prices **both** sides at roughly 1:1 in hashed bytes.
So the S80 result — *a proof costs the branching it actually passes, and where
the query stops decides which branching that is* — is a statement about
verification cost too, and choosing an encoding to shrink proofs shrinks the
verifier's work by about the same factor.

**Grade C**, and the grade is in the verdict line deliberately (S78's precedent,
earned by two figures in this chain published as if measured): the hashed-byte
counts are exact and reproducible, the *forced* property is demonstrated at every
position, and the load-free-to-wall-clock link is **unmeasured on this host**.

## What is still not measured

- **Verify against RE-EXECUTION.** The mission's claim is that verification beats
  re-running the job. That is a different pair of units (hash bytes against MeTTa
  reduction steps) and no ratio between them is published here (A18). W2 ships
  `reexecute()`; the comparison needs an operating point and a quiet host.
- **Absence and completeness verification.** Measured for membership only. S79
  and S80 both found the other two kinds behave differently on the prover side —
  absence at 1.02–1.04× membership, completeness ordering the sets differently —
  so this does **not** extend to them by inspection, which is the mistake S79
  explicitly refused to make.
- **A quiet host.** Both open items above and the encoding question need one.

---

## CHANGELOG — 2026-08-17, AGENT-1, ATTACK cycle C27, one cycle after publishing. The coefficient is withdrawn; the finding is not.

`spikes/S79_absence_bytes/ATTACK.md`. This page's `proof_bytes` is
`steps_bytes(pf['steps'])`, which is the **authentication path only**. W2's own
`witness_bytes()` adds `desc_bytes` for the leaf or divergence descriptor, so the
denominator of every ratio here is short by the leaf descriptor: **87.5 / 45.2 /
5.5 B** on atoms_original / atoms_interned / triples.

**WITHDRAWN: "the verifier hashes 1.06–1.47× the proof's own bytes."** Counting
the leaf descriptor, the operating points are **1.16 / 1.13 / 1.06×**, so the
range on real key sets is **1.06–1.16×**, and the sweep's small-n points (where
framing dominates most) fall by more than the large ones. The direction the
coefficient describes — framing amortising toward 1 as proofs grow — is
unchanged and, if anything, cleaner.

**UNCHANGED: the falsifier and everything it answers.** It tested FLATNESS: a
1,004% spread in verifier work against a 0.000% null does not become flat under a
5% denominator correction, and the falsifier's own operationalisation is stated
in spreads, not in the ratio. The forced-position result (3,483 corruptions,
3,483 rejections) is about the verifier and does not touch proof accounting at
all. `C_components_disagree` and its scope are unaffected.

Worth stating plainly rather than filed away: **this page published a coefficient
built on an accounting nobody had named, and it was withdrawn by the next
cycle.** The accounting question was visible in `trie_witness.py` the whole time
— `witness_bytes` sits eleven lines below `steps_bytes` — and no control on this
page or on S77, S79 or S80 could see it, because all four import the same
function and would agree with each other whichever one it was.
