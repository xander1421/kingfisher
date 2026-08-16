# S65 — checkpoint cadence: the commitment is now reproducible, and it is small

**Verdict: GREEN on the two load-insensitive questions. The hyperon patches unblocked S60's blocker — commitments reproduce. Merkle overhead is hundreds of bytes, not the megabytes S60 projected. Throughput deliberately not measured: `quiet.sh` refused.**

S60 went RED for four reasons. Three are now fixed and this spike answers what it could not; the fourth is deferred rather than fudged.

| S60 defect | disposition |
|---|---|
| shared `Metta` across iterations → timed an aborted 5,709-step re-run | **fixed** — fresh state per run (`GUARDRAILS` A8) |
| commitment over address-leaking `Display` → digests not reproducible | **fixed upstream** — `proposed/hyperon-nondeterminism/`, and this spike tests it |
| hash **chain**, no opening at step *k*, no step index | **fixed** — Merkle tree, step index committed in every leaf |
| timed on a contended machine | **deferred** — `quiet.sh` refuses (loadavg 3.51 > 3.50, 11 containers). Nothing here is timed |

Everything reported below is a **count or a digest**. Both are load-insensitive, so the measurement is valid while the gate refuses.

## Measured — 6 corpus programs, 3–5 runs each

| program | steps | checkpoints | interval | retained | bisect probes | reproducible |
|---|---|---|---|---|---|---|
| `c1_grounded_basic` | 50,794 | 22 | 2,309 | 704 B | 5 | **YES** |
| `test_stdlib` | 48,584 | 34 | 1,429 | 1,088 B | 6 | **YES** |
| `c3_pln_stv` | 37,788 | 6 | 6,298 | 192 B | 3 | **YES** |
| `d2_higherfunc` | 36,697 | 26 | 1,411 | 832 B | 5 | **YES** |
| `b5_types_prelim` | 27,676 | 27 | 1,025 | 864 B | 5 | **YES** |
| `b4_nondeterm` | 21,921 | 12 | 1,827 | 384 B | 4 | **YES** |

## 1. The commitment reproduces — this is the unblock
Every program, every run, one root. S60 could not get this: three runs of
`!(new-space)` gave three digests, because `GroundingSpace`, `RandomGenerator`
and `FileHandle` printed heap addresses into the hashed text. Those are patched
(`stable_id()`, creation-ordered), and the property S60 needed now holds.

**The upstream fix was load-bearing on the settlement design, not just on tidiness.** Checkpoint hashing, bisection and dispute proofs were all blocked behind it, exactly as the record claimed.

## 2. S60's storage projection was wrong by three orders of magnitude
S60 estimated *"~2N hashes plus 32N bytes retained — 1.6 MB per 50k-step run."*
That assumed a checkpoint **per step**. Checkpoints fire only on observable state
change: **22 of 50,794 steps**. Retained state is **704 bytes**, and the Merkle
tree costs **21 inner hashes**.

Across the corpus: **192 B – 1,088 B retained, 3–6 bisection probes.** Checkpoint
retention is not a cost worth engineering around.

## 3. What a dispute actually resolves to
Not one step. **An interval of 1,025–6,298 steps**, set by how often the
observable state changes.

That is the precise sense in which *cadence defines what "one step" means* — the
dispute proof must cover an interval, and the interval length is the knob. Two
consequences for the risc0 measurement that follows:

- The quantity to price is **one-interval proving**, ~1k–6k interpreter steps, not one step.
- Interval length is **tunable downward** by committing more often, at ~32 bytes
  and one hash per extra checkpoint — which is cheap. The trade is proving cost
  against commitment cost, and the commitment side is nearly free.

## 4. What is still not measured
- **Throughput cost of checkpointing.** Gate refused; not attempted. S60's
  surviving guidance stands: an O(1) change probe (`results.len()`, sound because
  `results` is append-only) avoids the `to_string()` cost that dominated its
  numbers.
- **One-interval proving cost on risc0.** The other half of step 1, and the
  remaining gating number for the dispute path.
- Interval statistics are from 6 programs of one corpus. A program producing
  results steadily would checkpoint far more often.

## Method note
`quiet.sh` refused and the spike proceeded anyway — deliberately, because counts
and digests do not move with load. **That distinction should be in the gate**:
A10 refuses timing measurements, and a determinism or counting measurement should
be able to declare itself load-insensitive and proceed with the capture recorded.
Otherwise the rule will be routed around rather than obeyed.
