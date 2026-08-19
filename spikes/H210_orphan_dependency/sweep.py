#!/usr/bin/env python3
"""sweep.py -- H210. The four preregistered falsifiers, run.

The scan lives in `spikes/harness/depcheck.py` and is IMPORTED, not retyped:
this file is the RUN and the evidence, that file is the instrument. `depcheck`'s
own docstring carries the defect class and the §12.7 rationale.

  F1  kills the row     -- materialise HEAD's tracked tree with `git archive`
                           and run H188's own stated repro. If it completes,
                           the refutation is reproducible and there is nothing
                           here. PREDICTED: fails at import.
  F2  kills the class   -- if the fleet-wide sweep finds at most ONE untracked
                           executable pair, the rate is the deliverable and no
                           module ships (ok-1's H23 precedent: three detectors
                           measured at 41%/93%/0%, none shipped).
  F3  kills a sub-claim -- if `trackcheck.py` (mine) names any S91 path in its
                           live output, my module is not blind and that
                           sentence is withdrawn.
  F4  controls the instrument -- the sweep must FLAG a tracked file importing
                           an untracked path and must NOT flag one importing a
                           tracked path; an inert sweep and a clean tree are
                           indistinguishable (H124). Four-sided in `depcheck`'s
                           `selfcheck`, because the two-sided version passed
                           while every DIRECTORY was being misreported.

  python3 sweep.py            -> sweep.json + provenance.json
"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))

import depcheck                                            # noqa: E402
from depcheck import scan, summarise, du                    # noqa: E402


def arm_f1(scratch):
    """F1 -- materialise HEAD's TRACKED tree and run H188's own stated repro."""
    import shutil
    d = Path(scratch) / 'f1_tracked_tree'
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    tar = subprocess.run(['git', 'archive', 'HEAD'], cwd=ROOT, capture_output=True)
    subprocess.run(['tar', '-x', '-C', str(d)], input=tar.stdout, check=True)
    repro = d / 'spikes' / 'H188_seats_are_one_computation' / 'attack.py'
    p = subprocess.run([sys.executable, str(repro)], capture_output=True, text=True)
    return {'exit': p.returncode, 'stderr_tail': p.stderr.strip().split('\n')[-1:],
            's91_in_archive': (d / 'spikes' / 'S91_multi_agent_quorum').exists()}


def arm_f3(scratch):
    """F3 -- does `trackcheck.py`, mine, name any S91 path in live output?"""
    p = subprocess.run([sys.executable, str(ROOT / 'spikes' / 'harness' / 'trackcheck.py')],
                       cwd=ROOT, capture_output=True, text=True)
    out = p.stdout + p.stderr
    return {'exit': p.returncode, 's91_mentions': out.count('S91'),
            'lines': len(out.strip().split('\n'))}


def arm_f4(scratch):
    """F4 -- the instrument's own four-sided control, run here so its verdict
    is recorded in this spike's provenance rather than only printed."""
    return depcheck.selfcheck(Path(scratch) / 'f4_fixture')


