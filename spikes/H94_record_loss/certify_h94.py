#!/usr/bin/env python3
"""H94 — the three claims, each as a control that can fail, then certify().

The numbers this row publishes are: `10ed3f2` refuses, the history replay has no
backlog, and the rule is quiet on the in-place rewrite that ATOM-3 measured a
line-level rule cannot be. Each is run here rather than asserted, and each states
what observation would have made it come out the other way.

  python3 spikes/H94_record_loss/certify_h94.py     # exit 0 = certified
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))

from kfcheck import certify                     # noqa: E402
from provenance import Control                  # noqa: E402
import recordloss as R                          # noqa: E402

LOSS_COMMIT = '10ed3f2'      # the defect this module exists for
INPLACE_COMMIT = 'a477a74'   # a CLAIM line rewritten in place AND grown


def git(*a):
    return subprocess.run(['git'] + list(a), capture_output=True, text=True,
                          cwd=ROOT).stdout


# --- F1. The check must see the defect it was built for, or the row is withdrawn.
c1 = Control('f1_sees_its_own_defect',
             'replaying 10ed3f2 must refuse and name the four lost cycles',
             null_must_contain='the four `## Cycle` keys deleted by that commit',
             can_fail_because='recordloss returns 0 on 10ed3f2 — a check that '
                              'cannot see the commit it was written for')
lost = R.replay(LOSS_COMMIT).get('HANDOFF.ok-1.md', set())
c1.observe(len(lost) == 4, sorted(lost), f'{LOSS_COMMIT}: {len(lost)} keys lost')

# --- F2. H14: a checker with a standing backlog is one everyone learns to bypass.
c2 = Control('f2_no_backlog',
             'every committed revision of every covered document, replayed',
             null_must_contain='a refusal on a revision that loses no record',
             can_fail_because='a third refusal, or either of the two failing to '
                              'name a record that a reader agrees left the file')
revs = refusals = 0
detail = []
for path in sorted(p for p in git('ls-files').split('\n') if p and R.covered(p)):
    rl = git('rev-list', '--reverse', 'HEAD', '--', path).split()
    revs += max(0, len(rl) - 1)
    for rev in rl[1:]:
        if R.replay(rev).get(path):
            refusals += 1
            detail.append(f'{rev[:7]} {path}')
c2.observe(refusals == 2, detail, f'{revs} revisions judged, {refusals} refusals')

# --- F3. The prior art, resolved rather than recalled: ATOM-3's d278d01 measured
# that a LINE-level deletion rule fires falsely here. Both revisions where git
# renders a CLAIM/DONE line as deleted are checked; the key rule must refuse the
# one that lost the record and stay quiet on the one that rewrote it in place.
c3 = Control('f3_inplace_rewrite_quiet',
             'a CLAIM line rewritten in place and grown must not refuse',
             null_must_contain='a refusal on a476/a477-style in-place growth',
             can_fail_because='recordloss refuses a477a74, which would make this '
                              'rule the false-positive one ATOM-3 already measured')
line_level = ['48c9059', 'a477a74']    # git renders a removed CLAIM/DONE in both
quiet = [r for r in line_level if not R.replay(r)]
c3.observe(quiet == ['a477a74'], quiet,
           'line-level rule would fire on 2 of 137 CHANNEL revisions; key rule on 1')

ok, problems = certify(
    HERE,
    deps=[], no_deps_reason='no external repo: the subject is this repo\'s own history',
    artifacts=[os.path.join(ROOT, 'spikes/harness/recordloss.py'),
               os.path.join(HERE, 'falsify.py'),
               os.path.join(HERE, 'F1.out'),
               os.path.join(HERE, 'F2.out'),
               os.path.join(HERE, 'checks.out')],
    controls=[c1, c2, c3],
    allow_dirty=True,
    note='H94 — a completed record must not leave an append-mostly document. '
         'Tree is dirty with four other lanes\' in-flight work; the artifacts '
         'above are hashed, which is what pins this run.',
    falsifier='If replaying 10ed3f2 did not refuse, the check cannot see the '
              'defect it was built for and the row is withdrawn. If the history '
              'replay refused on a revision that lost no record, the rule is a '
              'checker everyone learns to ignore (H14) and it narrows or dies.')

for p in problems:
    print('  PROBLEM', p)
print('certify:', 'OK' if ok else 'REFUSED')
sys.exit(0 if ok else 1)
