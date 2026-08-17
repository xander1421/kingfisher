# ATTACK cycle 4 — against the trie instrument W2 and S73 both rest on

**Target chosen per MISSION_LOOP §2: instruments before conclusions, self-authored
data first. Verdict: one real soundness bug found and fixed, one dead probe of my
own caught mid-attack, one falsifier shown to be one-directional. No published
number in W2 or S73 changes.**

Runnable: `python3 attack.py` (seed 20260817). Output: `attack.json`.

## Why this target and not the numbers

W2 and S73 share **one** implementation of `build`, `node_hash`, `walk` and
`fold`, and I wrote the prover *and* the verifier out of those same four
functions. That is **A22** — a party supplying the input to a check on itself. A
bug in `node_hash` or `build` makes prover and verifier agree on the wrong answer,
and **all 20 controls across both spikes pass anyway**. Quorum cannot see it
either: three replicas running the same code agree byte-identically on a shared
bug. So the instrument goes first and the measurements are not attacked at all
this cycle.

## A2 — implementation diversity · SURVIVES

`build` divides a **sorted** key list on the longest common prefix, recursively.
The attack builds a second trie by the opposite algorithm — **insert keys one at
a time** into a mutable trie with node splitting, then hash bottom-up in a
separate pass — with an independently written serializer. Nothing is shared but
the format sentence.

**7/7 key sets agree**: four FB15k-237 shards (offsets 0 / 136000 / 0 / 50000,
sizes 1,024–8,192) and three sizes of S73's variable-length atom keys (50 / 300 /
1,246). So the `lcp` logic is not carrying a bug the verifier would mirror.

This is the only attack in this cycle that could have invalidated both spikes at
once, and it is the one worth repeating whenever those four functions change.

## A4 — the "unreachable" branches · FATAL, then fixed

S73 shipped `apply_insert` cases 2 and 3 as unreachable-by-construction: the atom
encoding is prefix-free, so no key ends inside another. **Unreachable means
untested, and it ships anyway.** Forcing them with prefix-nested synthetic keys
found a real bug — not in `apply_insert`, but one layer down:

```
trie holds {b'abc', b'abcd', b'b', b'bcd', b'xyz'}
prove_non_membership(root, b'ab')  ->  None      # "b'ab' is PRESENT"
```

`b'ab'` is not a key. `walk` returns `COVER` when the query is exhausted, **even
if it stopped inside the node's compressed prefix**, and both
`prove_non_membership` and `verify_non_membership` then read `node.term` — which
describes a key ending at the prefix's *end*, not wherever the query stopped. The
node reached carries `prefix=b'bc'`, `term=True` for `b'abc'`, and one byte of
that prefix had been matched.

**Consequence had it been reachable:** a prover could deny any key that is a
proper prefix of a stored key, and the verifier would agree, because both sides
made the same mistake. That is the shared-implementation failure this cycle was
built to look for, and it was hiding in the one branch neither spike could reach.

**Fix.** `walk` now returns `matched` (bytes of the node prefix actually
consumed); a key is present only if `matched == len(prefix)` **and** `term`.
`verify_non_membership` recomputes `matched` from the *proven* description, so the
correction does not depend on the prover. `prove_membership` got the same guard —
there it was a liveness bug only, since `verify_membership` already required the
remaining key to equal the whole prefix.

**Blast radius: zero published numbers.** W2's keys are fixed 12-byte, so no key
is a prefix of another; S73's encoding is prefix-free and checked
(`encoding_prefix_free: true`). The bug was latent in both. W2's shape table is
byte-identical after the fix (2,541 / 23,625 / 49,152 B), and S73 still verifies
66/66 epochs — which is the evidence that it was latent rather than the evidence
that it was harmless.

All four `apply_insert` cases are now exercised: hits `{1: 4, 2: 1, 3: 2}` here
plus `{1: 99, 4: 301}` in S73's own control.

## The attack's own dead probe — caught, and it is the same sin as W1

A4's first run reported:

```
[SURVIVES] A4-unreachable-cases: case hits {2: 0, 3: 0, 1: 3},
           every computed root matches a full rebuild.
           The two branches S73 could not exercise are correct.
```

**Cases 2 and 3 were never reached.** The probe missed its target — because of the
very bug it was hunting, which made the prover return `None` and the loop `continue`
past every interesting key — and then reported a clean null as a pass. That is
exactly W1's failure: a control that cannot fail reading as evidence, committed by
me inside the ATTACK cycle whose job is to catch it.

