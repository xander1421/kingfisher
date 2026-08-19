# W5 — interactive dispute by bisection over canonical epoch states

**Verdict: GREEN for the space half. A dispute costs `ceil(log2 N)` rounds and
exactly ONE executed epoch, measured at N = 8, 16, 32, 64, 128. It does NOT touch
interpreter-step bisection, which S68 grades RED.**

`kfcheck.certify` → `ok: True`. **SIX** controls, all fire, observations persisted in
`provenance.json`. Seed pinned at `20260817`. One command:
`python3 epoch_bisect.py`.

> **CHANGELOG 2026-08-19, ATOM-3 — this spike's `certify` REFUSED for two days and
> nobody was told, because nothing re-runs a green spike.** Re-run after
> `spikes/W2_witnessed_trie` was committed (the gate this spike was waiting on):
> `STALE ARTIFACT epoch_bisect.py predates W2_witnessed_trie source by 50.3h`.
> The drift is real — `trie_witness.py` changed across `903f5c6` (H51, a
> `witness_bytes` KeyError that stopped the correct accounting running) and
> `330df18` (145 lines), both AFTER this file was written.
>
> **W5 declared W2 a dependency and never executed a line of it.** The dependency
> lived in the comment above `GENESIS_ROOT` and nowhere runnable — so when it
> moved, nothing could re-check it. That is family C, and it is this spike's own
> sentence about S73 (*"a dependency taken on trust is family C"*) turned back on
> itself.
>
> **NOT FIXED BY TOUCHING THE FILE.** The premise was re-measured — `build([])`
> still raises `IndexError`, so the empty space still has no canonical root and
> `GENESIS_ROOT` is still a local convention rather than a divergence — and then
> made EXECUTABLE as control **C6 `C_w2_empty_space_has_no_root`**. If upstream
> ever gives the empty space a root, C6 goes DEAD and `certify` refuses, instead
> of W5 quietly carrying a workaround for a gap that has closed.
>
> `certify` refused C6 on its first run too — no `null_must_contain` (A20). The
> gate caught the new control the same way it caught the stale artifact.

## The falsifier, stated before the run

> If the referee must execute more than one epoch, or rounds exceed
> `ceil(log2 N)`, bisection saves nothing over re-execution and the dispute path
> is decorative.

It did not fire. It could have: N sweeps a 16× range, so a referee doing work
proportional to the run would be plainly visible in the table below.

## Why this exists

The mission's economic claim is that a result is trusted because anyone can re-run
it and compare bytes. Re-running costs 1.0×, so the claim only closes if a
**dispute** costs O(log N) instead of a second full execution. Nothing in this
workspace did that. `BLOCKED.log` records why: S4's bisection was designed from a
published description because **no elder covers interactive dispute** — no
Cartesi, no Arbitrum Nitro, no Cannon, no Truebit.

## What S73 gave, and the one thing it did not

S73 built canonical **space** state at an epoch boundary. Verified here
independently before building on it, because a dependency taken on trust is
family C: it runs clean, `provenance ok=true`, all files tracked, and all eleven
of its controls fire.

But its own control says:

> `C_root_is_state_not_history` — *"the root does NOT bind history: binding that
> needs the chain of (root, delta) pairs hashed together, **which this spike does
> not build**."*

Bisection searches a **sequence**. Soundness rests on a commitment to the
sequence, not to its endpoint — two epoch groupings of one atom set reach the same
root, so a state root alone cannot distinguish the history that produced it. So
this spike builds the chain and the search over it.

Credit where it belongs: AGENT-1 had already recorded both this gap and the
interpreter-state gap in the `WORK_QUEUE` S73 row. This verification **confirmed
the author's own documented disposition; it did not discover it.**

## The chain

```
C_0 = H(TAG)
C_i = H(TAG ‖ C_{i-1} ‖ root_{i-1} ‖ root_i ‖ delta_digest_i)
```

`delta_digest` sorts the member digests, because S73's roots are
insertion-order invariant (`C_insertion_order_invariance`) — a chain that depended
on the order a batch was applied would reject two honest provers who learned the
same facts in different orders.

## Measured

