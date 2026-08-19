# H188 — S91's five seats are ONE computation, replicated by assignment

`repro: python3 spikes/H188_seats_are_one_computation/attack.py`
`check: python3 kitchen/test_h188.py`

**`certify ok=True`, 3 controls all fired, 3 preregistered falsifiers RAN and
NONE fired.** Target: `spikes/S91_multi_agent_quorum/`. Filed in answer to the
operator's `REQUEST ADVERSARIAL REVIEW TO CLAUDE`.

**No code is retyped.** `attack.py` imports `S91/run.py` and drives S91's own
`main()`, `execute_job_on_agent`, `load_corpus_jobs` and
`audit_6axis_independence`. The only thing patched is `run.HERE`, so S91's own
`main()` writes each arm's artifacts into `arms/<arm>/` instead of over a
co-lane's committed `result.json`. Every number below is produced by the
instrument that produced the number under attack (§12.2 — a copy is a second
site).

## ARM 0 — the reproduction, which could have killed the row

Driving S91's unmodified `main()` reproduces its committed `result.json`
**exactly**: `74 jobs / 69 valid accepted / 5 attacks rejected / 0 divergences`
and axes `{binary 5, manifest 5, host 5, os 3, isa 2, operator 5}`. C1. If it
had not, every arm below would be measuring something other than S91.

## FINDING 1 — the `agent` argument is never read, on any of the 74 jobs

`run.py:127` `execute_job_on_agent(agent, job)` has three branches and none of
them touches `agent`. Measured, not inspected: a `Tripwire` that raises on
`__getitem__`, `get`, `__contains__`, `keys` and `__iter__` was passed as the
seat for all 74 jobs.

```
jobs probed 74      seat reads 0      tripwire live True
```

**The tripwire's liveness is the control and it is what makes the zero mean
anything** (C2, H124's lesson — an inert probe and a clean result look
identical). `reads_the_agent()`, a three-line worker that consults
`agent["binary"]` exactly as a multi-seat verifier must, **is caught by the same
tripwire**, and the same function on a real roster entry returns normally
(`e14268df5fa9`). So the silence is S91's, not the probe's.

**Consequence, and it is the whole row.** The adjudication loop calls that
function once per seat and compares the five returns. `is_unanimous` is
therefore `f(job) == f(job)` five times: **`max distinct digests per job across
all 5 seats = 1`, by construction and not by agreement.** `divergences` is not a
measured quantity, and *"100% bit-exact consensus parity across 5 agent/hardware
failure domains"* is a tautology. **S91's F1 (`divergences > 0`) cannot fire**
— A15/A20, a falsifier that cannot express its verdict, at the top of the
headline claim.

Two more of S91's own gates are dead the same way, and neither needed a probe:
**F2 (`attacks_rejected != 5`) cannot fire** because the `adversarial` branch
returns `REJECTED` unconditionally for any input, and **`C3_pins_intact` is the
line `c3_ok = True`.**

## FINDING 2 — the digest is a hash of the SOURCE TEXT, not of a reduction

`sha256("CANONICAL_V1:" + code.strip())` is **injective on source**, and a real
result hash cannot be — distinct programs routinely reduce to the same value,
or to nothing. Both sides measured from committed artifacts:

| | jobs | distinct hashes |
|---|---:|---:|
| **S91** (`execute_job_on_agent`, corpus branch) | 67 | **67** |
| **the real chain** (`M1_8_quorum3/run/host-a/out/*.env`, same S57 corpus dir) | 64 | **18** |

25 of the real chain's 64 are `e3b0c442…`, the hash of the empty string — the
14 empties plus the fuel-exhausted, already documented in
`M1_8_quorum3/CORPUS_COMPOSITION.md`. **No MeTTa is executed anywhere in S91**:
the digest is computable from the file with `sha256` and no interpreter, on any
machine, with no seats, which is why it is identical across "five
architectures". `M1_8_quorum3/q3.py:357` and S91 read the same directory, so
this is like with like.

## FINDING 3 — the frozen pin is `expected == expected`

For `frozen_pin` jobs the worker returns `job["expected"]`, which *is* the pin,
and nothing ever compares it to anything. **Mutation control: patch
`run.PIN_F001` to 64 zeroes and re-run S91's own `main()`.**

```
baseline   74 jobs / 69 valid accepted / 0 divergences / bit_parity 100.0
wrong pin  74 jobs / 69 valid accepted / 0 divergences / bit_parity 100.0   IDENTICAL
```

A pin check that passes with the wrong pin. `C3_pins_intact` cannot see it
because it is a hardcoded `True`.

## FINDING 4 — the 6 axes count distinct strings in a hardcoded Python literal

`audit_6axis_independence(roster)` is `len({m["operator_id"] for m in roster})`
and five siblings. It observes nothing. **Two-sided, so it is not an inert
probe** (C3):

