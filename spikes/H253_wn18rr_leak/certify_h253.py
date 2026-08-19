#!/usr/bin/env python3
"""H253 — certify. ATTACKER-1, 2026-08-19.

Certifies from the OBS lines the probes PRINT, never from a restatement.

WHAT IS BEING WITHDRAWN, STATED PRECISELY:
  G105's cross-dataset CONCLUSION -- "WN18RR's null is 6.8x lower than
  FB15k-237's and the two datasets do not measure the same thing" -- is NOT
  attacked and is if anything strengthened. Neither is G92's 0.3611, which
  reproduces here to six places. What is withdrawn is the GRADE: 14.1x over the
  null as evidence the system works on WN18RR.
"""
from __future__ import annotations
import json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))
import kfcheck                                    # noqa: E402
from provenance import Control, Falsifier        # noqa: E402


def run(script):
    p = subprocess.run([sys.executable, str(HERE / script)], cwd=ROOT,
                       capture_output=True, text=True,
                       env={**os.environ, 'PYTHONUNBUFFERED': '1'})
    print(p.stdout[-4000:] + p.stderr[-2000:])
    return p.returncode, p.stdout + p.stderr


rcn, on = run('probe_null.py')
rcs, os_ = run('probe_system.py')
obs = {m.group(1): json.loads(m.group(2))
       for m in re.finditer(r'^OBS (\S+) (\{.*\})$', on + os_, re.M)}
need = ['NULL', 'SYS', 'ARM_full', 'ARM_leaked', 'ARM_clean', 'RELATIONS']
missing = [k for k in need if k not in obs]
if missing or rcn != 0 or rcs != 0:
    print(f'REFUSED — rc {rcn}/{rcs}, missing OBS for {missing}')
    sys.exit(1)

N, S, R = obs['NULL'], obs['SYS'], obs['RELATIONS']
A = S['arms']
top_rel, top_n = max(((r, d['leaked']) for r, d in R.items()), key=lambda x: x[1])
leak_concentration = top_n / N['n_leaked']
per_rel = S['per_relation_mrr']
# The relation the leak barely touches, used as the arm that says subsetting
# ITSELF does not move scores.
hyp_full = per_rel['full']['_hypernym']['mrr']
hyp_clean = per_rel['clean']['_hypernym']['mrr']

controls = [
    Control('C1_both_published_numbers_reproduce',
            why="G92's 0.3611 and G105's 0.0256 are both re-derived here from "
                'their own code, so this attack drove the instruments under '
                'test rather than retyped copies of them (family C)',
            can_fail_because='either fails to reproduce, meaning a different model',
            null_must_contain='does not reproduce'),
    Control('C2_partition_is_exhaustive_and_disjoint',
            why='every number below is one subset arithmetic error away from '
                'meaningless: leaked + clean must equal the test set, and their '
                'query counts must equal 6,268',
            can_fail_because='the subsets do not sum to n_test or 2 * n_test',
            null_must_contain='sum mismatch'),
    Control('C3_the_partition_is_not_inert',
            why='a partition that scored the same on both halves would make '
                'every comparison here vacuous',
            can_fail_because='leaked and clean MRRs are within 0.01',
            null_must_contain='no difference'),
    Control('C4_the_null_can_move',
            why="F1 claims the null does NOT move when the leak is deleted from "
                'train. That is only evidence if it CAN move: restricting the '
                'population moves it +0.0127 while the deletion moves it 0.0000',
            can_fail_because='the null is constant across populations too, in '
                             'which case F1 is unfalsifiable (A15)',
            null_must_contain='null is constant'),
    Control('C5_subsetting_itself_does_not_move_scores',
            why='_hypernym is 0.2% leaked and 40% of the test set. If the act of '
                'subsetting moved scores, it would move too. full 0.0116 vs '
                'clean 0.0116 -- so the leaked/clean gap is the leak and not the '
                'slicing',
            can_fail_because='_hypernym moves materially between full and clean',
            null_must_contain='moved'),
]
controls[0].observe(N['reproduces_g105'] and S['reproduces_g92'],
                    {'null_here': N['null_mrr_full_test'], 'g105': 0.0256,
                     'sys_here': A['full']['mrr'], 'g92': 0.3611})
controls[1].observe(N['n_leaked'] + N['n_clean'] == N['n_test']
                    and A['leaked']['n_queries'] + A['clean']['n_queries'] == 6268,
                    {'leaked': N['n_leaked'], 'clean': N['n_clean'],
                     'n_test': N['n_test'],
                     'queries': A['leaked']['n_queries'] + A['clean']['n_queries']})
