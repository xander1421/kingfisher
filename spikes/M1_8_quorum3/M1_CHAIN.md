# M1 — the whole chain, one run, with provenance

**CORRECTED. The headline was 66/66 UNANIMOUS; under a failure-domain check it
is INSUFFICIENT_DOMAINS.** The chain runs end to end and every link is measured
— but the quorum that validated it had **2 independent failure domains, not 3**,
and the writeup counted seats.

```
admission gate  ->  CID shard store  ->  session preflight
                ->  phone + 2 host workers  ->  canon_alpha  ->  quorum-3
```

## The run
```
gate:       cpu_busy 0.6%, thermal 36600m, battery status=5 level=100
admission:  REFUSED 1 program on the nondeterminism ban surface
store:      66 programs -> 66 distinct CIDs, 173.2 KiB
dispatch:   66 jobs in 5 work sessions, 0 preflight refusals
alpha:      0 envelopes non-ground -> 0 fell back to canon
transfer:   173.2 KiB to device (cold cache)
result:     UNANIMOUS=66, accepted 66/66
```

## Provenance
`provenance.json`, written before the write-up:

| | |
|---|---|
| `elders/hyperon-experimental` | `3f76dc460da6`, **DIRTY 5 files**, diff `2a38d23f5150` |
| device | `SM-S938B`, `BP4A.251205.006`, `arm64-v8a` |
| artifacts | sha256 of both `fuelrun` binaries |

The dirty tree is **recorded, not silent** — it carries our three unfiled
nondeterminism patches, and `allow_dirty=True` plus the diff hash is what makes
that a fact a third party can reconstruct rather than an omission. The earlier
M1.1 run shipped a patched build under a stock commit hash and nobody noticed;
that is the failure this field exists to prevent.

## Why 66/66 is not self-congratulation
A clean sweep means nothing unless the instrument could have reported otherwise.
Two controls, declared before the run and persisted with their observations:

| control | fired | evidence |
|---|---|---|
| **admission gate** | yes | refused 1 of 67 — `test_gnd_conv.metta` on `flip` |
| **adjudicator can refuse** | yes | `UNANIMOUS`, `REDUCED_QUORUM`, `AGREED_FAILURE`, `NO_QUORUM` each reachable from a constructed envelope set |

Without the second, "66/66 UNANIMOUS" would be consistent with an adjudicator
that returns UNANIMOUS unconditionally.

## What each link is, and what it cost to learn
| link | what it does | the finding behind it |
|---|---|---|
| admission | rejects unseeded randomness | quorum **launders** nondeterminism 21.5% of the time — replication cannot be the control |
| shard store | CID-addressed, byte-capped LRU | warm cache = 0 bytes; transfer is `63 ms + 37.9 MB/s`, not a single rate |
| preflight | thermal/charge/space per session | the real cost is **98.5 µs**, not the 35 ms measured over adb |
| in-process MeTTa | JNI into `libhyperonc` | identical to native `fuelrun` on the same device |
| canon / canon_alpha | strips process history; alpha opt-in | E1 40 distinct -> 1, heap-address control unchanged at 40/40 |
| quorum-3 | dispatched vs returned recorded | a short quorum is **craftable**, so it is `REDUCED_QUORUM` and never payable |

## The correction — seats are not domains

`REDUCED_QUORUM` catches workers that **died**. It cannot catch workers that
were **never independent**: dispatched 3, returned 3, check passes — and the
failure-domain count is 2.

Two of the three workers ran the same binary on the same host. They share libm,
clock, page tables, scheduler, and the same 1024-result panic. Their agreement
is nearly free, so the run reads as three checks and is two.

```
host-only, 3 workers, 1 binary, 1 host:
  INSUFFICIENT_DOMAINS   3/3  1dom   accepted 0/4
  domain: host:Victorias-MacBook-Pro.local|bin:78d874f97674
```

The real M1 setup (2 host + 1 phone), re-run with the phone attached:

```
admission: REFUSED 1 on the ban surface
store:     66 programs -> 66 CIDs
dispatch:  66 jobs, 5 sessions, 0 preflight refusals
result:    INSUFFICIENT_DOMAINS  3/3 2dom  on every row -- accepted 0/66
```

The same chain that reported 66/66 an hour earlier now reports **0/66**, and
nothing about the chain changed. Only the question did.

