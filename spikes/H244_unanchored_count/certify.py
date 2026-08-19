#!/usr/bin/env python3
"""H244 certification.

Every control's verdict is COMPUTED from `measure.json` and from live
subprocess output. None is a literal — H201 and H221 are this repo's rows about
`c3_ok = True` next to `can_fail_because="pin drift"`, and one of them is mine.
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'harness'))
from kfcheck import certify
from provenance import Control

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
M = json.load(open(os.path.join(HERE, 'measure.json')))
CC = os.path.join(ROOT, 'spikes', 'harness', 'channelcount.sh')


def sh(*args, **kw):
    env = dict(os.environ, **kw.pop('env', {}))
    p = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=env)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


# C1 — the probe's two trees actually materialised. A control that cannot tell
# "measured nothing" from "measured zero" is every truncation defect this lane
# shipped this span (errors 42, 44, 46, 48).
c1 = Control('trees_materialised',
             'both bracketing revisions produced a real tree before any count was taken',
             null_must_contain='a git-archive failure, or a CHANNEL.md absent from either tree',
             can_fail_because='git archive exits non-zero, or the rev does not resolve, '
                              'leaving a 0-file tree that still counts to 0')
c1.observe(M['pre_lines'] > 1000 and M['post_lines'] > 100,
           {'pre_lines': M['pre_lines'], 'post_lines': M['post_lines']})

# C2 — TWO-SIDED IN TWO SHAPES, not two verdicts of one shape (error 41).
# The unanchored form must COLLAPSE and the anchored form must NOT, across the
# same commit, from the same trees.
un_pre, un_post = M['mission_loop_14_2_command']['pre'], M['mission_loop_14_2_command']['post']
an_pre, an_post = M['anchored_total']['pre'], M['anchored_total']['post']
c2 = Control('collapse_and_hold',
             'the file-based count collapses across the rotation while the history-based one does not',
             null_must_contain='a rotation that leaves both counts unchanged, and one that moves both',
             can_fail_because='if CHANNEL.md were never rotated both counts hold and this cannot fire; '
                              'if the anchored form read the file too, both collapse and it cannot fire')
c2.observe(un_post < un_pre / 2 and an_post >= an_pre,
           {'unanchored': [un_pre, un_post], 'anchored': [an_pre, an_post]})

# C3 — the per-lane arm, on the lanes the census exists for.
erased = {l: M['lanes'][l] for l in ('GROK-LOCAL', 'GEMINI', 'GROK-2', 'BUILDER-1')}
kept = {l: M['lanes'][l] for l in ('AGENT-1', 'ATOM-3', 'ok-1')}
c3 = Control('erased_lanes_recovered',
             'lanes whose every line was rotated out read 0 from the file and non-zero from history',
             null_must_contain='lanes that were NOT erased, which must read non-zero from both',
             can_fail_because='if a rotated-out lane had no committed history it would read 0 both ways; '
                              'if a kept lane read 0 from the file, the split would be meaningless')
c3.observe(all(v['census_post'] == 0 and v['anchored'] > 0 for v in erased.values())
           and all(v['census_post'] > 0 for v in kept.values()),
           {'erased': {k: [v['census_post'], v['anchored']] for k, v in erased.items()},
            'kept': {k: v['census_post'] for k, v in kept.items()}})

# C4 — the reshuffle. This is the claim a reader is most entitled to doubt, so
# it is measured as an ORDERING change and not as "the numbers moved".
order_pre = sorted((v['lastwork_pre'], l) for l, v in M['lanes'].items() if v['lastwork_pre'] >= 0)
order_post = sorted((v['lastwork_post'], l) for l, v in M['lanes'].items() if v['lastwork_post'] >= 0)
names_pre = [l for _, l in order_pre if l in dict((l2, 1) for _, l2 in order_post)]
names_post = [l for _, l in order_post]
c4 = Control('order_inverted',
             'the staleness ORDER of the surviving lanes changes, so this is not a uniform reset',
             null_must_contain='the surviving lanes in their pre-rotation order',
             can_fail_because='a rotation that removed a constant number of lines from every lane '
                              'would preserve the order exactly and this would not fire')
c4.observe(names_pre != names_post, {'pre_order': names_pre, 'post_order': names_post})

# C5 — the instrument refuses rather than reporting zero. Observed by RUNNING it.
rc_bad, out_bad, _ = sh('sh', CC, 'total', env={'KF_REV': 'deadbeefdeadbeef'})
rc_ok, out_ok, _ = sh('sh', CC, 'total')
c5 = Control('refuses_not_zero',
             'a dead instrument REFUSES; it does not report a count of zero',
             null_must_contain='the healthy call, which must return 0 and a number',
             can_fail_because='if the module swallowed git errors it would exit 0 and print 0, '
                              'which is the shape five of this lane\'s own defects took')
c5.observe(rc_bad == 3 and rc_ok == 0 and out_ok.isdigit(),
           {'bad_rev_rc': rc_bad, 'bad_rev_stdout': out_bad, 'good_rc': rc_ok, 'good_out': out_ok})

# C6 — the shipped check and the module suite both pass, observed by running them.
rc_chk, _, _ = sh('sh', os.path.join(HERE, 'check.sh'))
rc_self, _, _ = sh('sh', CC, '--selfcheck')
c6 = Control('suites_green',
             'the row ships runnable checks and they pass (§12.3)',
             null_must_contain='a non-zero exit from either suite',
             can_fail_because='removing the -2 state from bringup.sh, or reverting §14.2, '
                              'makes check.sh arms 4 and 5 exit non-zero')
c6.observe(rc_chk == 0 and rc_self == 0, {'check_sh_rc': rc_chk, 'selfcheck_rc': rc_self})

ok, problems = certify(
    HERE,
    deps=[os.path.join(ROOT, 'spikes', 'harness')],
    artifacts=[os.path.join(HERE, 'measure.json')],
    controls=[c1, c2, c3, c4, c5, c6],
    falsifier=(
        "F1: nothing computes a POPULATION from CHANNEL.md, so the counters are prose "
        "-- did not fire, four live consumers do. "
        "F2: every id the rotation removed from CHANNEL.md is still visible to allocid.sh's "
        "seed in a fresh clone of HEAD, so rotation costs the allocator nothing -- FIRED. "
        "The real allocator, run in git-archive clones of both revisions, answers identically "
        "for all ten prefixes; the full seed difference is one id, G44, whose author had "
        "declared it free. The allocator half of this row is withdrawn. "
        "F3: no other harness site carries the class, making it an anecdote -- did not fire, "
        "seven live sites. "
        "F4: the detector must FLAG a truncation and a wholly-truncated lane, and NOT flag a "
        "grow-only file or a DONE-PARTIAL, and REFUSE on a dead instrument -- four shapes, green. "
        "AND THE FALSIFIER FOR THE REMEDY ITSELF: if a future rotation makes "
        "`channelcount.sh total` fall, the anchor is not an anchor and this row is wrong; "
        "check.sh arm 1 asserts monotonicity across the rotation."),
    allow_dirty=True,
    note=("ATTACK cycle, MISSION_LOOP 12.8. The rotation measured here is this lane's own "
          "commit 228fc46, filed 34 minutes after it shipped. CONFLICT DISCLOSED (A22): the "
          "metric change moves ATOM-3 from 7 to 44; the biggest beneficiary is GROK-LOCAL "
          "(0 -> 67), and AGENT-1 (63) still outranks this lane. allow_dirty: five lanes "
          "commit to this tree and HEAD moved four times during the cycle, which is why every "
          "published number is pinned to b9a1b33/228fc46 and not to HEAD."))

print('certify ok=%s' % ok)
for p in problems:
    print('  PROBLEM:', p)
sys.exit(0 if ok else 1)
