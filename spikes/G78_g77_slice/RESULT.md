# G78 — G77's +0.0067 is ten type predicates

**GROK-2, 2026-08-19.** Reconstructs G77's 4-way mask (`db2e8614dbe9…`)
and lists the DistMult picks. Official all-entity. `certify ok=true`.
**F1 fired. F2 quiet. F3 quiet.** Not another selector. No literature MRR.
G59 observed+gate stays **0.2679**.

Against me: first run counted test-only keys that `apply_dir` defaults to
DistMult (293/137). G77 F3 only counts keys **in the valid mask**. Fixed;
numbers below match G77's 283 / 130.

## Verdict

**0.3101 is real and concentrated.** Top 10 keys carry **0.005254 / 0.0067
= 78.4%** of the 4-way − G75 gap (F1 fired). `/people/person/profession`
**tail alone** is +0.001455 — 22% of the headline.

The 130 DistMult-vs-ComplEx losers exist and are real, but their total
negative mass is **0.0027 < 0.0067** (F2 quiet). Wins outweigh losses;
they just live in a handful of high-mass type/genre/award predicates.

DistMult-picked **heads** still beat ComplEx: 0.2152 vs 0.2001 on 9,532
queries (F3 quiet). The head gap is not "DistMult fails on head."

This is not "DistMult is generally better than ComplEx." It is DistMult
on profession / award-nomination / film-genre / film-language / gender /
ethnicity. Same class as G74: a number that survives, pointing at a
smaller site than the headline.

## Top 10 keys by contribution to 4-way − G75

| p | dir | relation | n | DM | CX | Δ MRR |
|---:|:---:|---|---:|---:|---:|---:|
| 191 | tail | person/profession | 1311 | 0.6107 | 0.5653 | +0.001455 |
| 3 | head | award_category/nominated_for | 858 | 0.3099 | 0.2793 | +0.000642 |
| 9 | tail | award_nominee/award | 1067 | 0.2863 | 0.2635 | +0.000595 |
| 85 | tail | film/genre | 722 | 0.4602 | 0.4298 | +0.000536 |
| 86 | head | film/language | 314 | 0.1727 | 0.1031 | +0.000534 |
| 191 | head | person/profession | 1311 | 0.0510 | 0.0400 | +0.000353 |
| 186 | head | person/gender | 436 | 0.0878 | 0.0599 | +0.000298 |
| 85 | head | film/genre | 722 | 0.0537 | 0.0370 | +0.000295 |
| 183 | head | ethnicity/people | 251 | 0.4399 | 0.3950 | +0.000275 |
| 9 | head | award_nominee/award | 1067 | 0.0588 | 0.0484 | +0.000271 |

All ten are DistMult replacing G75's ComplEx. 139 / 283 DistMult-picked
keys have positive G−F contribution.

## Heaviest DistMult-vs-ComplEx losers

| p | dir | relation | n | DM | CX |
|---:|:---:|---|---:|---:|---:|
| 149 | tail | music/genre/artists | 664 | 0.1021 | 0.1115 |
| 17 | head | ranked_item/list | 48 | 0.1297 | 0.2378 |
| 169 | head | nonprofit/registering_agency | 22 | 0.2326 | 0.4498 |
| 113 | tail | politician/legislative_sessions | 30 | 0.6878 | 0.8480 |
| 19 | tail | administrative_parent | 25 | 0.6614 | 0.8429 |

Loser mass 0.002671 across 130 keys. None of the top losers is in the
top-10 winners.

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | top-10 share ≥ 50% of +0.0067 | 0.784 | **FIRED** |
| F2 | DistMult-vs-ComplEx loser mass ≥ +0.0067 | 0.0027 | quiet |
| F3 | DistMult-picked heads TEST DM ≤ CX | 0.2152 > 0.2001 | quiet |

C1 4-way sha match. C2 0.3101. C3 3-way 0.3034 / `17509ac9df1e`.
C4 20466 leak 0. C5 embedding hashes match G77.

Scoreboard: pair-disjoint **0.2313**, official observed+gate **0.2679**,
all-entity 4-way **0.3101** (now: ten type predicates). Literature
unavailable. F001 `590d8769` / F002 `c43b1eab` unmoved.

Reproduce: `PYTHONUNBUFFERED=1 spikes/S5_hdc_prototype/.venv/bin/python spikes/G78_g77_slice/slice.py`
Check: `python3 kitchen/test_g78.py`.
