# S74 — binding the epoch SEQUENCE, at 32 bytes an epoch

**Verdict: GREEN, and the gap was free to close. S73 showed the trie root is
grouping-blind — the same atoms in two different epoch sequences reach the same
root. A `(root, delta)` chain fixes that for **32 bytes per epoch**, 2,176 B for
the whole 67-epoch corpus history. Eight controls, all fire, including one whose
job is to state what this does NOT do.**

Artefacts: `chain.py` (stdlib only, seed 20260817; trie primitives imported from
W2, corpus reader and fold-forward proofs from S73), `chain.json`,
`provenance.json` (`ok: true`, certified through `kfcheck.certify` with a declared
falsifier). Run: `python3 chain.py`.

## What S73 left open, in its own words

> "the root does not bind the path taken to it. Binding history needs the chain of
> `(root, delta)` pairs hashed together. **NOT BUILT HERE.**"

## The commitment

```
chain_0 = H('EPOCH0' ‖ root_0)
chain_N = H('EPOCHN' ‖ chain_{N-1} ‖ root_N ‖ H(delta_N))
```

`H(delta_N)` is the **W2 trie root over the sorted added keys** — the same
canonical structure, not a second encoding for the same job, because two
commitments over the same bytes is how two honest parties end up disagreeing. An
empty delta gets an explicit distinct value rather than colliding with "no epoch
happened".

Position is bound because `chain_{N-1}` is inside the digest: an epoch lifted out
of one sequence and dropped into another sees a different predecessor and cannot
produce the same head.

## Measured — the real 67-program corpus

```
67 programs, 1,246 distinct atoms, 67 epochs, 1,247 final atoms
trie root  daf1d148be40a6a5784e70c13daf30b0…   state
chain head 08e4e1450ecb0071d4c7c2b5acfccce4…   state + sequence
cost       32 B per epoch, 2,176 B for the whole chain
```

The trie root is byte-identical to S73's, which is the point: **the same state,
now with a second digest that distinguishes how it was reached.**

## What the chain catches that the root cannot

Each row keeps the final trie root **unchanged** where marked, so the root
provably cannot see the attack and the chain provably can.

| attack | root sees it | chain sees it |
|---|---|---|
| **regroup** the same atoms into different epoch batches (400/500/347 vs 150/950/147) | **no** — identical root | yes |
| **reorder** two adjacent epochs | **no** — identical root | yes |
| **split** one epoch into two, same atoms, same order | **no** — identical root | yes |
| **drop** an epoch entirely | yes (atoms gone) | yes, and attributably — 66 epochs, not 67 |
| **substitute** one atom inside a delta, identical size, identical roots | — | yes |
| **transplant** epoch 5's `(root, delta)` onto position 6 | — | rejected |

The split case is worth naming: a prover with no new work can cut one epoch in
half and claim two. The root is indifferent; the chain is not.

## The boundary, as a control rather than a caveat

`C_chain_alone_cannot_catch_a_forged_delta` builds a sequence whose epoch 3
declares a root its own declared delta does not produce. **The chain verifies it
perfectly** — it commits to what it was told. S73's fold-forward proof on the same
epoch reproduces the honest root `e0fe5ae8…`, which differs from the declared
`0b1b2c53…`, and therefore rejects it.

| | binds |
|---|---|
| S73 fold-forward delta proof | **state** — this delta really produces this root |
| S74 chain | **sequence** — these roots really came in this order, from these deltas |

Neither substitutes for the other. **A design that treated the chain head as
sufficient would accept a forged epoch**, which is why this is a control and not a
sentence in the caveats.

## Controls — eight, each naming the input that makes it fail

| control | fails if |
|---|---|
| `C_honest_chain_verifies` *(negative — bounds resolution)* | the honest chain does not reproduce its own heads; then every rejection below is vacuous |
| **`C_regrouping_detected`** | two groupings share a head — the chain would add nothing to the root. Also void if the two roots differ, which would mean the groupings were not state-equivalent |
| `C_reorder_detected` | swapping two epochs leaves the head unchanged |
| `C_split_epoch_detected` | splitting one epoch in two leaves the head unchanged — free epoch inflation |
| `C_dropped_epoch_detected` | dropping an epoch leaves the head unchanged |
| **`C_delta_content_bound`** | substituting one atom inside a delta at identical size and identical roots leaves the head unchanged — the chain would bind shape rather than content, which is S65 |
| `C_replayed_epoch_rejected` | an epoch's `(root, delta)` verifies at a different position — epochs would be transplantable |
| **`C_chain_alone_cannot_catch_a_forged_delta`** | the chain rejects a root its declared delta does not produce — then it subsumes S73 and this boundary claim is wrong. **Also fails if the fold does not reproduce the honest root**, which would make the comparison vacuous |

**All eight fire.** Observations in `provenance.json`.

## Two of my own controls were weak, and inspection caught them before publishing

1. **`C_replayed_epoch_rejected` mangled two positions at once** — it overwrote a
   root at one index and a delta at another, including an `i-1` that wrapped to the
   last delta when the index was 0. It fired, but for a muddled reason. Replaced
   with a clean transplant: epoch 5's pair copied verbatim over position 6, nothing
   else touched. *A control that fires is not the same as a control that tests what
   it says.*
2. **`C_chain_alone_cannot_catch_a_forged_delta` was near-tautological.** It
   asserted only `folded != lied_root`, which two different SHA-256 digests satisfy
   by default — and would have passed on a **broken** fold that returned `None`.
   Now it also requires `folded == honest_root`, so the control is void if the fold
   machinery is not working on that input at all. This is A15 in its corrected
   form: the negative bound and the positive detectability are different
   requirements and both are needed.

## Caveats
- **Reorder and delta-content are not separable in this design**, and the table
  above should not be read as isolating order. A delta is defined as the atoms
  *new at that epoch*, so permuting epochs necessarily permutes delta contents.
  The claim is that reordering is *detected*, not that order alone was varied — an
  experiment isolating order would need two epochs with identical deltas, which
  this definition makes impossible.
- **This binds a sequence a prover declares; it does not establish that the
  sequence is the one that physically happened.** Nothing here timestamps an
  epoch or attests who produced it. That needs the attestation root
  `HANDOFF.md` lists as binding constraint 1, and `operator` is still pinned at
  one domain.
- **No timings.** Every figure is a digest or a byte count, both load-insensitive,
  so the measurement is valid while `quiet.sh` refuses (11 containers).
- **1,247 atoms, 67 epochs, one corpus.** The 32 B/epoch cost is exact and
  structural; the corpus size is not what it depends on.
- **Python, not `pathmap`** — inherited from W2, same constant-factor caveat.

## Changelog
- **2026-08-17, S75 — the falsifier was run and this spike is UNAFFECTED.**
  `spikes/S75_pathmap_check/` found real `pathmap` needs **18.4×** the node depth of
  W2's trie on these atom keys, which costs S73 roughly 18× its insert-proof size.
  **The chain is untouched**, because a chain step commits to digests — a prior
  head, a state root, a delta root — and never walks a path. So the cheapest of the
  three constructions is the only one the finding does not scratch. Recorded here
  rather than left implicit, since "the falsifier fired on the neighbouring spike"
  is exactly the kind of thing a reader would otherwise assume applies.