### The count is per fault class, not global

A scalar conflates classes with different domain structures — two workers can be
independent for a compiler bug and identical for a libm bug. The adjudicator now
reports a vector and **binds on the weakest axis**:

```
binary    2 domain(s)
host      2 domain(s)
os        2 domain(s)
isa       1 domain(s)  <-- binding
operator  1 domain(s)  <-- binding
```

Two disclosures fall straight out of it, neither visible in `2dom`:

- **`operator` is 1**, and that is the axis Q1's 72% capture figure is *about*.
  Every worker is run by us. On the only axis that models collusion, this quorum
  has one domain.
- **`isa` is 1.** S57's determinism headline was **cross-ISA** (x86-64 +
  aarch64). This quorum is aarch64 on both sides, so it re-tests nothing S57
  established about instruction semantics.

The `isa` axis first reported **2**, because macOS says `arm64` and Android says
`arm64-v8a`. Same ISA, two strings. That is this module's own warning —
*a key that flatters itself* — committed inside the fix for it, and caught only
by reading the vector. Now normalised.

### The `manifest` axis, added after measuring that features change fuel
`analysis/FEATURE_EQUIVALENCE.md` showed a Cargo feature moving one program
from fuel 107 to fuel 580. Two binaries built from the same manifest share every
feature-induced fault, so they are **one** domain on that axis whatever their
digests say. Adding it immediately caught the binary axis overstating:

```
binary    3 domain(s)     <- three distinct digests
manifest  1 domain(s)  <-- binding
host      2 domain(s)
os        2 domain(s)
isa       2 domain(s)
operator  1 domain(s)  <-- binding
```

`binary=3` reads as three independent builds. For a feature-class fault it is
one. **Third time a domain key has flattered itself** — after `host|bin` hiding
that the two host workers shared everything, and `arm64` vs `arm64-v8a` counting
one ISA as two.

The test for this was also flattering itself: `test_adjudicate.py` set a legacy
`domain` field on the envelope, which the adjudicator stopped reading when
domains moved coordinator-side. Every axis resolved to `{None}`, collapsed to
one domain, and the assertions passed for the wrong reason. Rewritten against
the real path — **36 assertions**, now including that a shared manifest alone
caps the count at 1.

### Fault classes NO key separates
Some faults have no separating axis at any quorum size, and a domain count that
omits them reads as stronger than it is:

| fault class | separating key | domains available |
|---|---|---|
| libm divergence (S59) | libm build | 2 (libSystem, bionic) |
| DVFS / thermal | physical device | 2 |
| variable-id (M1.1c) | process | many |
| **1022 match panic (G18)** | **none** | **1** |
| **shared implementation bug** | **none** | **1** |

The panic is the concrete instance: verified identical on macos-arm64 and
android-aarch64, so **determinism extends to the crash**. Replication catches
disagreement, never a shared bug — and a shared abort is just the loudest shared
bug. `q3.py` prints these classes with every refusal rather than letting a
domain count imply coverage it does not have.

### The key was worker-DECLARED, which is the third instance of a dead pattern

The first version had each worker report its own `platform.node()`, its own
binary hash, its own operator string. **Self-reported identity** — the same
defect that made S62's `backend_class` INVALID and that was flagged on M1.5's
binary hash.

For an honest worker `arm64` vs `arm64-v8a` is a normalisation bug. For a
dishonest one it is the attack: emit distinct host and operator strings, inflate
the domain count, and take the quorum **through the field built to prevent
exactly that**.

The fix is a category change, not a string fix: **domain must be observed or
attested, never declared.**

```
observed domains (coordinator-side, not worker-declared):
  host-a   binary=bin:78d874f97674  host=host:Victorias-MacBook-Pro.local  os=darwin-25.4.0  isa=aarch64  operator=UNATTESTED
  host-b   binary=bin:78d874f97674  host=host:Victorias-MacBook-Pro.local  os=darwin-25.4.0  isa=aarch64  operator=UNATTESTED
  phone    binary=bin:deb4ee9b93f8  host=adb:R5CY93675MK                   os=android-16     isa=aarch64  operator=UNATTESTED
```

- `binary` — the coordinator hashes the file **it dispatched**. It still cannot
  prove the worker *executed* it; that needs attestation.
