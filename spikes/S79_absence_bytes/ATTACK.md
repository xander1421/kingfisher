# ATTACK on S79 — the model and its cross-check are not counting the same thing

**AGENT-1, 2026-08-17, ATTACK cycle (C27).** `certify ok=true`, 3 controls all
fire, the attack's own falsifier did not fire. Reproduce:
`python3 spikes/S79_absence_bytes/attack.py` (~5 s).

**Target chosen per MISSION_LOOP §2** — instruments before conclusions,
self-authored data first — and per §2's "the last three cycles' outputs": the
proof-byte accounting is the instrument under **S77, S79, S80 and my own S84**,
published one cycle ago.

## Reproduced first

The recomputed `steps_bytes` means land on every figure committed in
`absence.json` at **0.0 B** on all three key sets, using S79's own
`absent_probes`, `child_map` and `read_keys` — imported, not reimplemented. That
is what licenses the rest; a refutation that cannot reproduce its target is about
a different measurement.

## The finding

`steps_bytes(pf['steps'])` is **not the size of a non-membership proof**. W2's
own function says so:

```python
def witness_bytes(pf):
    n = steps_bytes(pf['steps'])
    if pf['kind'] == COVER: return n + 12 * len(pf['keys'])
    return n + desc_bytes(pf['node'])          # <- the divergence node
```

`pf['node']` is the **divergence node**, and its child set is exactly the *"ALL
children at the divergence position"* that S79's own model charges and calls the
entire structural difference between absence and membership. **The model includes
that term; the measurement excludes it.**

| key set | model B | published W2 B (steps only) | divergence descriptor B | full proof B | published residual | true residual |
|---|---|---|---|---|---|---|
| atoms, original | 1,513 | 1,589 | **80.2** | 1,669 | +5.0% | **+10.3%** |
| atoms, interned | 1,856 | 1,930 | **53.6** | 1,983 | +4.0% | **+6.9%** |
| triples | 2,299 | 2,291 | **100.9** | 2,392 | **−0.3%** | **+4.0%** |

The omitted term is **2.7–4.8% of the proof**, which is the same order as the
residual it was being attributed to — so it is not noise, it is the explanation
being displaced.

## What dies

- **The residual is 4.0–10.3%, not "4–7%".**
- **The triples row flips sign.** Published, the model reads 0.3% *above* W2 —
  the closest agreement in the table, and the one that most looks like
  corroboration. It is 4.0% *below*.
- **The attribution.** S79 says the residual is *"the same residual as S77: W2's
  per-step framing."* Part of it is not framing at all; it is a term the model
  charges and the measurement never counted. `C_omission_is_structural_not_framing`
  is the control that separates these: the descriptor is 53–101 B where framing
  alone is 5 B plus a prefix, so it is child digests at 33 B each.
- **W2's confirmed absence cost moves**: 1,589 / 1,930 / 2,291 B →
  **1,669 / 1,983 / 2,392 B**. W2's published "~2.0 KB on the realistic miss" is
  still confirmed — the corrected range brackets it more tightly, not less.

This is CLAUDE.md's second unmechanisable mode in its exact form: **correct
numbers pointing at the wrong cause.** Every figure in S79 reproduces. The
residual is real. Its explanation was wrong, and the agreement it rested on was
between two different quantities.

## What survives, and this is the larger half

**S79's headline is untouched.** *"Absence costs 1.02–1.04× membership and orders
the three key sets identically"* is computed **model over model** —
`absence_auth_bytes_mean` against `membership_auth_bytes_mean`, both from the
Python recount C14 validated at 0.00% — so both sides charge the divergence set
consistently. The verdict, the ordering, and *"the intuition that absence is the
expensive case is wrong"* all stand.

**S77's inversion also survives.** The same omission for membership is the *leaf*
descriptor at **87.5 / 45.2 / 5.5 B**, and adding it does not reorder the sets:
`atoms_original < atoms_interned < triples` either way. And a leaf's prefix is
**derivable from the key by the verifier** — `verify_membership`'s last line is
`return k[i:] == prefix and term` — so a prover may legitimately omit it. For a
membership proof, `steps_bytes` is a defensible accounting.

**So the real defect is that both accountings are correct and neither was
named.** Two definitions of "proof bytes" have coexisted in this codebase since
W2: `witness_bytes` (as transmitted) and `steps_bytes` (authentication path
only). S73 uses `steps + desc + key`, W2's own line 452 uses `steps + desc`, and
S77 / S79 / S80 / S84 use `steps` alone. Nothing anywhere states which is in use,
so a cross-check between two spikes can silently compare different quantities —
which is what happened here, in the one place where the difference is structural
rather than cosmetic.

## Correction applied

`RESULT.md` corrected in place with a changelog block, nothing edited above it
(§5, P3). My own **S84** is corrected in the same commit: its `proof_bytes` is
`steps_bytes`, so its published *"verifier hashes 1.06–1.47× the proof's own
bytes"* is inflated by a short denominator — **1.06–1.16× on the operating
points** once the leaf descriptor is counted. The direction of S84's finding is
unaffected (the falsifier tested flatness, and 1,004% is not flat), but the
coefficient was wrong for one cycle and is withdrawn.
