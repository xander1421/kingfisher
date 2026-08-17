# S36 — witnessed verification as a JOB, on the case replication cannot reach

**AGENT-1, 2026-08-17.** `python3 witnessed_job.py` · `witnessed_job.json` ·
`certify ok=true`, 4 controls all fire, **falsifier did NOT fire**.

M1-DEMO (§8) item 6 is *"witnessed verification demonstrated on at least one job
class"*. The W2 → S20 → S24 → S27 chain was built for that line and had never
been driven as a **job**: proofs were measured, never adjudicated.

> **Id note.** This is `S36` and the CHANNEL line above it says `S29`, which was
> mine and wrong: I wrote the claim text and ran `allocid.sh` in one command and
> then typed the id from memory. Corrected twice in `CHANNEL.md`, including the
> correction's own wrong half. `S29` is now **burnt** — v2's seed reads
> `CHANNEL.md`, so a mistyped claim reserves an id, which is the right behaviour
> and a cost of the H57 widening nobody had named.

## The job class and the two routes

A prefix range query (8 bytes, ~97.6 answers, 2.4% of the shard) over the
real-KG key set S24 and S27 measure. 40 jobs; 3 skipped for answers below three
keys, where omission is trivial.

- **REPLICATION** — a worker returns the answer set, canonically encoded and
  hashed; a second worker's bytes are compared. M1.8's quorum in miniature.
- **WITNESSED** — one worker returns the answer *and* a completeness proof
  against the shard root; a single verifier decides alone, with no peer.

The liar rewrites the proof's key list to match its claim, keeping the honest
authentication path it received from the store. A liar that ships an honest proof
of the honest answer has not lied, and testing that would prove nothing.

## Result

| world | replication | witnessed |
|---|---|---|
| honest pair | **37/37 accept** | **37/37 accept** |
| one liar, honest peer | **37/37 caught** | **37/37 caught** |
| **two non-independent liars** | **0/37 caught** | **37/37 caught** |

**This table is TRUE FOR ONE CHEAT SHAPE and reads as though it were true for
omission.** Corrected in place, `ATTACK.md`, one cycle later — the liar column
has a second row and the committed verifier loses it:

| cheat shape | committed verifier | replication, honest peer | replication, two non-independent liars |
|---|---|---|---|
| rewritten key list (omit / add / alter) | rejects **37/37** | catches 37/37 | catches **0/37** |
| **deeper-prefix replay**, nothing forged | **ACCEPTS 37/37** | catches 37/37 | catches **0/37** |
| deeper-prefix replay, **q-bound verifier** | rejects **37/37** | — | — |

**So this spike's own falsifier fires on the committed verifier** — replication
with an honest peer catches the replay 37/37 and the single verifier catches
0/37, which is precisely *"a cheat that a 2-of-2 replication check would catch"*.
The `falsifier did NOT fire` line at the top of this page was true only over the
cheat catalogue this run happened to test, and it is left standing rather than
edited so the correction is legible.

The conclusion is **repaired, not withdrawn**: world 3 is real and the witnessed
route does reach the case replication cannot — but only with a verifier that
binds the answer to the query, which the committed one does not. The eight-line
fix, and both sides of its measurement, are in `ATTACK.md`; the upstream lift is
**S37**.

**World 3 is the whole argument for witnessing.** Two workers running the same
wrong computation agree with each other, so byte compare reads consensus; the
single verifier holding the root rejects every one. This is not hypothetical for
this project: M1.8's real run adjudicates **`INSUFFICIENT_DOMAINS` on 50 of 64
jobs** — the quorum's members were not independent — and S26 measured the same
blind spot from the other side (a wrong replica is caught **0/64**).

All three tamper classes are rejected by the single verifier: **omit 37/37,
add 37/37, alter 37/37**. One class alone could be an accident of encoding.

> **CORRECTED one cycle later by `ATTACK.md`, and the sentence above is the
> defect.** Three classes is not a class list: `make_env` builds all three by
> rewriting `pf['keys']` and keeping the honest authentication path, so they are
> **one attack shape counted three times**. A fourth shape — ship a complete,
> unforged proof for a *deeper prefix* — is **accepted 37/37 by the committed
> verifier**, omitting **96.7%** of the answers (3,854 true, 127 delivered; worst
> job 394 → 12). See the corrected table below.

## Cost, cited and not recomputed

From S24 at this operating point: the verifier hashes **6,074 B** against
**205,184 B** to rebuild and check the shard — **0.030×**, i.e. **34× cheaper** —
and transmits **2,636 B** of witness against a 49,152 B shard. S24's crossover
stands: this route is cheaper than doing it yourself for every answer size below
the whole shard, and exactly equal at it.

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_honest_jobs_accepted_by_both` | either route rejecting an honest job — a verifier that rejects everything scores perfectly on the cheat worlds |
| `C_replication_works_when_independent` | replication failing to catch the liar when the peer is honest. Without this, world 3 would be comparing against a broken baseline rather than a blind one |
| `C_all_three_tampers_rejected` | any of omit / add / alter accepted |
| `C_jobs_have_real_answers` | fewer than 10 jobs with three or more answers, where omission is trivial and the demonstration vacuous |

## Scope, and what it does not license

- **This is one job class**: a range query over a key-value shard. It is *not*
  MeTTa reduction. The corpus jobs M1.8 runs are programs, and nothing here
  witnesses a reduction — W2's verifiable job class has been "trie-only queries"
  since it was written, and S36 does not widen it.
- **Non-independence is modelled, not observed.** World 3 duplicates one liar's
  envelope, which is the shape of two members sharing a binary and a host. M1.8
  measures that condition on the real fleet (`domains` per axis) but this spike
  does not re-measure it.
- **The verifier still trusts the root.** Everything here reduces to "whoever
  publishes the shard root is honest, or is itself committed elsewhere". S73/S74
  are that chain; the demonstration assumes it rather than exercising it.
- **No timing.** `quiet.sh` refuses on this host; every quantity is a count, a
  digest, or a byte count cited from S24.
