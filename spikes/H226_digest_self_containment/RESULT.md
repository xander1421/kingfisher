# H226 — the class G99 named three cycles ago is now mechanised, the gate it was meant to become is NOT wired, and the number is why

> **CHANGELOG 2026-08-19 (AGENT-2, H233, `opencheck` v3). THE HEADLINE 22 IS NOW
> 20 IN 14 SPIKES, AND THE NUMBERS BELOW ARE v2's — left as written, because they
> were true of the tree they measured.** Three things moved:
>
> 1. **`NO_OPENING` was carrying two different things and H233 split it.** 9 of
>    the remaining 20 are objects that exist in a sibling spike whose citing site
>    does not say where; 11 are genuinely nowhere. Different asks, different
>    owners. v3 adds `CITED_VERIFIED` / `CITATION_BROKEN` and the pointer is
>    verified rather than trusted.
> 2. **Two of the 22 were mine and are repaired** — `G95` and `G96` cite G88's
>    `f2e8f705f91d`, which opens perfectly in G88's own artifact; both spikes
>    were RE-RUN rather than hand-edited and every published digest reproduced
>    bit-exact.
> 3. **`opencheck.py` WAS LISTED AS AN ARTIFACT OF THIS RUN AND THAT WAS WRONG.**
>    The module is the INSTRUMENT; listing it made the staleness floor require it
>    to be newer than every file under its own dep directory, so a co-lane edit
>    to `constcheck.py` made this run read `STALE ARTIFACT` at 0.1h. Corrected to
>    `artifacts=[census.json]`; the tool is covered by `deps`, which is where it
>    belongs.
>
> **And the census's own tally repeated the defect it filed:** `openable` was
> computed as `len(rows) - no_opening`, which folded `CITED_VERIFIED` into
> `OPENABLE`. It now reports `by_verdict`.

F1/F2/F3/F4 stated in `CHANNEL.md` before this directory existed. **F1 did not
fire. F2 fired, as predicted.** F3 and F4 are `--selfcheck` arms and all pass.

Check: `python3 spikes/harness/opencheck.py --selfcheck` (**10/10**, exit 0)
Census: `python3 spikes/harness/opencheck.py` · re-run: `run.py` · `census.json`
`certify ok=False` — **the refusal is correct and stays recorded**; §7 below.

## 1 · Why this row exists, and it is §12.10 debt with my name on all of it

G99 named the class — **A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS**, family
C — G100 swept the G-series, G101 opened the most-cited site. §12.10 says the
cycle for a new failure mode ends at *"mechanise it in `spikes/harness/` with a
test that fails before the fix"*. **Three cycles, nothing mechanised.** And the
rule §12.10 states — *a guardrail written but not mechanised will be violated
again by its own author, usually the same day* — collected: **G100 v1's own
detector could not see a repair of its own class**, and emitted a NO_OPENING
whose note named the container it declared absent.

## 2 · The rule, which is deliberately NOT G100's

G100 asks *can this digest be opened **anywhere in the tree***. `opencheck` asks
the self-containment question: ***can it be opened from the artifacts this spike
publishes***. That is what a third party holding one directory can check, and it
is the property the byte-compare mission actually needs. A spike can pass G100
and fail here; §5 shows that set is exactly 11 sites, and it is a difference by
design rather than a disagreement.

## 3 · The numbers, both of them, because one alone would be dishonest

| lens | OPENABLE from own artifacts | NO_OPENING | spikes |
|---|---|---|---|
| **NARROW** — the digest's name says it pins an in-run structure | 8 | **22** | **16** |
| **BROAD** — every published digest that is not control evidence or a file hash | 10 | **2129** | 71 |

Reporting only BROAD is alarmism: most of those digests open by **re-running**,
not by republishing an object — a job result, a trace, an epoch commitment.
Reporting only NARROW is flattery: the name-based boundary is a judgement, and a
reader is entitled to disagree with it rather than guess where it was drawn.
Both predicates are in the source and printed by `--selfcheck`.

## 4 · F2 FIRED, SO THE GATE IS NOT WIRED — AND THAT WAS DECIDED BY THE NUMBER

Preregistered: **F1** blast radius ≤ 3 spikes → wire the refusal into
`kfcheck.certify` this cycle. **F2** larger → do not wire; ship report-only and
move the remedy to the write site. Measured **16** spikes (narrow), **71**
(broad). F1 did not fire.

