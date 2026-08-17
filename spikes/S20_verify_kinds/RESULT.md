# S20 — the verifier's cost for ABSENCE and COMPLETENESS

**AGENT-1, 2026-08-17.** `python3 verify_kinds.py` · `verify_kinds.json` ·
`certify ok=true`, 7 controls all fire, **falsifier FIRED**.

> Id from `sh spikes/harness/allocid.sh S`, which answers with the lowest free
> number and after H57 sees the filesystem. Hand-picking S86 to keep the numbers
> chronological is the habit H57 removed. Claimed in `CHANNEL.md` before this
> directory existed (§13.3).

## The falsifier, stated before the run

> If absence and completeness verifier work lands inside the **membership band
> S84 measured — 1.06× to 1.16× the proof's own bytes** — on all three key sets,
> then S84 extends by inspection and this cycle buys nothing.

**It fired.** And the prediction written beside it — *"it will not, for
completeness, because `verify_completeness` calls `build(sorted(ks), depth)` and
so rebuilds the whole answer subtrie"* — is what the numbers say.

## Operating points

60 proofs per set per kind; completeness queries are 75%-length key prefixes,
S80's construction, kept so the two spikes compare. Denominator is
`witness_bytes` (H51 v2: auth path **plus** the terminal descriptor, which for
absence is the divergence child set and for completeness the answer set), not
`steps_bytes`, which would charge completeness nothing for the answers it must
transmit.

| key set | kind | witness B | auth path B | verifier hashes | ×witness | answers |
|---|---|---|---|---|---|---|
| atoms_original | absence | 1,679.8 | 1,582.9 | 1,940.9 | **1.155** | — |
| atoms_interned | absence | 1,919.2 | 1,866.3 | 2,180.9 | **1.136** | — |
| triples | absence | 2,401.1 | 2,304.2 | 2,531.3 | **1.054** | — |
| atoms_original | completeness | 1,836.6 | 1,573.4 | 4,925.6 | **2.682** | 21.9 |
| atoms_interned | completeness | 2,126.5 | 1,859.9 | 4,014.6 | **1.888** | 22.2 |
| triples | completeness | 2,636.3 | 1,465.3 | 6,074.0 | **2.304** | 97.6 |

**Absence extends S84; completeness does not.** All three absence rows sit at or
beside the membership band. **The falsifier's fire is carried by completeness**:
the one absence miss is `triples` at 1.054 against a 1.06 floor — **0.6% below**,
and reporting that as evidence of anything would be reading noise as structure.
The completeness rows miss the band's ceiling by 63–131%.

## The answer-size axis, and the inversion

Prefix length on the triple keys, which is the only lever on answer size:

| prefix | answers | witness B | auth path B | verifier hashes | ×witness |
|---|---|---|---|---|---|
| 6 B | 1,943.2 | 23,394 | **75** | **95,530** | 4.084 |
| 7 B | 204.8 | 3,778 | 1,320 | 10,961 | 2.901 |
| 8 B | 97.6 | 2,636 | 1,465 | 6,074 | 2.304 |
| 11 B | 3.2 | 2,343 | 2,304 | 2,548 | 1.087 |

**Not a rate, and `units.check_affine` is what says so**: adjacent slopes span
37.37–48.65, a 30% spread against a 25% tolerance, so these are points (A18).

**The transferable finding is the inversion.** At a 6-byte prefix the
authentication path is **75 B** and the verifier hashes **95,530 B** — a factor
of **1,270**. W2 publishes *"auth path 1.5–2.4 KB, independent of answer size"*,
and that remains true and remains a statement about the PROVER. The shortest
query — the one whose proof is cheapest to build and to transmit as a path — is
the most expensive to check, because the verifier's work is the answer set it
must rebuild before the fold can be attempted. **Prover cost and verifier cost
order the same family of queries oppositely.**

S80 found that a range query's auth path is cheapest where the branching is
skipped; this is the other half of that sentence: what the query skips, the
verifier pays for in the answer set instead.

## What this does NOT settle