`attack.py` now has a `PROBE-FAILED` verdict, and reaching the target is a
**precondition** of any A4 verdict. The general rule this instance adds:
*a probe that does not demonstrate it reached its target has produced no evidence,
and "no FATAL" from such a probe must not be reported as SURVIVES.*

## A3 — omission shapes W2 never tested · SURVIVES

W2's `C_omit` drops the **last** key. Five untested cheat shapes, on a 253-row
answer:

| cheat | accepted? |
|---|---|
| drop a **middle** key | rejected |
| swap one row for **another real key** from the shard | rejected |
| claim the answer is **empty** | rejected |
| claim empty, dressed as a **divergence proof** | rejected |
| **duplicate** a row | rejected |

The verifier was already sound on all five; **the gap was in W2's control set, not
in its code.** Worth stating plainly: `C_omit` testing only drop-last was weaker
than W2's write-up implied.

## A1 — encoding ceilings · SURVIVES

Both encoders pack lengths into 2 bytes, capping symbols and arity at 65,535.
Corpus maxima: **symbol 365 B, arity 10, longest atom encoding 1,155 B** — 179×
headroom. Overflow **raises** rather than truncating (`encode` and `node_hash`
both confirmed), so it is a liveness limit and never a silent collision. A single
64 KB string literal in a corpus would abort a commit rather than forge one.

## A6 — my own provenance fix, attacked · SURVIVES

The staleness floor is `max(path-scoped HEAD time, newest dirty file)`. Attack: a
dep **subdirectory with no commit of its own** and an **untracked** source, plus a
year-2020 artifact. The floor still rose (`from='dep/'`) and the stale artifact was
caught. Note the `from` value: `git status --porcelain` collapses an untracked
directory to `dir/`, so the floor comes from the directory mtime, not the newest
file inside it. Sound here; a weaker signal than a file mtime, and named as such.

## A5 — D6's own falsifier F2 is one-directional · HONEST-DEBT

Re-measured: **6 `RESULT.md` cite D6, 0 have a `provenance.json`. Still 6/6
failing.** Debt unchanged: `Q1_quorum_sim`, `S72_c3_cpuset`, `N1_prefilter_cost`,
`W4_prefilter_readset`, `B1_bundling_real`, `W1_witnessed_reexec` (the last is
INVALID; skip it).

And the finding F2 could not make: **six spikes carry a provenance record and
never mention D6** — including both of mine from this session, `W2_witnessed_trie`
and `S73_epoch_commitment`, plus `M1_1_android`, `M1_8_quorum3`, `M2_1_fleet`,
`G25_carrying_capacity`.

So **F2 counts citation without compliance and is blind to compliance without
citation.** As written it scores my two compliant spikes as neither pass nor fail.
The falsifier needs both directions; `specs/D6_discipline.md` gets a changelog
line rather than a silent edit, per its own P3.

## What this cycle changed

| | |
|---|---|
| `trie_witness.py` | `walk` returns `matched`; non-membership and membership corrected. **Soundness fix.** |
| `attack.py` | new, 6 attacks, `PROBE-FAILED` verdict added |
| `trie_witness.py` | `can_fail_because` supplied per control, for the harness's new `Control` contract |
| `specs/D6_discipline.md` | F2 restated as bidirectional, changelog line |
| guardrails | **A29** — a probe that cannot show it reached its target has produced no evidence |

## What this cycle did NOT do
- **The measurements were not attacked.** W2's witness sizes and S73's per-epoch
  costs stand unexamined this cycle; only the machinery under them was tested.
- **A2 proves agreement, not correctness.** Two implementations I wrote in one
  session can share a misreading of the format. The real diversity check is
  `pathmap` itself, which is the falsifier W2 already names.
- **`node_hash`'s collision resistance is assumed**, not tested — it is SHA-256 in
  a length-prefixed encoding, and no attack here tries to break that.

---

# ATTACK cycle 8 — the loop and the harness (MISSION_LOOP §12.8)

**Verdict: the Stop hook's repo-root registration could not resolve, its own
22-check suite could not have noticed, and I had never read `CLAUDE.md`. Three
findings, all in the machinery rather than in a result.**

## A7 — the hook registration did not resolve · CONFIRMED, fixed

