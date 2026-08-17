# What each check can and cannot detect

Every gate in the M1 chain, with its **detection floor** — the smallest
deviation it can see. A check whose floor is not stated reads as verification
when it may only be a bound.

| check | detects | detection floor / blind to |
|---|---|---|
| **admission** (`bansurface`) | unseeded randomness by syntax | **blind** to randomness reached via an unenumerated `import!`, or `py-atom` resolving a runtime string into any Python callable — undecidable, not merely hard. Build-level removal remains the primary control |
| **quorum agreement** | one replica diverging | **blind to shared bugs** — every honest evaluator computing the same wrong answer. **Launders nondeterminism at 21.5%** (M1.8b): two of three coincide and an arbitrary answer is recorded as canonical |
| **REDUCED_QUORUM** | a worker that returned nothing | **exact** — dispatched and returned are both coordinator-held. No floor |
| **INSUFFICIENT_DOMAINS** | agreement from too few failure domains | **exact on the axes it has**, and the axes are not exhaustive. `operator` is pinned `UNATTESTED` because no attestation root exists, so on the axis Q1's capture model is about, it can only ever report 1 |
| **domain mismatch** | a worker claiming a domain we did not observe | **exact** — string comparison against a coordinator-held value |
| **residency** (`observed_residency`) | a worker misreporting which shards it holds | **exact against an honest device shell.** **Zero against a compromised device**, which controls its own filesystem view. This moves trust from our worker process to the device OS — an improvement, because the worker is the thing under test — but it is not verification against a hostile device |
| **timing** (`observed_ms`) | nothing, at useful resolution | **floor ~2.8x.** Serialised, coordinator-observed 193.8 ms against 68.2 ms declared. Can only detect a lie larger than the observation noise, so it cannot detect the lie it exists to catch. Recorded as an upper bound; **police `fuel_used` instead**, which is in the agreement key |
| **`canon` / `canon_alpha`** | process-history noise in results | **exact and directional** — verified not to erase a real divergence (heap-address control stays 40/40). `canon_alpha` is lossless only on **ground** results, enforced by `is_ground()` |
| **shard store integrity** | a corrupt or substituted blob | **exact host-side** (`get` re-hashes before serving). **Absent device-side** — the phone trusts its own cache file, so device-side corruption is caught only by quorum |
| **preflight** | thermal/charge/space at dispatch | **per session, not per job**, in this harness. On-device the real cost is 98.5 µs so per-job is viable; the session granularity is an adb accommodation |
| **provenance** (A24) | an artifact predating its source | **exact** on mtime. **Blind** to an artifact built from a *different* tree with a *newer* mtime — it proves "could not have come from here", never "did come from here" |

## The general shape
Three of these are exact because the coordinator already holds the reference
value: dispatched/returned counts, observed domain strings, the seed it issued.
That is the cheap conversion — **check against something you already hold**,
rather than trusting less or attesting more.

The rest have floors, and the floors cluster into two kinds:

- **A21-family** — the instrument is coarser than the deviation (timing, 2.8x).
- **A22-residual** — the check is exact but rests on a party that could be the
  adversary (residency against a compromised device; admission against a
  runtime-resolved callable).

Neither is fixed by running the check harder. The first needs a different
quantity — fuel rather than time. The second needs an attestation root, which
this project does not have, and which is the same missing piece the `operator`
domain axis reports as 1.
