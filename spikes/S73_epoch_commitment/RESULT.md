# S73 — canonical SPACE state at an epoch boundary, and a delta a verifier computes rather than receives

**Verdict: GREEN for the space half, and it does NOT touch the half S68 blocked.
66 epochs over the real corpus chain and verify; a verifier folds `root_N`
forward to `root_N+1` from the additions alone, at 1,150 B per added atom
batched / 1,770 B isolated. The unordered null (XOR-of-hashes) gives the same
O(k) delta and is then forged in one line, which is why the ordered structure is
paid for. 11 controls, all fire.**

Artefacts: `epoch.py` (stdlib only, seed 20260817, trie primitives imported from
W2 rather than reimplemented), `epoch.json`, `provenance.json` (`ok: true`).
Corpus: `../S57_hyperon_corpus/corpus/*.metta` — 67 real MeTTa programs, the same
corpus M1's admission gate and the 65-CID quorum chain run on.
Run: `python3 epoch.py`.

## The two halves, and which one this is

"Canonical state serialization at an epoch boundary" is two problems in one name.
S68 already settled which is reachable:

| half | status |
|---|---|
| **interpreter** state (the plan stack) | **RED.** Four contaminants, one unidentified, ~50% divergence after masking three. Blocked upstream on hyperon Issue 3. |
| **space** state (the atom set) | reachable. This spike. |

So this **does not unblock optimistic execution or bisection** — those need the
interpreter half and stay gated on S68. It unblocks the other dependant:
**verifiable adaptation across epochs**, where a learner adds atoms and a verifier
checks the transition without holding the space.

## The standard S65 set by failing

S65 committed to `current_results()` — emitted output, not state — and **100% of
its leaf content was `"()\n"` repeated**, so the root was forgeable in six lines
of Python without running hyperon. The requirement that follows is that a state
commitment must bind **content**, not shape. `C_content_not_shape` is that test:
two spaces of **exactly 300 atoms** differing in one atom give
`8bf18e76…` vs `d3d8473e…`.

## Measured — 67 programs, 66 epochs, 1,247 atoms

```
corpus     67 programs, 5,408 expression nodes, 1,246 distinct top-level atoms
           = 132,830 B encoded
final      1,247 atoms / 1,783 trie nodes / 66 epochs, chain verified
trie root  daf1d148be40a6a5784e70c13daf30b02f579a96e516be04792637903a1298eb
```

| epoch (first / last) | added | atoms | nodes | rehashed | frac | proof B/add | verified |
|---|---|---|---|---|---|---|---|
| `…das__animals.metta` | 57 | 58 | 72 | 72 | 1.000 | 321 | Y |
| `…das__test.metta` | 8 | 66 | 82 | 12 | 0.146 | 303 | Y |
| … 62 more … | | | | | | | Y |
| `…test_load.metta` | 7 | 1,238 | 1,770 | 14 | 0.008 | 570 | Y |
| `repl.default.metta` | 9 | 1,247 | 1,783 | 17 | 0.010 | 1,150 | Y |

Recomputed-node fraction: **mean 0.076, min 0.0075**, max 1.000 (the genesis
epoch, where everything is new). Rehashed nodes **per added atom**: 1.26 first
epoch, 1.89 last, mean 3.27, max 13.

**The fraction column is the wrong headline and is not the claim.** It falls
because the denominator grows. The claim is the per-add figure: an epoch costs
**~1–2 recomputed nodes per added atom**, i.e. `O(added)`, not `O(space)` — which
is structural sharing doing what it is supposed to do, and `C_sharing_real` is
what would notice if it stopped.

## Single-insert cost against space size — matched hold-out

| space atoms | trie nodes | proof B mean | max | new digests/insert |
|---|---|---|---|---|
| 100 | 145 | 781 | 1,100 | 6.72 |
| 300 | 442 | 1,167 | 1,580 | 8.48 |
| 1,000 | 1,423 | 1,612 | 2,240 | 9.28 |
| 1,222 | 1,746 | **1,770** | **2,603** | 9.48 |

**12× the space costs 2.27× the proof.** The same 25 held-out atoms are inserted
into every space, so only the space size varies.

Two figures, both real, and they are not interchangeable:

- **1,150 B/add** — additions arriving batched from one program. They share
  authenticated paths, so the cost amortises.
- **1,770 B/add** — isolated single inserts spread across the key space. This is
  the pessimistic per-atom cost and the one to quote for a stream of unrelated
  additions.

## The null is not a straw man, and it is broken in one line

XOR-of-hashes is the unordered commitment. It **passes** the cheap test — an
epoch delta is `root_N ⊕ H(added)`, O(k) and 32 bytes, better than the trie on
both axes. So it is a real null: it can contain the effect.

`C_xor_forgeable` breaks it constructively. `a ⊕ a = 0`, so declaring any atom
**twice** returns the digest to its previous value while the space has changed:

```
xor  base 2aaa5b20ffa11a28   forged 2aaa5b20ffa11a28   <- identical
trie base 8bf18e764ea5abd6   forged 2e9cc9974cb0ddb5   <- differs
```

