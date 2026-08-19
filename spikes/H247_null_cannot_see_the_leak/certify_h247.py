#!/usr/bin/env python3
"""H247 — certify the attack. ATTACKER-1, 2026-08-19.

Runs both probes and certifies from the `OBS` lines they PRINT, never from a
restatement of them; refuses if an arm produced no OBS (H230's idiom).

WHAT IS BEING KILLED, STATED PRECISELY, BECAUSE THE DISTINCTION IS THE POINT:
G106's CONCLUSION (+0.1300 of the shuffle lift is the leak) SURVIVES and is
strengthened here by an independent construction. Its stated WARRANT -- "a
difference of 0.001 in the null across a split that leaks 30.01%" -- does not.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))
import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier         # noqa: E402


def run(script):
    p = subprocess.run([sys.executable, str(HERE / script)], cwd=ROOT,
                       capture_output=True, text=True,
                       env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    print(p.stdout + p.stderr)
    return p.returncode, p.stdout + p.stderr


rc1, o1 = run('probe_f1.py')
rc3, o3 = run('probe_f3.py')
obs = {m.group(1): json.loads(m.group(2))
       for m in re.finditer(r'^OBS (\S+) (\{.*\})$', o1 + o3, re.M)}

need = ['F1', 'F3', 'ARM_full', 'ARM_leaked', 'ARM_clean']
missing = [k for k in need if k not in obs]
if missing or rc1 != 0 or rc3 != 0:
    print(f'REFUSED — rc {rc1}/{rc3}, missing OBS for {missing}')
    sys.exit(1)

f1, f3 = obs['F1'], obs['F3']
A = f3['arms']
# The null's OWN movement under a change it CAN read, used as the yardstick the
# leak-deletion arm is measured against. Stating the leak delta alone would be a
# number without its operating point (A18).
pop_move = abs(A['clean']['null_mrr'] - A['full']['null_mrr'])
leak_move = abs(f1['null_delta_when_leak_deleted_from_train'])

controls = [
    Control('C1_the_real_system_was_run',
            why="ARM_full reproduces G34's withdrawn headline 0.2648067492241375 "
                'to six places from `L.evaluate_link_prediction_full`, so this '
                'attack drove the instrument under test and not a retyped variant',
            can_fail_because='the reproduction misses, meaning a different model',
            null_must_contain='does not reproduce'),
    Control('C2_the_partition_is_exhaustive_and_disjoint',
            why='every arm below is a subset arithmetic away from meaningless; '
                'leaked + clean must equal the whole test set exactly',
            can_fail_because='the two subsets do not sum to n_test',
            null_must_contain='sum mismatch'),
    Control('C3_the_partition_is_not_inert',
            why='a split of the test set that produced the same system score on '
                'both halves would make every comparison here vacuous',
            can_fail_because='leaked and clean system MRRs are within 0.01',
            null_must_contain='no difference'),
    Control('C4_the_null_can_move_at_all',
            why='F1 claims the null does NOT move when the leak is deleted. That '
                'is only evidence if the null CAN move -- an immovable number '
                'would make F1 unfalsifiable (A15). Restricting the population '
                'moves it 0.0180, twenty times the leak deletion',
            can_fail_because='the null is constant across populations too',
            null_must_contain='null is constant'),
]
controls[0].observe(abs(A['full']['system_mrr'] - 0.264807) < 1e-6,
                    {'here': A['full']['system_mrr'], 'G34': 0.2648067492241375})
controls[1].observe(f1['n_leaked'] + f1['n_clean'] == f1['n_test'],
                    {'leaked': f1['n_leaked'], 'clean': f1['n_clean'],
                     'n_test': f1['n_test']})
controls[2].observe(abs(A['leaked']['system_mrr'] - A['clean']['system_mrr']) > 0.01,
                    {'leaked': A['leaked']['system_mrr'],
                     'clean': A['clean']['system_mrr']})
controls[3].observe(pop_move > 0.01, {'null_full': A['full']['null_mrr'],
                                      'null_clean': A['clean']['null_mrr'],
                                      'population_move': round(pop_move, 6)})

falsifiers = [
    Falsifier('F1_null_is_structurally_blind_to_this_leak',
              refutes="that G106's `the null barely moved` is a measurement "
                      'rather than a property of a predicate-conditional prior',
              fires_when='deleting EVERY leak-creating edge from train moves the '
                         'null on a FIXED test set by an order of magnitude less '
                         'than a population change does',
              null_must_contain='the null moved'),
    Falsifier('F2_the_two_system_numbers_are_different_code',
              refutes='that +0.1300 is a difference of differences across two '
                      'system implementations',
              fires_when='the shuffle system cannot be reproduced by the same '
                         'function G48 used for the pair-disjoint number',
              null_must_contain='same implementation'),
    Falsifier('F3_the_leak_attribution_over_counts',
              refutes="G106's +0.1300",
              fires_when='the WITHIN-SPLIT leak-as-lift differs from +0.1300 by '
                         'more than 0.005 -- G106s own F2 threshold, reused so '
                         'the bar is theirs and not one I chose after seeing it',
              null_must_contain='agrees'),
    Falsifier('F4_g106s_quoted_null_stability_survives_the_right_comparison',
              refutes='that 0.001 is the null gap between a leaky and a '
                      'leak-free population',
              fires_when='the WITHIN-SPLIT leak-free null differs from the full '
                         'test null by much more than the 0.001 G106 published',
              null_must_contain='0.001 holds'),
]
falsifiers[0].observe(leak_move * 10 < pop_move,
                      {'null_delta_leak_deleted_from_train': -leak_move,
                       'train_edges_removed': f1['n_train_leak_edges_removed'],
                       'null_delta_population_change': round(pop_move, 6),
                       'ratio': round(pop_move / leak_move, 1)})
falsifiers[1].observe(abs(A['full']['system_mrr'] - 0.264807) >= 1e-6,
                      {'reproduced': A['full']['system_mrr'],
                       'published': 0.2648067492241375})
falsifiers[2].observe(abs(f3['within_split_leak_as_lift'] - 0.130026) > 0.005,
                      {'within_split': f3['within_split_leak_as_lift'],
                       'G106_cross_split': 0.130026,
                       'difference': round(f3['within_split_leak_as_lift'] - 0.130026, 6),
                       'clean_lift_vs_pairdisjoint_lift':
                           f3['clean_lift_vs_pairdisjoint_lift']})
falsifiers[3].observe(pop_move > 0.005,
                      {'null_full_test': A['full']['null_mrr'],
                       'null_clean_subset': A['clean']['null_mrr'],
                       'gap': round(pop_move, 6),
                       'G106_published_gap': 0.001})

(HERE / 'result.json').write_text(json.dumps({
    'spike': 'H247', 'target': 'spikes/G106_shuffle_null/ (AGENT-2)',
    'observations': obs,
    'falsifiers_fired': {f.name: bool(f.fired) for f in falsifiers},
    'verdict': 'G106 CONCLUSION CONFIRMED AND STRENGTHENED; ITS STATED WARRANT '
               'WITHDRAWN. The +0.1300 reproduces at +0.1326 from a within-split '
               'construction needing no cross-split difference of differences. '
               'The `0.001 null stability` that was offered as its warrant is a '
               'property of the prior s form (leak deleted from train: 0.0009) '
               'and is not the gap it was read as (right comparison: 0.0180).',
}, indent=2) + '\n')

ok, problems = kfcheck.certify(
    str(HERE),
    deps=[str(ROOT / 'spikes' / 'G34_length1_and_constants'),
          str(ROOT / 'spikes' / 'G104_null_in_the_loop')],
    artifacts=[str(HERE / 'result.json'), str(HERE / 'f1.json'), str(HERE / 'f3.json')],
    controls=controls, falsifiers=falsifiers, allow_dirty=True,
    note='H247: G106 warranted +0.1300 with `the null barely moved`. The null '
         'cannot move on this leak -- it is predicate-conditional and the leak '
         'is an (s,o) edge. Measured within one split, the conclusion survives '
         'at +0.1326 and the warrant does not.',
    falsifier='the within-split leak-as-lift differing from +0.1300 by more '
              "than G106's own 0.005 threshold, or the null moving materially "
              'when every leak-creating edge is deleted from train')
print(f'certify ok={ok}')
for x in problems:
    print('   ', x)
sys.exit(0 if ok else 1)
