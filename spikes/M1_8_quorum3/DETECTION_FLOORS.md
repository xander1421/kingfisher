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

---

## Two floors closed since this table was written

**Device-side shard integrity — was "absent", now exact.**
The worker verifies the cached blob **on the device** before running it. The CID
*is* the hash, so this needs no extra metadata: `sha256sum` the file, compare to
the multihash, evict and refetch on mismatch.

Control, run rather than argued — corrupt a cached shard and see whether the
pipeline notices:
```
on-device sha, pre-corruption   6e99de46fcad885dd82540f7caf5…
on-device sha, post-corruption  3398b5c2a9131cb63d2d21240a5d…
-> phone bytes_pushed 2002  (rejected the cache, refetched)
-> status OK, fuel 58, agree 3/3
```
Previously a corrupt shard was caught only by quorum — i.e. by three devices
disagreeing, which is the expensive way to find a bit flip, and which fails
outright when the corruption is identical across devices.

Residual floor: this catches corruption and substitution. It does **not** catch
a device that verifies correctly and then executes something else.

**ISA monoculture — was 1 domain, now 2.**
Added an x86-64 build of the same source, run under Rosetta. Distinct `binary`
and `isa` domain, same `host` and `os` domain — which is precisely why the count
is per-axis rather than scalar.

```
binary    3 domain(s)
host      2
os        2
isa       2      <- was 1
operator  1      <- binding
```

This restores the cross-ISA property S57's headline had and the quorum had
quietly lost, and all jobs still agree 3/3 — so aarch64 and x86_64 produce
byte-identical results inside the live pipeline, not just in S57's corpus run.

**The mismatch detector caught a real error doing it.** The worker declared
`isa=arm64` — its own Python process — while the coordinator observed `x86_64`
from the binary via `lipo -archs`. Self-declaration was simply wrong, and the
axis would have silently merged two ISAs into one domain. The detector's first
firing was benign (`operator`); this one was not.

`operator` remains the binding axis at 1 and cannot be raised without an
attestation root.
