# S68 — an interpreter-state commitment is not reachable on hyperon as it stands

**Verdict: RED, and it gates the settlement design. Even with three separate contaminants neutralised, the interpreter-state string diverges on ~half of runs. The dispute path cannot be built on this engine until the divergence is fixed upstream.**

S65's commitment was destroyed because it committed to `current_results()` —
emitted output, not state — and 100% of its leaf content was `"()\n"` repeated,
so an attacker forged the root in 6 lines of Python without running hyperon. The
identified rebuild target was `Debug for RunnerState` (`mod.rs:527-534`), which
exposes `interpreter_state` including the plan stack and changes on ~100% of
steps. This tests whether that target is usable.

## Measured — `c1_grounded_basic`, 250 steps

| what is neutralised | distinct digests / trials |
|---|---|
| nothing (raw `Debug`) | **10 / 10** |
| `0x…` addresses masked | 5 / 5 |
| + `Variables({…})` sorted | 5 / 5 |
| + `id: N` masked | **2 / 20** (11 vs 9) |

Masking takes it from *completely* nondeterministic to *nearly* deterministic,
and stops there. The residual is a stable binary split — one ordering decision
that goes two ways at roughly even odds.

## The three contaminants, in the order they surfaced
1. **Raw code pointers** — `ret: 0x100c44640` in the plan stack.
2. **`Variables({…})` hash-set iteration order.**
3. **Variable ids baked into content**, which is Issue 3 of the upstream report
   and is worse than an ordering problem. Two runs of the same program:
   ```
   A:  VariableAtom { name: Store(Allocated("rargs"),  …), id: 8 }
   B:  VariableAtom { name: Store(Allocated("result"), …), id: 9 }
   ```
   Different variables receive different ids across runs, so **sorting cannot
   fix it** — the content itself differs, not just the order. `id` is drawn from
   `NEXT_VARIABLE_ID.fetch_add` (`hyperon-atom/src/lib.rs:222-226,330`) and
   participates in the derived `Hash` that keys `matcher::Bindings`, so set
   order and id assignment are mutually determining.
4. **A fourth, unidentified.** Survives all three masks at ~50% incidence.

## Why masking is not a fix even where it works
A verifier cannot mask. Two replicas must produce the same bytes from the same
computation; a canonicalisation applied afterwards only hides a divergence that
already happened, and cannot distinguish "same computation, different
representation" from "different computation". Masking here is a **diagnostic**,
used to count contaminants, not a proposed mechanism.

## Consequence for the settlement design
`RISKS.md` R-NEW's dispute path is optimistic settlement plus bisection to an
interval, then a succinct proof of that interval. Bisection requires the prover
to commit to state at arbitrary step *k*, and **there is currently no state
commitment available**:

- `current_results()` — forgeable, binds no computation (S65).
- `Debug for RunnerState` — not reproducible, four contaminants, one unidentified.

So the dispute path is **blocked upstream**, not merely uncosted. That changes
the standing of the hyperon work from "worth contributing" to **gating**: Issue 3
is on the critical path for settlement, and it is currently the one item in
`proposed/hyperon-nondeterminism/` shipped as a report without a patch.

The happy path is unaffected — Merkle-batched commitments over *results* plus
payment channels need no state commitment. Only disputes do.

## What would have to be true
1. Variable identity reproducible for a fixed program — Issue 3.
2. `Bindings` iteration ordered by content rather than hash.
3. No pointer in any `Debug` reachable from the state.
4. The fourth contaminant found and removed.

None is deep; all are upstream. Until then, a dispute can only be resolved by
**re-execution**, which is the cost the succinct-proof design existed to avoid.

## Caveats
- One program, 250 steps, one machine. The residual 11/9 split is stable across
  20 trials but has not been characterised on other programs.
- The fourth contaminant is **not identified**. It could be a fifth and sixth;
  the method only shows that masking three leaves ~50% divergence.
- `Debug` output is not a designed commitment format. A purpose-built
  `state_digest()` on `RunnerState` could sidestep the representation issues
  entirely while still binding the plan stack — untried, and the constructive
  path if upstream is willing.
