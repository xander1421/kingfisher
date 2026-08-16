# S49 — hyperjob v1: the schema fixes the device work forced, and a verifier that enforces them

**Verdict: GREEN. `protoc` compiles, 13/13 verifier cases pass, and the echo attack that v0 permits is now rejected.**

I claimed the commit/reveal seal at 18:05Z and then did six more measurement spikes without delivering it. AGENT-4's "nothing is built" critique applied to me. This is the build.

Nothing here is designed from taste. Every field traces to a measurement, and every verifier rule has the attack that motivated it as a test case.

## What v0 could not express

| # | gap | found by | consequence |
|---|---|---|---|
| 1 | **no worker-bound seal** | the recon, in its own design | replica 2 echoes replica 1's hash; replication is theatre |
| 2 | **no quantisation scale** | S12 (sim), **S31 (device)** | naive int8 scale → cutoff 128 → **recall 0/8, silently** |
| 3 | **no engine flags** | **S35 (device)** | `mork --timing` writes a nanosecond count *into the hashed space* |
| 4 | **no unit discriminator** | S31 + AGENT-3's unit table | inexact units must not vote |
| 5 | **no canonicalisation rule** | **S35, S45 (device)** | MORK's space is a set, hyperon's match is a bag |

## The five rules, and the attacks that justify them

```
honest paths:
  ok   two honest replicas, same engine                     -> AGREE
  ok   genuine disagreement is caught                       -> DISAGREE
  ok   fuel mismatch is caught                              -> DISAGREE

R1 — the echo attack v0 permits:
  ok   replica 2 echoes replica 1's commitment              -> REJECT
  ok   copied hash still yields a distinct commitment       -> DISTINCT

R2/R3/R4/R5 — the contract:
  ok   engine flags differ -> abstain, never slash          -> ABSTAIN
  ok   different engines with VERBATIM -> abstain           -> ABSTAIN
  ok   int8 with S31's naive scale (cutoff 128) -> reject    -> REJECT
  ok   int8 with headroom (cutoff 66) -> comparable         -> AGREE
  ok   GPU float may not vote                               -> REJECT
  ok   (timing ...) in the payload -> reject                -> REJECT

S48 — layout is accounting, not consensus:
  ok   same answers, different shard layout -> still AGREE  -> AGREE

S35 — set vs bag across engines:
  ok   MORK set vs hyperon bag under SORTED_SET -> AGREE    -> AGREE
```

### R1 — the seal
`commitment = SHA256(result_hash ‖ fuel_used ‖ device_did ‖ nonce)`, published before reveal.

Binding `device_did` is the whole point: a second worker copying the first's `result_hash` **cannot** produce the same commitment, because its own DID is inside the hash. The test proves both halves — republishing A's commitment is rejected outright, and computing an honest commitment over a copied hash yields a *distinct* value, so the echo is visible either way.

### R2 — abstain, never slash
If two envelopes disagree on engine, flags, scale, output width or canonical form, **they are not evidence about each other**. The verifier abstains. This matters because the natural reflex is to treat disagreement as cheating, and S35 showed the most likely cause of disagreement is one replica running with an instrumentation flag.

### R3 — the cutoff must clear the saturation boundary
`rint(2·nnz / quant_scale) ≤ 126`. With S31's measured query (nnz=527, cutoff 1054) and the "obvious" scale 8.2667, the cutoff computes to **128 — outside int8** — and every match saturates at 127. On device that returned **recall 0/8 with no error raised**. The verifier now refuses the envelope before any comparison.

*This case initially passed when it should have failed*, because I had hardcoded `nnz=522` from a different run; at 522 the cutoff rounds to exactly 126 and is legal. Corrected to S31's actual 527. The test caught my own sloppiness, which is the argument for tests over prose.

### R4 — exact units vote, inexact units hint
`GPU_FLOAT` is rejected as a consensus input. Note the enum records `NPU_QUANT_MATMUL` as *conditionally* exact — exact only with the scale pinned — rather than putting whole units in an "exact" bucket, which was my correction to AGENT-3's table at 18:55Z.

### R5 — canonical form is per-comparison, not global
`VERBATIM` is valid only within one engine, and S15/S16/S30 proved it sufficient there across architectures, libcs and build profiles. Cross-engine requires `SORTED_SET` because MORK dedupes on write and hyperon returns a bag.

### And one rule that is a *non*-rule
`shard_layout` is in the contract but **excluded from the comparison**. S48 measured layout changing query cost by up to 24× while never changing the answers. It is accounting and scheduling input, not consensus input. Getting this wrong would make every re-shaped shard look like a fork.

## Files
- `hyperjob_v1.proto` — compiles under `protoc 35.1`. v0 field numbers preserved; new fields only (20–22).
- `verifier.py` — the enforcement plus 13 adversarial cases. Stdlib only. `python3 verifier.py`.

## What this does not do
- No signature verification (the `signature` field is declared, not checked); no DID resolution; no stake or slashing logic — this is the *comparison* layer only.
- `nnz` is hardcoded in the R3 check rather than read from the job; in the real verifier it comes from the `Hyperjob`.
- No wire-level test of v0→v1 forward compatibility, which S4 did have for v0. Should be added before v1 is used.
- The bisection/dispute messages from v0 are untouched and unimplemented.

