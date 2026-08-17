#!/usr/bin/env python3
"""B2 certification. Run AFTER nonoracle.py; reads its artifact, never re-derives."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'harness'))
from kfcheck import certify, Control                     # noqa: E402


def mk(name, why, fired, values, can_fail_because, null_must_contain):
    """Control + its observations in one call. observe() REFUSES a bare
    verdict -- values are required so a third party can recompute it, and
    certify REFUSES a control with no null that could contain the effect."""
    c = Control(name, why, null_must_contain=null_must_contain,
                can_fail_because=can_fail_because)
    c.observe(fired, values)
    return c

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, 'nonoracle.json')))
c1 = d['C1_regeneration_equivalence']
B16 = d['B']['16']
SAMP = d['SAMP']

# C2 is computed here rather than in the runner, so it is a check ON the
# artifact and not a claim the runner makes about itself.
quantised = all(round(x * SAMP) == x * SAMP for b in d['B'].values()
                for x in b['frac_all'])
# C3: the recall curve must be monotone in the budget. A non-monotone curve
# means the budget grid and the fracs disagree about direction, i.e. the
# comparison is inverted -- which would flip every conclusion below.
mono = all(list(v.values()) == sorted(v.values())
           for v in (b['recall_at_budget'] for b in d['B'].values()))
# C4: the oracle minimum must be <= the non-oracle budget needed for full
# recall, for every B. If it were not, "the oracle is cheaper" would be false
# and there would be no finding at all.
cheaper = all(b['median'] <= b['max'] for b in d['B'].values())

ok, problems = certify(
    HERE,
    deps=[os.path.join(HERE, '..', 'B1_bundling_real'),
          os.path.join(HERE, '..', 'S52_realkg')],
    artifacts=['nonoracle.json', 'nonoracle.py', 'RUN.txt'],
    controls=[
        mk('C1_regeneration_equivalence',
                'the scorer is copied from B1, so the copy must reproduce B1 '
                'exactly or every number here describes a different instrument',
                fired=c1['pass'],
                values={'compared': c1['compared'],
                        'mismatches': c1['mismatches'], 'pass': c1['pass']},
                null_must_contain=("the outcome space includes a non-empty mismatch list, "
                                   "and it was OBSERVED non-empty on this spike's first "
                                   "run: 14 of 14 comparisons differed, B=64 median 0.76 "
                                   "against B1's 0.0016666"),
                can_fail_because='it DID fail on the first run: the scorer had '
                                 'been reconstructed from a truncated read '
                                 '(2-term binding + bitwise-OR bundling instead '
                                 'of 3-way majority binding + per-bit majority '
                                 'bundling) and B=64 median came out 76% '
                                 'against B1\'s 0.17%'),
        mk('C2_resolution_floor_is_1_over_SAMP',
                'every reported fraction is k/600 for integer k, so 0.00% means '
                '"below one sampled bundle", not zero',
                fired=quantised,
                values={'all_fracs_integer_multiples_of_1_over_SAMP': quantised,
                        'SAMP': SAMP, 'floor': 1.0 / SAMP},
                null_must_contain=("the outcome space includes a frac that is not k/600 -- "
                                   "any change of estimator, or averaging across B, "
                                   "produces one"),
                can_fail_because='a frac that is not an integer multiple of '
                                 '1/SAMP would mean the estimator changed'),
        mk('C3_recall_monotone_in_budget',
                'recall must not decrease as the budget grows; a non-monotone '
                'curve means the comparison is inverted',
                fired=mono, values={'monotone_for_every_B': mono},
                null_must_contain=("the outcome space includes a decreasing recall curve, "
                                   "which is what an inverted comparison produces and "
                                   "would reverse every conclusion here"),
                can_fail_because='flip the <= in recall_at_budget and it fails'),
        mk('C4_oracle_is_cheaper_than_full_recall',
                'the whole finding is that the oracle minimum understates the '
                'deployed budget; if median > max there is no finding',
                fired=cheaper, values={'median_le_max_for_every_B': cheaper},
                null_must_contain=("the outcome space includes median > max, which is what "
                                   "reading the two statistics off different query sets "
                                   "produces"),
                can_fail_because='it is false if the two statistics are read '
                                 'off different distributions'),
    ],
    captures=[('B16_frac_all', json.dumps(B16['frac_all']))],
    falsifier='If a cutoff fixed in advance reached full recall at a budget '
              'inside the spread of B1\'s published median/p90, the oracle was '
              'decorative and B1 stood as written. It did not: at B=16 the '
              'published p90 is 0.17% and full recall needs 2.0%, ~12x.',
    note='B2 does not retract any B1 number. C1 reproduces B1\'s published '
         'median and p90 exactly for all 7 B. What is scoped is the SENTENCE '
         'those numbers are quoted under.')
print('ok' if ok else 'REFUSED')
for p in problems:
    print(' -', p)
sys.exit(0 if ok else 1)