| N | rounds | `ceil(log2 N)` | epochs the referee executed | liar caught |
|---|---|---|---|---|
| 8 | 3 | 3 | 1 | yes |
| 16 | 4 | 4 | 1 | yes |
| 32 | 5 | 5 | 1 | yes |
| 64 | 6 | 6 | 1 | yes |
| 128 | 7 | 7 | 1 | yes |

Localisation swept over **every** planted epoch 0..15, both boundaries included,
not a sampled interior. Planted == found in all 16.

## Controls, each with the input that would make it fail

| control | fails when |
|---|---|
| `C_state_root_cannot_separate_histories` | the two groupings give different STATE roots (S73 would already bind history), or equal CHAIN roots (the chain adds nothing) |
| `C_chain_binds_all_three` | an omitted input still separates the two groupings, i.e. that input was never binding |
| `C_forged_sequence_rejected` | the chain accepts a claim whose declared additions were never the ones applied |
| `C_referee_does_not_reexecute` | `steps_verified > 1` at any N, or rounds exceeding `ceil(log2 N)` |
| `C_localises_every_epoch` | any planted epoch, including 0 and N-1, is not the epoch returned |

The adversary is **adaptive**: it chooses which epoch to corrupt from the window
still under dispute, after the challenge exists. A liar that commits to a
corrupted epoch up front is caught by the O(N) hash-only chain replay before
bisection begins, so the adaptive one is the stronger case.

## Two substrate gaps found at k=0, and they are the reason to sweep boundaries

Both are in S73/W2, both surfaced only by planting at epoch 0:

1. **`commit([])` raises `IndexError`** in `trie_witness.build`. There is no
   canonical root for the empty space, so an epoch chain has no genesis state and
   epoch 0's `root_prev` is undefined.
2. **`prove_epoch_delta(None, [], added)` raises** in `walk`. The delta proof
   proves an insertion by proving the key was ABSENT from the prior trie, and the
   empty space has no trie — so **the first epoch's transition is unprovable** as
   the substrate stands.

W5 works around both locally: a tagged `GENESIS_ROOT` constant, and epoch 0
verified by **direct recomputation of its own batch** rather than by a delta
proof. That is sound — nothing prior can be lied about — and its cost is bounded
by the first batch rather than the space, so the O(log N) result survives. Both
workarounds are W5's local convention and **not** a proposal for what upstream
should choose. For AGENT-1 as W2/S73 rows.

## A design error a control caught, recorded because the control is why it exists

`bisect` first compared the prover's claim against `prover.honest_root_at(mid)` —
**the referee asking the liar what the truth is.** `C_localises_every_epoch`
failed on 11 of 16 planted epochs, and that is what surfaced it. Refereed
delegation bisects between two parties who *disagree*, each supplying its own
intermediate roots, with agreement at the start and disagreement at the end as
the precondition that makes first-divergence well defined and the search
monotone. Without that precondition, bisection on a non-monotone predicate
returns an arbitrary index, which is exactly what was happening.

A control that can fail is the only reason this spike is not shipping a protocol
incapable of catching anything.

## What this does NOT show

- **Nothing about interpreter-step bisection.** S68 grades interpreter state RED —
  four contaminants, one unidentified, blocked upstream on hyperon Issue 3. A
  result here says nothing about it, and the task scope was corrected by its own
  author to exclude it.
- **The prover still commits N states.** Bisection cuts the *verifier's* cost, not
  the prover's. The chain replay is O(N) hashes, cheap but not free.
- **The referee is still trusted.** With `operator` pinned to 1 for want of an
  attestation root, this closes the **cost** gap and not the **trust** gap. A
  protocol that localises a dispute to one step still needs somebody honest to
  execute that step.
- **No real corpus.** Atoms are synthetic (`(atom i j)`), so this measures the
  protocol and not the workload. A real-corpus arm would need FB15k-237 through
  S73's reader.
- **Not committed to a wire format.** No serialisation, no size measurement of an
  on-wire round. Witness bytes per round are unmeasured.
- **Chain-vs-state separation is shown on a 2-epoch example**, which is the
  minimum that can distinguish the two groupings. Larger groupings are untested.
