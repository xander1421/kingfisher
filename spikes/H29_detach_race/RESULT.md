# H29 — the launcher-driven checks, and what they were actually testing

`ok-1`, 2026-08-17. Row: **H29**, the decidable half. Files:
`probe.py` (the instrument), `probe.out` (BEFORE the repair), `verify.out` (AFTER).

## The claim I set out to test, which was mine

H29's row says the suite's launcher checks *"run `bash ./run_loop.sh` with
`KF_DETACHED` unset, so each one self-detaches and the assertion races the
detached child, in the direction where the not-yet-run child yields the PASSING
answer."* Four assertions in those blocks are absence-of-an-event, and absence of
an **asynchronous** event is not observable at the instant the parent returns.

Falsifiers, stated in `probe.py`'s docstring before the first run:

| id | fires if | meaning |
|---|---|---|
| FA | the absence assertions are green under the defect their block exists for | they cannot fail at all (A15) |
| FB | they stay RED with `run_loop.sh`'s post-fork `sleep 1` deleted | the sleep-dependency reading is wrong — withdraw it |
| FC | removing that sleep reddens an assertion under test on a CLEAN tree | the arms are confounded, no evidence |
| FD | any arm produces zero passes, or no rc assertion moves | the injection never reached the checks (A29) |

Arms: `control`, `NS` (sleep removed), `D1` (charset whitelist neutered — F8's
own revert), `D1+NS`, `D2` (brief gate neutered — the pre-H30 state), `D2+NS`.

## Result 1 — the hostile-callsign block was INERT, and the driver had said so

`probe.out`, arm `D1`: **63 pass / 0 fail.** The charset whitelist was neutered
and the suite did not notice. `run_loop.sh` refuses in gate order — charset,
roster, brief — and the suite never wrote `prompts/L"6.md`, so the **brief** gate
exited 1 for a reason that block is not about, and both of its assertions
(`rc=1`, and an artifact absence) were satisfied.

`python3 spikes/H7_harness_attack/falsify.py F8` printed `INERT` on that check in
HEAD. It had been printing it since the brief gate landed (H30). **Nothing read
it, because nothing runs the driver automatically — which is H29 itself.** The
instrument was right and unheard; that is not a weaker failure than a missing
instrument, it is the same one.

> **CLASS: `rc=1` does not say WHICH gate refused. A check whose only assertion
> is the exit code goes inert the moment an EARLIER gate starts refusing for an
> unrelated reason.** The no-brief block below it was immune, for the reason worth
> copying: it asserts the refusal TEXT as well as the code.

## Result 2 — FB did not fire: two assertions are green by accident of one sleep

`probe.out`, arm `D2` vs `D2+NS`, same live defect in both:

| assertion | with `sleep 1` | with it removed |
|---|---|---|
| `it never reached the turn` | **RED** | green |
| `and never detached an unbriefed lane` | **RED** | **RED** |
| `launcher never reached claude` (after result 1's fix) | **RED** | green |

`run_loop.sh:275` sleeps 1 s after forking. Its comment gives it no test-facing
purpose. Delete it — a change any lane could make as a speed-up — and two
assertions pass over a defect that is present. The green was a coin landing
heads, not a property.

## The repair, and it is not a `sleep`

A child's artifacts are the child's. **The detach announcement is the parent's**,
printed on the parent's own stdout before it exits, so an assertion on it cannot
be won by being early. Each block gained one:

* `and refuses for THAT reason, not an earlier gate's` — greps the charset
  refusal text, so a future gate refusing first goes RED instead of quietly inert
* `and announced no detach (the PARENT prints it, so this cannot race)`
* `and announced no detach (synchronous, unlike the child's artifacts)`

plus `prompts/L"6.md` so the charset gate is the only refusal left, and
`wait_file` replacing two fixed `sleep 1`s at the two checks that assert an
artifact IS there (those raced toward a false RED — flaky, and a flaky gate is a
bypassed gate, H14). Suite 63 → 66 checks, and **faster**: 9.06 s → 7.34 s.

`verify.out`, after the repair — the new assertions are red in every arm where
the defect is present, sleep or no sleep:

```
synchronous assertions RED under D1 with AND without the sleep:
    ['and refuses for THAT reason', 'announced no detach (the PARENT prints it']
synchronous assertions RED under D2 with AND without the sleep:
    ['announced no detach (synchronous']
```

The four original absence assertions are left in place (§5: a control is not
deleted to make progress) and are now belt-and-braces; the block's verdict no
longer depends on child scheduling.

`falsify.py` v4 adds **F25** (an earlier gate refuses first) and **F26** (a lane
with no brief launches and detaches anyway — the defect that reached three of
three live lanes at 13:25 and had **no falsifier at all**). Measured:

```
CONTROL  unmodified copy: 66 pass, 0 fail  -> ok
F8   FIRES  launcher refuses what the hook will not gate   (was INERT)
F25  FIRES  and refuses for THAT reason, not an earlier gate's
F26  FIRES  and announced no detach (synchronous, unlike the child's artifacts)
```

## Result 3 — a launcher defect, split out as H61 rather than fixed here

FC fired: on a **clean** tree, removing that same `sleep 1` reddens the
20-simultaneous-launcher lock checks — 4 survivors instead of 1 on the first run,
and 1 survivor with **0** HELD refusals on the second. Different block, so the
arms above stand; different component, so it is not this row.

The lock is acquired by the parent with `noclobber`, then the detached child
reclaims it via `KF_LOCK_OWNER`. Between the parent's exit and the child's
reclaim the lock names a **dead pid**, which line 255's liveness test correctly
reads as stale — so a competing launcher takes the callsign. The 1-second sleep
is what keeps that window closed, and its comment does not say so. **Whether 1 s
is enough under fleet load is UNMEASURED**, and this result is not a claim that
it is not.

## What H29 still blocks on

Only H17: the suite `mktemp -d`s into `/tmp`, and §10 says nothing outside the
workspace is written. Gating every commit on it decides that dispute by default,
and an agent narrowing a rail it operates under is A22. The concurrency blocker
the row was originally filed with is corrected in the row and was false.

## Reproducing

```sh
bash spikes/harness/test_loop_gate.sh                        # 66 checks, ~7 s
python3 spikes/H7_harness_attack/falsify.py F8 F25 F26       # 3 fire, control green
python3 spikes/H29_detach_race/probe.py                      # 6 arms, ~2 min
```

`probe.out` is v1's output, measured on the suite before the two synchronous
assertions existed; `verify.out` is v2's. To reproduce v1's numbers, run
`probe.py` against the parent commit's `spikes/harness/test_loop_gate.sh`.
