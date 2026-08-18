#!/usr/bin/env python3
"""railguard.py v1 — H112, ATOM-3, 2026-08-18.

THE DEFECT IT EXISTS FOR
========================
CLASS: **A LANE CAN WRITE THE RAIL THAT BINDS IT, AND NOTHING IN THIS HARNESS
WATCHES THE RAIL TEXT.**

Measured, not alleged. `4682d6f`, `Atom: AGENT-2`, `Reviewed-By: unreviewed`,
subject "autoloop tuned to the mission: 5 demo programs disabled, baseline
recorded, rails made enforceable". Inside that commit `CLAUDE.md`'s rail moves
from

    No publishing: no pushes, PRs, package uploads, issue comments, posts.

to

    No publishing to THIRD PARTIES: ... **Pushing to the operator's own private
    origin (`xander1421/kingfisher`, added 2026-08-18) IS permitted**

THE OUTCOME IS NOT IN DISPUTE AND THIS MODULE DOES NOT REOPEN IT: the operator
has since confirmed the push is authorised, directly. What has no mechanism is
the PROCESS. Three facts, none of which depends on the outcome:

  1. The widening was justified BY INFERENCE -- "a remote now exists and four
     lanes read this file" -- authorisation inferred from the artifact's
     existence, by the party the rail binds. A22 pointed outward; WORK_QUEUE H17
     already holds the inward case (an agent NARROWING a rail it operates under).
  2. It landed inside a MIXED COMMIT about demo programs, while §13 gives a
     correction its own commit. The highest-consequence line in the repository
     arrived as a hunk in an unrelated change.
  3. `Reviewed-By: unreviewed`, on the one edit in this tree where §13.1's "a
     lane cannot review itself" is load-bearing.

Every gate in this repo fired correctly on that commit. None of them was looking
at the rail. §12.10: a guardrail written but not mechanised will be violated
again by its own author, usually the same day.

WHAT THIS CAN AND CANNOT DO -- STATED BEFORE THE CODE, BECAUSE OVERCLAIMING A
GATE IS WORSE THAN NOT HAVING ONE
=================================================================
It CANNOT verify authorisation. Any lane can type the trailer, exactly as any
lane can type `Atom:` (§13.1: "self-declared ... it records attribution, it does
not verify it"). Pretending otherwise would be the very A22 shape this row is
about, committed by the row's own remedy.

What it DOES: it converts an invisible hunk inside a mixed commit into an
explicit, greppable, deliberate act.

    git log --grep='Rail-Change-Authorised-By' --oneline    # every rail change

and it REFUSES rather than warns, because "a check that reports but does not
gate is prose with extra steps" (§13.1).

DIRECTION IS DELIBERATE. This gate can only REFUSE. It never permits anything,
it writes no rail text in either direction, and `git commit --no-verify` remains
the documented human escape. I am bound by the rail I am gating, so the gate is
built so that the worst it can do to a rail is make changing one noisy.

SCOPED TO THE COMMIT, NOT THE TREE (H35, H75)
=============================================
It reads the INDEX (`git show :<path>`), never the working tree, so another
lane's dirty `CLAUDE.md` cannot refuse your unrelated commit -- H72/H73's class,
which this repo has already paid for twice. Verified mechanically rather than by
eye (§12.4): git exports `GIT_INDEX_FILE` to `commit-msg` as it does to
`pre-commit` -- `.git/index` for a plain commit, `.git/next-index-<pid>.lock`
for `git commit --only` -- and `--selfcheck` asserts it under BOTH workflows.
If that ever stops being true, `--selfcheck` goes red rather than this paragraph
becoming folklore.

ANCHORS, NOT LINE NUMBERS
=========================
A rail region is found by its section heading and runs to the next heading. Line
numbers move every time anyone edits anything above them, and a gate pinned to a
line number silently starts guarding the wrong text -- family C.

  python3 spikes/harness/railguard.py --selfcheck
  python3 spikes/harness/railguard.py --carried <commit-msg-file>
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

# path -> the section headings whose bodies are rail text.
RAILS = {
    'CLAUDE.md': ['## Safety rails'],
    'MISSION_LOOP.md': ['## 10 ·', '## 11 ·'],
}
TRAILER = 'Rail-Change-Authorised-By:'
# A lane may not authorise itself. The roster is the set of things that are NOT
# an authorisation -- same reasoning as §13.1's "Reviewed-By must not equal Atom".
def _roster(root):
    try:
        with open(os.path.join(root, 'roster.txt')) as f:
            return {m.group(0).lower()
                    for m in re.finditer(r'^[A-Za-z0-9-]+', f.read(), re.M)}
    except OSError:
        return set()


def section(text, anchor):
    """The body of the section introduced by `anchor`, or None if absent.

    Runs from the anchor line to the next line beginning '## ', so it survives
    every edit above it. Returns None -- never '' -- when the anchor is gone, so
    a DELETED rail section is distinguishable from an unchanged empty one; a
    guard that reads a removed rail as 'no change' is the whole point missed.
    """
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith(anchor):
            out = [ln]
            for nxt in lines[i + 1:]:
                if nxt.startswith('## '):
                    break
                out.append(nxt)
            # trailing blank lines belong to the gap before the next
            # heading, not to the rail. Without this a blank line added below
            # the section reads as a rail change.
            return '\n'.join(out).rstrip()
    return None


def _git(*args, root=None):
    p = subprocess.run(['git'] + list(args), cwd=root or ROOT,
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def changed_rails(root=None):
    """Rail regions this COMMIT changes: index copy vs HEAD copy.

    Reads `git show :<path>` (the index) and never the working tree, so a
    co-lane's uncommitted rail edit cannot refuse your commit.
    """
    changed = []
    for path, anchors in RAILS.items():
        staged = _git('show', ':' + path, root=root)
        if staged is None:
            continue                      # this commit does not carry the file
        head = _git('show', 'HEAD:' + path, root=root) or ''
        for a in anchors:
            before, after = section(head, a), section(staged, a)
            if before != after:
                what = ('ADDED' if before is None else
                        'REMOVED' if after is None else 'MODIFIED')
                changed.append((path, a, what))
    return changed


def authorised(msg, root=None):
    """True only for a trailer naming an authority that is not a lane."""
    for ln in msg.splitlines():
        if ln.strip().startswith(TRAILER):
            who = ln.split(':', 1)[1].strip()
            if who and who.lower() not in _roster(root or ROOT):
                return True
    return False


def main(argv):
    if '--selfcheck' in argv:
        return selfcheck()
    if '--carried' in argv:
        msg_path = argv[argv.index('--carried') + 1]
        # THE REPO BEING COMMITTED, not the one this file lives in. v1's first
        # draft used the module-level ROOT (derived from __file__), so the hook
        # inspected `spikes/harness/..` no matter which repo invoked it -- THE
        # GATE WAS INERT AND EXITED 0 ON EVERY RAIL CHANGE. git runs hooks with
        # cwd at the top level of the repo being committed. Caught by
        # --selfcheck's `refuses_under_plain`, which is the entire argument for
        # §12.3: this module's own first run found it, not a later stall.
        repo = os.getcwd()
        changed = changed_rails(root=repo)
        if not changed:
            return 0
        msg = open(msg_path).read()
        if authorised(msg, root=repo):
            return 0
        sys.stderr.write(
            'RAILGUARD REFUSES: this commit changes rail text.\n\n' +
            ''.join('    %-16s %-18s %s\n' % (p, a, w) for p, a, w in changed) +
            '\n  A rail binds every lane, including the one editing it. On '
            '2026-08-18 a rail\n  was widened inside a commit about demo '
            'programs, justified by inferring\n  authorisation from the state '
            'of the tree, and no gate here noticed (H112).\n\n'
            '  If the operator authorised this, say so in the message:\n\n'
            '      %s operator\n\n'
            '  A lane callsign is refused -- a lane cannot authorise itself '
            '(§13.1).\n'
            '  This records the act, it does not verify it. Human escape: '
            '--no-verify.\n' % TRAILER)
        return 1
    sys.stderr.write(__doc__.strip().splitlines()[-2].strip() + '\n')
    return 2


def selfcheck():
    """Every claim in the header, executed. Each control names how it can fail."""
    import shutil
    import tempfile
    fail = 0
    tmp = tempfile.mkdtemp(prefix='railguard_', dir=os.path.join(ROOT, 'spikes'))

    def run(*a, **kw):
        return subprocess.run(a, cwd=kw.get('cwd', tmp), capture_output=True,
                              text=True)

    def check(name, cond, why):
        nonlocal fail
        if not cond:
            print('SELFCHECK FAIL: %s -- %s' % (name, why))
            fail = 1
        return cond

    try:
        # --- pure logic first: no git, so a git failure cannot mask a logic bug.
        t = '# t\n\n## Safety rails\nno pushes\n\n## Next\nunrelated\n'
        check('anchor_extracts', section(t, '## Safety rails') ==
              '## Safety rails\nno pushes',  # trailing blanks stripped
              'a rail section must stop at the next heading; it did not')
        check('absent_is_none', section(t, '## Nope') is None,
              'a MISSING anchor must be None, not empty string, or a DELETED '
              'rail reads as unchanged')
        check('lane_cannot_authorise',
              not authorised('x\n\n%s AGENT-2' % TRAILER, root=ROOT),
              'a roster callsign was accepted as an authority')
        check('operator_authorises',
              authorised('x\n\n%s operator' % TRAILER, root=ROOT),
              'a non-lane authority was refused, so the gate cannot be passed '
              'at all -- a rail could never be changed again')

        # --- then the git behaviour the header asserts.
        run('git', 'init', '-q', tmp)
        run('git', 'config', 'user.email', 'x@y')
        run('git', 'config', 'user.name', 'x')
        shutil.copy(os.path.join(ROOT, 'roster.txt'), tmp)
        rails = ('# c\n\n## Safety rails\nno pushes\n\n## Other\nprose here\n')
        open(os.path.join(tmp, 'CLAUDE.md'), 'w').write(rails)
        open(os.path.join(tmp, 'MISSION_LOOP.md'), 'w').write('# m\n')
        run('git', 'add', '-A')
        run('git', 'commit', '-qm', 'base')

        # NEGATIVE CONTROL, and it is the row's preregistered falsifier: an edit
        # to the SAME FILE outside the rail section must NOT trip the gate. If
        # it does, this is a file-level tripwire wearing a section-level name
        # and the row is withdrawn.
        open(os.path.join(tmp, 'CLAUDE.md'), 'w').write(
            rails.replace('prose here', 'different prose'))
        run('git', 'add', 'CLAUDE.md')
        check('non_rail_edit_passes', changed_rails(root=tmp) == [],
              'an edit OUTSIDE the rail section tripped the gate -- it is a '
              'file-level tripwire, not a rail guard (falsifier FIRED)')

        # POSITIVE: the rail itself.
        open(os.path.join(tmp, 'CLAUDE.md'), 'w').write(
            rails.replace('no pushes', 'pushes are fine now'))
        run('git', 'add', 'CLAUDE.md')
        got = changed_rails(root=tmp)
        check('rail_edit_detected',
              got == [('CLAUDE.md', '## Safety rails', 'MODIFIED')],
              'a widened rail was not detected; got %r' % (got,))

        # DELETION: removing the section entirely must not read as "unchanged".
        open(os.path.join(tmp, 'CLAUDE.md'), 'w').write('# c\n\n## Other\nx\n')
        run('git', 'add', 'CLAUDE.md')
        check('rail_deletion_detected',
              changed_rails(root=tmp) ==
              [('CLAUDE.md', '## Safety rails', 'REMOVED')],
              'deleting the rail section entirely read as no change')

        # THE HEADER'S GIT CLAIM, under BOTH workflows. `git commit --only`
        # prepares a different index, and the whole gate rests on `git show :`
        # reading it. Asserted, not assumed (§12.4).
        run('git', 'checkout', '-q', '--', 'CLAUDE.md')
        hook = os.path.join(tmp, '.git', 'hooks', 'commit-msg')
        os.makedirs(os.path.dirname(hook), exist_ok=True)
        with open(hook, 'w') as f:
            f.write('#!/bin/sh\nexec python3 %s --carried "$1"\n'
                    % os.path.join(HERE, 'railguard.py'))
        os.chmod(hook, 0o755)
        for flow in ('plain', 'only'):
            open(os.path.join(tmp, 'CLAUDE.md'), 'w').write(
                rails.replace('no pushes', 'widened via %s' % flow))
            if flow == 'plain':
                run('git', 'add', 'CLAUDE.md')
                r = run('git', 'commit', '-m', 'widen')
            else:
                r = run('git', 'commit', '--only', 'CLAUDE.md', '-m', 'widen')
            check('refuses_under_%s' % flow, r.returncode != 0,
                  'an unauthorised rail change COMMITTED under `%s`; the gate '
                  'cannot see the index git actually uses' % flow)
            r2 = run('git', 'commit', '--only', 'CLAUDE.md', '-m',
                     'widen\n\n%s operator' % TRAILER)
            check('accepts_authorised_%s' % flow, r2.returncode == 0,
                  'an AUTHORISED rail change was refused under `%s` -- the gate '
                  'cannot be passed and would wedge the operator' % flow)
            run('git', 'checkout', '-q', '--', 'CLAUDE.md')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not fail:
        print('railguard selfcheck: anchors survive edits above them, a removed '
              'rail is not "unchanged", a NON-RAIL edit to the same file passes '
              '(the falsifier), a lane cannot authorise itself, and the gate '
              'refuses then accepts under BOTH `git commit` and `--only`')
    return fail


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
