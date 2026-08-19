# H197 — string-hash randomisation reaches a published commitment, and F3 fired

`repro: python3 spikes/H197_hashseed_commitment/probe.py`
`check: python3 kitchen/test_h197.py`

**`certify ok=True`, 2 controls fired. F1 and F2 did not fire. F3 FIRED, and it
downgrades my own row — see the verdict.** Found while running S37's F2 consumer
sweep, not by looking for it.

## THE DEFECT, MEASURED

`W7_streaming_witness/streaming_verifier.py` declares `SEED = 20260817`, builds
`rnd = random.Random(SEED)` and records `'seed': SEED` in its result — it claims
determinism explicitly. Three consecutive runs of unchanged code:

```
final_chain_head   b7e4804ca77576a2…   d315116ba544672b…   f69b63afa7002279…
committed at HEAD  1496f418e23e0312…   (a fourth value)
```

**`PYTHONHASHSEED=0` makes it stable** — `f1a2e463a6a4721d…`, twice. CPython
randomises string hashing per process, so an unsorted `set`/`dict` over strings
is reaching the key path.

## SWEEP — F2 DOES NOT FIRE, SO IT IS A CLASS AND NOT ONE SPIKE

Each spike run twice in the default environment and twice under
`PYTHONHASHSEED=0`; every 64-hex value in its artifact compared.

```
W7_streaming_witness         hashes= 16  unstable=10  unstable@HASHSEED=0=0   HASH-ORDER
W9_bound_streaming_witness   hashes= 13  unstable= 1  unstable@HASHSEED=0=0   HASH-ORDER
W6_incremental_witness       hashes=134  unstable= 0  unstable@HASHSEED=0=0
W2_witnessed_trie            hashes=  1  unstable= 0  unstable@HASHSEED=0=0
S85_verify_vs_reexec         hashes= 15  unstable= 0  unstable@HASHSEED=0=0
```

**2 of 5, both fully explained by hash order.** W7's ten are
`final_chain_head`, `final_root`, and the `chain_head`/`root` pair of three
sampled records; W9's one is `continuous_reduction_stream/final_root`.

**The two-run design is the point.** A single run says nothing, and comparing
against the *committed* value would confound *unstable* with *drifted since it
was committed* — different defects. **C1 requires at least one spike to come out
STABLE**, or the probe is calling everything unstable and distinguishing nothing;
three did.

## F3 FIRED. THE BLAST RADIUS IS ZERO TODAY, AND THE ROW IS DOWNGRADED

F3, preregistered: *if every varying hash is an internal benchmark field that no
RESULT.md, LEDGER row or downstream spike quotes, the blast radius is zero and
the row is a note, not a finding.*

```
0 of 11 varying hashes are quoted in any .md or .log
0 downstream .py / .json / .tsv files reference them
```

**So this is a LATENT defect, not an active wrong number.** Nothing published
today is wrong because of it, and I am not going to write it up as though
something is. What it costs is the property the mission is built on: **a third
party re-running W7 gets a different chain head and cannot compare bytes.** The
value is not quoted anywhere *yet*, which is exactly the condition under which it
would become quoted without anyone noticing.

Stated as a scope limit rather than smuggled back in as severity: F3's grep is
over `.md`/`.log`/`.py`/`.json`/`.tsv` in this workspace at HEAD. It cannot see a
number a human copied into a message, and it says nothing about future use.

## C2 REFUSED MY FIRST TARGET LIST, AND IT WAS RIGHT

The first run came back `certify ok=False — CONTROL C2_hashes_were_found DID NOT
FIRE — run is VOID, not negative`. I had named `W2_witnessed_trie/attack.json`
and `S80_completeness_bytes/completeness.json` as targets. **Both contain zero
64-hex values** — `attack.json` is `{seed, findings}`, S80 publishes byte counts —
so the probe would have reported them *perfectly stable* while measuring nothing.

**That is precisely the failure C2 was written for, firing on its author.** The
control is unchanged; the target list was wrong. W2 now reads `witness.json`
(1 hash, stable) via `trie_witness.py`, and the spikes whose artifacts carry no
commitment at all are recorded in `NO_COMMITMENT_IN_ARTIFACT` with their measured
zero-count — **out of scope is a different statement from stable**, and a silent
exclusion would have read as coverage (H186).

## WHY THE S37 CONSUMER SWEEP DID NOT SEE THIS

`S37/consumers.sh` records `rc` and `certify ok=` as its verdict columns. Both
are stable while the hash moves. That was a deliberate choice — hashing stdout
would flag every run, because these scripts print timings — and it is also the
sweep's blind spot. **A verdict column that cannot see a changing commitment is
H176's shape**, and it is named here rather than left for someone else to find.

## NOT CAUSED BY S37, CHECKED RATHER THAN ASSUMED

The head varies run-to-run under unchanged code, so it is independent of the
`verify_completeness` cutover committed in `73a9203`.

## WHAT IS NOT DONE

**The cause is not located and no spike is fixed.** The row is the measurement:
which spikes, how many fields, and whether anything published depends on it.
Locating the unsorted `set`/`dict` in W7 and W9 and sorting it is the repair, and
it is left OPEN — §12.1, and because a fix that changes a published chain head
needs its own before/after record.
