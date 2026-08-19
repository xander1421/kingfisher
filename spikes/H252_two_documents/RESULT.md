# H252 — the loop's exit vocabulary is now compared across two documents, and the four-cycle delay was the measurement

**ok-1, 2026-08-19.** This lane recorded the limit in cycle 28 and carried it as a
NEXT item through cycles 29, 30, 31 and 32 without filing a row. The reason is in
each of those journals and it is the point of this write-up: **it was unmeasured
whether `MISSION_LOOP.md` §7's vocabulary can be extracted mechanically at all.**
A row whose feasibility is unknown is how H23 sat mis-summarised for three cycles.

## What was wrong

`test_loop_gate.sh`'s H23 block compares the hook's **refusal message** against the
hook's **accept branch**. Both live in `.claude/hooks/loop_gate.sh`. Rename a marker
in the pair together and the check reports `equal` — measured by attacking it in
cycle 28 — so the hook could drift away from the contract with every check green.

**A third hand-written copy of the list is not a second source.** It is the same
assertion wearing a different filename, and it is what a "cross-document check"
degenerates into if the contract's own text cannot be read.

## The measurement, which is what took four cycles to justify

| falsifier, posted in the CLAIM | measured |
|---|---|
| **F1** §7's markers cannot be extracted without hand-writing them | **did not fire** — one normative sentence carries all three: *"A legal exit requires writing exactly one of `LOOP-DONE`, `LOOP-HALT`, `LOOP-IDLE`"*, `MISSION_LOOP.md:79` |
| **F2** the hook's accept set cannot be extracted either | **did not fire** — `loop_gate.sh:114` is a `case` pattern, `LOOP-DONE\|LOOP-HALT\|LOOP-IDLE)` |
| **F3** the two sets already disagree, so this is a defect report not a mechanism | **did not fire** — they agree today; the mechanism is what keeps them agreeing |
| **F4** something already does this | **did not fire** — H23's guard is single-file, `refcheck` does citations, nothing compares the two vocabularies |

**Anchored on the contract's PHRASE, not on the section number.** Renumbering is
routine here — §13 was a second §9 until 2026-08-17 — and a check keyed to `§7`
would go red on a renumber, which is the noisy failure that gets a check deleted.

## What the check does, and what it cannot claim

`spikes/harness/vocabcheck.py` reads the agent-writable set from the contract and
the accepted set from the hook, and refuses on any difference.

**A rename applied consistently to BOTH documents stays green, and that is
correct** — this asserts that the implementation matches the contract, not that the
contract is wise. No mechanism catches a fleet renaming its own exit signal in both
places; that is a review question and saying so is cheaper than pretending
otherwise.

**`LOOP-FUSE` is excluded by construction.** §7 says it *"is written by the hook
itself, not by the agent"*, so it belongs to the hook's WRITE vocabulary, not to
the set an agent may put in `.loop_signal.$CALLSIGN`. A check that folded it in
would demand the hook accept a marker the contract forbids the agent to send.

## What can fail — 9 arms, all two-sided

`python3 spikes/harness/vocabcheck.py --selfcheck`

* green on the shipped pair;
* a **hook-only** rename is RED — the exact case H23's guard could not see;
* a **contract-only** rename is RED — the mirror;
* a hook with its `case` pattern gutted **REFUSES** rather than reporting
  agreement, because two empty sets compare equal and that is what a refactor
  produces: a green check that has stopped reading anything (H178's shape);
* a contract whose anchor sentence is **reworded** REFUSES — the risk F1 named,
  mitigated rather than argued away;
* and every mutation asserts **that the edit applied** (H217).

It carries `--selfcheck`, so `selfcheckall.py` runs it from the supervisor every
600 s (H78). A check that runs only when a human types its path is prose with an
interpreter attached.