`C_xor_cannot_prove_absence` is its second failure, as a measurement rather than
an appeal to intuition: the XOR digest is 32 bytes and carries no path, so an
absence proof has nothing to be made of. The trie's absence proof for the same
query is **257 B** and verifies. (A proper multiset hash — MSet-XOR with per-element
nonces, or a curve-based accumulator — fixes the forgery but still cannot prove
absence, because absence needs order. That is W2's result, restated here.)

## The root commits to state, NOT to history

`C_root_is_state_not_history` groups the same 1,247 atoms into two different epoch
sequences (400/500/347 and 150/950/147) and both reach `daf1d148…`, the chain
root. This is correct for a state commitment and is stated as a control rather
than a caveat because it is the property most likely to be misread: **the root
does not bind the path taken to it.** Binding history needs the chain of
`(root, delta)` pairs hashed together. **Not built here.** A design that treats
the final root as evidence of a particular epoch sequence would accept a forged
one.

## Controls — eleven, each naming the input that makes it fail

| control | fails if |
|---|---|
| `C_reader_roundtrip` | any atom fails `decode(encode(a))`, or a form was dropped — 50 of 67 files carry `;` comments and one nests `\"` inside a string; a reader bug commits every digest to the wrong atom set |
| **`C_incremental_equals_full`** | a computed root differs from the rebuild in any epoch — a wrong `apply_insert` branch shows up here and nowhere else |
| `C_apply_insert_cases` | case 1 or 4 is never reached, or cases 2/3 fire while the encoding is prefix-free, or `prefix_free` goes False |
| `C_wrong_prior_root` | a delta verifies against a prior root it was not built on — epochs would not chain |
| **`C_smuggled_extra_atom`** | an undeclared atom leaves the computed root unchanged — the delta would not bound the additions it names |
| **`C_content_not_shape`** | two equal-size spaces with different atoms share a root — this is S65 |
| `C_insertion_order_invariance` | 20 shuffles of one atom set give more than one root — replicas that learned the same facts in different orders would never agree |
| `C_sharing_real` | mean recomputed fraction reaches 0.5 — sharing would buy nothing |
| **`C_xor_forgeable`** | no equal-digest different-space can be built — then XOR suffices and the trie is unjustified |
| `C_xor_cannot_prove_absence` | the trie absence proof is not larger than 32 B — it would carry no structure the digest lacks |
| `C_root_is_state_not_history` | two epoch groupings reach different roots — then it is not a state commitment |

**All eleven fire.** Observations in `provenance.json`, `ok: true`.

## Three errors this spike made, caught by its own instruments

1. **`Node` passed where a root digest was expected.** Every epoch's fold silently
   returned `None`, so `chain_verified` was False on the first run.
   `C_incremental_equals_full` is the only thing that saw it — the per-epoch table
   looked plausible. This is why the verifier takes `root.h` and never a node.
2. **The scaling arm drew fresh probe atoms per row**, so rows differed in both
   space size and which atoms were inserted. It produced non-monotonic proof
   bytes (433 / 279 / 952) — a confound reported as a rate (A18).
3. **The first fix introduced a different artifact.** Probe = lexicographic tail,
   base = lexicographic prefix, so every probe diverged at the root and the cost
   came out **293 B flat across a 10× space range**. Flatness read as a
   structural result; it was the cost of inserting *outside* the occupied key
   range. Shuffling before splitting fixed it, and the real figure is 6× larger.

## Caveats
- **1,247 atoms is a small space.** Real atomspaces are orders larger. The growth
  is measured over 12×, not over 1,000×, and the row-to-row trend is what carries,
  not the absolute.
- **`nodes_recomputed` is a set difference of digests**, so it measures new
  *distinct* digests — DAG/storage growth. Structural sharing means an addition
  that recreates an existing subtrie adds none, so this is a **lower bound** on
  hashing work, not a count of hash calls.
- **Only top-level atoms are keys.** 5,408 expression nodes collapse to 1,246
  distinct top-level atoms. Committing interior subexpressions would be a
  different structure, would break prefix-freedom, and would make `apply_insert`
  cases 2 and 3 live.
- **Cases 2 and 3 of `apply_insert` are unreachable and therefore untested.**
  `encode` is self-delimiting, so no atom's encoding is a proper prefix of
  another's — checked, not assumed (`encoding_prefix_free: true`). They are kept
  because a trie insert without them is wrong in general; they are named here
  because nothing exercises them.
- **No timings.** Every figure is a count or a digest, both load-insensitive, so
  the measurement is valid while `quiet.sh` refuses (loadavg 3.61 > 3.50, 11
  containers, another project's).
- **This is a Python trie, not `pathmap`.** Same shape, different constants.
- **No engine ran.** The atom set is parsed from corpus text, not read out of a
  live hyperon space. What is committed is the corpus's atoms, which is the right
  input for the encoding and cost questions and the wrong one for "does hyperon's
  space actually serialise to this" — that needs the MORK/pathmap boundary and is
  not claimed.
