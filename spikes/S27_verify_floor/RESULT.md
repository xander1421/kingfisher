# S27 — the completeness verifier has ZERO implementation slack; the constant is the commitment format

**AGENT-1, 2026-08-17.** `python3 verify_floor.py` · `verify_floor.json` ·
`certify ok=true`, 3 controls all fire, **falsifier did NOT fire**.

S20 left an open item and wrote it down rather than running it: *"a verifier
that streamed the answer set into an incremental fold would hash the same key
bytes but might allocate fewer node descriptors; nothing here says 2–4× is a
lower bound."* §12.12 says that shape — a falsifier written and marked not yet
run — is how every surviving error in this repo got through.

## The falsifier, stated before the run

> If the verifier hashes materially more than the sum of the answer subtrie's
> node descriptors — more than the **root's own definition** requires — the
> constant is implementation slack and can be reduced. If it equals that sum, no
> verifier can do better without changing the commitment format, and
> "implementation-shaped" is refuted.

Threshold fixed in the file at 1%. **Measured slack: 0.000% on all three key
sets.** The verifier hashes exactly what recomputing the root requires, to the
byte. **S20's open item is answered in the negative: the 2–4× is the format, not
the implementation.**

## Where every hashed byte goes

Query prefix length is chosen by a rule — the length whose mean answer set is
nearest 10 — not by hand, after `C_answer_sets_are_non_trivial` refused a first
run whose hand-picked constant gave 1.6 answers on the interned set.

| key set | L | answers | verifier hashes | model | slack | content | framing | digests | path fold |
|---|---|---|---|---|---|---|---|---|---|
| atoms_original | 7 | 134.0 | 22,900.2 | 22,900.2 | **+0.000%** | **62.40%** | 5.94% | 27.04% | 4.62% |
| atoms_interned | 8 | 128.3 | 12,834.9 | 12,834.9 | **+0.000%** | 43.29% | 8.80% | **40.03%** | 7.88% |
| triples | 8 | 96.5 | 6,011.1 | 6,011.1 | **+0.000%** | **0.17%** | 13.28% | **60.23%** | 26.32% |

(shares are of the modelled total and are recomputed from `verify_floor.json`,
not read off the run's summary line — the first draft of this table quoted
framing and path-fold shares that were neither.)

**The spread across key sets is the digest share, and the digest share is set by
key length.** On original atoms — long keys, unbranched runs — 62% of the
verifier's work is the answer keys' own bytes, which any scheme must read. On
12-byte triples the keys are 0.17% of it and **60% is 32-byte child digests**:
the verifier is hashing the commitment, not the data. That is the same mechanism
S77 found on the prover side, arriving on the verifier side: **short keys
concentrate branching, and branching is what a Merkle structure charges for.**

So the levers are the **digest width** and the **fan-out**, both properties of
the commitment format. A 16-byte digest would remove ~30% of the verifier's work
on triples and ~13% on original atoms; nothing a verifier author writes can
remove any of it.

## Controls (3, all fire)

| control | what would have made it not fire |
|---|---|
| `C_model_is_not_the_measurement` | the model is a **separate traversal that hashes nothing**, so it can disagree with the counting hashlib — and it did, until the path-fold term was added. If model and measurement shared code, 0.000% would be a tautology |
| `C_answer_sets_are_non_trivial` | any set's mean answer below 2 keys, where the subtrie is a single node and the decomposition is trivially content-only. **It refused the first run as VOID at 1.6 answers**, which is what produced the rule-based prefix choice |
| `C_shares_sum_to_the_whole` | content + framing + digests + path fold not accounting for every modelled byte — a fourth category would mean the decomposition is not the `node_hash` definition it claims to be |

## The defect this run made, and it is the interesting half

The first model **omitted the authentication-path fold entirely** and reported
**+35.7% to +1,899.5% "implementation slack"**. There was none: `fold`
recomputes each step as `node_hash(prefix, term, sorted(pairs + [(b, h)]))`, so
every path position is hashed too — and with **one more edge than `steps_bytes`
counts**, because the taken child is in the hashed input while not being
transmitted.

That is `S79-ATTACK`'s finding wearing the other hat. There, the *model* charged
a term the *measurement* excluded; here the *measurement* included a term the
*model* excluded. Both directions look like a real effect with a plausible size,
and both are settled the same way — by making the model's traversal independent
of the measured code, so the two can disagree.

Had the falsifier's threshold been 50% instead of 1%, `atoms_original`'s +35.7%
would have passed as "no slack" and the missing term would never have surfaced.
**A tight threshold on a quantity that should be exactly zero is what turned a
wrong model into a visible failure.**

## Scope

- **Three key sets, one query shape** (prefix range queries at one length per
  set). Membership and absence verifiers fold a path without rebuilding
  anything; their floor is the path alone and is not measured here.
- **The floor is the floor of THIS commitment.** It says no verifier can hash
  less *for this node format*; it says nothing about a different authenticated
  structure (a vector commitment, a different arity, a shorter digest).
- **Hashed bytes, not seconds** — `quiet.sh` refuses on this host, and the same
  instrument and pinned `trie_witness` as S20 and S24, so the three compare.
