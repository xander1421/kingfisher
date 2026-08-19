# G74 — the 28 analog_only heads G65 never listed

**GROK-2, 2026-08-19.** Reconstructs G65's valid-select (`6670401bde8a…`,
172 / 28 / 14 / 9) and reads the 28. Official split. `certify ok=true`.
**F1 quiet. F2 fired. F3 quiet.** No literature MRR. Official headline stays
**0.2679**.

## Verdict

The 28 are a **transferable head slice**, not a valid-set fluke, and they
are **not rare**. On their 4,118 official-test head queries, analog_only
**0.2371** vs gated-head **0.2257** (+0.0114). Same gap on valid (0.2369 vs
0.2247). On the 172 G51-selected heads analog_only **loses** (0.1106 vs
0.1495) — global replace is still wrong.

They are **common**: median train 819.5 vs 339 for the G51 set (F2 fired).
They are **more often pred-gate OFF** (12/28 = 0.4286 vs 0.1919; F3 quiet).
Only 2/28 have zero 2-hop rules. "G51 is silent" is the wrong story.

The architecture that almost recovers G65's +0.0012 footnote **without
per-predicate analog_only selection**: on every pred-gate-OFF head, use
analog_only instead of the frequency prior. That is arm G **0.2689** vs
G65-D **0.2691** vs G59 **0.2679**. I am **not** moving the official
headline. +0.0010 is the G61/G63 neighbourhood, under +0.005.

Zero-rules (E) is +0.0002. "Flatter head" (F, 145 preds) **loses** (0.2623).

## The 28

| p | relation (short) | n_train | rules | gate | test n | ao | gated |
|---:|---|---:|---:|:---:|---:|---:|---:|
| 5 | award_honor/ceremony | 2834 | 0 | OFF | 323 | 0.3541 | 0.3465 |
| 24 | event/entity_involved | 276 | 2 | OFF | 20 | 0.1535 | 0.0783 |
| 33 | popstra/friendship | 1511 | 6 | ON | 32 | 0.0289 | **0.0822** |
| 38 | org/phone/service_location | 345 | 21 | OFF | 38 | 0.2754 | 0.1949 |
| 47 | job_title/company | 734 | 15 | OFF | 85 | 0.4756 | 0.4259 |
| 54 | degree/student | 260 | 1 | ON | 27 | 0.6636 | 0.6698 |
| 56 | institution/colors | 856 | 3 | ON | 90 | 0.0184 | 0.0102 |
| 59 | institution/student | 2640 | 5 | ON | 311 | 0.1002 | 0.0943 |
| 62 | field_of_study/student | 259 | 0 | OFF | 34 | 0.2246 | 0.2020 |
| 71 | film/cinematography | 336 | 3 | OFF | 17 | 0.0001 | 0.0001 |
| 73 | film/country | 2407 | 46 | OFF | 131 | 0.0148 | 0.0144 |
| 80 | film/featured_locations | 977 | 11 | ON | 100 | 0.0263 | **0.0348** |
| 88 | film/other_crew | 384 | 5 | ON | 26 | 0.0088 | **0.0193** |
| 96 | film/release_region | 12893 | 52 | OFF | 1447 | 0.2276 | 0.2223 |
| 126 | hud_county_place/place | 459 | 13 | OFF | 48 | 0.0001 | 0.0001 |
| 128 | location/adjoins | 2051 | 15 | ON | 55 | 0.0402 | 0.0161 |
| 137 | region/religion | 596 | 7 | ON | 60 | 0.5210 | 0.3798 |
| 140 | netflix_genre/titles | 2671 | 5 | ON | 124 | 0.3888 | 0.3177 |
| 148 | artist/track_role | 1772 | 25 | ON | 152 | 0.0907 | 0.0892 |
| 156 | performance_role/group | 1327 | 8 | ON | 167 | 0.6044 | 0.6062 |
| 166 | olympic_sport/country | 2130 | 11 | OFF | 258 | 0.5236 | 0.5203 |
| 170 | org/child | 191 | 7 | OFF | 20 | 0.1334 | 0.0741 |
| 177 | role/leaders/org | 756 | 9 | OFF | 70 | 0.8447 | 0.7630 |
| 185 | person/employer | 316 | 7 | ON | 24 | 0.0949 | 0.0920 |
| 187 | person/languages | 783 | 22 | ON | 98 | 0.0415 | 0.0212 |
| 190 | person/places_lived | 3738 | 32 | ON | 305 | 0.0054 | **0.0171** |
| 209 | sports_position/team | 3500 | 5 | ON | 22 | 0.3578 | 0.3274 |
| 218 | event/locations | 363 | 7 | ON | 34 | 0.1602 | 0.0954 |

20/28 beat gated on test, 2 tie, 6 lose. The group transfers; six
individuals (friendship, featured_locations, other_crew, places_lived,
plus two ties-to-loss) are valid overfit. p=96 (film release region) is
1,447/4,118 of the slice's test heads.

16/28 are pred-gate **ON**: analog_only beat G51 on *head* even though G51
beat prior on both directions. Those 16 are the extra +0.0002 of G65-D
over arm G, and they include the six test losers. The transferable half is
the gate-OFF prior replacement.

## Arms (official test, both directions)

| arm | head | MRR |
|---|---|---:|
| A pred-gate | G59 | **0.2679** |
| D G65 valid-select | {prior, analog, analog_only, g51} | 0.2691 |
| E analog_only if 0 rules | 23 preds | 0.2681 |
| F analog_only if H_sub > H_obj | 145 preds | 0.2623 |
| G analog_only if pred-gate OFF | 66 preds | 0.2689 |

## Falsifiers (signed)

| F | fires_when | observed | |
|---|---|---|---|
| F1 | analog_only ≤ gated on the 28 at TEST | 0.2371 vs 0.2257 | quiet |
| F2 | median n_train(ao) ≥ median n_train(g51) | 819.5 ≥ 339 | **FIRED** |
| F3 | P(gate OFF\|ao) ≤ P(OFF\|g51) | 0.4286 > 0.1919 | quiet |

C1 choice sha match. C2 172/28/14/9. C3 20466 leak 0. C4 pred-gate 0.2679.
C5 train `6e4c2782169a…`.

Scoreboard: pair-disjoint **0.2313**, official **0.2679**. Literature unavailable.
F001 `590d8769` / F002 `c43b1eab` unmoved.

Reproduce: `PYTHONUNBUFFERED=1 python3 spikes/G74_analog_only_slice/slice.py`.
Check: `python3 kitchen/test_g74.py`.
