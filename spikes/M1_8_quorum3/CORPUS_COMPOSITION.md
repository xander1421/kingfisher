# What the 64-program corpus could have detected

`repro: spikes/M1_8_quorum3/classify.py`

**Falsifier, stated before running:** *the corpus has full discriminating
power — all 64 programs evaluate, so 64/64 agreement is evidence of
cross-architecture evaluation determinism.*

**Refuted.** 38 of the 64 never execute the code under test.

| class | n | distinct hashes | fuel | what it is |
|---|---|---|---|---|
| `empty` | **14** | 1 | 58–107 | no output at all; `results_text: ""`, keyed on `sha256("")` = `e3b0c442…` |
| `import-failure` | **24** | 14 | 107 | `(Error (import! …) Failed to resolve module top:agents)` — the Python extensions are absent, so MeTTa never reaches the program |
| `error-only` | **4** | 3 | 107–1829 | evaluated, result is an assertion `Error` |
| `evaluated` | **22** | 15 | 132–50794 | real evaluation, real results |

```
executed MeTTa:      26/64
could NOT diverge:   38/64
```

Identical on all four workers (`host-a`, `host-min`, `host-x86`, `phone`).

## Why this matters

Nothing diverged, and that remains true. What is withdrawn is the **size of the
evidence base**. On 38 of the 64 programs a genuinely divergent host would have
agreed anyway, because there was nothing to disagree about: an empty result is
byte-identical to another empty result, and `Failed to resolve module
top:agents` is byte-identical on aarch64 and x86_64 because it is produced by
the module resolver before any evaluation happens.

So the honest claim is **26 programs executed MeTTa across four workers and
agreed**, of which 22 produced non-error results with 15 distinct hashes. Not
64.

This is **family A** — the instrument cannot produce the answer. It was not
found by a check failing. Every check passed, every run agreed, and the number
was arithmetically correct. It was found by asking what the corpus *could* have
detected, which no gate in this repo asks.

## The stale artifact underneath it

`result.json` claimed `INSUFFICIENT_DOMAINS: 64`. Re-adjudicating the same
envelopes under current code gives:

```
INSUFFICIENT_DOMAINS = 50    NO_RESULTS = 14
```

The artifact predated the `check_nonempty` wiring in `key()` by **7 minutes**.
The 14 empties now correctly route to `NO_RESULTS` — a worker that returned an
empty capture did not answer, and three workers agreeing on nothing is not a
quorum. `provenance`'s staleness check catches this by mtime, and `certify`
refuses on it; the artifact simply had not been regenerated since the guard
went in.

**A guard added and a result regenerated are two separate acts.** Wiring
`check_nonempty` fixed the code and left every stored artifact still asserting
the pre-fix number, in the file a reader would quote.

## What this does not say

- It is not a divergence. Zero workers disagreed on any of the 26.
- It is not an argument for a bigger corpus by itself. 24 of the 38 are dead
  for one fixable reason — no Python extension modules on the runner — and
  fixing that converts them into real evidence rather than adding programs.
- The 4 `error-only` programs **did** evaluate; an assertion failure is a real,
  deterministic result. They are counted as executed.

## The general form

Every other detection floor in `DETECTION_FLOORS.md` was found by asking *what
can this check miss?* This one needed a different question: **what can the
input exercise?** A perfect check over an inert corpus reports success forever.
