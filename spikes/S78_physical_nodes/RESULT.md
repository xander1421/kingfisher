# S78 — S77's caveat, run in the cycle after it was written. S77 survives with 3.0× margin.

**Verdict: a physical-node commitment reorders the key sets only if it costs more
than 6.10 B of framing per physical node on the path. Minimal framing is a
segment length, 1–2 B, so S77's inversion survives with a 3.0× margin. The
question is decidable from `merkleization.rs` itself: its node hash is
`(value, [(path, child_hash)])`, so a single-child physical node carries no
sibling digest either — the same reason the logical view charges nothing for an
unbranched run. 4 controls, all fire.**

**GRADE D, stated in the code and in the verdict line, not in a footnote.**
Arithmetic over inputs measured in S77, plus one **E** input read from `pathmap`
source. It is published as a **threshold and a source reading**, never as a
measured byte count. The entire S75→S76→S77 arc is what happens when a D is
written in a verdict line that reads like a B, and this page is the first in the
chain to say so before saying anything else.

Artefacts: `threshold.py`, `threshold.json`, `provenance.json`
(`kfcheck.certify ok=true`). Run: `python3 threshold.py`.

## The falsifier, stated before the run

> If a commitment over `pathmap`'s **physical** nodes reorders the three key
> sets, S77's inversion is specific to the logical byte view and its retraction
> of S75 and S76 needs qualifying.

It does not reorder them, above a framing cost three times larger than any
framing anyone would build.

## Why this was a real risk and not a formality

S77 counts siblings at **logical** byte positions. `pathmap`'s `merkleize`
hashes **physical** nodes, and the atom trie has **83,210** of them against
**3,160** for triples. Charged per physical node, that 26× would swamp the 785 B
sibling gap and flip the ordering straight back — which would have made S77 a
statement about a view nobody deploys.

## What the source settles

`elders/PathMap/src/merkleization.rs:53`, its own comment, with the loop beneath
implementing exactly it:

```
// hash = (value, [(path, child_hash)])
```

To recompute a physical node's hash a verifier needs the node's value and, for
**every** child, that child's path segment and its hash. For k children that is
k−1 sibling digests. **For a single-child node it is zero**: the one path segment
is key bytes the verifier already holds, and the one child hash is what it just
computed from below. So a long unbranched run costs a physical commitment no
digests, for the same reason it costs the logical one none.

Read as a **property**, not a name (A30): the control requires the composition
comment, the per-child iteration, and both `path.hash` and `child_hash.hash`
inside it. A grep for "hash" in a file called `merkleization.rs` cannot tell a
commitment from a dedup key — that is the exact mistake S75 made, and it cost a
control there.

## The threshold

| | siblings | auth bytes | physical nodes on path |
|---|---|---|---|
| atoms, original | 45.7 | 1,461 | **139.1** |
| atoms, interned | 56.4 | 1,803 | 61.3 |
| triples | 70.2 | 2,246 | **10.3** |

The deciding pair is the set with the fewest sibling digests and the most
physical nodes (atoms) against its opposite (triples): a **785 B** sibling gap
over a **128.8** physical-node gap.

**Flip threshold = 785 / 128.8 = 6.10 B of framing per physical node.**

A verifier walking physical nodes needs to know where segment boundaries fall,
which the key bytes do not say. That is a length field: **1–2 B**. The ordering
therefore holds with a **3.0×** margin, and it would take a framing scheme
carrying six bytes of metadata per node to overturn it.

## Controls — four, each naming the input that makes it fail

| control | fails if |
|---|---|
| **`C_single_child_physical_node_carries_no_digest`** | the composition comment is absent, or the loop does not hash a `(path, child_hash)` pair per child — i.e. the node hash is not built from its children's digests one at a time. `merkleization.rs` is equally free to hash a fixed child array or a 256-slot map, either of which charges per node and flips this |
| `C_inputs_are_the_committed_ones` | any value is missing or non-numeric in S77's `measure.json`. This spike computes rather than measures, so retyping a number out of a page would be D6 hole H5 performed on purpose |
| **`C_threshold_is_decision_relevant`** | the threshold falls outside 1–32 B per node. **Below 1 B**, even a length field flips the ordering and S77 needs qualifying; **above 32 B**, a full digest per node would not flip it and the caveat was never a risk. Both are real outcomes, which is what lets this control fail |
| **`C_inversion_survives_minimal_framing`** | the threshold is at or below 2 B per physical node. The atom trie's 139.1 nodes per path against the triples' 10.3 is a 13× gap with ample room to overturn 785 B |

**All four fire.**

## What this does not settle

- **No physical commitment exists to measure.** `pathmap` depends on no
  cryptographic hash at all (S75), so F is a property of a scheme nobody has
  built. The threshold is the durable half of this result; the "1–2 B" is an
  engineering judgement about the cheapest correct scheme, not a measurement.
- **Dedup is not modelled.** `merkleize` replaces identical subtries with shared
  pointers (1,565 of 3,160 nodes reused on triples, 61 of 83,210 on atoms). A
  commitment over the resulting DAG could be cheaper than over the tree, and it
  would be cheaper for the set that already wins.
- **Membership only, one corpus, `pathmap` 0.3.0** — carried from S77 unchanged.

## Why this exists at all

S77's caveats named this as "the obvious next probe". Its predecessor's caveat —
*"no proof was actually generated on `pathmap`"* — was named the same way, in
S75, carried into S76 verbatim as "the binding one", and left unrun for three
cycles while two spikes published numbers that depended on it. **A caveat naming
an unmeasured quantity is an unrun falsifier holding up every number on the
page.** This one was run in the next cycle, and it cost about twenty minutes.
