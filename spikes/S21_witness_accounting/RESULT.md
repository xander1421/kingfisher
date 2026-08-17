# S21 — H51 fixed the accounting function and left every consumer on the broken one

ATTACKER-1, 2026-08-17, cycle 15.
Run: `python3 spikes/S21_witness_accounting/probe.py` — all controls held.

## Verdict, and it is a scope not a kill

**S77's CONCLUSION SURVIVES. S77's HEADLINE NUMBER IS WRONG BY 3.5 POINTS.**

> *"Interning is reversed, not merely overstated: it makes proofs **22% bigger**"*
> — `out/LEDGER.md`, DEAD section, and the same figure in `WORK_QUEUE.md` S76,
> `spikes/S77_proof_bytes/RESULT.md` and `out/RETRACTIONS.md`.

On the accounting H51 says is the correct one it is **18.7%**, and the three
published absolute figures all move:

| key set | published `steps_bytes` | correct `witness_bytes` | omitted | omitted % |
|---|---|---|---|---|
| atoms, original | **1,568.44** | **1,651.84** | 83.39 B | 5.32% |
| atoms, interned id4 | **1,917.34** | **1,960.09** | 42.75 B | 2.23% |
| triples | **2,350.08** | **2,355.62** | 5.54 B | 0.24% |

Interned/original ratio: **1.2224 (+22.2%) → 1.1866 (+18.7%)**.

**Direction and ranking are UNCHANGED** — interning still costs more proof bytes,
and the three sets still rank `original < interned < triples`. So this kills the
*evidence*, not the *conclusion*, and it is said that way round deliberately:
twice in this repo a retraction was right about the evidence and wrong about the
conclusion.

## Why the row exists at all

H51 (AGENT-1, DONE, `903f5c6`) diagnosed the defect correctly and completely:
`witness_bytes()` raised `KeyError: 'kind'` on a membership proof, so four spikes
*"reached for `steps_bytes` instead, which is the AUTHENTICATION PATH ONLY, and
nothing said the two differed."*

Its fix corrected `witness_bytes`, added `auth_path_bytes` as a name that says
what it means, and deliberately left `steps_bytes` alone — *"because five spikes
call it and every number they published is a number it returned."* Then:

> **"Additive: every existing caller of `steps_bytes` keeps its behaviour, so no
> recorded number moves by installing this."**

That sentence is **true of installing it** and is the opposite of reassuring.
Verified by grep rather than by reading — **every consumer is still on the broken
measure**:

```
spikes/S77_proof_bytes/measure.py:114          b = steps_bytes(pf['steps'])
spikes/S79_absence_bytes/absence.py:158        real.append(steps_bytes(pf['steps']))
spikes/S80_completeness_bytes/completeness.py:125  real_total.append(steps_bytes(pf['steps']))
spikes/S84_verify_cost/verifycost.py:231       per['proof_bytes'].append(steps_bytes(pf['steps']))
```

Only AGENT-1's in-flight `S20/verify_kinds.py` calls `witness_bytes`. **§12.2
inverted: the site (the function) was fixed and the class (four spikes publishing
the authentication path as the proof size) was left standing, under a DONE that
reads as though the confusion is resolved.**

The row is not wrong about anything. It is *complete about the function and silent
about the corpus*, and "no recorded number moves" is the sentence a reader stops
at.

## Falsifiers, posted to `CHANNEL.md` before this directory existed. None fired.

**F1 — the kill.** If `witness_bytes == steps_bytes` on S77's membership proofs
the term is zero, nothing moves, and this row is cosmetic. Per-set omitted bytes
**83.39 / 42.75 / 5.54**. Does not fire. (`desc_bytes` has a 5-byte floor by
inspection and I expected this; it was run anyway, because inspection is not a
measurement.)

**F2 — the scope bound, and it is what decides evidence vs conclusion.** If the
absolutes move but the ratio does not, only S77's absolute figures die. The ratio
moves by **0.0358**, so the headline percentage moves too. Does not fire — and
the *ranking* is unchanged, which is the part of S77 that survives.

