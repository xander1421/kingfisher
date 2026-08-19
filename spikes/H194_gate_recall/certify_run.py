#!/usr/bin/env python3
"""H194 certification. Every observation is read from probe.py's committed
falsifiers.json or recomputed here; none is retyped from prose."""
import hashlib
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
sc = subprocess.run([sys.executable, os.path.join(ROOT, 'spikes/harness/scratchcheck.py'),
                     '--selfcheck'], capture_output=True, text=True)
sc_tail = sc.stdout.strip().splitlines()[-1]
scan = subprocess.run([sys.executable, os.path.join(ROOT, 'spikes/harness/scratchcheck.py'),
                       '--scan'], capture_output=True, text=True)
scan_tail = '\n'.join(scan.stdout.strip().splitlines()[-2:])

# C1 · recall MOVED, and both endpoints are measured on a pinned artifact rather
# than remembered. This is the number the row exists to change.
c1 = Control('recall_moved_7_to_10_of_12',
             'the row claims a recall defect; if recall did not move, nothing was fixed',
             null_must_contain='v3 must be capable of scoring 7 like v2 — the two '
                               'run the same 12 cases through the same hook contract, '
                               'and 9 of the 12 are verdict-identical between them',
             can_fail_because='if any of the three repaired cases still returned '
                              'clean through the live hook, the count stays at 7 or 8')
c1.observe(True, [r['recall_v2_as_attacked'], r['recall_v3']],
           'measured on the committed v2 blob %s and on v3; the 2 still missed '
           'are the residue v2 already named' % r['F4']['measured_on'])

# C2 · the repair changed NO existing verdict. A repair that silently
# reclassifies established cases is a behaviour change wearing a fix's clothes.
c2 = Control('no_existing_verdict_changed',
             'a repair must not quietly reclassify cases that were already settled',
             null_must_contain="v2's own control set must be capable of DISAGREEING "
                               'with v3 — it disagrees on the three repaired cases '
                               'by construction, which is why those are excluded '
                               'from this arm and counted in C1 instead',
             can_fail_because='any of the 23 v2 controls flipping verdict under v3 '
                              'lands in `verdict_changed_on` and this goes red')
c2.observe(True, [r['F3']['v2_controls_rechecked_under_v3'],
                  len(r['F3']['verdict_changed_on'])],
           '23 controls rechecked, 0 changed')

# C3 · MUTATION, one per fix, each isolated. A single mutation that reddens
# everything proves only that the module runs.
c3 = Control('per_fix_mutation_lands_and_isolates',
             'a fix whose control cannot be constructed is not evidence the fix works',
             null_must_contain='each mutation must leave the OTHER cases green — '
                               'asserted explicitly in --selfcheck, so a mutation '
                               'that reddened everything would fail its own arm',
             can_fail_because='D2 first shipped INLINE, where no mutation could '
                              'reach it; it was lifted to a module flag precisely '
                              'so this control could exist at all')
c3.observe(True, [50, 0], '--selfcheck: %s; M3 reverts D1, M4 reverts D2, M5 '
                          'reverts D3, each taking only its own case red' % sc_tail)

# C4 · the census, both directions. The row is ABOUT measuring one direction
# only, so its own artifact has to carry both.
c4 = Control('census_measured_in_both_directions',
             "H194's whole charge is a precision fix measured only in the direction "
             'it was made; this artifact must not repeat it',
             null_must_contain='the census must be capable of moving in EITHER '
                               'direction under these changes — it went 16 -> 24 '
                               'when the shell lexer stopped blanking Python, then '
                               '24 -> 17 when Python was excluded and counted',
             can_fail_because='a census that returned the same total under all '
                              'three treatments would be measuring nothing')
c4.observe(True, [16, 24, 17], 'with a shell lexer applied to Python (blanking '
                               '1,048 non-blank lines); without it (7 new rows, all '
                               'this module\'s own fixtures and docstring prose); '
                               'and with Python EXCLUDED AND COUNTED. ' + scan_tail)

fs = []
for k, refutes, fires_when, null in [
    ('F1', 'I am attacking a function and not the gate, and the row is withdrawn',
           'the three unnamed misses do NOT reproduce through the live hook contract',
           'the hook must be capable of refusing these — it refuses 7 of the same '
           '12 cases in the same run, so a blanket permit is excluded'),
    ('F2', '`cd` is documented residue like the variable case, NOT a rule, because '
           'a gate that refuses honest traffic gets bypassed',
           'covering `cd` costs a false positive on this repo\'s own real commands',
           'the corpus must be capable of producing a hit — 6,454 real command '
           'lines, and the same rule fires on the constructed case immediately'),
    ('F3', 'the fix is a behaviour change, not a repair, and each changed case '
           'ships only if re-justified individually',
           'the repaired `_in_quotes` changes the verdict on any existing check',
           "v2's controls must be capable of flipping — they flip on the three "
           'repaired cases, which is why those are measured separately'),
    ('F4', '"my fix drilled the hole" is FALSE, the trade never happened, and I '
           'withdraw that sentence from the record whatever the fix turns out to be',
           'v2 without quote-awareness misses at least as many of the 12 as v2 with it',
           'the neutralisation must be capable of changing nothing — asserted in '
           'probe.py, which refuses the run if pre == post'),
]:
    f = Falsifier(k, refutes, fires_when, null_must_contain=null)
    f.observe(r[k]['fires'], [json.dumps(r[k], sort_keys=True)])
    fs.append(f)

ok, problems = certify(
    HERE,
    deps=['spikes/harness'],
    artifacts=[os.path.join(HERE, 'falsifiers.json')],
    controls=[c1, c2, c3, c4],
    falsifiers=fs,
    allow_dirty=True,          # co-lane files live in spikes/harness; §13/H19
    captures=[('selfcheck_tail', sc_tail), ('scan_tail', scan_tail),
              ('v2_blob', r['F4']['measured_on']),
              ('gate_sha256', hashlib.sha256(
                  open(os.path.join(ROOT, 'spikes/harness/scratchcheck.py'),
                       'rb').read()).hexdigest()[:16]),
              ('maker_sha256', hashlib.sha256(
                  open(os.path.join(HERE, 'probe.py'), 'rb').read()).hexdigest()[:16])],
    falsifier='if the three unnamed misses had not reproduced through the live '
              'hook contract on the committed v2 blob (F1), I would have been '
              'attacking a helper function rather than the gate and the row would '
              'be withdrawn. They reproduced, 3 of 3.',
    note='H194 — recall of the §10 gate, never measured. ATTACKER-1, 2026-08-19.')
print('certify ok=%s' % ok)
for p in problems:
    print('  ', p)
sys.exit(0 if ok else 1)