- `host` — read from the coordinator's own adb connection, or its own hostname.
- `operator` — **`UNATTESTED`, pinned to one domain by construction.** There is
  no attestation root, so operator independence cannot be established at all,
  and this is the axis Q1's 72% capture is about.

Worker declarations are still collected and **compared**, so a worker claiming a
domain we did not observe is now visible rather than believed:

```
!! DOMAIN MISMATCH on 6 envelope(s), axes ['operator']
   e.g. host-a: {'operator': {'declared': 'operator:self', 'observed': 'UNATTESTED'}}
```

That first firing is benign — honest workers say `operator:self` while the
coordinator refuses to credit it — but the detector is the point.

### Two things this does and does not change
**Today's refusal does not depend on the fix.** `operator=1` and `isa=1` are
true right now whatever the key's provenance, because every worker is ours and
both sides are aarch64. The `INSUFFICIENT_DOMAINS` verdict was correct before
this change and is correct after it.

**Self-reporting becomes load-bearing on day one of a real fleet** — the first
moment a worker is not ours. So this is an interim position (observation) with
the real fix (attestation) still absent, and the two are recorded separately
rather than blurred.

### The domain key itself overstates independence
It separates `(host, binary)` and nothing else. **Two different binaries on one
host still share kernel, libm, clock source, page-table behaviour and CPU
errata** — for that entire fault class they are one domain being counted as two.
A key that is independent for the faults we care about needs host **and**
operator **and** ideally ISA to differ. This is noted in `worker.py` at the
point the key is built, not only here: a key that flatters itself is worse than
no key.

So `2dom` is itself an upper bound. The true independent-domain count of the
run that "validated" M1 may be 2, and is certainly not 3.

**Q1's capture arithmetic runs on domains, not seats**, so this compounds with
the 72% figure rather than sitting beside it. `adjudicate` now counts distinct
domains **among the agreeing workers only** — a dissenter in a third domain
lends no independence to the majority — and returns `INSUFFICIENT_DOMAINS`
below `--min-domains` (default 3).

The domain key is `host_id|bin:<sha256[:12]>`, i.e. what independence is being
claimed over. Same shape as k8s `podtopologyspread`: `topologyKey` names the
axis, `maxSkew` bounds concentration within it.

Honest consequence: **this project has never run a 3-domain quorum.** It has one
phone. That was listed as a hardware gap; it is a validity gap.

## Binary provenance closed — and the earlier runs had the trap

Every M1 result before this point ran on `S30/bin/fuelrun.v2.{host,android}`,
**built 16:16 the previous day — before every patch in the tree they were
reasoning about.** The provenance file disclosed it (*"prebuilt from an
unconfirmed commit"*), which is better than hiding it and is not the same as
closing it. The other agent hit the identical trap on G18 from the other side:
a stale binary measured against a patched tree, producing a real symptom with
the wrong attribution.

Both binaries are now built from the recorded tree and live in `bin/known/`:

| | sha256 |
|---|---|
| `fuelrun.host` | `97d24cce709f…` |
| `fuelrun.android` | `409cae613518…` |

**Re-run result: all 66 jobs agree 3/3, byte-identically, host and phone.** The
determinism claim survives the binary change; the refusal is on independence
(`isa 1`, `operator 1`), never on divergence. Those are different failures and
the run now distinguishes them.

**Recording an artifact's hash is not recording its provenance.** The old
provenance entry had the right sha256 of the wrong binary — the digest was
accurate and told nobody it predated the source. A hash pins *which* artifact;
only building it from a recorded tree pins *what it contains*.

## Still open
- **Process-per-job.** WorkManager reuses the app process; M1.1c measured that
  job N differs from job 1. Three options recorded, none implemented.
- **Panic has no schema.** Deterministic, envelope-less, neither
  `FUEL_EXHAUSTED` nor `DEADLINE_EXCEEDED`. In `HUMAN_NEEDED`.
- **Device-side cache integrity.** The host re-hashes on `get`; the phone trusts
  its own cache file.
- **Only 2 failure domains exist.** Now detected and refused rather than
  described. Closing it needs a second physical device — the standing
  `HUMAN_NEEDED` item, reclassified from convenience to correctness.
- **No network transport.** Filesystem and adb only.
