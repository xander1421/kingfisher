# M1.8 — quorum-3 pipeline, end to end. GREEN, with a narrow claim.

**66/67 unanimous across three worker processes and two operating systems.
The one refusal is the corpus's own nondeterministic program.**

First thing in this workspace that composes rather than measures: a coordinator,
three worker processes, a filesystem/adb transport, and BOINC's majority rule,
running hyperon's own test corpus.

## Shape

```
q3.py (coordinator)
  |-- run/host-a/{in,out}  ->  worker.py --via local  ->  fuelrun.v2.host    (macOS arm64)
  |-- run/host-b/{in,out}  ->  worker.py --via local  ->  fuelrun.v2.host    (macOS arm64)
  '-- run/phone/{in,out}   ->  worker.py --via adb    ->  fuelrun.v2.android (Android aarch64)
```

Three OS processes, each polling its own inbox. Filesystem transport is
PORT_PLAN M1.7's "ship a filesystem-backed transport too", and it is the honest
shape for the phone as well: **the phone is pulled, never dialled** (S8).
A fresh `fuelrun` per job, never a reused runner — PORT_PLAN M1.3 gives two
independent derivations (S60/A8 atomspace pollution; process-global
`NEXT_VARIABLE_ID`).

## Result — 67 programs, fuel limit 2,000,000

| | |
|---|---|
| UNANIMOUS (3/3) | **66** |
| NO_QUORUM | 1 |
| accepted | **66/67** |
| agreed status | OK 65, FUEL_EXHAUSTED 1 |
| device gate | `cpu_busy 0.9%, thermal 39700m, battery status=5 level=100` |

| worker | median | total |
|---|---|---|
| host-a | 9.2 ms | 5.4 s |
| host-b | 9.0 ms | 5.5 s |
| phone | 50.3 ms | 14.1 s |

Phone median includes adb round-trip, so 50.3 ms is transport + compute, not compute.

## The refusal is a positive control that fires

`python__sandbox__test_gnd_conv.metta` calls `(flip)`, a coin flip. S57 identified
it as the corpus's own positive control. Here all three workers returned:

```
host-a  OK  fuel 1012  hash 822f8dc1b0d4d22c...
host-b  OK  fuel 1012  hash 0867719ceca29e30...
phone   OK  fuel 1012  hash bd007a029ff9e19c...
```

Three different hashes at **identical fuel**. The pipeline refused it.

Two things follow, and the second is the load-bearing one:

1. **`fuel_used` alone is not an agreement key.** All three agree on fuel and
   disagree on output. The key must be `(status, fuel_used, sorted_hash)`; drop
   the hash and this program is accepted unanimously. Recorded because S57's v1
   harness made the mirror-image mistake, hardcoding `status`.
2. **This experiment has a positive control and it fired** — unlike N1c, N1d and
   N1e, where the whole difficulty was that the control could not fire. It is not
   one I built; it was already in hyperon's corpus. Nothing here is trustworthy
   because a control fired once, but "the instrument can distinguish agreement
   from divergence" is now demonstrated rather than assumed.

`test_adjudicate.py` — 11 assertions, all passing — pins the cases the corpus
does not reach: 2-of-3 majority, all-different, missing replicas (one survivor
must **not** be a majority), fuel-only divergence, status-only divergence, and
two agreeing crashes (`MAJORITY` verdict with `CRASH` in the key — callers must
read the key, not the verdict).

## What this does NOT show

- **Not a trust-independent quorum.** Two of three workers are the same binary on
  the same host. This exercises the *pipeline*, not Sybil resistance. Q1's finding
  stands untouched: 72% wrong-accept on rare shards against one operator with five
  devices, and the S69/S70 root cause (verification eligibility coupled to shard
  residency) still has no fix.
- **No shard store.** Programs are file paths, not CIDs. M1.5 is untouched, so
  M1's exit criterion ("fetches a shard by CID") is not met.
- **No scheduling.** No WorkManager, no charge-time constraints in the loop; the
  device gate is checked once by the coordinator, not enforced per job. M1.3 open.
- **No signing, no attestation.** Envelopes are plain JSON.
- **Corpus is hyperon's own**, which S57 established contains zero transcendental
  evaluations. Agreement here is agreement inside the admissible job class, which
  is the only class the determinism claim ever covered.

## Files
`q3.py` coordinator · `worker.py` worker · `test_adjudicate.py` self-check ·
`result.json` full envelopes for all 201 executions
