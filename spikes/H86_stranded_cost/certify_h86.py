#!/usr/bin/env python3
"""H86 — ATOM-3, 2026-08-18. Certifies the row whose OWN CLAIM LINE is retracted.

WHAT THIS ROW CLAIMED WHEN IT WAS OPENED (CHANNEL.md:371, ATOM-3, 2026-08-17)
-----------------------------------------------------------------------------
  "`spikes/harness/stranded.sh` ... NO LONGER COMPLETES. It exceeded a 2-minute
   bound twice just now, on the same tree where it finished in ~20 seconds when
   I published it. ... the cost is O(files x history) ... CLASS: A DIAGNOSTIC
   WHOSE COST SCALES WITH THE THING IT MEASURES, SO IT DIES EXACTLY WHEN IT
   BECOMES USEFUL."

THAT CLASS IS WITHDRAWN. The number was real; the model was wrong (CLAUDE.md
family E). Same script, same repo, one day later: 19.3 s.

  run                     wall      user     sys     CPU total   cpu%
  v1  2026-08-17 21:36   232.0 s   13.00   20.12      33.1 s      14%
  v1  2026-08-18 11:37    19.3 s    7.16   11.37      18.5 s      96%
  v2  2026-08-18 11:37    13.6 s   11.34    4.04      15.4 s     113%

86% of the 3:52 was the process NOT RUNNING. And `14% cpu` was printed in
`v1_full.time`, the very artifact the claim quoted -- the refutation was inside
the evidence at publication time. `spikes/quiet.sh` gates load-bound
measurements (MISSION_LOOP.md §3); it was never run before the claim, and it
REFUSES on this host right now.

WHAT SURVIVES, WITH ITS OPERATING POINT (A18)
----------------------------------------------
The one-pass rewrite is CORRECT -- the preregistered falsifier ran and did not
fire -- and buys 1.20x CPU / 1.42x wall at loadavg 7.25 on 14 cores, over 359
paths and 461+ commits. Not a rescue. It removes 688 forks: system time
11.37 -> 4.04 s, traded for awk scanning, user 7.16 -> 11.34 s. Whether that
also degrades more gracefully under load is UNTESTED and NOT CLAIMED (§12.12:
an unrun falsifier is how every surviving error here survived).

WHAT THE ROW ACTUALLY FOUND, AND IT IS NOT WHAT IT WENT LOOKING FOR
--------------------------------------------------------------------
CLASS: `git status --porcelain` COLLAPSES AN UNTRACKED DIRECTORY TO ONE ENTRY,
so a `[ -f ]` guard drops every file inside it while the scan reports a count
that reads as total coverage. `stranded.sh` was blind to 151 files in 16
directories -- including 8 LIVE SPIKE DIRECTORIES from four lanes. A new spike
directory is the commonest stranded artifact this repo makes, and the tool built
to find stranded work could not see one. Fixed with `-uall`: 382 -> 483 paths.

Second site, found by grepping the class and NOT fixed here (H102, reported to
livechat.log per §12.9): `spikes/harness/provenance.py:86`, inside certify's own
dirty-dependency guard -- the family-C guard.

  python3 spikes/H86_stranded_cost/certify_h86.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify, Control                       # noqa: E402


def sh(*args, **kw):
    return subprocess.run(args, cwd=kw.get('cwd', ROOT), capture_output=True,
                          text=True).stdout


def status_paths(uall):
    cmd = ['git', 'status', '--porcelain'] + (['-uall'] if uall else [])
    return [ln.split()[-1] for ln in sh(*cmd).splitlines() if ln.split()]


def main():
    # ---- C1: the defect is present in plain porcelain and absent under -uall.
    plain, uall = status_paths(False), status_paths(True)
    dirs = [p for p in plain if os.path.isdir(os.path.join(ROOT, p))]
    hidden = 0
    for d in dirs:
        for _, _, fs in os.walk(os.path.join(ROOT, d)):
            hidden += len(fs)
    c1 = Control(
        'untracked_dirs_collapse',
        'the scan must be shown to have been blind: plain porcelain returns '
        'DIRECTORY entries that the [ -f ] guard drops',
        null_must_contain='a tree with zero untracked directories, where plain '
                          'and -uall agree and there is nothing to find',
        can_fail_because='if every untracked path were already a file, `dirs` '
                         'would be empty, `hidden` 0, and plain == -uall -- the '
                         'defect would not exist on this tree and C1 would not fire')
    c1.observe(len(dirs) > 0 and hidden > 0 and len(uall) > len(plain),
               {'plain_paths': len(plain), 'uall_paths': len(uall),
                'directory_entries_dropped': len(dirs),
                'files_hidden_behind_them': hidden,
                'dirs': sorted(dirs)},
               '%d directories hid %d files' % (len(dirs), hidden))

    # ---- C2: the fix's control is MUTATION-TESTED. Strip -uall from the
    # shipped scan, run --selfcheck, and require it to go red; restore, require
    # green. A control nobody has seen fail is a control nobody has tested.
    # The mutant is written to a COPY, never to the shipped file. Mutating
    # spikes/harness/stranded.sh in place -- which the first draft did -- opens
    # a window in which a co-lane's `git commit` captures the BROKEN version
    # (H19, H66), and `finally` does not close a window, it only shortens it.
    # `stranded.sh` takes ROOT from $(pwd), so a copy run from the repo root is
    # the same program reading the same tree.
    tool = os.path.join(ROOT, 'spikes', 'harness', 'stranded.sh')
    src = open(tool).read()
    assert 'git status --porcelain -uall' in src, 'anchor gone; refusing to guess'
    live = os.path.join(HERE, '.mut_live.sh')
    mut = os.path.join(HERE, '.mut_broken.sh')
    open(live, 'w').write(src)
    open(mut, 'w').write(src.replace('git status --porcelain -uall',
                                     'git status --porcelain'))
    try:
        clean = subprocess.run(['sh', live, '--selfcheck'], cwd=ROOT,
                               capture_output=True, text=True)
        mutant = subprocess.run(['sh', mut, '--selfcheck'], cwd=ROOT,
                                capture_output=True, text=True)
        restored = subprocess.run(['sh', tool, '--selfcheck'], cwd=ROOT,
                                  capture_output=True, text=True)
    finally:
        for f in (live, mut):
            os.path.exists(f) and os.remove(f)
    c2 = Control(
        'selfcheck_is_mutation_tested',
        'the new control must FAIL when the fix it guards is removed, or it is '
        'decoration (A15)',
        null_must_contain='a selfcheck that queries git directly rather than the '
                          'shipped scan -- which is what the FIRST DRAFT of this '
                          'control did, and it stayed green under the mutant',
        can_fail_because='if --selfcheck returned 0 with -uall stripped, C2 does '
                         'not fire; that is exactly what the first draft did')
    c2.observe(clean.returncode == 0 and mutant.returncode != 0
               and restored.returncode == 0,
               {'unmutated_rc': clean.returncode, 'mutant_rc': mutant.returncode,
                'restored_rc': restored.returncode,
                'mutant_stdout': mutant.stdout.strip()[:160]},
               'green -> red -> green across the mutation')

    # ---- C3: the retraction's own evidence. The published cost model must be
    # shown to be contradicted by a field of the measurement it was built on.
    tfile = os.path.join(HERE, 'v1_full.time')
    ttext = open(tfile).read() if os.path.exists(tfile) else ''
    c3 = Control(
        'wall_was_not_cpu',
        'the retraction rests on cpu%% being far below 100 in the ORIGINAL '
        'artifact, not on a re-run being fast',
        null_must_contain='a v1_full.time showing ~100% cpu, which would mean '
                          'the 232 s really was this process computing and the '
                          'O(files x history) story would stand',
        can_fail_because='if v1_full.time read e.g. "95% cpu" the original claim '
                         'would be supported and this retraction would be wrong')
    c3.observe('14% cpu' in ttext,
               {'v1_full.time': ttext.strip(),
                'cpu_seconds_then': 13.00 + 20.12, 'wall_seconds_then': 232.02,
                'wall_seconds_now': 19.30, 'cpu_seconds_now': 7.16 + 11.37},
               'the artifact quoted by the claim contained its refutation')

    # ---- C4: the class propagated. A second site must exist, or "fix the CLASS"
    # was rhetoric (§12.2).
    hits = sh('grep', '-rn', 'git status --porcelain',
              'spikes/harness/').splitlines()
    other = [h for h in hits if 'stranded.sh' not in h and '-uall' not in h]
    c4 = Control(
        'class_has_a_second_site',
        '§12.2 requires grepping the whole harness for the class before the row '
        'closes; a class with one instance is a site',
        null_must_contain='a harness where stranded.sh is the only reader of '
                          'git status --porcelain, in which case there is no '
                          'class to propagate and H102 should not be filed',
        can_fail_because='if grep returned only stranded.sh, C4 does not fire '
                         'and the "CLASS" framing is withdrawn')
    c4.observe(len(other) > 0,
               {'other_sites': [o.strip()[:120] for o in other]},
               '%d site(s) besides stranded.sh' % len(other))

    out = {
        'retracted_claim': 'stranded.sh "no longer completes"; cost is '
                           'O(files x history)',
        'retraction_reason': 'family E -- number real, model wrong. 86% of the '
                             '232 s wall was not this process running.',
        'timings': {
            'v1_2026-08-17T21:36': {'wall_s': 232.02, 'user_s': 13.00,
                                    'sys_s': 20.12, 'cpu_pct': 14},
            'v1_2026-08-18T11:37': {'wall_s': 19.30, 'user_s': 7.16,
                                    'sys_s': 11.37, 'cpu_pct': 96},
            'v2_2026-08-18T11:37': {'wall_s': 13.60, 'user_s': 11.34,
                                    'sys_s': 4.04, 'cpu_pct': 113},
        },
        'speedup_cpu': round((7.16 + 11.37) / (11.34 + 4.04), 3),
        'speedup_wall': round(19.30 / 13.60, 3),
        'operating_point': {'loadavg_1m': 7.25, 'cores': 14, 'paths': 359,
                            'commits': '461+', 'quiet_sh': 'REFUSES'},
        'wall_citable': False,
        'wall_reason': 'spikes/quiet.sh REFUSES on this host (loadavg 6.86 vs '
                       '3.50, 4 foreign containers, mediaanalysisd 167.9%). '
                       'CPU seconds are the load-insensitive measure and the '
                       'ratio is published with its operating point (A18, §3). '
                       'The S84 precedent.',
        'contention_resistance': 'NOT CLAIMED -- falsifier not run (§12.12)',
        'falsifier_preregistered_and_run': {
            'text': 'if one git log --name-only pass does not reproduce v1\'s '
                    'exact classification on the current tree, the rewrite is '
                    'wrong and v1 stays',
            'fired': False,
            'result': 'IDENTICAL file-by-file (verdict, owner, path) over 359 '
                      'paths; v2a == v2b across the v1 run',
            'protocol_verdict': 'NOT DECISIVE -- compare.sh\'s drift control '
                                'fired: the tree fingerprint moved at all four '
                                'boundaries. Recorded as the control reported '
                                'it. The control was NOT narrowed to make it '
                                'pass (H26b).',
            'scope': 'covers the HIST rewrite ONLY. The -uall fix deliberately '
                     'CHANGES the output (359 -> 483 paths) and is therefore '
                     'not covered by an identity falsifier; C1 and C2 cover it.',
        },
        'coverage': {'before_uall': len(plain), 'after_uall': len(uall),
                     'files_recovered': hidden,
                     'directories_recovered': len(dirs)},
    }
    # Whose uncommitted files remain in the dep, so `allow_dirty` is a
    # disclosure and not a shrug.
    dirty_residue = [ln.strip() for ln in
                     sh('git', 'status', '--porcelain', '--',
                        'spikes/harness').splitlines() if ln.strip()]
    out['dep_dirty_residue'] = dirty_residue
    out['dep_pinned_commit_for_tool'] = sh(
        'git', 'log', '-1', '--format=%h', '--',
        'spikes/harness/stranded.sh').strip()

    with open(os.path.join(HERE, 'h86.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'harness')],
        artifacts=[os.path.join(HERE, 'h86.json')],
        controls=[c1, c2, c3, c4],
        captures=[('compare_verdict', open(os.path.join(HERE, 'compare.out')).read())],
        # ACKNOWLEDGED, not waved through. `stranded.sh` -- the only file in this
        # dep this row changed -- is COMMITTED (afcf3a5) before this runs, so the
        # build is pinned for the thing under test. What remains dirty in
        # spikes/harness/ belongs to other lanes and I may not commit it (§13,
        # H19, H66); H72/H73 are the standing rows for a shared-tree gate one
        # lane cannot clear. The residue is enumerated below at run time, so a
        # reader can see exactly which files were dirty and whose they are.
        allow_dirty=True,
        note='dep spikes/harness is dirty in files this row does not touch: '
             + '; '.join(sorted(dirty_residue)) if dirty_residue else
             'dep spikes/harness clean',
        falsifier='if v1_full.time had shown ~100% cpu, the 232 s would have '
                  'been real work, the O(files x history) class would stand, '
                  'and this retraction would be wrong')

    print(json.dumps(out, indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
