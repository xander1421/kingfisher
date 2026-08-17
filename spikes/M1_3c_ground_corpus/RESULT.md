# M1.3c — "which is the entire corpus" is true on 26 of 64 and untested on the rest, and 23 of the untested mention variables

**AGENT-1, 2026-08-17.** `certify ok=true`, 3 controls, all fire; the falsifier
**did not fire**. Reproduce: `python3 spikes/M1_3c_ground_corpus/ground.py`
(~1 s, no seed — it reads committed artifacts).

## The sentence under test

`spikes/M1_3_worker/WORKER_RESULT.md:73`, which closes what `WORK_QUEUE.md` M1.1
calls the largest open M1 issue — process-per-job against WorkManager's process
reuse:

> Process reuse is safe for **ground-result** jobs, which is the entire corpus.

The load-bearing clause is the parenthetical. Derivation (2) of the
process-per-job requirement is that `NEXT_VARIABLE_ID` is process-global, so job
N occupies a different variable-id space than job 1. A ground result has no
variable, so no printed id, so nothing for that id space to move. The sentence
is self-authored, was never measured, and `HANDOFF.md` NEXT 3 says in as many
words: *verify before spending a cycle.*

**Falsifier, stated before the run:** if any admitted program's recorded result
is non-ground, reuse is not safe for this corpus and M1.1's issue is not closed.

## What was measured

```
programs                      64
recorded results non-ground    0      <- falsifier did NOT fire
executed MeTTa                26      <- the evidence base
untestable                    38
  ... whose SOURCE mentions a variable   23
sources mentioning a variable  45 of 64
```

**Where it can be tested, the sentence holds: 0 of 26.** No variable survives
into any recorded result of any program that actually evaluated.

## Where it does not hold is not the claim, it is the word "entire"

38 of 64 programs never reached evaluation. Their recorded results are ground for
reasons that have nothing to do with the programs:

- **14 emit the empty string.** An empty result is ground the way
  `e3b0c442…` is a hash of data — it is CLAUDE.md's own family-B example, and
  counting it as evidence of groundness is the same substitution.
- **24 die at their first `import!`** with `Failed to resolve module top:agents`,
  because the Python extensions are absent on this host. That string is ground on
  every architecture whatever the program would have returned; it is evidence
  about the module resolver, not about the program.

**23 of those 38 have sources that mention a variable.** The source scan is
reported as an **upper bound and never as the verdict** — a program can bind `$x`
in a rule that never surfaces in a result, and treating a name grep as the
property is A30, the mistake S75 made with `fn witness`. But it is the right
bound for this question, because it says the untested set is not obviously safe.

So the honest form of the sentence is: **process reuse is safe for the 26
programs that execute in this environment.** The other 38 are refused by an
absent dependency, not by anything about their determinism, and the environment
that makes them run is the deployment environment.

This is `CORPUS_COMPOSITION.md`'s finding arriving at a second claim. That
document refuted *"64/64 agreement is evidence of determinism"* by counting what
the corpus could have shown; the same corpus is here supporting a second
64-shaped claim, and the same 38 programs are carrying it.

## The verdict on M1.1

**CORRECTED, not reopened.** M1.3b's mechanism is real: a fresh `Metta` per job
plus `canon` at the comparison boundary, 31 distinct raw hashes collapsing to 1.
What is withdrawn is the scope. The closure is conditional on the current
environment, and `WORKER_RESULT.md` already names the residual — *"it remains
unsafe for the aliasing class, whose admission gate is still open"* — so the two
sentences were in tension in the same paragraph, one of them saying the corpus is
entirely safe and the next saying a class of it is not.

Two ways to close it for real, neither taken here:

1. **Admit on the property, not on the population.** The ban surface (`D5`) is
   the place: a job whose result can contain a variable is a different class, and
   the admission gate decides it per program rather than a sentence deciding it
   for the corpus.
2. **Keep process-per-job for the variable class only**, which costs the fork
   exactly where derivation (2) is live.

## Controls

| control | fired | what it rules out |
|---|---|---|
| `C_scanner_finds_variables` | yes — 45 of 64 sources, variables found | a regex matching nothing would report a perfectly ground corpus and be indistinguishable from the claim being true |
| `C_sources_resolve` | yes — 64 of 64 CIDs resolve to blobs in the committed store | the source half being about a subset nobody named |
| `C_execution_split_reproduces` | yes — 26, against `CORPUS_COMPOSITION.md`'s independently published 26 | this file's own notion of "executed" being a second unvalidated instrument |

The third is the one worth keeping: the executed/not-executed split is computed
here from the resolver-error string and the empty result, by different code than
the published classifier, and it lands on the same 26. A disagreement would have
meant one of the two documents is wrong about the corpus, which is a bigger
finding than this one.