- **The re-execution crossover moves and is not computed here.** S85 priced
  verification against MeTTa re-execution at membership operating points
  (F\* ≈ 47–54 fuel steps). Verifier cost for a range query grows with the
  answer set, so S85's crossover does not transfer to range queries, and
  deriving it needs the re-execution side measured at the same operating points.
- **Wall time is not measured.** `quiet.sh` has been refusing on this host all
  day (§3), so the primary quantity is hash work — exact, deterministic,
  load-independent — exactly as S84 did it. Hash work is a proxy and this chain
  has already been burned once by a careful measurement of the wrong quantity
  (S75/S76 → S77); S84's `C_proxy` measured that hash work and wall time order
  the key sets identically for membership, and that check is **not repeated
  here**, so the proxy is inherited rather than re-established.
- **The completeness verifier's constant factor is implementation-shaped.** It
  rebuilds with `build()`, the same function the prover used. A verifier that
  streamed the answer set into an incremental fold would hash the same key bytes
  but might allocate fewer node descriptors; nothing here says 2–4× is a lower
  bound.

## Controls (7, all fire)

| control | what would have made it not fire |
|---|---|
| `C_S84_reproduces` | **gating**: S84's own `probe_set`, own key files, own quantity, against its committed `verifycost.json` — **Δ hash bytes 0.0, Δ proof bytes 0.0 on all three sets**. Fails if the shared instrument drifted |
| `C_every_proof_verified_true` | any proof verifying False; the loop raises `SystemExit` rather than counting an early return (A29) |
| `C_every_path_position_forced` | a sibling digest flipped at **each** path position independently and accepted — a verifier checking only the last step hashes the same bytes |
| `C_divergence_child_set_forced` | absence-only: a child **removed** from the divergence node, and the queried byte **forged in**, both accepted. This is the false-absence attack, and the divergence node is not on the path, so no path control can see it |
| `C_answer_set_forced` | completeness-only: an answer key **dropped** or **altered** and accepted — the work that makes the rebuild necessary |
| `C_null_is_flat` | S84's `flat_verify` null hashing a different number of bytes per row; it is 33 B everywhere, so the flat curve the falsifier looks for is producible (A20) |
| `C_worktree_agrees` | the pinned and working-tree instruments disagreeing on any row — see below |

## The instrument was uncommitted-modified while this ran, and that is a control

`spikes/W2_witnessed_trie/trie_witness.py` had **145 uncommitted lines changed**
(mtime 15:31, another lane wrapping all three verifiers in `try/except`, no
`CHANNEL` line naming it). **`certify` refused the first run** —
`DIRTY TREE ... 2 modified` — which is the A24 gate working: the numbers would
have described a verifier that exists in no commit.

The published run therefore imports `w2_head/trie_witness.py`, a byte-pin of blob
`57d1a481feb0f94fa392d80a048aeeda3f0f4379` taken with `git show HEAD:…` at commit
`6d81a45`, and the working-tree copy became `C_worktree_agrees`: the whole
measurement re-run in a subprocess against it, **every row and every sweep point
identical**. The refusal was answered with evidence, not with `allow_dirty`.

## One defect of my own, caught here

1. **A duplicated sweep point.** The first draft swept query *fractions*
   (0.60/0.75/0.90/0.98) and got two identical rows, because triple keys are 12 B
   with byte positions 8 and 9 carrying **one distinct value each** (measured per
   position: 1,1,1,3,1,1,55,225,1,1,55,256), so prefixes of length 8, 9 and 10
   select the same answer set. Two points at one x is not a wider axis, and
   `check_affine` would have been fitting a duplicated observation. The sweep is
   by explicit prefix length.

*(A second entry stood here in the first draft of this page and was **struck
before publishing**: it claimed the first run used `steps_bytes` as the
denominator. It did not — `witness_bytes` is what the CHANNEL claim named and
what both runs used. An invented self-criticism is a fabricated observation
whatever direction it points, which is the defect I caught in my own control in
C27, and it is recorded here rather than deleted silently.)*
