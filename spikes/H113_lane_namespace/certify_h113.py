#!/usr/bin/env python3
"""H113 certification. deps is the SPIKE, not the repo root -- see the H88
correction: deps=[<repo root>] makes the staleness floor a fleet-activity clock
in a five-lane tree, and 2 of 91 recorded dep entries did that.
"""
import hashlib, os, subprocess, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'harness')))
from kfcheck import certify, Control
from provenance import Falsifier

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
os.chdir(HERE)

def save(n, t):
    open(os.path.join(HERE, n), 'w').write(t); return n

# ABSOLUTE PATHS. v1 ran ['bash','./probe.sh'] with cwd=ROOT, where neither
# script exists, so both produced nothing -- and `certify` REFUSED on the empty
# run ("carries no observations") instead of passing it. That refusal is the
# module working: an empty capture read as data is family B, and it is why
# `observe` demands values rather than a boolean.
probe = subprocess.run(['bash', os.path.join(HERE, 'probe.sh')], cwd=ROOT,
                       capture_output=True, text=True)
save('probe.out', probe.stdout + probe.stderr)
fals = subprocess.run(['bash', os.path.join(HERE, 'falsify.sh')], cwd=ROOT,
                      capture_output=True, text=True)
save('falsify.out', fals.stdout + fals.stderr)

# The measurement the row turns on, recomputed here rather than quoted from prose.
prefixes = subprocess.run(
    "grep -oE '^\\| *[A-Z]+[0-9]+' WORK_QUEUE.md | tr -d '| ' | sed 's/[0-9]*$//' | sort -u",
    shell=True, cwd=ROOT, capture_output=True, text=True).stdout.split()
lane = subprocess.run("sed -n 's/^ *LANE-ROWS: *//p' prompts/AGENT-1.md | head -1",
                      shell=True, cwd=ROOT, capture_output=True, text=True).stdout.split()
lines = lambda r: [l.strip() for l in r.stdout.splitlines() if 'PASS' in l or 'FAIL' in l]

c_ns = Control(
    'P_is_not_a_row_namespace',
    "the row turns on P not existing as a row prefix; if it does exist the row is void",
    null_must_contain='the full set of row prefixes WORK_QUEUE.md carries, which must be non-empty',
    can_fail_because='add one `| P1 |` row to WORK_QUEUE.md and P appears in this list')
c_ns.observe('P' not in prefixes, ['prefixes=' + ','.join(prefixes), 'P_present=%s' % ('P' in prefixes)],
             'twelve P0-P3 strings in that file are priority tiers and section points, not row ids')

c_claim = Control(
    'brief_claims_only_real_prefixes',
    'the repaired brief must name only prefixes the queue carries -- that is the whole fix',
    null_must_contain='a LANE-ROWS line, which must be present and non-empty to be judged',
    can_fail_because='add P back to LANE-ROWS, or delete the line, and probe.sh exits 1 (F1/F2)')
c_claim.observe(probe.returncode == 0 and bool(lane) and all(p in prefixes for p in lane),
                ['LANE-ROWS=' + ' '.join(lane), 'probe_rc=%d' % probe.returncode] + lines(probe))

c_mut = Control(
    'check_detects_its_own_removal',
    'a check nobody has broken on purpose is a check nobody has tested',
    null_must_contain='an untouched copy, which must stay green',
    can_fail_because='F3 is the two-sided half: quoting the withdrawn claim in PROSE must stay GREEN, and probe v1 went RED on exactly that')
c_mut.observe(fals.returncode == 0, lines(fals),
              'F1 reinstate P -> red; F2 delete the line -> red; F3 quote it in prose -> green; mutations asserted non-no-op')

f_pre = Falsifier(
    'the brief was right about P',
    "H113's claim that prompts/AGENT-1.md names a row namespace that does not exist",
    'a P row is found in WORK_QUEUE.md, or some file defines P0-P5 as a row-id namespace rather than a priority tier',
    null_must_contain='the complete prefix list extracted from the queue table')
f_pre.observe('P' in prefixes, ['P_in_queue_prefixes=%s' % ('P' in prefixes)],
              'did not fire: D2 says "Last P0 freeze-gate item", HUMAN_NEEDED says "(§5 P1)"')

ok, problems = certify(
    HERE, deps=[HERE], artifacts=['probe.out', 'falsify.out'],
    controls=[c_ns, c_claim, c_mut], falsifiers=[f_pre],
    captures=[('probe.sh', hashlib.sha256(open('probe.sh','rb').read()).hexdigest()[:16]),
              ('prompts/AGENT-1.md', hashlib.sha256(open(os.path.join(ROOT,'prompts/AGENT-1.md'),'rb').read()).hexdigest()[:16])],
    allow_dirty=True,
    note='H113: the lane-definition file assigned this lane a row namespace that exists in no other file.',
    falsifier='if a P row exists in WORK_QUEUE.md, or any file defines P0-P5 as row ids rather than a priority tier, H113 is withdrawn')
print('ok=%s' % ok)
for p in problems: print('  PROBLEM:', p)
sys.exit(0 if ok else 1)