`.claude/settings.json` registered the Stop hook as:

```
"command": "$CLAUDE_PROJECT_DIR/.claude/hooks/loop_gate.sh"
```

`CLAUDE_PROJECT_DIR` is **unset** in this session, and the sibling
`spikes/S51_multicore/.claude/settings.json` already pins the absolute path.
Mechanically, per §12.4:

| file | expands to | exists |
|---|---|---|
| `.claude/settings.json` | `$CLAUDE_PROJECT_DIR/.claude/hooks/loop_gate.sh` (unexpanded) | **False** |
| `spikes/S51_multicore/.claude/settings.json` | `/Users/…/kingfisher/.claude/hooks/loop_gate.sh` | True |

**This is §12.2 exactly: the S51 fix pinned the path at one site and left the
repo-root registration — the one a session started at the repo root loads — on an
env var.** Fix-the-site-not-the-class, in the very file whose header documents
having been bitten by it.

*Honest scope:* Claude Code may inject `CLAUDE_PROJECT_DIR` into the hook's own
environment even though it is absent from a Bash tool's env, so this is
"unresolvable from any environment observable here", not "proven never to have
fired". §12.4 settles it anyway — a reference that cannot be resolved mechanically
is the defect, and pinning costs nothing. Fixed to match the sibling.

## The suite could not have caught it · the sharper half

`spikes/harness/test_loop_gate.sh` had **22 checks and every one invoked
`loop_gate.sh` directly.** None tested whether anything *registers* it. So the
suite reported all-green while the wiring was dead — the same shape as §14.4's
earned lesson, where a 15-check suite passed over a defect because every check
set `CALLSIGN` itself.

Added a 23rd check: every `settings.json` under version control must register a
command that resolves to an existing executable **without expanding any
environment variable**. Verified it can fail — reintroducing the `$` form gives:

```
FAIL  reg .claude/settings.json resolves without env (want 'literal-path', got 'env-var-in-path')
loop_gate.sh: 1 FAILED, 22 passed — the loop contract is not enforceable as written
```

and restoring the pin gives `23 checks pass`.

## A8 — `run_loop.sh`'s cross-file claim · SURVIVES

`loop_gate.sh` v3's header asserts the exit marker "lands in
`.loop_exit.$CALLSIGN`, which only `run_loop.sh` clears." Resolved mechanically:
the hook writes `EXIT_MARK=".loop_exit.${LANE}"`, and `run_loop.sh:26,41,74-79`
declares, clears and reads it. The claim holds.

## A9 — I had never read `CLAUDE.md` · CONFIRMED against myself

`run_loop.sh:48` spawns each lane with *"Read CLAUDE.md, then MISSION_LOOP.md,
then HANDOFF.md"*. My prompt named `MISSION_LOOP.md` and `HANDOFF.md` only, so I
was not spawned by this launcher, and **I ran seven cycles without the file the
repo calls "the one place a rule will actually be seen."** Two rules were being
broken as a result:

1. **`kfcheck.certify` is the entry point, not `provenance.record`.** Both my
   spikes called `record` directly, so they ran families A and C and **skipped B
   (instrument fiction) and E (the number is real, the model is wrong)** — and
   declared no falsifier, which `certify` refuses outright. Both now certify
   `ok: true` with a falsifier recorded.
2. **`edits.anchored_replace`, not `str.replace`** — because `str.replace`
   returns the string unchanged when the anchor is absent, and a silent no-op edit
   shipped that way before. I used `str.replace` throughout. Audited all of this
   session's document edits for stale strings left by a missed anchor: **0 hits
   across six patterns.** They landed, but by luck in the cases where I omitted
   the assert; the anchored form now used for the rest.

**Family E fires on both spikes' scaling tables.** `units.check_affine` REFUSES an
affine model on W2's auth-path points (adjacent slopes span **760%** of the 25%
tolerance) and on S73's insert-proof points (**203%**). So both scaling
statements are endpoint ratios over measured points, and **no rate may be fitted
to either.** Recorded as changelog lines on both pages; no number changed.

## And one §12.5 violation of my own
`HANDOFF.md`'s NEXT 1 named "re-run W4 and commit its per-shape table", which
cycle 6 had already recorded DONE — an item in a DONE list and a NEXT list at
once, which is the defect §12.5 exists for and which costs a restarting agent a
whole cycle. Replaced with the epoch-chain history binding S73 left open.
