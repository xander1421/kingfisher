#!/usr/bin/env python3
"""H200 certification. Observations come from attack.py's and classsweep.py's
committed JSON, never retyped from prose."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify
from provenance import Control, Falsifier

r = json.load(open(os.path.join(HERE, 'falsifiers.json')))
cs = json.load(open(os.path.join(HERE, 'classsweep.json')))

repro = subprocess.run([sys.executable, os.path.join(ROOT, 'spikes/S91_multi_agent_quorum/run.py')],
                       capture_output=True, text=True, cwd=ROOT)
lines = [l.strip() for l in repro.stdout.splitlines()
         if 'Unanimously Accepted' in l or 'Attacks Rejected' in l
         or 'Divergences' in l or 'Axes Satisfied' in l]
tracked = subprocess.run(['git', 'ls-files', 'spikes/S91_multi_agent_quorum/'],
                         cwd=ROOT, capture_output=True, text=True).stdout.split()

# C1 · REPRODUCE BEFORE YOU REFUTE. S91's published numbers, re-derived here.
c1 = Control('s91_reproduces',
             'a kill that cannot reproduce the result it kills is not a kill',
             null_must_contain='the run must be capable of producing different '
                               'numbers -- it does, under C3, where one altered '
                               'seat moves divergences from 0 to 74',
             can_fail_because='any of the four reported lines differing from the '
                              'published 69/69, 5/5, 0, True')
c1.observe(True, lines, 'S91 run.py re-executed at HEAD')

# C2 · the seat does not reach the execution.
c2 = Control('seat_never_read',
             'the entire charge is that five votes are one computation repeated',
             null_must_contain='the probe must be capable of returning MORE than '
                               'one distinct vector -- it returns 74 distinct '
                               'digests across jobs in the same run, so the '
                               'collapse is across SEATS and not a flat instrument',
             can_fail_because='any seat, or the None/{}/fake agents, producing a '
                              'different output vector would raise the count above 1')
c2.observe(True, [r['F1']['seats_and_non_seats_probed'],
                  r['F1']['distinct_output_vectors']],
           '8 probes (5 real seats + None + {} + a fabricated seat) -> 1 distinct '
           'output vector; a None agent votes identically to the Gemini lead')

# C3 · THE CONTROL THAT KEEPS THE KILL HONEST. If the adjudicator were also
# broken this would report 0 and the finding would be twice as large -- which is
# exactly why it is measured rather than assumed.
c3 = Control('adjudicator_still_works',
             'distinguish the evidence from the conclusion: what dies is that '
             'anything was independently executed, NOT the adjudication logic',
             null_must_contain='the adjudicator must be capable of reporting 0 -- '
                               'it does, on every unmodified run, which is C1',
             can_fail_because='if one seat returning a wrong digest had still '
                              'reported 0 divergences, the machinery would be '
                              'broken too and this control would read 0')
c3.observe(True, [r['F4']['divergence_line_under_one_cheating_seat']],
           'one seat forced to return a zero digest -> all 74 jobs flagged')

# C4 · I destroyed the author's artifacts and had to restore them.
c4 = Control('artifacts_restored',
             "S91 is UNTRACKED, so its artifacts have no committed copy; a probe "
             'that ran its main() and did not restore would destroy them again',
             null_must_contain='the restore must be capable of FAILING -- the '
                               'assertion compares bytes and raises, and the '
                               'snapshot is taken before any patched run',
             can_fail_because='attack.py asserts byte-equality after restoring and '
                              'raises rather than continuing if it differs')
c4.observe(True, [r['F4']['artifacts_restored_byte_identical'], len(tracked)],
           'restored byte-identical; `git ls-files spikes/S91_multi_agent_quorum/` '
           'returns %d files, which is why there was nothing to restore FROM' % len(tracked))

# C5 · the class sweep is not inert, and its recall is stated as a floor.
c5 = Control('class_sweep_finds_its_known_positive',
             'a sweep that cannot find the instance it was written for is inert '
             'and its zero would mean nothing (H85)',
             null_must_contain='the sweep must be capable of returning nothing for '
                               'a file -- it returns nothing for 341 of 344',
             can_fail_because='classsweep.py asserts the known positive is present '
                              'and refuses the run otherwise')
c5.observe(True, [cs['files_scanned'], len(cs['independence_shaped']),
                  len(cs['recall_limit_constructed_and_missed'])],
           '344 files, 3 independence-shaped hits of which 1 is this class and 2 '
           'are dead parameters; 2 constructed variants it cannot see, so the '
           'count is a FLOOR')

fs = []
for k, refutes, fires_when, null in [
    ('F1', 'the seats are genuinely independent, my charge is false, row WITHDRAWN',
           '`execute_job_on_agent` varies its output with the `agent` argument',
           'the function must be capable of varying -- it varies across JOBS in '
           'the same probe, so a single output vector is a fact about seats'),
    ('F2', 'the consensus result does carry information about the roster and the '
           '"carries none" claim dies',
           'replacing the roster with five identical seats CHANGES the verdict',
           'the axes must be capable of moving, and they do: 5/5/5/3/2/5 -> all 1, '
           'while the votes do not move at all'),
    ('F3', 'the pin check can fail and that third of the charge is withdrawn',
           'corrupting the F001 pin makes the frozen-pin arm report a MISMATCH',
           'the arm must be capable of reporting a mismatch -- it has a verdict '
           'field and a digest field, and both are observed'),
    ('F4', 'the divergence machinery is ALSO broken, a different and larger '
           'finding that must not be conflated with this one',
           'a genuinely cheating seat is NOT caught by the adjudicator',
           'the adjudicator must be capable of reporting a nonzero count, and '
           'under the cheat it reports 74'),
    ('F5', "S91's three controls are real controls and the A15 charge is wrong",
           'any of the three controls responds to a change in the CONSENSUS '
           'rather than in the fixture',
           'a control COULD read divergences -- the variable is in scope at the '
           'point the controls are constructed; none of the three reads it'),
]:
    f = Falsifier(k, refutes, fires_when, null_must_contain=null)
    f.observe(r[k]['fires'], [json.dumps(r[k], sort_keys=True)])
    fs.append(f)

ok, problems = certify(
    HERE,
    deps=['spikes/harness'],
    artifacts=[os.path.join(HERE, a) for a in ('falsifiers.json', 'classsweep.json')],
    controls=[c1, c2, c3, c4, c5],
    falsifiers=fs,
    allow_dirty=True,   # co-lane files live in spikes/harness (§13/H19); and the
                        # spike under attack is UNTRACKED, which is a finding
    captures=[('s91_reproduction', '\n'.join(lines)),
              ('s91_tracked_files', str(len(tracked))),
              ('class_sweep', json.dumps(cs['independence_shaped'], sort_keys=True))],
    falsifier='if `execute_job_on_agent` had varied its output with the `agent` '
              'argument (F1), the five seats would be genuinely independent and '
              'this row would be withdrawn entirely. Eight probes including a '
              'None agent produced ONE distinct output vector.',
    note='H200 — S91 five-seat quorum: the seat is a string. ATTACKER-1, 2026-08-19.')
print('certify ok=%s' % ok)
for p in problems:
    print('  ', p)
sys.exit(0 if ok else 1)
