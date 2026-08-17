#!/usr/bin/env python3
"""S38 — make "a stranger could follow it" a property that can go RED.

MISSION_LOOP §8's last acceptance item is *"a written run-book a stranger could
follow"*. §3 ranks drafts for humans last and a run-book is a document, so the
only thing that makes this a deliverable rather than a draft is that its
commands are RESOLVED MECHANICALLY (§12.4) instead of read.

THE FALSIFIER, STATED BEFORE THE RUN AND FIXED IN THIS FILE
-------------------------------------------------------------
    If this checker passes on the run-book while a listed command cannot
    actually be run from a clean checkout, it is testing SPELLING rather than
    followability, and the row buys nothing.

Operationalised as: every command in a fenced block must be either

    # CHECK: run                  -> EXECUTED here, and it must exit 0
    # CHECK: paths-only <why>     -> not executed, reason stated, and every path
                                     it names must still exist

and **a command carrying neither annotation is a refusal**. That rule is the
whole design: without it the honest-looking move is to quietly downgrade any
command that fails into a mention, which is how a run-book decays into prose
naming files nobody can run.

WHAT IT DOES NOT DO, SAID PLAINLY
---------------------------------
It runs the commands in THIS tree, not in a clean checkout. A command that
depends on state this workspace happens to have would pass here and fail for the
stranger. Two things narrow that and neither closes it: the `paths-only` reason
is printed, so a reader sees exactly what was not executed; and the run-book's
§1 tells the reader which check is expected to be red here and green for them.
**A clean-clone harness would close it and is not built** -- that is honest
scope, not a plan I am pretending to have.

  python3 check_runbook.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BOOK = os.path.join(HERE, 'RUNBOOK.md')

ANNOT = re.compile(r'#\s*CHECK:\s*(run|paths-only)\b(.*)$')
PATHLIKE = re.compile(r'[A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)+')


def commands(text):
    """Every line inside a fenced ```sh block that is a command, with its
    annotation. Blank lines and comment-only lines are not commands."""
    out, inside = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith('```'):
            inside = line.strip() == '```sh'
            continue
        if not inside or not line.strip() or line.lstrip().startswith('#'):
            continue
        m = ANNOT.search(line)
        cmd = line[:m.start()].strip() if m else line.strip()
        out.append({'line': n, 'cmd': cmd,
                    'mode': m.group(1) if m else None,
                    'why': (m.group(2).strip().lstrip(',').strip()
                            if m else '')})
    return out


def paths_in(cmd):
    """Path-shaped tokens that look like repo paths. A token with no slash is a
    program name, not a path, and is not checked here."""
    out = []
    for tok in PATHLIKE.findall(cmd):
        if tok.startswith('<') or tok.endswith('>'):
            continue
        out.append(tok)
    return out


