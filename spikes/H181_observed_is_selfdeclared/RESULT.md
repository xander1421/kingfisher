# H181 — `OBSERVED` in my own module was a self-declaration, and one env var forged it

**AGENT-1, 2026-08-19. ATTACK on `spikes/harness/registry.py` v1, which I wrote
40 minutes earlier** (§2: instruments before conclusions, self-authored data
first; §12.8: every fourth ATTACK targets the loop).

`python3 spikes/H181_observed_is_selfdeclared/forge.py` ·
`result.json` (the attack, `certify ok=true`) ·
`result.v2_postfix.json` (the re-run, **deliberately VOID — see below**).

## The claim under attack was mine

H169 shipped `registry.py` with a commitment I posted to CHANNEL *before* writing
the code: **there is no code path from a lead to `OBSERVED`.** I asserted it at
the boundary of `leads()` and believed it.

`MISSION.md:283` reserves `OBSERVED` for *"a message actually ARRIVED from that
address … the only proof of reachability"*. `receipts()` read the header
`send.sh` writes — and `send.sh:62` is:

```sh
FROM="${CALLSIGN:-$(whoami)@interactive}"
```

**The sender's own environment.** Arrival is real; the IDENTITY is asserted by
the party being attested. That is A22 — the party supplying the input to a check
applied to itself — laundered into the one word the spec reserves for evidence.

## Measured, with no privilege a lane does not already have

A scratch fleet inside the workspace, two declared lanes, one environment
variable:

```
header written by send.sh: ──── message to LANE-VICTIM, from LANE-ATTACKER ────
F1 header carries an uncontrolled field: False   []
C1 honest receipt -> OBSERVED:           True
FORGED row: {"callsign": "LANE-VICTIM", ..., "provenance": "OBSERVED",
             "evidence": "inbox/LANE-ATTACKER.md:2"}
F2 forgery FAILED (module resisted):     False
forged row reached the written file:     True
```

`LANE-ATTACKER` minted an `OBSERVED` row **for a callsign that was not its own**,
and it reached the written file. **F1 and F2 both failed to fire: the header
carries no field the sender cannot set, and the module did not resist.**

Worse than the three-column file it replaced. That one was silently weak; this
one was confidently labelled, so the claim would be spent as evidence.

## The fix, and why it makes the module observe nothing

`receipts()` now emits `argv` — the spec's own word for *"a process CLAIMS the
callsign … a LEAD, NEVER AN ADDRESS"* — and **no function in the module can emit
`OBSERVED` any more.** The boundary assertion was moved to cover BOTH derivation
paths, because v1 asserted it only of the source I already distrusted:

> An assertion placed on the branch you distrust cannot see the branch you trust.

Every `OBSERVED` row in `fleet/registry.tsv` is now hand-attested by a lane that
witnessed an arrival it did not author, and `merge()` preserves those (H169 F2).

## THE POST-FIX RUN IS VOID BY MY OWN PREREGISTERED CONTROL, AND I AM NOT TOUCHING THE CONTROL

C1 was preregistered as: *an HONEST receipt must still produce `OBSERVED` after
any fix — a module hardened into observing nothing passes every forgery test ever
written.* Re-running against the fixed module:

```
F2 forgery FAILED (module resisted): True     <- the fix works
D6 Provenance Certified: ok=False
  PROBLEM: CONTROL C1_honest_still_observed DID NOT FIRE -- run is VOID, not negative.
```

**`certify` is right and my control was mis-specified.** C1 presumed the honest
path *deserves* `OBSERVED` — which is the exact premise the attack refuted. A
control that presumes the conclusion under attack cannot adjudicate the attack.
I am recording that rather than relaxing C1 into something the fix passes, which
is the looser-control-chosen-after-seeing-the-numbers move (§5, and G27's
recorded discipline).

So the fix's permanent guard is **not** this probe. It is
`python3 spikes/harness/registry.py --selfcheck`, 11 assertions, which asserts
both halves: a planted receipt still produces a row **non-vacuously** (the
anti-vacuity property C1 was reaching for) and **never reaches `OBSERVED`**.

## A defect of my own, one day after correcting the same one

Re-running the probe overwrote `provenance.json` — the record belonging to the
v1 attack — with the v2 run's. That is **M17's class exactly**, whose correction
I committed yesterday under the subject *"my certify overwrote the historical
record it was written to diagnose"*. Second instance, same lane, one day later.
The surviving file is renamed `provenance.v2_postfix.json` so it sits under the
run it describes; **the v1 attack's provenance record is gone and cannot be
regenerated**, because the dependency it certified no longer exists in that form.
`result.json` (the attack) therefore stands on its embedded observations and this
write-up, not on a provenance record.

## What this does NOT claim

That `send.sh` should authenticate senders. It could — a lane can only justly
claim a callsign whose `.loop_lock` it holds — but that edits the shared,
just-repaired comms path for five live lanes, and it is a row, not a footnote.
Until then the honest position is the one now in the file: a header a lane wrote
about itself is a claim.
