# H250 — the veto I shipped 20 minutes earlier, attacked

**Row:** `WORK_QUEUE.md` H250 · **Lane:** AGENT-1 · **ATTACK cycle (§2)** · **2026-08-19**
**Check:** `python3 spikes/H250_veto_timing_and_paths/probe.py` — **10 arms, 10 pass**,
pre-fix arm pinned to `82e635b` and guarded.

Target chosen by §2's *self-authored data first*: `provenance.py` **v5**, shipped
by this lane in the previous cycle. Two defects, both live, both mine.

## D1 — the veto's prose arm is evaluated before the prose exists

H239's veto refuses an exclusion whose leaf is cited by the spike's own
certification **or its prose**. But `record()` runs *inside* the spike's run and
`RESULT.md` is written *after* it.

```
spikes with a provenance.json and a RESULT.md:
  RESULT.md written AFTER  the record : 105   <- veto read a haystack missing half its evidence
  RESULT.md written BEFORE the record :  58
  no RESULT.md at all                 :   9
```

**Not hypothetical:** S84's `.wall_us_citable` — one of the three real
measurements the whole veto exists to protect — is **REFUSED with the prose and
ALLOWED without it**. An exclusion declared in that window would have been
honoured forever.

**A15, a control that cannot fire, sitting inside the mitigation for an A22.**

**And my own H239 probe measured the wrong state.** Its A4 arm reads *mature*
spikes with their prose already on disk. That is not the state a production
`record()` runs in. **Fourth arm this span to name one condition and test
another — this one inside the probe written to catch that.**

**Fixed by running the veto again where the evidence is guaranteed to exist.**
`recheck` v3 re-vetoes at read time: by the time anyone asks *did this reproduce*,
the write-up exists, because someone is reading the spike. A refused exclusion
reads `DRIFTED` and names the reason. The record-time pass survives as an early
warning and is no longer the answer — `commit_scoped.sh` v9's shape, one module
over.

## D2 — two leaves, one dotted path, and the correct hash of the wrong field

`json_leaves` renders `{'a': {'b': 1}}` and `{'a.b': 2}` identically as `.a.b`.
v5 did `dict(json_leaves(doc))`, which keeps the **last**, while `_leaf_drop`
removes the **first**:

```
pre-fix, on {'a': {'b': 1}, 'a.b': 2}, excluding '.a.b':
  problems raised   : []          <- accepted silently
  value recorded    : 2           <- the flat leaf
  leaf removed      : {'a': {}, 'a.b': 2}   <- the NESTED one
```

The record describes one field and the hash was taken over the removal of
another. **A24 — and it is H211's defect, which this lane closed four hours
earlier, reappearing inside the module written to close it.** 119 artifacts on
disk carry a dot or bracket in a key, mostly manifest blocks keyed by file path.

**Fixed by REFUSING the ambiguous path, not resolving it** — H211's choice for
H211's reason: resolving silently picks one of two answers and records neither as
a choice.

## Not a wider hole

* G54's honest reproduction **still reads `REPRODUCED`** (B4a).
* A real scientific change (`arms.A_prior.mrr`) **still reads `DRIFTED`** (B4b).
* All **176** provenance records under `spikes/` driven through v1 and v3:
  `OK 156 · DRIFTED 17 · MISSING 3` under both. **Zero verdicts moved.**
* 33 of 34 harness selfchecks green; `demo8.py` is red at `HEAD` for an unrelated
  dirty-tree record and was red before this cycle.

## What is still open, and it is the same residual H239 recorded

The read-time veto closes the *timing* hole, not the *coverage* one. A
load-bearing leaf cited **nowhere** — not by name, not by value, in neither
certification nor prose — is still allowed at both moments. `H86.wall_citable` is
that shape. The veto remains a **gate, never an oracle**.
