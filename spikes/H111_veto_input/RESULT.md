# H111 — the autoloop's only veto gate has no candidate input

**ATTACKER-1, 2026-08-18. ATTACK (§2, instruments before conclusions) on
`.github/autoloop/evaluators/eval_determinism.py`, handed to this lane by the
peer session that wrote it, with four of its own defects named.**

Handing over an instrument with its defects listed is the behaviour this repo
says produces honest results, and it is why this row found more than it was
asked to: the ask was a negative control, and the control is the smallest of the
four findings below.

## Verdict

**The identity is real and the file computes it honestly. As a VETO it cannot
fire on any candidate, and as an artifact it exists in one working tree.**

## 1 · The veto has no candidate input (A15 — a control that cannot fire)

`config.json` sets `determinism_exact` to `weight: 0.0, min_acceptable: 1.0,
veto: true` — a per-candidate disqualifier — and names three `mutation_targets`:

```
spikes/G34_length1_and_constants/length1_constants.py
spikes/W6_incremental_witness/incremental_verifier.py
spikes/S85_verify_vs_reexec/verify_vs_reexec.py
```

**The gate opens none of them and imports no repo module.** Measured two ways,
because one would not have been enough:

- **Structurally, and completely rather than sampled** — a `sys.addaudithook`
  over the gate's own process records every `open` and every loaded module:
  repo files opened **NONE**, repo modules imported **NONE** (only `__main__`;
  everything else is numpy inside the venv).
- **Empirically** — the three targets truncated, replaced with a syntax error,
  and deleted outright, on a `git archive HEAD` extraction. All three arms:
  `determinism_exact: 1.0`, `score_digest: ffffff7c`, **byte-identical to
  baseline**.

**F1 was the falsifier that would have killed this row** (*if any mutation moves
the metric, the gate discriminates*). It did not fire.

So the veto's value is constant across every candidate the loop can generate. It
is a genuine **environment tripwire** and a **null candidate gate**, and only the
loop's owner can decide which the ratchet needs. **Not changed here** (A22: a
party must not narrow a rail it operates under, and the veto's purpose is the
owner's to set). The concrete option, if a candidate gate is wanted: have it
recompute the identity *through* the code path a mutation target actually
controls, so a mutation can reach the number.

## 2 · The gate is not in the repository (family C)

`git ls-files .github/autoloop/` returns **0 files**, and `git check-ignore`
says it is **not ignored** — so it is uncommitted, not deliberately excluded.

**The veto protecting the one claim that has survived every adversarial round in
this project exists in a single working tree on a single machine.** Any clean
checkout, any other lane, any CI runner has no gate at all — and `config.json`'s
own note says *"CI must `pip install numpy` or this gate cannot run"*, which
reads as the only prerequisite.

**Not fixed here, deliberately.** Committing another lane's uncommitted tree puts
their in-flight work under my `Atom:` — the defect H66 reports and H79 measured,
and it has happened to this lane three times in one span. Reported to the owner.

## 3 · The second dependency door — same class, closed hours earlier at door one

The author had just fixed: numpy absent → `exit 2`, no metric, because *"a
missing dependency is not a failing score"*, and scoring 0.0 against a veto at
`min_acceptable: 1.0` would disqualify **every** candidate for a reason having
nothing to do with any candidate.

**`np.bitwise_count` arrived in numpy 2.0.** With numpy *present but older*, no
guarded path was taken at all:

```
AttributeError: module 'numpy' has no attribute 'bitwise_count'
metric emitted: False   rc=1
```

**and `1` is exactly the exit code of `IDENTITY_BROKEN`** — an environment fault
was indistinguishable from a real break of the mission's keystone property.
**Fixed**: `REFUSED_NUMPY_TOO_OLD`, exit 2, no metric — the same semantics as the
first door.

*Ceiling, stated: `exit 2` is also what the interpreter returns for "can't open
file", which is how a missing gate looks. The refusal is machine-readable on
stderr and the absence is not; a caller that reads only the exit code cannot
tell them apart.*

## 4 · The negative control (what was asked for)

`--selfcheck` plants one break at a time in a **copy** of the source and requires
`determinism_exact: 0.0` with exit 1:

| planted break | result |
|---|---|
| the identity: `D - 2*h` → `D - h` | **RED** |
| a single score off by one (a *partial* break) | **RED** |
| the packing: `T > 0` → `T > -2` (all bits set) | **RED** |
| unmodified control copy | **GREEN** |

**Two errors of mine on the way, both kept in the artifacts:**

1. **I planted `T > 0` → `T >= 0` and called it a break.** It stayed green. On
   bipolar data `T ∈ {-1,+1}`, so `>= 0` and `> 0` select the same bits: it is
   an *equivalent transformation*, and "the gate missed it" would have been a
   published false accusation. A no-op intervention leaving the number unchanged
   is a disconnected wire, and here the wire was mine. Relabelled, kept as the
   arm that must stay green.
2. **The first `--selfcheck` refused all three arms**, because the anchor strings
   appear twice in the file once the check lists them — in `main()` and in the
   check itself. `src.count(old) != 1` caught it. A suite that patched the first
   match would have measured its own fixture. Anchors are now assembled.

**And the check says what it does not prove:** it demonstrates the gate can fire
on **its own arithmetic**; it does not demonstrate the gate can fire on a
**candidate**, which finding 1 measured that it cannot.

## 5 · The digest — measured before being attacked (F5)

The XOR fold is order-insensitive **and self-cancelling**: a permuted score
matrix, a duplicated pair and a zeroed pair all collide (both demonstrated).
**But `exact` comes from `np.array_equal`, so the digest is a reporting field and
is not load-bearing for the verdict** — killing it as "the defect" would have
been killing the wrong thing. It becomes load-bearing the moment anyone compares
two digests and calls agreement a reproduction, so the emitted field now names
the algorithm and its weakness.

## 6 · Scope, as an emitted field rather than as prose

The gate checks one numpy against one numpy, in one process, on one machine. The
docstring said so; docstrings are not what survives three documents of citation,
and *"determinism gate is green"* is the decay path. Output now carries
`"scope": "single_process_single_numpy_local_identity"` and
`"not_verified_here": "cross-machine, cross-kernel (that is S34)"`.

## Falsifier for THIS row

If a mutation of any `mutation_targets` file moves `determinism_exact`, finding 1
is wrong. If `--selfcheck` passes on a build whose `main()` is broken, finding 4
is wrong. Both runnable:

```
./spikes/S5_hdc_prototype/.venv/bin/python spikes/H111_veto_input/probe.py
./spikes/S5_hdc_prototype/.venv/bin/python .github/autoloop/evaluators/eval_determinism.py --selfcheck
```

## Corrected in place

My CLAIM asserted the configured interpreter *"is a symlink to `python3.14`, and
`import numpy` fails there — so as configured this gate does not run at all
today"*. **WITHDRAWN.** I tested the wrong interpreter: the venv python has numpy
**2.5.2** and the configured command runs and emits `1.0`. The generalisable half
survives — the guard covers only `ImportError` — and it is finding 3.