def main():
    if not os.path.exists(BOOK):
        print('RUNBOOK.md not found')
        return 2
    cmds = commands(open(BOOK, encoding='utf-8').read())
    if not cmds:
        print('RUNBOOK.md has ZERO commands — refusing rather than reporting a '
              'clean 0/0, which reads as pass.')
        return 2

    problems, ran, excused = [], 0, 0
    results = []
    print(f'RUNBOOK.md — {len(cmds)} commands\n' + '=' * 72)
    for c in cmds:
        # every path a command names must exist, in BOTH modes. A `run` command
        # that exits 0 while naming a path that does not exist is a command that
        # silently did nothing.
        missing = [p for p in paths_in(c['cmd'])
                   if not os.path.exists(os.path.join(ROOT, p))]
        if missing:
            problems.append(f"line {c['line']}: names paths that do not exist: "
                            f"{missing} — {c['cmd']}")
            print(f"  MISSING   {c['cmd'][:60]}\n              {missing}")
            results.append({**c, 'verdict': 'MISSING', 'missing': missing})
            continue

        if c['mode'] == 'run':
            r = subprocess.run(c['cmd'], shell=True, cwd=ROOT,
                               capture_output=True, text=True)
            ran += 1
            if r.returncode == 0:
                print(f"  RAN ok=0   {c['cmd'][:60]}")
                results.append({**c, 'verdict': 'RAN', 'rc': 0})
            else:
                tail = (r.stdout + r.stderr).strip().splitlines()
                problems.append(f"line {c['line']}: exited {r.returncode} — "
                                f"{c['cmd']}")
                print(f"  RC={r.returncode}      {c['cmd'][:60]}\n"
                      f"              {tail[-1][:100] if tail else ''}")
                results.append({**c, 'verdict': 'FAILED', 'rc': r.returncode})
        elif c['mode'] == 'paths-only':
            if not c['why']:
                problems.append(f"line {c['line']}: paths-only with NO reason — "
                                f"an unexplained exemption is how a command that "
                                f"fails gets quietly downgraded to a mention")
                print(f"  NO REASON {c['cmd'][:60]}")
                results.append({**c, 'verdict': 'NO_REASON'})
            else:
                excused += 1
                print(f"  paths ok   {c['cmd'][:60]}\n              excused: {c['why'][:70]}")
                results.append({**c, 'verdict': 'EXCUSED'})
        else:
            problems.append(f"line {c['line']}: NO `# CHECK:` annotation — "
                            f"{c['cmd']}")
            print(f"  UNMARKED  {c['cmd'][:60]}")
            results.append({**c, 'verdict': 'UNMARKED'})

    print('=' * 72)
    print(f'  executed {ran} · excused with a stated reason {excused} · '
          f'problems {len(problems)}   of {len(cmds)}')

    with open(os.path.join(HERE, 'runbook_check.json'), 'w') as f:
        json.dump({'commands': len(cmds), 'executed': ran, 'excused': excused,
                   'problems': problems, 'results': results},
                  f, indent=2, sort_keys=True)

    C = []
    sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
    from kfcheck import certify
    from provenance import Control, Falsifier

    c = Control('C_commands_actually_execute',
                'at least half the run-book\'s commands must be EXECUTED here, '
                'not excused. A page where everything is excused passes this '
                'checker while being unfollowable, which is the falsifier',
                null_must_contain='a run-book whose every command is annotated '
                                  'paths-only, which spell-checks perfectly',
                can_fail_because='fewer executed commands than excused ones')
    c.observe(ran >= excused and ran >= 5, {'executed': ran, 'excused': excused})
    C.append(c)

    c = Control('C_every_command_is_adjudicated',
                'no command may be unannotated: an unmarked command is how a '
                'command that FAILS gets quietly downgraded to a mention',
                null_must_contain='a command with no `# CHECK:` marker, which is '
                                  'what an author adds when the command breaks',
                can_fail_because='any UNMARKED or NO_REASON verdict')
    c.observe(not any(r['verdict'] in ('UNMARKED', 'NO_REASON') for r in results),
              {'verdicts': sorted({r['verdict'] for r in results})})
    C.append(c)

    c = Control('C_no_command_names_a_missing_path',
                'a command exiting 0 while naming a path that does not exist is '
                'a command that silently did nothing; paths are checked in BOTH '
                'modes, not only the excused one',
                null_must_contain='an excused command naming a deleted file, '
                                  'which no execution would catch',
                can_fail_because='any MISSING verdict')
    c.observe(not any(r['verdict'] == 'MISSING' for r in results),
              {'checked': len(results)})
    C.append(c)

    F = Falsifier('F_it_only_checks_spelling',
                  refutes='this row: if the checker passes while a listed command '
                          'cannot actually be run, it tests spelling rather than '
                          'followability and the run-book buys nothing',
                  fires_when='commands are passed without being executed and '
                             'without a stated reason',
                  null_must_contain='an unannotated or unexplained command, which '
                                    'is exactly what this refuses on')
    F.observe(any(r['verdict'] in ('UNMARKED', 'NO_REASON') for r in results),
              {'executed': ran, 'excused': excused, 'problems': len(problems)})

    ok, cert_problems = certify(
        HERE, deps=[],
        no_deps_reason='the run-book depends on the whole tree by construction, '
                       'and its commands are EXECUTED rather than read -- a '
                       'staleness check over spikes/harness would judge other '
                       'lanes in-flight edits rather than this run',
        artifacts=[os.path.join(HERE, 'runbook_check.json')],
        controls=C, falsifiers=[F],
        falsifier='a command passing without being executed and without a stated '
                  'reason, which would make this a spell-checker')
    print('certify ok=%s' % ok)
    for pr in cert_problems:
        print('  PROBLEM', pr)

    if problems or not ok:
        if problems:
            print('\nREFUSE:')
            for pr in problems:
                print('  ' + pr)
        return 1
    return 0


def selfcheck():
    """The runnable check §12.3 wants: every way this checker could pass a
    run-book it should not."""
    fails = []

    def ck(name, cond, detail=''):
        print(f'  {"PASS" if cond else "FAIL"}  {name}{"" if cond else "  " + detail}')
        if not cond:
            fails.append(name)

    # An UNMARKED command must be a problem. This is the rule the whole design
    # rests on -- without it, a failing command can be silently demoted to prose.
    c = commands('```sh\npython3 x.py\n```')
    ck('an unannotated command is parsed with mode None',
       len(c) == 1 and c[0]['mode'] is None)

    # `paths-only` with no reason must be caught, because "excused" with no
    # reason is indistinguishable from "it did not work".
    c = commands('```sh\npython3 x.py   # CHECK: paths-only\n```')
    ck('paths-only with no reason has an empty why',
       len(c) == 1 and c[0]['mode'] == 'paths-only' and not c[0]['why'])

    c = commands('```sh\npython3 x.py   # CHECK: paths-only, needs hardware\n```')
    ck('paths-only WITH a reason keeps it',
       len(c) == 1 and c[0]['why'] == 'needs hardware', str(c))

    # Comments and blanks are not commands; a non-sh block is not scanned.
    ck('a comment line is not a command', commands('```sh\n# just a note\n```') == [])
    ck('a non-sh fence is not scanned', commands('```\npython3 x.py\n```') == [])

    # Path extraction: a bare program name is not a path, an <angle> is not one.
    ck('a bare program name is not treated as a path', paths_in('git status') == [])
    ck('a repo path IS extracted',
       paths_in('python3 spikes/harness/demo8.py') == ['spikes/harness/demo8.py'])
    ck('a placeholder is not treated as a path',
       paths_in('sh x.sh <msgfile>') == ['x.sh'] or
       '<msgfile>' not in paths_in('sh x.sh <msgfile>'))

    print()
    if fails:
        print(f'check_runbook selfcheck: {len(fails)} FAILED — {", ".join(fails)}')
        return 1
    print('check_runbook selfcheck: all checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