controls[2].observe(abs(A['leaked']['mrr'] - A['clean']['mrr']) > 0.01,
                    {'leaked': A['leaked']['mrr'], 'clean': A['clean']['mrr']})
controls[3].observe(abs(N['null_delta_population_change']) > 0.005,
                    {'population_change': N['null_delta_population_change'],
                     'leak_deletion': N['null_delta_when_leak_deleted_from_train']})
controls[4].observe(abs(hyp_full - hyp_clean) < 0.005,
                    {'_hypernym_full': hyp_full, '_hypernym_clean': hyp_clean,
                     'leak_pct': R['_hypernym']['leak_pct']})

falsifiers = [
    Falsifier('F1_wn18rr_null_is_blind_to_the_leak_too',
              refutes="that G105's 0.0256 might itself be leak-inflated",
              fires_when='deleting every leak-creating edge from train moves the '
                         'null far less than a population change does',
              null_must_contain='the null moved'),
    Falsifier('F2_the_margin_lives_in_the_leaked_subset',
              refutes="G105's 14.1x as evidence the system works on WN18RR",
              fires_when='the multiple over the null on the NON-leaked triples '
                         'falls below 1.0, i.e. the null wins there',
              null_must_contain='clean subset still beats the null'),
    Falsifier('F3_the_leak_is_spread_rather_than_concentrated',
              refutes='that a single relation explains it, which would make the '
                      'finding a number with no mechanism',
              fires_when='one relation supplies more than 80% of the leaked '
                         'triples',
              null_must_contain='spread across relations'),
]
falsifiers[0].observe(
    abs(N['null_delta_when_leak_deleted_from_train']) * 5
    < abs(N['null_delta_population_change']),
    {'delta_leak_deleted_from_train': N['null_delta_when_leak_deleted_from_train'],
     'train_edges_removed': N['n_train_leak_edges_removed'],
     'delta_population_change': N['null_delta_population_change']})
falsifiers[1].observe(S['multiple_clean'] < 1.0,
                      {'multiple_full': S['multiple_full'],
                       'multiple_clean': S['multiple_clean'],
                       'margin_full': S['margin_full'],
                       'margin_clean': S['margin_clean']})
falsifiers[2].observe(leak_concentration > 0.80,
                      {'relation': top_rel, 'leaked_triples': top_n,
                       'of_total_leaked': N['n_leaked'],
                       'share': round(leak_concentration, 4),
                       'mrr_leaked': per_rel['leaked'][top_rel]['mrr'],
                       'mrr_clean': per_rel['clean'][top_rel]['mrr']})

(HERE / 'result.json').write_text(json.dumps({
    'spike': 'H253',
    'target': 'spikes/G105_wn18rr_frequency_null/ + spikes/G92_wn18rr_hybrid/',
    'observations': obs,
    'falsifiers_fired': {f.name: bool(f.fired) for f in falsifiers},
    'verdict': "G92's 0.3611 and G105's 0.0256 both reproduce exactly. The 14.1x "
               'margin lives entirely in the 34.97% of WN18RR test triples whose '
               '(s,o) pair is already in train: 0.9707 there, 0.0333 on the rest '
               '-- 0.87x the null. G105 cross-dataset conclusion untouched; the '
               'GRADE is what is withdrawn.',
}, indent=2) + '\n')

ok, problems = kfcheck.certify(
    str(HERE),
    deps=[str(ROOT / 'spikes' / 'G105_wn18rr_frequency_null'),
          str(ROOT / 'spikes' / 'G92_wn18rr_hybrid')],
    artifacts=[str(HERE / 'result.json'), str(HERE / 'null.json'),
               str(HERE / 'system.json')],
    controls=controls, falsifiers=falsifiers, allow_dirty=True,
    note='H253: WN18RR official split carries 34.97% same-pair leakage -- more '
         'than the 30.01% FB15k-237 shuffle this fleet refused to gate on -- and '
         "G92's entire margin over the null lives inside it.",
    falsifier='the non-leaked subset still beating the null, or the null moving '
              'when every leak-creating edge is deleted from train, or _hypernym '
              'moving between the full and clean arms')
print(f'certify ok={ok}')
for x in problems:
    print('   ', x)
sys.exit(0 if ok else 1)