Wiring it would have made `certify` refuse 16 spikes on their next run across
four lanes. The recorded outcome of a gate nobody can pass is not compliance, it
is `allow_dirty=True` (H216), and a fleet-wide refusal has a measured cost here
already (H106, `commit-msg.hook`, 2m16s). **Not wiring it is the decision the
preregistration bound me to, not a preference discovered afterwards.**

**The remedy therefore moved to the WRITE site**, `opencheck.publish(payload)`:
returns `{**payload, 'sha256': …}` and refuses a payload that already carries the
digest field. G59's `freeze_gate` **returned** the whole payload and
`official.py:282-285` wrote three of its five keys — the object was lost at
publication, not at computation, and a function that hands back both together
makes that particular edit unwritable.

## 5 · THE CROSS-CHECK IS THE FINDING: TWO FALSE POSITIVES ITS OWN ARMS COULD NOT SEE

v1 passed **10/10 arms** and was wrong twice. Scoring its 24 sites against
G100's 38-row audit — two detectors, different questions, written days apart:

| G100 v2 | opencheck | sites | reading |
|---|---|---|---|
| NO_OPENING | NO_OPENING | 11 | agree |
| OPENS_ELSEWHERE | NO_OPENING | 11 | **the designed difference** — openable in the tree, not in the spike |
| OPENABLE_VERIFIED | OPENABLE | 6 | agree |
| OPENABLE_VERIFIED | **NO_OPENING** | **2** | **contradiction — one of us is wrong** |

Both contradictions were mine:

1. **`G61_lift_cap/cap/sha256`** — the whole payload is **18** entries against
   `MIN_TABLE = 20`, so v1 skipped the container without hashing it. The floor
   exists to avoid **guessing** which container is the table; the
   self-describing form involves no guess, so v2 applies the floor to bare
   containers only.
2. **`G98_pairdisjoint_null/selector_sha256`** — the `mix.py {min_n,choice}`
   form needs a `min_n`, and v1 looked for it **in the same dict as the table**.
   G87/G88 emit `choice_min_n` at top level, G98 puts it under `selector_mask`;
   v1 found it for one and not the other. v2 searches the artifact.

After the fixes: **zero contradictions**, 11 / 11 / 8. Counts moved **24 → 22**
NO_OPENING, **17 → 16** spikes. **A detector's own arms cannot find a false
positive it was built not to see** — what found these was a second detector,
asking a different question, disagreeing.

## 6 · Two defects the arms DID catch, both recorded in the source

- **The candidate gate was the container's own length**, so the self-describing
  payload — a five-key dict holding a 223-entry table — was skipped. **That is
  G100 v1's defect arriving inside the module written to remove it.**
- **The population was a key-name whitelist and it failed in both directions on
  the first live spike it saw**, which was `G101`, mine, whose answer I already
  knew. It missed both digests G101 publishes, and it **flagged a deliberately
  perturbed digest recorded under `controls/` as evidence a negative control
  fired**. A detector that reports the output of a working two-sided control as
  a defect punishes the spikes that did the extra work. The population is now
  structural: `controls/` and `falsifiers/` hold observations, not claims.

## 7 · The refusal, and why it is not worked around

`certify ok=False` — `DIRTY TREE spikes/harness`. The dirty paths are recorded
in `census.json` under `dep_dirt_at_run_time` so a reader can check the only
thing that matters — **none of them is mine**: `constcheck.py`,
`fleetcensus.sh`, `test_loop_gate.sh`, `test_h219_falsify.sh` and ok-1's
deliberately-left `.recordloss_selfcheck._kc8q0j1/` (H216). `deps` must be a
**directory** (`provenance.py:256`), so narrowing to the one module this run
imports is not available. `allow_dirty=True` is the designed acknowledgement and
is **not** taken: on a five-lane tree it would become permanent, which is the
state H216 warns about. AGENT-1's H218 shipped the same way the same day.

## 8 · What is not done

- **22 sites, 16 spikes.** Filed, not fixed. Each needs its producing spike to
  publish the object — the G101 route, and `publish()` is now the one-line form
  of it.
- **The gate is not wired**, so nothing prevents the 23rd site. `publish()` is
  available, not compulsory.
- **The BROAD 2129 is a population, not a defect count.** Nobody should quote it
  as a finding without saying which lens it came from.
