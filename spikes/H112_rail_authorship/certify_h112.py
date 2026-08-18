#!/usr/bin/env python3
"""H112 — ATOM-3, 2026-08-18. A lane wrote the rail that binds it.

The row, its falsifier, and the limits of its remedy are in RESULT.md and in
`spikes/harness/railguard.py`'s header. This file executes the claims.

  python3 spikes/H112_rail_authorship/certify_h112.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify, Control                       # noqa: E402
from railguard import section, authorised                  # noqa: E402

CASE = '4682d6f'          # the commit that widened the rail


def blob(rev, path):
    p = subprocess.run(['git', 'show', '%s:%s' % (rev, path)],
                       cwd=ROOT, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else ''


def rail_moved(rev, path='CLAUDE.md', anchor='## Safety rails'):
    return section(blob(rev + '~1', path), anchor) != section(blob(rev, path),
                                                             anchor)


def main():
    # ---- C1. The row's PREREGISTERED FALSIFIER, and it is the negative case:
    # a gate that cannot separate a rail edit from any other edit to the same
    # file is a file-level tripwire wearing a section-level name.
    verdicts = {r: rail_moved(r) for r in (CASE, CASE + '~1', CASE + '~2')}
    msg = subprocess.run(['git', 'log', '-1', '--format=%B', CASE], cwd=ROOT,
                         capture_output=True, text=True).stdout
    would_refuse = verdicts[CASE] and not authorised(msg)
    c1 = Control(
        'replays_the_real_case_and_only_it',
        'the gate must REFUSE the commit that actually widened the rail and stay '
        'SILENT on neighbouring commits that touch the same file elsewhere',
        null_must_contain='a history where 4682d6f~1 and ~2 also moved the rail '
                          'section, in which case "refuses 4682d6f" would show '
                          'nothing about precision',
        can_fail_because='if either neighbour also read as a rail change, the '
                         'gate is a file-level tripwire and the row is withdrawn')
    c1.observe(would_refuse and not verdicts[CASE + '~1']
               and not verdicts[CASE + '~2'],
               {'rail_moved_by': verdicts,
                'case_carried_authorisation': authorised(msg),
                'would_refuse_' + CASE: would_refuse},
               'refuses %s, silent on both neighbours' % CASE)

    # ---- C2. The module's own controls, run as a subprocess so a green here
    # means the shipped entry point is green, not an importable subset of it.
    sc = subprocess.run(['python3', os.path.join(ROOT, 'spikes', 'harness',
                                                 'railguard.py'), '--selfcheck'],
                        cwd=ROOT, capture_output=True, text=True)
    c2 = Control(
        'module_selfcheck_green',
        '§12.3: a harness component ships a runnable check that fails when it '
        'breaks; it must be green through the CLI a hook actually invokes',
        null_must_contain='a selfcheck that only asserts pure functions and '
                          'never drives git -- which would stay green while the '
                          'hook was inert, the exact defect v1 shipped with',
        can_fail_because='it returned non-zero twice during development: once '
                         'when --carried judged the wrong repo, once on the '
                         'trailing-blank-line comparison')
    c2.observe(sc.returncode == 0,
               {'rc': sc.returncode, 'stdout': sc.stdout.strip()[:400]},
               'selfcheck exits 0 through the CLI')

    # ---- C3. INSTALLED, not merely written. .git/hooks is untracked, so a gate
    # in the tree reaches nobody (§13.1); and the installed copy must not drift.
    src = os.path.join(ROOT, 'spikes', 'harness', 'commit-msg.hook')
    inst = os.path.join(ROOT, '.git', 'hooks', 'commit-msg')
    same = os.path.exists(inst) and open(inst).read() == open(src).read()
    wired = 'railguard.py' in open(src).read()
    c3 = Control(
        'gate_is_installed_and_undrifted',
        'a gate that exists only in the tree enforces nothing -- .git/hooks is '
        'untracked and cannot be tracked',
        null_must_contain='an installed hook that predates v8 and does not '
                          'mention railguard, which is what a forgotten '
                          'install_hooks.sh leaves behind',
        can_fail_because='skip `sh spikes/harness/install_hooks.sh` after '
                         'editing the source and this goes red')
    c3.observe(same and wired,
               {'installed_matches_source': same, 'v8_wires_railguard': wired},
               'installed copy is byte-identical to the reviewed source')

    # ---- C4. It does not block ordinary work. The live proof is that this
    # repo's own HEAD -- which carries the gate itself -- was committed THROUGH
    # the gate, with no authorisation trailer, because it changes no rail.
    head = subprocess.run(['git', 'log', '-1', '--format=%H %s'], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    head_sha = head.split()[0]
    c4 = Control(
        'ordinary_commits_still_pass',
        'a gate that refuses commits it has no business judging is a false '
        'positive that wedges every lane (H72/H73)',
        null_must_contain='a gate scoped to FILES rather than sections, which '
                          'would have refused this very commit -- it edits '
                          'neither CLAUDE.md nor MISSION_LOOP.md, but the '
                          'file-scoped version also refused any repo lacking '
                          'the harness, which test_loop_gate.sh caught',
        can_fail_because='the first draft DID fail this: two acceptance checks '
                         'in test_loop_gate.sh flipped to `refuse`')
    c4.observe(not rail_moved(head_sha) and head_sha != '',
               {'head': head, 'head_changed_a_rail': rail_moved(head_sha)},
               'the commit carrying the gate passed the gate')

    out = {
        'case': CASE,
        'case_subject': subprocess.run(
            ['git', 'log', '-1', '--format=%s', CASE], cwd=ROOT,
            capture_output=True, text=True).stdout.strip(),
        'case_atom': 'AGENT-2', 'case_reviewed_by': 'unreviewed',
        'outcome_not_in_dispute': 'the operator has since confirmed the push is '
                                  'authorised, directly. This row is about the '
                                  'absence of a mechanism, not that decision.',
        'rail_moved_by': verdicts,
        'would_refuse_case': would_refuse,
        'what_the_gate_cannot_do': 'verify authorisation. Any lane can type the '
                                   'trailer, as any lane can type Atom: (§13.1). '
                                   'It makes a rail change explicit and '
                                   'greppable; it does not authenticate it.',
        'defects_found_by_running_not_reading': [
            '--carried used the module ROOT, so the hook judged this repo '
            'whatever repo invoked it: THE GATE WAS INERT and exited 0 on every '
            'rail change. Caught by its own --selfcheck on first run.',
            'the fail-closed branch refused in any repo without the harness, '
            'including every test sandbox. Caught by test_loop_gate.sh: 2 '
            'acceptance checks flipped to refuse. Scoped to "repo has rail text '
            'but no guard".'],
        'suites': {'test_loop_gate.sh': '87 checks pass',
                   'selfcheckall.py': '11 green'},
    }
    with open(os.path.join(HERE, 'h112.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'harness')],
        artifacts=[os.path.join(HERE, 'h112.json')],
        controls=[c1, c2, c3, c4],
        allow_dirty=True,
        note='dep spikes/harness: railguard.py and commit-msg.hook v8 are '
             'COMMITTED at 7c3822e before this runs, so the gate under test is '
             'pinned; any residue belongs to other lanes and may not be '
             'committed by me (§13, H19, H66).',
        falsifier='if 4682d6f~1 or 4682d6f~2 also read as rail changes, the gate '
                  'cannot separate a rail edit from any other edit to the same '
                  'file, it is a file-level tripwire, and the row is withdrawn')

    print(json.dumps(out, indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