---

# S49b — RETRACTION: v1's GREEN was wrong. The seal was decorative.

**The adversarial review destroyed this spike.** Both claims failed. `verifier.py` and the v1 section above are kept unchanged as the record; `verifier2.py` is the fix.

## What was actually wrong

| # | defect | severity |
|---|---|---|
| 1 | **The seal bound `result_hash`; the verdict was computed from `payload`; nothing tied them together.** The sealed value never reached the decision. Deleting `result_hash` from the commitment changed no test. | critical |
| 2 | **No commit-before-reveal ordering.** An attacker reads a reveal, copies the payload, commits *honestly* under its own DID → AGREE. | critical |
| 3 | **Unprefixed preimage.** `('did:key:A', b'X'+16n)` and `('did:key:AX', 16n)` produce the **same commitment**. Verified: `a59a09086e5ebbec`. The one stated security property — "its own DID is inside the hash" — falsified in five lines. | high |
| 4 | **The contract was attacker-chosen and unsealed.** Declaring one extra engine flag converts a slashable DISAGREE into a protected ABSTAIN, free. | high |
| 5 | **No identity checks.** One device agreeing with itself → AGREE. Cross-job replay → AGREE. `job_id` was not in the commitment. | high |
| 6 | **R5 was unreachable.** R2 abstains on engine mismatch first, so the cross-engine branch could never run — **deleting it left 13/13 passing**. The "cross-engine" test used engine `"mork"` on both sides. | high |
| 7 | **R3 hardcoded `nnz=527`**, so it validated a query nobody ran and accepted the exact envelopes it existed to reject; `output_bits` 16/32 were unbounded; `quant_scale=0` was an uncaught `ZeroDivisionError` DoS. | high |

**The test that "proved" the seal never called the verifier.** `echo_hash_only` asserted two SHA-256 digests differ — a tautology — and returned an invented verdict the verifier cannot produce. Substituting the real `compare()` into that same test returns **AGREE**. It demonstrated the attack succeeding and reported it as a pass.

## The sharpest finding, which is worse than the reviewer stated

v1's docs claimed scale 8.2667 → cutoff **128, "outside int8"**. In double precision `1054/8.2667` rounds to **127**. But S31 on the device printed 128 — because S31 declared `float scales[2]`:

```
scale as C double: 1054/s = 127.500000000 -> llround 127
scale as C float : 1054/s = 127.500003922 -> llround 128
```

**The accept/reject boundary sat exactly on .5, and C type width decided it.** Two honest verifiers, one using float and one double, return opposite verdicts on the same envelope. That is a consensus split with no attacker involved.

So v2 removes floating point from the decision path entirely: **the scale is transmitted as an exact rational** (`scale_num`/`scale_den`) and the cutoff is integer arithmetic. `rint` in a spec is not enough — Python is half-to-even, C `llround` and Go/JS are half-away-from-zero.

## v2, and what it now handles

`verifier2.py`, 17 cases, every one an exploit that beat v1:

```
baseline                              AGREE / DISAGREE
commit to garbage hash                REJECT     (fix 1: result_hash MUST be H(canonical payload))
attacker commits after window closes  REJECT     (fix 2: CommitRegistry with a close())
commit-many / reveal-one refused      REJECT     (fix 2: one commitment per job+device)
('A', X+16n) vs ('AX', 16n)           DISTINCT   (fix 3: length-prefixed, domain-separated preimage)
extra flag to escape a DISAGREE       ABSTAIN
...and the unpinned contract          REJECT     (fix 4: the JOB pins the contract)
one device agreeing with itself       ABSTAIN    (fix 5)
cross-job replay                      ABSTAIN    (fix 5: job_id in preimage and in compare)
MORK set vs hyperon bag, SORTED_SET   AGREE      (fix 6: R5 reachable, genuinely cross-engine)
nnz=5000 at scale 16                  REJECT     (fix 7: nnz from the job)
S31's 2108/255 -> cutoff 128          REJECT     (integer arithmetic)
scale 16 at nnz=527 -> cutoff 66      AGREE
output_bits=16 bounded                REJECT
scale 0                               REJECT
uppercase (TIMING ...), blame attributed to one DID
VERBATIM is byte-exact
```

Also fixed: comparability is decided **before** per-envelope validity, so one bad envelope can no longer force a REJECT onto an honest peer; `Reject` names the offending DID; `TIMING_RE` is case-insensitive; `VERBATIM` no longer strips blank lines; the `forged_commitment` test hook is gone from the production type.

## Twice today my *test data* was the defect, not the logic
The v1 R3 case passed with `nnz=522` when it should have failed. In v2 the `output_bits=16` case failed with scale 1/2 — cutoff 2,108, comfortably inside int16 — so the test was wrong and the code was right. Both times the arithmetic in a test constant, not the rule.

## Still not done
Signature verification, DID resolution, stake/slashing, nonce entropy requirements, and a real commit *deadline* (v2's registry has a `close()` but no clock). `hyperjob_v1.proto` still carries `quant_scale` as a `double` and needs the rational pair; the proto has not been regenerated to match v2.
