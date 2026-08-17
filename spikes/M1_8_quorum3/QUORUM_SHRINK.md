# M1.8c — quorum shrinkage is an availability attack, and the pipeline was laundering it

**Reported by review, reproduced, three defects found, all fixed.** The
adjudicator now reports `dispatched` and `returned`, and a short quorum is never
a verdict.

## The reproducer
`hyperon` panics above **1024 results** — `TK_MAX_EXPRESSION_SIZE = 1<<10`, and
`collapse` builds one expression holding every result.

```
n=1023  exit=0    status OK
n=1024  exit=134  SIGABRT  (two distinct panic sites: trie.rs:179 unwrap on
                            None, trie.rs:539 the size assert)
```

## Three defects, worst last

**1. The coordinator crashed on a crashing job.** A CRASH envelope has no
`fuel_used`, so the key is `('CRASH', None, None)` — truthy, so the
`if k else '-'` guard passed, and formatting `None` raised
`TypeError: unsupported format string passed to NoneType.__format__`. One
panicking job took down the whole run.

**2. Agreed failure was counted as agreement.** Three workers agreeing that a
job *died* returned `MAJORITY` with `CRASH` in the key, and `accepted` counted
it. The test even documented this — *"the verdict says MAJORITY and the key
carries CRASH. Caller must read the key."* **The caller was me and I did not.**
A comment is not a control. Now a distinct `AGREED_FAILURE`, excluded from
`accepted`.

**3. A shrunken quorum read as a clean verdict — and it is craftable.**
`{n}/3` was **hardcoded** and nothing recorded how many workers returned. A
2-of-3 majority where one worker *aborted* was indistinguishable from a 2-of-3
majority where all three returned and one *disagreed*. Those are opposite
claims: one is an availability failure, the other is a detected disagreement.

### Why 3 is an attack, not a bug
The panic threshold is **result cardinality**. Cardinality depends on the shard.
The **job author chooses the program**. So an adversary can author a job that
crosses 1024 results against an honest device's shard but not against their own,
kill the honest workers, and be left holding the entire quorum.

- Cost: **one crafted job.** No stake, no Sybils, no collusion.
- **Q1's 72% capture figure assumed quorum size was fixed.** It is not.
- Nothing that bounds *who gets seats* helps: `DuplicateSourceInMatch`, spread
  constraints and stake all bound seat allocation. None bound how many seats
  **survive execution**.
- **Admission cannot close it by construction.** The ban surface is syntactic
  over an enumerated op set; result cardinality is not knowable from source. A
  100-fact program panics if the query is 2-hop.

### The fix is one field, not cryptography
`adjudicate` now returns `(verdict, key, agreed, dispatched, returned)`, and
`returned < dispatched` yields **`REDUCED_QUORUM`** before any agreement test.
Display shows `agreed/returned(dispatched)`. `UNANIMOUS 2/2` and
`UNANIMOUS 2/3 (1 aborted)` are now different claims, and only the first is
payable. Same move as `quiet.sh` refusing rather than declaring.

`test_adjudicate.py`: **24 assertions**, including the attack shape
(`[ok, ok, None]` must be `REDUCED_QUORUM`, never `MAJORITY`) and every failure
status.

## Still open — the schema (their item 4)
A panic is **deterministic** (both devices abort identically, verified) but
**envelope-less**. `RESULT_FUEL_EXHAUSTED` is deterministic and payable;
`RESULT_DEADLINE_EXCEEDED` is infrastructure and unpaid. A panic is neither.
`hyperjob` has no result kind for it, so the first production panic will be
classified as whatever the code happens to do. **Decision required, recorded in
`HUMAN_NEEDED`.** The pipeline currently answers `AGREED_FAILURE` and refuses to
pay, which is a safe default and not a specification.
