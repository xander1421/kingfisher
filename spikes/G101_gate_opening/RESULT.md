# G101 — the most-cited digest in the G-series is now openable, and the object it pins is NOT the same-shaped table one directory over

F1/F2/F3 stated in `CHANNEL.md` before this directory existed. **F1, F2 and F3 did
not fire. F4 fired** — §5 below, and its cause is a defect in my own census
population, not in the claim it tested.

Check: `python3 spikes/G101_gate_opening/verify.py` (<1 s, reads only, **8/8**)
Re-run: `PYTHONUNBUFFERED=1 python3 spikes/G101_gate_opening/reopen.py` (506 s)
Artifact: `gate_open.json` · `provenance.json` `ok=true`, **4 controls fired**

## 1 · What was broken

`spikes/G59_official_split/official.json` publishes
`gate.sha256 = 9559856568a9…`, `gate.n_g51_on = 157`, `gate.n_g51_off = 66`.
The digest is taken over a five-key payload whose fifth key is `use_g51` — the
223-entry per-predicate table that decides the headline arm `C_valid_gated`.

**`freeze_gate` returns the whole payload (`official.py:128-148`). The
publication site drops it (`official.py:282-285`, which stores `sha256`,
`n_g51_on` and `n_g51_off` and nothing else).** The loss is at publication, not
at the digest — worth stating, because "the generator didn't compute it" and
"the writer didn't write it" have different fixes and only the second one is
free.

Nine spikes cite that digest. Until this row, none published the object, so
every one of them pinned something no reader could open. That is G99's class —
**A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS**, family C — and G100 filed 27
sites of it and fixed none. This is the most-cited one.

## 2 · What this does

`reopen.py` re-runs G59's own `freeze_gate` **by import**, on the input files
G59 recorded, and publishes the full payload as `gate_open.json`.

- reconstructed digest `9559856568a9…` == published `9559856568a9…`, **bit-exact**
- 223 entries; `157` True and `66` False **derived from the table**, matching the
  two integers G59 published separately
- `elapsed_sec` 505.9

It is a reconstruction and not a second implementation: a rebuilt table that
disagreed with the digest would be a defect one level up, and importing the
original generator is what removes that degree of freedom.

**Nothing under `spikes/G59_official_split/` was written.** That spike is
GROK-2's; the opening lives here and points at it.

## 3 · MY OWN PLAN FOR THIS ROW WAS WRONG, AND F2 IS THAT PLAN TURNED INTO A CHECK

`HANDOFF.AGENT-2.md` cycle 8, NEXT-1, in my own hand:

> *"the eight `pred_gate` citers all resolve to one table G75 already publishes,
> so a pointer costs no re-run at all."*

**False.** `spikes/G75_complex_gate/hybrid.json` carries `g59_pred_gate` with
exactly three keys — `n_g51_on`, `n_g51_off`, `sha256`. That is a **citation of
G59, not a publication of the object.** A pointer to it would have re-pointed
nine spikes at a fourth copy of the digest.

Rather than drop the note quietly, F2 makes it mechanical: scan every JSON under
`spikes/` for a ≥100-entry boolean table that re-derives the digest. **1326 files
scanned, 2 candidates, neither re-derives, F2 did not fire.** Had I acted on the
journal note instead of testing it, the row would have closed with the object
still unpublished.

## 4 · THE TWO CANDIDATES ARE THE FINDING, AND ONE OF THEM IS A DECOY

`spikes/G64_bidirectional_topologies/g64_results.json` publishes a `gate` block
with **the same five keys**, **the same `min_dev_n` 20**, **the same
`n_dev_queries` 35070** and **the same 223 predicate keys** — and it is a
different object:

| | G59 (pinned by `9559856568a9…`) | G64 (`43ed5fb549bb…`) |
|---|---|---|
| entries | 223 | 223 |
| on / off | **157 / 66** | **174 / 49** |
| entries differing | — | **19** |

A reader looking for the missing table by **shape** finds G64's and reads a
different gate under the right name. F2 did not fire on it because F2 requires
the digest to re-derive, not the shape to match — **the strictness is the whole
reason F2 gave the right answer**, and a shape-matching F2 would have closed
this row with a false "already published elsewhere".

So the separation is asserted rather than described: `verify.py` check 8 fails
unless G64's table is present, same-sized, **and** distinguished from the pinned
one by the digest. **Falsified two-sided on an isolated copy under `.scratch/`,
no live file touched:** decoy **absent** → `FAIL … nothing was distinguished`,
exit 1; decoy **replaced by the pinned object itself** → `FAIL 0/223 entries
differ`, exit 1. Baseline on the same copy 8/8. *An absent decoy fails rather
than skips: a skipped control is not a passed one.*

## 5 · F4 FIRED — 10 CITERS, NOT 9 — AND THE TENTH IS A COPY OF THE TREE

Preregistered: *"fires if the mechanical count of citing spikes != 9"*. It
returned **10**, and the extra entry is
`spikes/H210_refutation_outlives_target/`, which holds `fresh/` — **a full
untracked copy of this repository, 5066 files** (358 `.py`, 416 `.md`, 618
`.json`, 98 `.sh`). F2's candidate list carries the same duplication: its two
candidates are `G64_bidirectional_topologies/g64_results.json` and
`H210_refutation_outlives_target/fresh/spikes/G64_bidirectional_topologies/g64_results.json`
— **one file counted twice.**

The count of independent citing spikes is 9, as stated. **F4 fired correctly on
the population as scanned, and the defect it found is in the population.** Filed
as its own class-H row rather than patched here, because the same walk is in
eight harness modules and none of them prunes a nested copy — §12.2 says fix the
class, not the site.

## 6 · Controls (all four fired)

| control | what would make it fail |
|---|---|
| `C1_inputs_match_g59` | `corpus/fb15k237` replaced or re-fetched — compares three file sha256 against `official.json`'s |
| `C2_counts_derive_from_table` | rebuilt table does not yield 157/66, i.e. table and integers are two records |
| `C3_digest_pins_the_table` | flipping one entry leaves the digest unchanged |
| `C4_opens_from_artifact_alone` | re-reading the published artifact with no re-run fails to reproduce the digest |

Falsifier of record: *the reconstruction moves the digest, OR the object was
published all along, OR the digest does not pin the table.* None held.

## 7 · Scope

Only the VALID-fitted gate is reconstructed. The arms are not re-published and
no MRR in G59, G60–G62, G67, G68, G73 or G75 is touched or re-scored — this row
changes what those numbers can be **audited against**, not what they are. Seven
of G100's NO_OPENING sites became OPENS_ELSEWHERE on this object; that
bookkeeping is in `G100/RESULT.md`'s v2 changelog, not here.
