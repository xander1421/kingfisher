# The D4 slot — what was it, and what should fill it

**Prepared 2026-08-17 by AGENT-1. One decision needed: pick a row, or amend §7.**

## The gap

`MISSION_LOOP.md` §7 makes `LOOP-DONE` conditional on **D1–D6 existing as written
specs**. On disk:

| id | spec | subject |
|---|---|---|
| D1+ | `specs/D1_seat_draw.md` | **who** verifies — seat draw over an epoch-committed registry |
| D2 | `specs/D2_canonical_result.md` | **what** is compared — canonical result serialization |
| D3 | `specs/D3_economics.md` | **payment** — economics as formulas |
| **D4** | **absent** | **?** |
| D5 | `specs/D5_ban_surface.md` | **what is admissible** — build-enforced ban surface |
| D6 | `specs/D6_discipline.md` | **how results are made** — written 2026-08-17 |

D4 is absent from `specs/`, was never a `WORK_QUEUE.md` row, and appears in no
`DECISIONS.log` entry. The only other trace of "D4" in the workspace is an
unrelated soak-test row ID in `spikes/M1_1_android/SOAK_RESULT.md`.

## Evidence about what happened

- `specs/D2_canonical_result.md` self-describes as **"Last P0 freeze-gate item"**,
  and `WORK_QUEUE.md`'s P0 table lists exactly D1+, D2, D3, D5. So the author
  treated the series as closed at four documents.
- `DECISIONS.log` entry 81 enumerates the post-demolition gate amendments as
  **D1+, D3, D6** — D4 is not among them.
- Conclusion: **D4 is most likely a numbering gap, not a lost document.** §7's
  "D1–D6" is range shorthand over a set that was never contiguous.

I did not act on that conclusion. Reading "D1–D6" as "the five that exist" is
weakening a gate to pass it (§5 P1), and the gate is the loop's own exit
condition, so the agent deciding it would be supplying the input to a check on
itself (A22).

## Candidates, if the slot should be filled rather than closed

| # | subject | why it is gate-shaped | evidence already on disk | cost |
|---|---|---|---|---|
| **1** | **Settlement and dispute** — how a disagreement is adjudicated and paid | It is the one axis with no spec and a **RED** blocker. Every other D covers a different question; this covers "what happens when the answers differ", which is the whole product | `out/RISKS.md` R-NEW + 2 addenda (settlement never costed, ~3,350× cap, succinct-proof route measured from `risc0`, dispute path "replaced, not repaired"); `spikes/S68_state_commitment/` **RED** — no interpreter-state commitment exists, so bisection is blocked upstream | Spec writable now; the *mechanism* is gated on hyperon Issue 3 |
| 2 | **Commit/reveal in the job schema** | `out/RISKS.md` #10 is literally "Our own schema is missing commit/reveal". Without it a late replica can copy an early one, which silently voids the independence D1+ draws seats for | RISKS #10; Q1's independence axes | Small; it is a schema clause |
| 3 | **Attestation / operator independence** | The `operator` domain is pinned at 1, so **every job is refused** on independence. This is the single binding constraint in `HANDOFF.md` | `HUMAN_NEEDED.md` (no attestation root); `reports/REPORT_Acurast_compute.md`; `q3.py` pins `UNATTESTED` | Spec writable; root not obtainable in-workspace |
| 4 | *(close the slot)* amend §7 to name the set explicitly | If D4 never existed, the honest repair is to fix the range, not invent a member | this document | One line in MISSION_LOOP.md |

## Recommendation

**Row 1 (settlement and dispute), or row 4.** Row 1 because it is the only
question the D-series does not already answer and the only one with a RED
upstream blocker sitting under it — a gate there would be load-bearing rather
than decorative. Row 4 if the intent was always five documents.

Rows 2 and 3 are real gaps but are narrower than the other D-documents; both fit
better as clauses inside D2/D1+ than as peers to them.

## The ask

Reply with `D4 = <row number>`. If row 1, I will write
`specs/D4_settlement.md` with falsifiers, marking the bisection mechanism as
gated on S68 rather than pretending it is reachable. If row 4, amend §7 to
`D1+, D2, D3, D5, D6` and I will close the queue row.
