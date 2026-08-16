# S35 — MORK vs hyperon on identical work, and an instrumentation flag that breaks consensus

**Verdict: GREEN, with three findings, one of which is a protocol defect nobody had.**

Prompted by a one-line question: *is this with MORK?* It was not. Every throughput number in this workspace — 383k steps/s, the 28,700 jobs/s fleet model, the 3.7× phone/laptop ratio — was measured on **hyperon**, the engine MORK exists to replace. MORK had only ever been run on device in S16, and there only for *agreement*, never for *speed*.

## The workload
Same semantics, both engines, one derivation step over a 400-node / 1,200-edge graph:
```
MORK      (exec 0 (, (Inheritance $x $y) (Inheritance $y $z)) (, (TwoHop $x $z)))
hyperon   !(match &self (, (Inheritance $x $y) (Inheritance $y $z)) (TwoHop $x $z))
```
Ground truth (3,579 unique `TwoHop` pairs) computed independently in `gen.py`, so both engines are checked against a third party rather than against each other.

## Finding 1 — MORK is 31.6× faster end to end, on the phone

Total process wall clock, best of 3, including load and dump — not an internal counter:

| | phone | host |
|---|---|---|
| **MORK** | **21 ms** | <1 ms internal / sub-10 ms total |
| **hyperon** | **663 ms** | 257 ms |

**31.6× on the same device, same task, same answer.** Both produced exactly the ground-truth set.

The fleet model in S32 is therefore **pessimistic by up to ~31× for this class of work**. 10,000 devices under 2-of-2 quorum goes from ~28,700 jobs/s to the high hundreds of thousands — *if* the workload is pattern-matching derivation, which is MORK's home turf. Deep recursive arithmetic (`fib`, `sumto`) is a different mix and was not tested; the number should not be generalised past join-shaped work.

**This makes M0.1 the most valuable unresolved item in the workspace, and it now has a price tag.** MORK carries no licence. The engine that is 31.6× faster is the one we may not ship. One email.

## Finding 2 — the two engines agree, after canonicalisation

Both produce the identical 3,579-element set, digest `ae30f82ea0f3`, matching ground truth.

But they do not agree *byte for byte*, and cannot:
- **MORK's space is a set** — it dedupes on write.
- **hyperon's `match` returns a bag** — at 60 nodes it returned 380 results for 365 distinct facts.

So cross-**engine** verification is possible but requires a canonical form (sort + dedupe) before comparison, where cross-**architecture** verification (S16, S15) is byte-exact with no canonicalisation at all.

Consequence for the protocol: `hyperjob_v0.proto`'s `EngineKind` field must be **binding on every replica of a job**, or the comparison rule has to change from `result_hash ==` to "canonicalise, then compare" — which is strictly weaker and more expensive. Mixing engines in a quorum buys independence from an engine bug, and costs the byte-comparison property that the entire thesis rests on. **Recommend: pin the engine per job, and treat cross-engine agreement as an offline audit tool rather than a consensus mechanism.**

## Finding 3 — `--timing` writes nondeterminism into the verifiable artifact

This one is a defect, found by accident when the phone appeared to produce 3,580 results against the host's 3,579.

It was not an engine divergence. Three runs on each machine, same flags, produce digest `30fb0298cf750c94` — **identical, phone and host, zero diff.** S16 stands.

The cause: `mork run --timing` writes a timing record **into the space**, which then lands in the dump:
```
(timing (exec 0 (, (Inheritance $a $b) (Inheritance $b $c)) (, (TwoHop $a $c))) 0 7887916)
(timing (exec 0 (, (Inheritance $a $b) (Inheritance $b $c)) (, (TwoHop $a $c))) 0 7667031)
```
Two runs, two different nanosecond counts, **in the artifact that consensus hashes.**

Three separate problems in one line:
1. **An instrumentation flag mutates the result.** A replica run with `--timing` and one without disagree, and the disagreement is indistinguishable from cheating.
2. **The injected value is a wall-clock duration** — nondeterministic by construction. Any replica with `--timing` enabled produces a *different hash every single run*, so it can never agree with anything, including itself.
3. It silently corrupted my own analysis for twenty minutes and looked exactly like the most damaging possible finding (an engine that disagrees across architectures).

**Protocol requirements this produces**, none of which are in the schema:
- the result envelope must pin the **engine flags**, not just the engine;
- instrumentation must never write into the space being hashed — timings belong in the envelope's `Timings` message, which S4 already has;
- a verifier should **reject** any dump containing a `(timing …)` record rather than compare it.

Generalised: *any* engine option that injects state into the result space is a consensus hazard. `--timing` is the one we found because it is the one we used; the audit should cover the rest.

## Reproducing
```sh
python3 gen.py 400 1200      # writes job.mm2, job.metta, expected.txt
./duel.sh 3
```
`duel.sh`'s canonicaliser greps `(TwoHop …)`, which is what caught the `--timing` record — deliberately left in place, because a naive canonicaliser is exactly what a real verifier would do.