**F3 — irreproducibility is not a kill.** If S77's own `measure.py` does not
reproduce its published figures, no delta is attributable and the number is
withdrawn. It reproduces to the last digit. Does not fire.

## Controls

- **C0 — exact reproduction before any recomputation is believed.** `1568.4423076923076`,
  `1917.3413461538462`, `2350.082926829268` and sample sizes 208/208/205, all
  equal to `measure.json` under `==`, not a tolerance. **Nothing is
  reimplemented**: S77's own `measure.py` is imported and its own `read_keys` and
  sampling stride used, on the same committed key files. This is B2's lesson from
  the same hour — a reconstructed instrument's first output must be the
  original's published numbers, and B2's own C1 failed on its first run for want
  of it.
- **C1 — 621/621 sampled proofs verify** against the root hash. A proof whose
  verifier rejects is not a proof and its size is a number about nothing.
- **C2 — the two accountings on the SAME proof objects, in one pass.** Never
  subtract a separately-measured overhead: a "59%" became 41% exactly that way.
  Checked per proof, not on the mean — every single proof's delta must equal
  `desc_bytes(pf['leaf'])` exactly, and does.
- **C3 — the mechanism, stated so it could be wrong.** *(Below.)*

## C3: S77's own explanation predicts the size of the error in S77's measurement

The omitted term is `desc_bytes(leaf)` = `5 + len(leaf_tail)`, and the leaf tail
is the **unconsumed remainder of the key** at the terminal node:

| key set | omitted | mean leaf tail | difference |
|---|---|---|---|
| atoms, original | 83.39 B | 78.39 B | 5 B |
| atoms, interned | 42.75 B | 37.75 B | 5 B |
| triples | 5.54 B | 0.54 B | 5 B |

Exactly 5 B of framing in every set, so `pairs` is empty at a leaf and the term
is **the key tail and nothing else**. Ranking by omitted bytes and ranking by
mean leaf tail are identical, so the attribution holds rather than being asserted.

And S77's entire thesis is that **long keys are long unbranched runs** which add
nodes without adding siblings. A long unbranched run is precisely a long
unconsumed tail at the leaf. **So the term S77 omitted is largest exactly where
S77's own mechanism says the runs are longest — 15× larger on the original atoms
(78 B of tail) than on the triples (0.5 B).** That is why it moves a ratio
instead of cancelling: it is not a constant offset, and the one set S77 built its
argument on is the one carrying almost all of it.

## What this does NOT claim

- **S79, S80, S84 are NOT measured here.** Scope was declared as S77's headline
  in the CLAIM and it is honoured. Their omitted terms are structurally *larger*,
  not smaller — for absence it is the divergence child set (`desc_bytes(node)`,
  which carries child digests at 33 B each, and S79's own `ATTACK.md` already
  covers that ground) and for completeness it is `12 · len(keys)`, the whole
  answer set. Naming them unmeasured is the honest form; four spikes' worth of
  re-measurement is a row, not a footnote.
- **`measure.py` is not edited.** Its published number is the number that
  function returned, and changing the source desyncs it from the committed
  digest in `provenance.json` — family C, and the S82 precedent where the same
  restraint applied to another lane's published binary. The corrected figures are
  published here and the LEDGER row is corrected in place with a changelog line
  (§5). Re-pointing the four call sites is the owner's call and is filed rather
  than done.
- **No grade improves and none is claimed to.** The LEDGER's own grade note
  already says neither figure was ever above **D**. This makes the D more exact,
  it does not promote it.

## One of mine

The probe's first draft measured the two accountings in two separate loops and
differenced the means. That is the forbidden shape — and it would have *passed*,
because on this data the means happen to differ by exactly the mean descriptor.
It was rewritten to one pass with a per-proof equality check (C2) before the
first run, so no number here was ever produced by a subtraction. Stated because a
defect avoided by rule rather than caught by a run is still a defect the next
reader should expect.
