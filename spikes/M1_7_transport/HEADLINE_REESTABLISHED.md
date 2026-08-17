# The headline, re-established on the current codebase

**Falsifier stated first:** *the 65/65 app-vs-host result still holds after
today's changes.* It does, at 64/64 — the count changed because admission now
rejects three programs, not because anything diverged.

Both drivers that produced the earlier numbers had **silently broken** in the
interim (bearer-token regression, `spikes/REGRESSION_SWEEP.md`). A headline
whose driver no longer runs is not a result you still have.

## Both paths, current code

```
shell agent over adb    64/64 envelopes, 9.7 s,  174,063 B, unauthorised 0
                        64/64 byte-identical to host (fuel_used AND sorted_hash)

app in-process (JNI)    64/64 envelopes, 51.3 s, 174,063 B, unauthorised 0
                        64/64 identical result text vs host
```

Everything in the chain is current: bearer auth on every endpoint, admission
rejecting three rules, `canon`/`canon_alpha` normalisation, feature-matched
binaries, the app built with a token-carrying `Transport`.

## Certified, not asserted
First real use of `harness/kfcheck.certify` on a live spike. It passed, and it
would not have if any of the following were true:

- a dependency tree were dirty and unacknowledged
- an artifact predated its source (A24)
- either control had failed to fire, carried no observations, or lacked a
  stated `can_fail_because`
- any server counter were non-zero and undeclared — this is why
  `unauthorised: 0` is now load-bearing rather than decorative
- no falsifier were declared

Two controls, both fired in the same run as the working path:

| control | fired | evidence |
|---|---|---|
| admission gate | yes | refused 3 of 67 on **three distinct rules** — `flip`, filesystem, feature-gated |
| preflight refusal | yes | `battery:100%<101% -> retry with backoff`, alongside 64 successful jobs |

The second matters most: a run where the gate only ever passes cannot
distinguish "the gate works" from "the gate is absent".

## Why the count moved 66 -> 64
Not a regression. Admission grew two rules today, each from a measured failure:

| rejected | rule | why |
|---|---|---|
| `test_gnd_conv.metta` | unseeded randomness | quorum launders nondeterminism 21.5% of the time |
| `mkdocs.metta` | filesystem | relative paths resolve against the runner's working dir |
| `integration_tests__das__test.metta` | feature-gated module | fuel 580 with `das`, 107 without — both honest |

Each rejection buys something specific: the first is safety, the second removes
a divergence quorum is structurally blind to, the third is what makes
`manifest = 2` possible.
