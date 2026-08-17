# M1.8b — quorum-of-3 blesses a random answer 21.5% of the time

**The ban list is not hygiene. It is load-bearing on safety, and here is the
number.**

`python__sandbox__test_gnd_conv.metta` calls `(flip)` — genuinely
nondeterministic. 200 quorum-of-3 trials through the real comparison path
(`fuelrun` x3, results canonicalised, keyed on `(status, fuel_used, hash)`):

| verdict | count | |
|---|---|---|
| UNANIMOUS | 0 | 0.0% |
| **MAJORITY** | **43** | **21.5%** |
| NO_QUORUM | 157 | 78.5% |

**Accepted: 43/200 = 21.5%.** In each of those, two devices coincided by chance
and the pipeline recorded an arbitrary answer as the canonical one. No device
misbehaved; every one was honest.

## Why this was nearly missed
M1.8's first run reported this program as NO_QUORUM and the write-up called it
*"the corpus's own positive control… known and explained."* True, and it read as
reassuring. It is not reassuring: **NO_QUORUM was the 78.5% case, observed once.**
A single observation of the safe branch was treated as the behaviour.

It surfaced only because a later run happened to land on MAJORITY and the
envelopes were inspected rather than the verdict. `sorted_hash` for the two
agreeing workers was byte-identical, so this is not an artifact of the
canonicalisation work — it would have happened under the original key.

## What it means
- **Majority-of-quorum does not detect nondeterminism. It launders it.** Three
  honest devices are not a check on a job that has no single right answer; the
  scheme silently converts "no answer" into "this answer" at better than 1 in 5.
- **The ban list (S59, static admission) is therefore a safety control, not a
  performance one.** Every argument that treated it as tidy-up is wrong.
  `RISKS.md` R-NEW already noted majority-of-quorum "degrades silently under an
  S59-class divergence"; this measures the degradation.
- **More replicas do not fix it.** They reduce the coincidence probability for a
  high-entropy output and do nothing when the output is low-entropy — a boolean
  result would reach majority ~75% of the time with three replicas. The fix is
  admission, not redundancy.

## What it does NOT say
- 21.5% is specific to this program's output entropy (a 4-flip sequence, 16
  outcomes). It is **not** a general rate; a coin-flip returning one boolean
  would be far worse and a high-entropy result far better.
- Nothing here says an admitted, deterministic job is unsafe. The point is
  precisely that safety rests on admission having excluded this class.

---

## Closed — the gate exists, and it is validated in both directions

`spikes/harness/bansurface.py`, wired into `q3.py`'s ingest.

The surface is **enumerated from the shipped build**, not guessed
(`builtin_mods/random.rs:99-132`): `flip`, `random-int`, `random-float`,
`new-random-generator`, `set-random-seed`, `reset-random-generator`, and the
ambient `&rng` token.

**The ban is deliberately not blanket.** LEDGER carries a grade-A row that a job
with a correctly-bound *seeded* generator is bit-identical across two ISAs, and
S58's rule is "seeded or removed", not "removed". So the gate separates them:

| | |
|---|---|
| REJECT | `flip` (takes no generator, cannot be seeded) |
| REJECT | ambient `&rng` — the module-level generator, not seeded by the job |
| REJECT | `random-int`/`random-float` with no `(new-random-generator <seed>)` in the job |
| REJECT | `reset-random-generator` / `set-random-seed` — mutate state mid-job, so the result depends on evaluation order |
| **ADMIT** | a generator explicitly built with `(new-random-generator 42)` and threaded through |

### Both directions measured
```
corpus 67:  ADMIT 66   REJECT 1
  REJECT python__sandbox__test_gnd_conv.metta  (flip)
```
It catches the exact program that was being laundered, and rejects **nothing
else**. Contrast the variable-aliasing gate, refuted earlier at 51% rejection:
a gate is only useful if both its error rates are known.

### Pipeline result after the gate
```
admission: REFUSED 1 program(s) on the nondeterminism ban surface
store: 66 programs -> 66 distinct CIDs
UNANIMOUS=66   accepted 66/66
alpha: 0 envelope(s) non-ground
```

The headline changes from *"66/67 with one NO_QUORUM"* to **"66/66 unanimous,
one refused at admission"** — and the difference is not cosmetic. Under the old
pipeline that program reached a quorum and was accepted 21.5% of the time.

### Still open
- The gate is **syntactic**. A program that reaches randomness through
  `import!` of a module we have not enumerated, or through a Python extension,
  is not caught. LEDGER's grade-A row already says the real enforcement is
  **by build** — ship a runtime with no unseeded random ops registered — and
  this gate is defence in depth, not the primary control.
- Nondeterminism from sources other than the random module (thread scheduling,
  the two variable-id mechanisms in M1.1c) is out of this gate's scope and
  handled elsewhere.
