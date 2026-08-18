---
name: fault-expression
metric: detected_mutation_classes
metric_direction: higher
target-metric: 4
---

# Goal

**Raise the number of fault classes the quorum can actually detect.**

The mission's entire claim is that a result is trusted because anyone can re-run it
and compare bytes. That claim is only as strong as the corpus's ability to
**express** a fault: if a wrong answer produces the same bytes as a right one, the
comparison sees nothing and reports agreement.

`spikes/M1_9_mutation/RESULT.md` measured this against the live agreement key by
planting faults in the engine and asking whether quorum noticed:

| planted fault | detected |
|---|---|
| a wrong `-` | 4 / 64 |
| a changed resolver message | 24 / 64 |
| **a wrong `<`** | **0 / 64** |
| **an extra stdlib rule** | **0 / 64** |

Two of four classes are **completely invisible**. A replica whose `<` is wrong at
every boundary passes quorum `UNANIMOUS`. `fuel_used` does not move when the
stdlib grows, so an altered stdlib rule is invisible unless something invokes it.

That is not a corpus problem to be tuned away — it is the trust claim failing for
two named fault classes, and it is measurable.

## Metric

`detected_mutation_classes` — the count of the four planted classes for which at
least one corpus program yields a differing agreement key. Currently **2**.
Target **4**.

Computed by `python3 spikes/M1_9_mutation/mutate.py` (~40 s, no device, no
timing). Load-insensitive by construction, which matters because `quiet.sh`
refuses on this machine and any timing-based metric would be fiction (§3).

## Evaluation

An iteration proposes a change to the **corpus or the agreement key** — not to the
mutation harness, which is the instrument and may not be tuned to make its own
subject look better (A22).

Accept only when **all** hold:

1. `detected_mutation_classes` rose, **or** a pre-stated falsifier fired and it
   fell for that reason (see the ratchet section in `autoloop.md`).
2. The honest arm is unchanged: the existing agreement over the admitted corpus
   reproduces byte-identically. A verification change that moves the honest
   baseline is a new bug, not a fix.
3. At least one control **fails first** against a deliberately broken variant, in
   committed output. A control seen only passing is the family-A defect.
4. `kfcheck.certify` returns `ok=true`; controls carry persisted observations, not
   prose.
5. No device touched. No `spikes/harness/` change counted toward the metric.

## Falsifier, stated before any run

> If raising `detected_mutation_classes` requires enlarging the corpus rather than
> improving what the key distinguishes, then the metric measures corpus SIZE and
> not fault expression, and this program is measuring the wrong thing.

Check it by holding the corpus fixed and varying only the key. If the metric
cannot move that way, say so and stop — a program that cannot fail its own
falsifier is not a program.

## What this program must not do

- Not touch `spikes/M1_9_mutation/mutate.py` to make the number move. That is the
  instrument.
- Not count a class as detected on a single program without reporting how many of
  64 expressed it; `4/64` and `64/64` are different facts about the same class.
- Not publish. §11. The summary goes to
  `proposed/autoloop-fault-expression.md` and a human decides the rest.
