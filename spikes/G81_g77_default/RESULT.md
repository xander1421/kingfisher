# G81 — G77's 210-key default is 2.9% of +0.0067

**GROK-2, 2026-08-19.** Splits G78's +0.0067 into G77 small-n DistMult
defaults vs valid-picked DistMult (n≥20). `certify ok=true`. **F1 quiet.
F2 quiet. F3 quiet.** Not another selector. Do not quote 0.3101 as SOTA.

Review finding 1 asked whether the unread 21.6% after G78's top 10 is
the 210-key default (G77 DistMult vs G75 ComplEx on n<20). It is not.

## Verdict

| bucket | n keys | test queries | contrib | share of +0.0067 |
|---|---:|---:|---:|---:|
| small-n default (n_valid<20) | 210 | — | **0.000191** | **2.85%** |
| valid-picked DistMult (n≥20) | 81 | — | **0.006549** | **97.75%** |
| other | — | — | −0.000011 | ~0 |
| G78 top 10 (all n_valid≥20) | 10 | — | 0.005254 | 78.4% |

The leftover 21.6% after the top 10 is **other valid-picked DistMult
keys**, not the default. G78's type-predicate story stands. Quoting
0.3101 as a *method* is still "DistMult on high-mass type predicates
selected on valid," not "DistMult as the small-n default."

## Falsifiers (signed)

| F | fires_when | observed |
|---|---|---|
| F1 | default share ≥ 0.50 | 0.0285 | quiet |
| F2 | default share ≥ 0.216 (G78 leftover) | 0.0285 | quiet |
| F3 | a G78 top-10 key has n_valid < 20 | 0 | quiet |

C1 n_small=210. C2 four sha `db2e8614dbe9`. C3 contribs sum to 0.0067.
C4 G78 4-way 0.3101 leak 0.

Scoreboard unchanged. Literature 0.338 is not a bar. F001/F002 pins unmoved.

Reproduce: `python3 spikes/G81_g77_default/split.py`
Check: `python3 kitchen/test_g81.py`
