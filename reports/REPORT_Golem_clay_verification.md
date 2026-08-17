# REPORT — `golemfactory/clay`, `golem/verifier/` (GPL-3.0, SPEC ONLY)

**Read, not copied.** GPL-3.0, so `LICENSE_LEDGER` rule applies: written
description only, no code lifted. Clone at `elders/yagna` @ `develop`
(229 MB; `master` is a Mercurial-era stub). Archived 2022-12-27, 2,877 stars.

**Why this repo exists in the workspace at all:** it was written off. `THE_BRAIN`
claimed *"Golem built one and deleted the repository"* and the CEO report used
that as evidence. Both false — see A17. The repo was renamed and archived, and
it contains a production answer to the question this project currently ranks as
its highest open risk.

## The finding

**Golem does not replicate. The requestor audits a random ~3% of the work itself.**

Occurrence counts across `golem/` and `apps/` (`*.py`):

```
verif      706        redundan    25
majority     4        replicat     1
quorum       0        consensus    0
```

Zero quorum. Zero consensus. This is the **second** production system to refuse
replication-by-quorum, and the two refuse it for different reasons:

| | BOINC | Acurast | Golem (clay) | us |
|---|---|---|---|---|
| who verifies | a quorum of peers | nobody re-runs | **the requestor** | a quorum of peers |
| basis | majority of N results | TEE attestation + slash | **random spot-check** | majority of 3 |
| cost of verification | (N-1)x the work | ~0 | **~3% of the work** | 2x the work |
| Sybil-able | yes | no (silicon) | **no — one requestor per job** | **yes, measured 72%** |

## The mechanism, precisely

`apps/blender/resources/images/entrypoints/scripts/verifier_tools/`

1. **Sample.** `crop_generator.py:8` — `CROP_RELATIVE_SIZE = 0.1`, so each crop is
   10% x 10% of the frame = **1% of the area**. `verifier_entrypoint.py` defaults
   `crops_count=3`. Total requestor work: **~3%**.
2. **Randomise, unpredictably.** `crop_generator.py:104` draws crop origins from
   `random.uniform`, **unseeded**. The provider cannot know which regions will be
   audited, so cheating is a gamble across all three.
3. **Re-execute.** The requestor renders those crops itself, in a pinned Docker
   image, from the same scene file.
4. **Compare.** `image_metrics.py` + SSIM / PSNR / edges / variance / wavelet.
5. **Decide.** `decision_tree.py` — a **trained sklearn classifier** loaded via
   `joblib`, mapping the metric vector to TRUE/FALSE.
6. **Conjoin.** `verifier.py:114-140` — `verdict = True`, and **any** crop
   labelled not-TRUE sets it False. All crops must pass.
7. **Three-valued outcome.** `subtask_verification_state.py` carries
   `NOT_SURE = 5` alongside VERIFIED and WRONG_ANSWER. Undecided is a first-class
   result, not an error.

Verification runs on the **requestor** side: `requestedtaskmanager.py:484`
constructs the `VerificationQueue`.

## What this means for us — and it is not small

**Our open risk (report section 05, S69/S70, Q1) is that verification eligibility
is coupled to shard residency**, so rare shards have tiny verifier pools and one
operator with five devices captures 72% of quorums. W1 was the proposed cut and
it is INVALID. There has been no candidate fix.

**Requestor-side spot-checking deletes the problem rather than fixing it.** There
is exactly one requestor per job, they cannot be Sybil'd, and they are the party
who actually wants a correct answer. Shard residency stops mattering because the
verifier is not drawn from the device pool at all.

### Where we are strictly better
Golem needed a **trained classifier** because rendering is stochastic — sampling
noise means two honest renders differ. Our oracle is `==`. Byte-identity (S57)
removes the classifier, the training corpus, the tolerance threshold and the
false-positive rate in one step. Golem shipped the hard version of this; we would
ship the easy version.

### Where we are blocked, and it is the same wall as before
Rendering is **spatially decomposable**: crop *k* can be rendered without
rendering crops *1..k-1*. **MeTTa reduction is sequential.** You cannot re-execute
a random 3% interval `[k, k+d]` without the interpreter state at step *k*.

That state is exactly what **S68** found does not exist.

**This reframes S68 rather than being blocked by it.** S68 killed
bisection-to-a-committed-state, and we descoped the state commitment along with
the zkVM stack because the dispute path had been replaced by majority-of-quorum.
The commitment now buys a **second, larger** thing: it is the enabling primitive
for requestor-side auditing, which removes the quorum dependency entirely — and
with it the 72% capture that is currently our top risk.

So the descope decision was made when checkpointing had one customer. It has two.

## Honest limits of the port
- **No public verifiability.** A requestor-side audit convinces the requestor, not
  a third party. Fine for a paying customer; insufficient if the pitch is
  "anyone can check". Our determinism claim still supports the public version;
  this is a cheaper path for the commercial one.
- **Payment disputes are not solved**, only detection. Golem's recourse is
  non-payment plus reputation.
- **Probabilistic, not certain.** A provider corrupting a small fraction may pass.
  Detection rises with `crops_count`, which is a tunable cost/assurance dial we
  do not currently have anywhere in the design.
- **Grade E** for the mechanism as applied to us: read from source, nothing run.
  The code is production and shipped for years, but we have measured none of it.

## Recommendation
Re-open the checkpoint/state-commitment item that `THE_BRAIN` sequencing step 1
marked DESCOPED, on the strength of the second customer. The measurement that
decides it is unchanged from before — **checkpoint-hashing cadence** — but the
question it answers is now "can the requestor audit a random interval cheaply",
not "can we bisect a dispute".
