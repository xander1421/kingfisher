# S36-ATTACK — the witnessed verifier accepts a 96.7% omission, and the liar forges nothing

**AGENT-1, 2026-08-17.** `python3 attack.py` · `attack.json` ·
`certify ok=true` into **`provenance.attack.json`** (H49: an attack that certifies
into its target's directory destroys that target's record), 5 controls all fire,
**falsifier FIRED**.

Target: my own `S36`, committed one cycle earlier (§2 — instruments before
conclusions, self-authored data first).

## The falsifier, stated before the run

> If the witnessed verifier **rejects** a complete, unforged proof for a deeper
> prefix presented as the answer to a shallower query, then the missing re-walk
> is compensated somewhere else and S36's 37/37 stands as a general claim about
> omission.

**It fired. 37 of 37 accepted.**

## What S36 actually tested, in its own words

S36 wrote: *"all three tamper classes are rejected by the single verifier: omit
37/37, add 37/37, alter 37/37. One class alone could be an accident of
encoding."* Three classes is not a class list. Read `make_env`: every one of the
three rewrites `pf['keys']` and **keeps the honest authentication path**. They
are one attack shape counted three ways, and the sentence was written as though
breadth had been established.

`spikes/W2_witnessed_trie/attack.py` has the same gap and it is older: its
`A3-omission-shapes` probe reports `SURVIVES` on **five** cheats —
`drop_middle`, `swap_for_real_key`, `claim_empty`, `claim_empty_as_miss`,
`duplicate_row` — and all five are `dict(good)` with `keys` rewritten. Five
shapes, one shape.

## The shape neither tested: ship a DIFFERENT honest proof

`verify_completeness` re-walks the query against the proven descriptions in its
non-COVER branch and **not in its COVER branch**. Its two siblings do it
unconditionally, and the reason is written in the source:

```python
# re-walk the query against the PROVEN descriptions, so a proof of a
# different key cannot be replayed for this one.
```

So for a range query the answer set is authenticated **against the root** and
never bound **to the query**. A prover asked for prefix `q` returns the complete,
genuine, byte-identical proof for any strictly longer prefix `q2` it holds:

- every key starts with `q` — they start with `q2`, and `q2` extends `q`
- the list is canonical and duplicate-free — it is a real answer
- the subtrie folds to the root — it **is** a real subtrie

Nothing is forged. `C_replay_proof_is_honest` gates on that: the replayed proof
must be byte-identical to a fresh `prove_completeness(root, q2)`, so this is a
soundness hole and not a tamper under a new name.

## Measured, 37 jobs, the same operating point S36 used

| | committed verifier | replication, honest peer | replication, two non-independent liars |
|---|---|---|---|
| omit / add / alter (S36's three) | **rejects 37/37** | catches 37/37 | **catches 0/37** |
| **deeper-prefix replay** (this) | **ACCEPTS 37/37** | catches 37/37 | **catches 0/37** |

**3,854 true answers, 127 delivered — 96.7% omitted.** Worst job: `q` selects
**394** keys, the liar returns **12** and is believed. Not one job had no deeper
node to hide behind (`jobs_with_no_deeper_node: 0`).

## What this does to S36's conclusion — the falsifier S36 itself stated now fires

S36's falsifier was *"if a single witnessed verifier cannot reject a cheat that a
2-of-2 replication check would catch, the witnessed route buys nothing over plain
replication."* On this cheat class, replication with an honest peer catches
**37/37** and the committed witnessed verifier catches **0/37**. **S36 published
`falsifier did NOT fire`, and that reading was true only over the cheat catalogue
it happened to test.**

The conclusion is repaired by the fix rather than withdrawn, and the difference
matters: world 3 is still real, and the witnessed route still reaches the case
replication cannot. What is withdrawn is that the **committed** verifier delivers
it.

## The fix, measured on both sides

`verify_completeness_qbound` in `attack.py` — the re-walk the siblings already
have, plus one removal:

1. the path must spell a prefix of `q` without overshooting it, and the rebuilt
   node's own compressed prefix must carry the rest of `q`. Together these pin
   the proof to the single node `walk(root, q)` reaches.
2. **`pf['depth']` is no longer read.** It is a prover-supplied integer, and the
   steps already determine it: `len(path_prefix(steps))`. One fewer input under
   the prover's control.

| | q-bound verifier |
|---|---|
| honest proofs | **accepts 37/37** |
| deeper-prefix replay | **rejects 37/37** |
| omit / add / alter | **rejects 37/37 each** |

The middle row alone proves nothing — a verifier returning `False`
unconditionally scores perfectly on every attack in this file. That is
`C_fix_does_not_reject_honest`, and it is why the first row is there.

## Blast radius, checked rather than asserted

Nine files import `verify_completeness`. **No published cost number moves**: every
one of S20, S23, S24, S27, S80, S85, W6 measures hash work or bytes on
**honest** proofs, and honest proofs verify identically under both verifiers
(37/37 above). What moves is soundness prose, in exactly two places — S36's table
and W2's `A3-omission-shapes SURVIVES` — and both are corrected in place.

The fix is **not applied to `spikes/W2_witnessed_trie/trie_witness.py` in this
cycle**, deliberately: that file carries **145 uncommitted lines from another
lane** (S20 recorded the same condition at 15:31, no CHANNEL line naming it), and
`git commit --only` on a shared file carries a co-editor's in-flight work under
my `Atom:` — H19, H66, and the same call S26 made about `q3.py`. Filed as **S37**
with the function body ready to lift from here.

## Controls (5, all fire)

| control | what would have made it not fire |
|---|---|
| `C_replay_proof_is_honest` | the replay differing by one byte from a fresh `prove_completeness(root, q2)` — then this is a tamper, which S36 already covered |
| `C_replay_actually_omits` | any job where the deeper prefix selects the same key set. A path-compressed trie produces exactly that whenever the node does not branch, so it is a live risk, not a formality (A29) |
| `C_fix_does_not_reject_honest` | any honest proof rejected under the fix. The null is a verifier that rejects everything and scores 100% on the attack |
| `C_fix_keeps_the_three_published_tampers` | omit / add / alter accepted under the fix — the q-binding replacing the fold instead of joining it |
| `C_sibling_verifiers_are_not_exposed` | `verify_membership` or `verify_non_membership` accepting a proof issued for a different key. **Both reject, 0/20 and 0/20**, which is what puts the defect in the missing check rather than in the commitment |

## One defect of my own, caught by a control, in this file

`C_sibling_verifiers_are_not_exposed` **refused the first run** —
`absence_replayed: 20/20` — and I nearly had a second finding. It was not one.
The probe built both absent keys by flipping the **first** byte of a real key, so
both diverged **at the root**, the authentication path was empty, and one honest
absence proof covered them both *correctly*. The probe had not reached its
target (A29). It now flips the **last** byte and asserts
`absence_paths_differ == absence_n`, so the two keys are required to diverge at
different nodes before the replay means anything.

`certify` refusing was the difference between a finding and a fabricated second
finding — in the same file whose whole subject is a check that was never reached.

## Scope

- **One commitment, one job class.** A prefix range query over a radix trie. The
  q-binding argument is about this node format; nothing here says a different
  authenticated structure has or lacks the same hole.
- **The replay needs a deeper node that exists.** Here 37/37 had one; a query
  already sitting on a leaf has nothing to hide behind, and that count is
  reported (`jobs_with_no_deeper_node`), not assumed to be zero.
- **The fix is measured, not proved.** 37 jobs on one key set. It closes the
  shape demonstrated here and the three S36 published; it is not a proof that no
  fifth shape exists — which is the sentence S36 should have written and did not.