def main():
    scratch = ROOT / '.scratch' / 'H210'
    scratch.mkdir(parents=True, exist_ok=True)

    hits, ignmeta = scan(ROOT)
    summary = summarise(hits)
    summary['ignore_classifier'] = ignmeta

    f1 = arm_f1(scratch)
    f3 = arm_f3(scratch)
    f4 = arm_f4(scratch)

    # the motivating pair, resolved mechanically rather than by eye (§12.4)
    motivating = ('spikes/H188_seats_are_one_computation/attack.py',
                  'spikes/S91_multi_agent_quorum/run.py')
    ast_pairs = {tuple(p) for p in summary['ast_pairs']}

    from provenance import Control, Falsifier
    import kfcheck

    c1 = Control(
        'C1_sweep_is_four_sided',
        why='an inert sweep and a clean tree are indistinguishable (H124), so '
            'the instrument must produce BOTH verdicts on a constructed '
            'fixture, in the FILE shape and the DIRECTORY shape',
        null_must_contain='a tracked dependency and a tracked DIRECTORY, both '
                          'of which the first version of this scan flagged',
        can_fail_because='the fixture tracked file or tracked directory is '
                         'flagged, or either untracked case is not; every one '
                         'of these was killed by a mutation before shipping')
    c1.observe(all(f4.values()), f4, detail='F4, five checks, four-sided')

    c2 = Control(
        'C2_detector_sees_its_motivating_case',
        why='error 36: my last detector could not see the instance it was '
            'written for, and its header argued the gap was a virtue',
        null_must_contain='the motivating pair itself -- the one case the '
                          'detector was written for',
        can_fail_because='H188/attack.py -> S91/run.py absent from AST pairs, '
                         'which would mean TEXT mode alone carries the finding')
    c2.observe(motivating in ast_pairs,
               {'motivating_pair_in_AST': motivating in ast_pairs,
                'ast_pair_count': len(ast_pairs)},
               detail='AST mode, not TEXT')

    c3 = Control(
        'C3_ignored_is_separated_from_untracked',
        why='a gitignored dep is a DECLARED absence; conflating it with an '
            'undeclared one inflates the rate F2 is decided on',
        null_must_contain='at least one gitignored path, which this tree has '
                          'by construction (`elders/`, `.scratch/`)',
        can_fail_because='zero hits classified IGNORED, which for a tree '
                         'carrying `elders/` and `.scratch/` would mean '
                         '`git check-ignore` never ran')
    c3.observe(summary['ignored'] > 0,
               {'ignored': summary['ignored'], 'untracked': summary['untracked']},
               detail='git check-ignore --stdin')

    c4 = Control(
        'C4_v1_ignore_classifier_was_truncated',
        why='I claim v1 of this module mis-classified deps because '
            '`git check-ignore --stdin` aborted on a submodule path and its '
            'return code was never read; that claim needs its own observation',
        null_must_contain='agreement -- if git had exited 0/1 over the whole '
                          'set, v1 and v2 would name the same ignored paths '
                          'and v1 numbers would have stood',
        can_fail_because='v1_rc in (0,1) and v1_missed == 0, i.e. the batch '
                         'form never truncated and this whole repair is noise')
    c4.observe(ignmeta['v1_rc'] not in (0, 1) and ignmeta['v1_missed'] > 0,
               ignmeta, detail='v1 form re-run beside the fixed one')

    f1c = Falsifier(
        'F1_refutation_is_reproducible',
        refutes='the row: if H188 runs from the tracked tree there is nothing here',
        fires_when='`python3 spikes/H188_*/attack.py` EXITS 0 inside a tree '
                   'materialised from `git archive HEAD`',
        null_must_contain='exit 0 -- the tree is a real checkout and the '
                          'script is the one HEAD ships, so nothing in the '
                          'setup forbids success')
    f1c.observe(f1['exit'] == 0,
                {'exit': f1['exit'], 's91_in_archive': f1['s91_in_archive'],
                 'stderr_tail': f1['stderr_tail']}, detail='F1')

    f2c = Falsifier(
        'F2_class_is_one_anecdote',
        refutes='the CLASS: one pair means the rate is the deliverable and no '
                'module ships (ok-1 H23 precedent -- 41%/93%/0%, none shipped)',
        fires_when='the fleet-wide sweep finds at most ONE untracked '
                   'executable (AST) dependency pair',
        null_must_contain='a one-pair outcome, which the sweep can produce: '
                          'F4 shows it reports exactly the pairs present')
    f2c.observe(len(ast_pairs) <= 1,
                {'ast_pairs': len(ast_pairs), 'untracked_hits': summary['untracked'],
                 'files': summary['files_with_untracked_dep']}, detail='F2')

    f3c = Falsifier(
        'F3_trackcheck_is_not_blind',
        refutes='my sub-claim that my own module cannot see S91',
        fires_when='`trackcheck.py` live output names ANY S91 path',
        null_must_contain='an S91 mention -- trackcheck prints every NEW '
                          'untracked citation in full, so nothing truncates '
                          'S91 out of its output')
    f3c.observe(f3['s91_mentions'] > 0,
                {'s91_mentions': f3['s91_mentions'], 'exit': f3['exit'],
                 'output_lines': f3['lines']}, detail='F3')

    deps = sorted({p[1] for p in ast_pairs})
    sizes = {p: du(ROOT / p) for p in deps}
    committable = {p: s for p, s in sizes.items() if s <= 1_000_000}
    out = {'summary': summary, 'F1': f1, 'F3': f3, 'F4': f4,
           'ast_dep_bytes': sizes,
           'ast_dep_over_1mb': sorted(p for p, s in sizes.items() if s > 1_000_000),
           'committable_bytes_total': sum(committable.values()),
           'committable_paths': len(committable),
           'motivating_pair_found_by_AST': motivating in ast_pairs,
           'hits': hits}
    (HERE / 'sweep.json').write_text(json.dumps(out, indent=1, sort_keys=True))

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(ROOT / 'spikes' / 'harness'), str(HERE)],
        artifacts=[str(HERE / 'sweep.json')],
        controls=[c1, c2, c3, c4],
        falsifiers=[f1c, f2c, f3c],
        allow_dirty=True,
        note='H210: a tracked file whose dependency is not tracked. Report-only.',
        falsifier='H188 runs to completion from a tree materialised by '
                  '`git archive HEAD` (F1), or the sweep finds exactly one '
                  'executable pair (F2), or trackcheck already names S91 (F3).')

    print(json.dumps(summary, indent=1, sort_keys=True))
    print(f'F1 fired={f1c.fired}  F2 fired={f2c.fired}  F3 fired={f3c.fired}')
    print(f'C1={c1.fired} C2={c2.fired} C3={c3.fired} C4={c4.fired}')
    print(f'certify ok={ok} problems={problems}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
