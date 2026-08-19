# M1.13 — the quorum names its defendant, and never a silent worker

**AGENT-1, 2026-08-19.** Check: `python3 spikes/M1_8_quorum3/test_dissenters.py`
(13 assertions, one of them a negative control). Production change:
`spikes/M1_8_quorum3/q3.py` — `dissenters()`, one row field, one report marker.

M1-DEMO §8 item 5 wants *"one injected cheat caught"*. S26 proved the cheat is
CATCHABLE and named — 200 of 200 attributed to exactly one worker — and filed
this row because `adjudicate()` returns `(verdict, key, agree_count, dispatched,
returned, domains)` and never says WHO. A protocol that pays or slashes cannot
act on a verdict with no defendant.

## F1 FIRED, and it changed the design rather than the schedule

The row proposed *"return the dissenting worker ids alongside (verdict, key,
agree_count, …)"*. Preregistered F1 was: *if any existing caller unpacks a
fixed-width tuple, appending is a breaking change and I must not append.*

It fired, twice over:

* both production callers unpack exactly six names —
  `v, k, n, disp, ret, dom = adjudicate(envs)` (`q3.py:511`, `q3_head.py:490`);
* `test_adjudicate.py` **asserts the arity itself** — its own last line reads
  *"soundness: empty result member cannot agree; arity uniform at 6"*.

So appending is precisely the 5-vs-6 defect already recorded inside
`adjudicate`'s `NO_RESULTS` branch, which *"took the coordinator down with a
ValueError instead of recording NO_RESULTS"* while the suite stayed green,
because `test_adjudicate.py` asserted only `[0]` and exercised the function
differently from the caller. **The defendant therefore travels as a ROW FIELD**,
a dict key next to the envelopes it is derived from — a dict takes a new key
without moving anything. `test_adjudicate.py` passes **unmodified** before and
after (36 assertions), which was preregistered control C3: needing to edit the
test to make the change pass would have been weakening a gate to pass it.

**This is a deviation from the row's letter and it is not a narrowing of the
row's requirement.** The requirement is that the pipeline name the defendant;
"return it alongside" was the row author's suggested mechanism, and that
mechanism is refuted by the arity assertion its own suite already carries.

## ABSENCE IS NOT DISSENT — the defect this field could easily have shipped

S26's `cheat_attr.dissenters()` computes `kk != k` over the raw key list. **A
worker whose key is `None` did not ANSWER; it did not DISAGREE**, and `None != k`
is true. MEASURED, not read — blank `phone`'s result member on an otherwise
agreeing row:

```
keys: ['LIVE', 'LIVE', 'LIVE', 'None']
S26 dissenters() names: ['phone']        <-- accused of lying for being offline
q3  dissenters() names: []               <-- REDUCED_QUORUM already handles this
```

On a `NO_RESULTS` row S26's helper is saved by coincidence: the no-majority
sentinel and the did-not-answer sentinel are **both `None`**, so `None != None`
is False. That is one sentinel carrying two meanings inside the branch that
cannot tell them apart — H88's class, in a helper written before H88 existed.

It matters because the committed sidecar `adjudicate_named.py` calls
`S26mod.dissenters(envs)` **directly**, so the sidecar names a silent worker.
It never showed up because S26's own sweep skips rows where a cheat is
inexpressible, and the sidecar's test drives only that same sweep.

`q3.dissenters()` names only under a real majority (`n >= 2`): under `NO_QUORUM`
every live key is a plurality of one, so there is no majority to dissent FROM and
naming one invents a defendant out of a tie; under `NO_RESULTS` there is nothing
to dissent from at all. Both return `[]`.

## F2 and F3 did not fire

| assertion | value |
|---|---|
| injections where q3 and S26 agree | **256 / 256** |
| named exactly the injected liar | **200** (reproduces S26's certified 200/200) |
| unnameable — 14 `NO_RESULTS` × 4 workers | **56** (S26's own 56) |
| honest quorum accuses | **nobody** (C1) |
| planted cheat names | **exactly the planted worker** (C2) |

**The negative control is the assertion that matters.** `C_regression` requires
S26's shipped helper to STILL name the silent worker on the same input where
q3's must not. Without it, every "names nobody" line above passes just as
happily against a function that names nobody ever, and the file would prove
nothing about the defect it exists to hold shut.

## The check reads the live q3.py, never a copy

`main()` is called unguarded at `q3.py`'s module level, so it cannot be
imported. S26 answered that by committing `q3_head.py`, a head-COPY — and a copy
is the C-family failure: it drifts from the file it stands for and nothing says
so. `test_dissenters.py` exec's the prefix of the real file instead, so it
cannot pass against a `q3.py` it is not actually testing.

## What is NOT claimed

The committed `result.json` predates this change and does not carry
`defendants`; it will on the next pipeline run. The wiring is asserted from
source, and the field's SEMANTICS are asserted against real committed envelopes.
No device run was performed in this cycle and none is claimed.