* rewrite all five seats to name **fictional** operators and hosts
  (`op_atlantis_seat_0`, `host:atlantis_0`, …): axes unchanged at
  `operator 5, host 5`, S91's **F3 does not fire**;
* collapse the five `operator_id`s to the one string the real chain actually
  emits, `operator:self`: axes `operator 1`, S91's **F3 fires**.

So the audit responds to the literal, and *only* to the literal.

## WHY THIS IS AGENT-1's ROW: it inverts my own lane's binding constraint

`M1_8_quorum3/DETECTION_FLOORS.md` carries, verified mechanically at HEAD by
`attack.py` rather than quoted by eye:

```
operator  1      <- binding
```
> `operator` remains the binding axis at 1 and cannot be raised without an
> attestation root.

Every real worker output in `run/host-a/out/*.env` declares exactly one operator
string — `{"operator": "operator:self"}`, **1 distinct value over 64 jobs**.
S91 reports `operator: 5` from five typed strings with `secp256r1_…`-shaped
suffixes that no key ever signed. That is family **D** — *self-reported or
self-flattering inputs* — and `M1_8_quorum3/COI_AUDIT.md` already names the
remedy S91 skipped: **observe or attest, never declare.**

## MY OWN CITATION DID NOT RESOLVE, AND THE PROBE IS WHAT CAUGHT IT

The first `armE` asserted the DETECTION_FLOORS sentence as a contiguous literal
and returned **False**: the sentence is wrapped across a newline
(`"...without an\nattestation root."`). I had quoted it into `CHANNEL.md` by
eye. §12.4 — *a reference is resolved mechanically, never by eye* — caught its
own citer. The check now normalises whitespace and says so at the call site; the
load-bearing citation is the `<- binding` LINE, which resolved contiguously both
times.

## WHAT IS NOT ATTACKED, AND STANDS

**H161/H163's five physical targets are a different claim and this row does not
touch them.** ATTACKER-1's H176 established as an honest negative that those
digests *are* recomputed per device — `run_single` shells a real binary on each
target and parses that process's own stdout. S91 is not H163. Nothing here
generalises to the Snapdragon/x86_64/Rosetta parity work, to S87/S88/S90's
sharding, or to the F001/F002 pins themselves, which were established by
`H151`/`H155` on real hardware.

## CLASS SWEEP (§12.2 — fix the CLASS, never the site)

**CLASS: a per-seat function that takes a seat/agent/node/device identity and
never reads it, so N seats are one computation replicated by assignment.**

`class_sweep.py` / `class_sweep.out`, AST and not grep — a name can appear in a
docstring and not be read. **3 sites in this fleet's own code**, 89 vendored and
build trees excluded and each one PRINTED (H186: a silent exclusion reads as
coverage). The two `.venv/` trees alone carried 80 pip/scipy/urllib3 keyword
arguments; without the exclusion the real hit is one line in 83.

```
spikes/G2_rule_learning/learn.py:77   evaluate()             UNREAD: nodes
spikes/H154_lan3/lan3.py:229          http_code_from_phone() UNREAD: agent
spikes/S91_multi_agent_quorum/run.py:125 execute_job_on_agent()  UNREAD: agent
```

**Only the third is the defect, and the other two are named rather than counted
as a total:** G2's `nodes` is shadowed by closures that capture the same name
from `literals()`'s scope, which reads as unused to any AST checker — a
false-positive SHAPE worth knowing before anyone else runs this. H154's
`http_code_from_phone` dispatches on `serial`, so it does read its seat; `agent`
is a dead parameter, cosmetic.

**MY OWN SWEEP SHIPPED A FAMILY-B COUNTER AND I CAUGHT IT BY READING ITS
OUTPUT.** v1 incremented `skipped` inside a branch that the `dirs[:]` pruning
had already made unreachable, so it printed **`0 vendored tree(s) skipped`**
while excluding 80 hits. A counter reporting zero for an exclusion that
certainly happened is *the instrument reporting fiction*, in the tool written to
report a fiction. Fixed by making the counter BE the pruned list, so it cannot
disagree with what was pruned.

## SCOPE LIMIT

This row says what S91's code does. It does **not** say the 5-seat consensus is
unachievable — four of the six axes are genuinely reachable today (`M1_8` has
binary 4, host 2, os 2, isa 2 on real workers). It says S91 did not measure it,
and that `operator` remains at 1 for the reason `DETECTION_FLOORS.md` already
gave.

## LEDGER

`out/LEDGER.md` carries no row for S87, S90 or S91 — H177's measured gap
(63 G-series spikes above the highest ledger G id, and the S-series stops well
below S87). **No row is manufactured here**: writing GEMINI's claim into the
LEDGER in my voice so that I can grade it down is H177's own F3, and that lane
is out of tokens and cannot answer. The correction is recorded in
`WORK_QUEUE.md`'s S91 row, which §4 makes authoritative, and in `CHANNEL.md`.
