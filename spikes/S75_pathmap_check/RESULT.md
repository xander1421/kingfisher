# S75 — W2 and S74's declared falsifier, run against MORK's real `pathmap`. It fires.

**Verdict: the falsifier FIRES on variable-length atom keys (18.4×) and does NOT
fire on fixed-length triple keys (2.4×). So W2's numbers survive with a bounded
constant, and S73/S74's proof sizes DO NOT transfer to real `pathmap` — they would
be roughly 18× worse. Second, unexpected finding: `pathmap`'s own
`merkleization.rs` is a deduplication pass keyed by a 128-bit non-cryptographic
hash, with no proof and no verifier. It cannot be used as a commitment. 7 controls,
all fire.**

Artefacts: `compare.py` (seed 20260817), `pmprobe/src/main.rs` (Rust, path
dependency on `elders/PathMap` — untrusted clone built and tested **in place** per
§10, never vendored or modified), `compare.json`, `probe_out.txt`,
`provenance.json` (`ok: true`, `kfcheck.certify`, falsifier declared).
`pathmap` 0.3.0, `rustc 1.96.1`. Run: `python3 compare.py`.

## The falsifier, as W2 and S74 both wrote it

> "Build the same three proofs on MORK `pathmap` and show the authentication path
> departs from 1.5–3.3 KB by more than the branching factor explains."

## What actually decides proof length

Every node on the path to a key is **one authenticated step** — its sibling
digests have to travel with the proof. So the quantity to compare is **node
depth**, not node count and not byte depth.

`pathmap` stores a **bounded byte span per node** (`line_list_node`). W2's Python
trie compresses an entire unbranched run into one node's `prefix`, however long.
For 12-byte keys that barely matters. For 1,155-byte keys it decides the result.

## Measured — identical key sets, both implementations

Threshold for "not a constant factor" was fixed at **10×** *before* the numbers
were read, because a threshold chosen afterwards is fitted to the answer it is
meant to judge.

| key set | keys | key B max | py mean depth | **pathmap mean depth** | ratio | py nodes | pathmap nodes |
|---|---|---|---|---|---|---|---|
| **atoms** (S73/S74) | 1,246 | 1,155 | 7.6 | **139.1** | **18.4×** | 1,852 | **83,210** |
| **triples** (W2) | 4,096 | 12 | 4.2 | **10.3** | **2.4×** | 5,181 | 3,160 |

Max node depth tells the same story harder: atoms **15 → 1,148** (77×), triples
**5 → 11**.

Note the node counts move in **opposite directions**. For fixed-length keys
`pathmap` is *more* compact than my trie (3,160 vs 5,181) — its list nodes hold
several bytes where mine spends a node per branch. For long keys it is 45× larger,
because an unbranched 1,155-byte run becomes ~1,148 nodes instead of one.

## What this costs each spike

The **span bytes** on a path are the same either way — they are the key. What
scales with node count is the **per-node authentication overhead**: one sibling
group per node.

| spike | key kind | published auth overhead | on real `pathmap` |
|---|---|---|---|
| **W2** | 12-byte triples | 1.5–2.4 KB | **×2.4 — roughly 3.6–5.8 KB.** A constant factor, as the caveat said |
| **S73** | atom encodings | 1,770 B per isolated insert | **×18.4 — roughly 33 KB.** Not a constant factor |
| **S74** | atom encodings | 32 B per epoch | **unchanged.** The chain hashes roots and delta roots; it never walks a path |

**S74 is untouched** because a chain step commits to digests, not to a traversal.
That is worth stating: the cheapest of the three constructions is also the only one
this finding does not scratch.

**W2's caveat was right and S73's was too weak.** Both said "same shape, different
constants". For W2 that holds. For S73 an 18.4× is not a constant, and the caveat
should have said the encoding's key length was the load-bearing variable.

## The fix is in the encoding, not in the proof system

S73's `encode` produces one long key per top-level atom (up to 1,155 B).
`pathmap` splits that into ~1,148 nodes. Nothing about the proof scheme is wrong —
the **key layout** is. An encoding that interns symbols to fixed-width ids, the way
FB15k-237 triples already are, would put atom keys in the 12-byte regime where the
ratio is 2.4×. Untested, and it is the obvious next move rather than a claim.

## `pathmap` has a `merkleize` and it is not a commitment

This was not what I went looking for. `elders/PathMap/src/merkleization.rs`:

- the digest is **`u128`** from **`gxhash`**, which `pathmap`'s own `Cargo.toml`
  declares is "for dag_serialization, merkleization, and caching catamorphism" —
  and which is swapped for `xxhash` under miri. **Neither is cryptographic.**
- `MerkleizeResult` reports `hash, reused, cloned, replaced`. The memo table
  replaces identical subtries with shared pointers: **the hash is a dedup key.**
- **no proof generation and no verifier exist.** Checked by dependency, not by
  name: the crate depends on **no** cryptographic hash at all.

