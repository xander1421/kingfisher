#!/usr/bin/env python3
"""H257 certification. Every control's verdict is COMPUTED, never a literal."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'harness'))
from kfcheck import certify
from provenance import Control

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
S = json.load(open(os.path.join(HERE, 'sweep.json')))


def sh(*a):
    p = subprocess.run(a, capture_output=True, text=True, cwd=ROOT)
    return p.returncode, p.stdout, p.stderr


def blob(rev, path):
    rc, out, _ = sh('git', 'show', f'{rev}:{path}')
    return out if rc == 0 else ''


# C1 — each hit is verified against the PARENT BLOB, not from the diff. A false
# accusation is the failure H105 measured at 8% and it is worse than silence.
checks = {}
for c, needle in (('bb2c229', 'PREDATES THE CURRENT FILE'), ('d066c4b', 'v2 (H88, AGENT-1')):
    checks[c] = (blob(c + '^', 'bringup.sh').count(needle), blob(c, 'bringup.sh').count(needle))
c1 = Control('introduced_not_preexisting',
             'each reported capture is absent from the parent blob and present in the commit',
             null_must_contain='a block that already existed in the parent, which must NOT be reported',
             can_fail_because='if a hit\'s block predated its commit the pair reads (1,1) and this fails; '
                              'that is the false-accusation direction and it is the one that matters')
c1.observe(all(p == 0 and n >= 1 for p, n in checks.values()), checks)

# C2 — the repair is MEASURED beside the form it replaces (the C4 habit).
v0, v1 = S['detector_v0_hits'], S['detector_v1_count']
c2 = Control('repair_measured',
             'the tightened pattern drops the prose false positive the loose one matched',
             null_must_contain='the v0 count, which must be strictly larger',
             can_fail_because='if v0 and v1 agreed, the tightening changed nothing and the '
                              '33% false-positive claim would be unevidenced')
c2.observe(v0 > v1 and v1 == len(S['detector_v1_hits']), {'v0': v0, 'v1': v1})

# C3 — the severity DOWNGRADE survives into the artifact. F3 fired; a control
# that only guarded the finding and not its limit would let the limit be dropped.
c3 = Control('severity_downgrade_recorded',
             'the artifact records 1 functional and 1 attributional, not 2 unqualified captures',
             null_must_contain='the total, which is 2 and must not be reported alone',
             can_fail_because='editing sweep.json to say functional_captures=2 makes this fail, '
                              'which is exactly the overstatement F3 guards against')
c3.observe(S['functional_captures'] == 1 and S['attributional_only_captures'] == 1
           and S['functional_captures'] + S['attributional_only_captures'] == len(S['detector_v1_hits']),
           {'functional': S['functional_captures'], 'attributional': S['attributional_only_captures'],
            'total_hits': len(S['detector_v1_hits'])})

# C4 — compliance is not punished. Observed by running the suite, not asserted.
rc_self, out_self, _ = sh('sh', os.path.join(ROOT, 'spikes', 'harness', 'codecarry.sh'), '--selfcheck')
rc_chk, _, _ = sh('sh', os.path.join(HERE, 'check.sh'))
c4 = Control('suites_green',
             'the shipped checks run and pass, including the arm that a correctly declared '
             'Carries: is NOT reported',
             null_must_contain='a non-zero exit from either suite',
             can_fail_because='loosening the pattern back to v0 makes the fixture\'s declared-Carries '
                              'arm report a hit, and that arm fails')
c4.observe(rc_self == 0 and rc_chk == 0 and 'correctly declared' in out_self,
           {'selfcheck_rc': rc_self, 'check_rc': rc_chk,
            'compliance_arm_present': 'correctly declared' in out_self})

ok, problems = certify(
    HERE,
    deps=[os.path.join(ROOT, 'spikes', 'harness')],
    artifacts=[os.path.join(HERE, 'sweep.json')],
    controls=[c1, c2, c3, c4],
    falsifier=(
        "F1: bb2c229 is the only instance, making this an anecdote -- did not fire, d066c4b is a "
        "second, verified against its parent blob. "
        "F2: foreign-named blocks are routinely ADDED by the file's owner re-citing history, so hits "
        "are mostly citations -- did NOT fire as stated (a v6 author adds only v6; older blocks survive "
        "as diff context, selfcheck arm 4). A DIFFERENT false-positive mechanism did appear and is "
        "recorded separately rather than merged into F2: the v0 pattern matched PROSE ('FIRED on v0 "
        "(AGENT-2 named as carried by AGENT-2-INT') at 1 in 3, 33%; the anchored pattern is 2 of 2. "
        "F3: every instance is attributional only, so the existing scope is adequate -- FIRED, PARTIALLY, "
        "and it downgrades this row: 1 of the 2 captures is functional (bb2c229, mine), the other is "
        "comment-only. The quotable rate is 2 captures in 400 commits, 1 functional. "
        "F4: four shapes -- flag an undeclared foreign block, do NOT flag a correctly declared one, do "
        "NOT flag a lane's own block, do NOT flag one surviving as context. Green. "
        "FALSIFIER FOR THIS ROW ITSELF: a hit whose named lane did not author the block is a false "
        "accusation (H105's 8%) and makes the count unquotable; check.sh arm 1 re-verifies both hits "
        "against their parent blobs."),
    allow_dirty=True,
    note=("ATTACK cycle, MISSION_LOOP 12.8. REPORT-ONLY and wired into nothing. Its home is "
          "carriescheck.py's POSITIONAL, which is ATTACKER-1's live module (H180) -- editing a "
          "co-lane's harness file to add a check about capturing co-lanes' harness files is the "
          "defect wearing the repair's clothes, so the merge is its owner's call. The row's opening "
          "instance injured this lane, which is why F3 was preregistered to downgrade it and is "
          "reported as having done so."))

print('certify ok=%s' % ok)
for p in problems:
    print('  PROBLEM:', p)
sys.exit(0 if ok else 1)
