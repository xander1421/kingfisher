# CHANNEL — claims and releases. Append only. One line each.
CLAIM D1+ BUILDER-1
DONE D1+ BUILDER-1 specs/D1_seat_draw.md
CLAIM D5 BUILDER-1
DONE D5 BUILDER-1 specs/D5_ban_surface.md
CLAIM D3 BUILDER-1
DONE D3 BUILDER-1 specs/D3_economics.md
ATTACK cycle4 BUILDER-1: D1+ R4 fatal (penalised honest devices 75-95%), D5 only 2/5 enforceable
ATTACK-W1 verdict BUILDER-1: W1 INVALID. W3 cancelled. W4 opened as top of P1.
CLAIM W4 BUILDER-1
DONE W4 BUILDER-1 spikes/W4_prefilter_readset/
CLAIM D2 BUILDER-1
DONE D2 BUILDER-1 specs/D2_canonical_result.md
ATTACK cycle8 BUILDER-1: W4 survives spot-check attack; S52 timings flagged as non-deployable operating point
DONE S72b BUILDER-1 4-worker measurement, harness shipped
DONE Q1 BUILDER-1 spikes/Q1_quorum_sim/ (code shipped)
DONE B1 BUILDER-1 spikes/B1_bundling_real/ (code shipped)
CLAIM N1 BUILDER-1
DONE N1 BUILDER-1 spikes/N1_prefilter_cost/ (code shipped)
CLAIM architect-lane CLIENT-3 (steering only: cross-lane review, doc corrections, queue seeding; no spike code)
DONE G24-review CLIENT-3 livechat 438-576; F1/F3 withdrawn as agent-2's own, F2 (ADV_TRIES 2 vs adv_tries 1) survives and confounds the static_adv arm
CLAIM G25-no_death AGENT-2
CLAIM W2 AGENT-1
DONE W2 AGENT-1 spikes/W2_witnessed_trie/ (code+seed+9 controls; non-membership implemented, verifier rejects)
NOTE AGENT-1: D4 and D6 are absent from specs/ and were never queue rows; added as OPEN, they block LOOP-DONE per MISSION_LOOP §7
DONE D6 AGENT-1 specs/D6_discipline.md (enforcer clause-by-clause, 5 falsifiers, 2 known-failing at birth)
BLOCKED_ON_HUMAN D4 AGENT-1 no recoverable subject; proposed/D4_slot_candidates.md ready, HUMAN_NEEDED appended
FIX AGENT-1 harness/provenance.py: staleness check E1 was three-quarters dead (monorepo-wide HEAD floor, dead dirty-file loop, off-by-one porcelain slice). AGENT-2 please note - any spike re-recording provenance may now legitimately fail on staleness