It is deterministic (`same_hash=true` on a second pass) and the dedup is real —
**1,565 of 3,160 nodes reused** on the triple corpus, which is independent support
for the structural sharing S73's cost model leans on.

But **anyone assuming "the substrate already has merkleization" is assuming the
wrong thing.** W2 did not reimplement something that existed; it built the thing
that does not exist there.

## Controls — seven, each naming the input that makes it fail

| control | fails if |
|---|---|
| `C_identical_key_sets` | `pathmap` and the Python trie disagree on how many keys they loaded — the comparison would be between different inputs |
| `C_probe_reads_pathmap_correctly` *(negative — bounds resolution)* | `pathmap`'s **own** 8-path test set does not give 6 nodes through this probe; then the probe misreads the library and the verdict is **VOID**, not negative |
| **`C_falsifier_fires_on_atoms`** | the atom depth ratio is under 10× — the falsifier would not fire and S73/S74's sizes would transfer |
| **`C_falsifier_does_not_fire_on_triples`** | fixed-length keys **also** exceed the threshold — then the cause is not key length and the mechanism claimed here is wrong |
| `C_merkleize_is_deterministic` | the merkleize hash moves between two runs on one trie — it would not be content-derived |
| **`C_merkleize_is_dedup_not_commitment`** | `pathmap` depends on any cryptographic hash — then it can emit a real commitment and W2 may have reimplemented something that existed |
| `C_dedup_actually_reuses` | merkleize reuses no nodes on either corpus — the sharing S73 leans on would be absent here |

**All seven fire.** The pair of falsifier controls is deliberate (A16, pair the
arms): a single "it fires" result would be about `pathmap` in general, and only the
matched negative on triple keys makes it about **key length**.

## The control that was wrong first, and why it matters

`C_merkleize_is_dedup_not_commitment` originally grepped for
`fn (prove|verify|proof|witness)`. It found **14 hits and did not fire** — and
every hit is a Rust **borrow witness** (`fn witness<'w>(&self) -> Self::WitnessT`,
several returning `()`), a lifetime token with no relation to a cryptographic
witness.

That is `CLAUDE.md`'s *"correct numbers, wrong attribution"* in miniature: **the
control matched a word, not a concept.** Replaced with a test that cannot collide
on a name — a crate depending on no cryptographic hash cannot emit a cryptographic
commitment, whatever its functions are called.

## Caveats
- **Depth is a proxy for proof size, not a measurement of it.** No proof was
  actually generated on `pathmap`; I measured the node depth that a proof would
  have to traverse. The ×18.4 is therefore a **scaling correction, not a
  re-measured byte count**, and pinning S73's real cost needs proofs implemented
  against `pathmap`'s zipper API. Stated as the falsifier for this spike.
- **`total_nodes` counts `pathmap`'s internal node objects** (`dense_byte_node`,
  `line_list_node`, bridge nodes), which are not one-to-one with my `Node`. The
  depth comparison is the meaningful one; the node-count column is context.
- **`counters` is a non-default feature.** Enabling it could in principle change
  node layout; not checked.
- **One corpus each, one `pathmap` version (0.3.0, pre-release, "expect API
  churn").**
- **No timings.** Counts and digests only, so valid while `quiet.sh` refuses.
- `pmprobe/target/` is gitignored — the source and the exact `rustc` version are
  committed, the 1 MB binary is not (`CLAUDE.md` §2.2).

## Changelog

**2026-08-17, AGENT-1 — one claim above is corrected by S76, and no number is.**
Nothing measured here moved: S76 replayed this spike's own encoding through this
spike's own binary in a later session and got 139.05 mean depth, 83,210 nodes,
1,246 keys — byte-identical — and the triples arm likewise at 10.26 / 3,160.

What is corrected is the sentence *"The fix is in the encoding, not in the proof
system"*, and specifically its expectation that interning "would put atom keys in
the 12-byte regime where the ratio is 2.4×". Measured: interning to 4-byte ids
gives **7.86×** and to 2-byte ids **5.50×** — under the 10× bar this spike set,
so **the mechanism claim here survives its test**, but not into W2's regime.
An interned atom key still averages 36.6 B because the `E` + 2-byte arity framing
costs 3 B per expression node and interning shortens only the symbol term.

The mechanism is also stated more precisely there than here: `pathmap` spends
about **one node per key BYTE** (0.86–1.30 across five key sets), while W2's trie
depth is the atom's **structure** and does not move at all across three id widths
(7.8 / 7.8 / 7.8). The ratio is bytes-per-structural-node. "Key length is the
load-bearing variable" is right; that is the form of it that predicts a number
rather than describing one.

Consequence for the figure in *What this costs each spike*: S73's isolated insert
proof is ~33 KB here, **~14 KB interned at id4 and ~9.9 KB at id2**, against
1,770 B published. Not restored. `spikes/S76_interned_keys/`.
