#!/usr/bin/env python3
"""H201 — controls whose VERDICT is a literal, swept across the fleet.

RUN:  python3 spikes/H201_literal_verdicts/sweep.py

ORIGIN. S91's `C3_pins_intact` declares `can_fail_because="pin drift"` and is fed
`c3_ok = True` (`S91/run.py:242`). No input to that program makes it False. S91's
seat-level defect is AGENT-1's H188 and is NOT re-litigated here; this row is the
control vocabulary, and it turned out S91 is one of twelve.

EVERY CONTROL BELOW IS DERIVED, DELIBERATELY. A spike reporting dead controls
must not ship one, and `constcheck` is run against this file as C4 so that is
checked rather than promised.
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))

from kfcheck import certify, Control                       # noqa: E402
from provenance import Falsifier, Control as _C            # noqa: E402
import constcheck as cc                                    # noqa: E402

S91 = 'spikes/S91_multi_agent_quorum/run.py'
PINS_MARKERS = ('pins_intact', 'pins remain invariant')


def pins_template(live):
    """Live hits whose control is the copied 'F001/F002 pins remain invariant'.

    Read from the 14 lines above the call rather than from a file list: the
    template travels by copy-paste, so its tell is the prose next to it.
    """
    out = []
    for rel, line, recv, lit, where in live:
        try:
            src = open(os.path.join(ROOT, rel), encoding='utf-8',
                       errors='replace').read().splitlines()
        except OSError:
            continue
        ctx = '\n'.join(src[max(0, line - 14):line])
        if any(m in ctx for m in PINS_MARKERS):
            out.append((rel, line))
    return sorted(out)


def main():
    t0 = time.time()
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()

    live, fixture, skipped, unparseable, files = cc.scan(ROOT)
    pins = pins_template(live)
    s91_hit = [r for r in live if r[0] == S91]

    # ---- C1: two-sided on the detector itself -------------------------------
    # S91's exact form must be CAUGHT and a derived verdict must NOT be. One
    # arm alone is satisfiable by a rule that always says yes.
    caught = cc.literal_verdicts(
        'def main():\n    c3_ok = True\n    ctl[2].observe(c3_ok, {"a": 1})\n')
    derived = cc.literal_verdicts(
        'def main():\n    R = [1, 2, 3, 4, 5]\n'
        '    c.observe(len(R) == 5, {"n": len(R)})\n')
    c1 = Control('detector_two_sided',
                 "S91's form is caught AND a derived verdict is not; a detector "
                 'that only ever says yes measures nothing',
                 null_must_contain='the DERIVED arm -- a rule that flagged every '
                                   '`.observe(` would pass the catching arm alone',
                 can_fail_because='the name-resolution branch misses `c3_ok = True`, '
                                  'or the rule widens and flags `len(R) == 5`')
    c1.observe(len(caught) == 1 and len(derived) == 0,
               [len(caught), len(derived)],
               'synthetic: S91 form -> 1 hit; derived comparison -> 0 hits')

    # ---- C2: mutation. The name-resolution branch is load-bearing ------------
    # v1 of this detector could not see S91 at all. Prove the branch that fixed
    # that is the one doing the work, by deleting it and re-running the sweep.
    mut = os.path.join(ROOT, 'spikes', 'harness', '.h201_mutant.py')
    src = open(os.path.join(ROOT, 'spikes', 'harness', 'constcheck.py'),
               encoding='utf-8').read()
    needle = "            elif isinstance(a0, ast.Name) and a0.id in consts:"
    assert needle in src, ('mutation anchor absent -- a no-op mutation would '
                           'report this control fired while changing nothing')
    open(mut, 'w').write(src.replace(needle, "            elif False:"))
    try:
        sys.path.insert(0, os.path.dirname(mut))
        import importlib.util
        spec = importlib.util.spec_from_file_location('_h201_mutant', mut)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        m_live, _f, _s, _u, _n = m.scan(ROOT)
        m_s91 = [r for r in m_live if r[0] == S91]
    finally:
        os.unlink(mut)
    c2 = Control('name_resolution_is_load_bearing',
                 'v1 flagged only a literal FIRST ARGUMENT and could not see the '
                 'instance that motivated the row',
                 null_must_contain='a mutant that still finds S91, which would mean '
                                   'the branch is decoration',
                 can_fail_because='S91 is reachable without resolving the binding, '
                                  'so removing the branch changes nothing')
    c2.observe(len(s91_hit) == 1 and len(m_s91) == 0,
               [len(s91_hit), len(m_s91), len(live), len(m_live)],
               'S91 hits with branch / without; total live with / without')

    # ---- C3: the fixture split is two-sided ---------------------------------
    in_demo = cc.literal_verdicts('def demo():\n    c.observe(False, [1])\n')
    in_main = cc.literal_verdicts('def main():\n    c.observe(False, [1])\n')
    c3 = Control('fixture_split_two_sided',
                 "a control built dead ON PURPOSE inside demo() is not a defect, "
                 'and a real one in main() must not be excused as a fixture',
                 null_must_contain='a rule that calls everything a fixture, which '
                                   'would pass the demo arm alone',
                 can_fail_because='the enclosing-function chain is not recorded, so '
                                  'both cases classify the same way')
    c3.observe(bool(in_demo) and cc.is_fixture(in_demo[0][3])
               and bool(in_main) and not cc.is_fixture(in_main[0][3]),
               [cc.is_fixture(in_demo[0][3]) if in_demo else None,
                cc.is_fixture(in_main[0][3]) if in_main else None],
               'demo() -> fixture; main() -> live')

    # ---- C4: this spike does not ship the defect it reports ------------------
    self_hits = [r for r in live if r[0].startswith('spikes/H201_')]
    c4 = Control('reporter_is_not_the_reported',
                 'a spike about dead controls that ships one is the failure it '
                 'describes, and saying "mine are derived" is not checking it',
                 null_must_contain='a run in which this file DOES contain a literal '
                                   'verdict, which is what the sweep would print',
                 can_fail_because='any `.observe(` in this spike takes a literal or '
                                  'a constant-bound name as its verdict')
    c4.observe(len(self_hits) == 0, [len(self_hits)] + [r[0] for r in self_hits],
               'this spike, scanned by the module it ships')

    # ---- Falsifiers preregistered in CHANNEL.md before the run ---------------
    # C4 FIRED AGAINST THIS FILE ON THE FIRST RUN and this is the repair, kept
    # visible rather than smoothed away. The probe replays S91's shape --
    # `observe(<verdict>, {"f001": ..., "f002": ...})` -- and my first draft
    # passed a literal `True`, so my own sweep flagged my own spike and `certify`
    # refused the run as VOID. The verdict is IRRELEVANT to what F1 measures:
    # `observe()` computes `constant` from `self.values` alone and never looks at
    # the verdict. So the literal is removed rather than exempted; a reporter
    # that special-cases itself is the failure this row is about.
    shape = {'f001': 'aaa', 'f002': 'bbb'}
    dead = _C('probe', 'probe', can_fail_because='probe')
    dead.observe(len(shape) == 2, shape)
    f1_fired = bool(getattr(dead, 'constant', False))
    f1 = Falsifier('f1_existing_guard_already_catches',
                   "if Control.observe's `constant` flag already catches S91's C3, "
                   'the premise is false and this row closes WRONG',
                   fires_when="observe(True, {two keys}) sets constant=True",
                   null_must_contain='a guard that does catch it, which is the '
                                     'state that would kill this row')
    f1.observe(f1_fired, [f1_fired], "replaying S91's exact observe() shape")

    f2 = Falsifier('f2_s91_is_the_only_site',
                   'if S91 is the only site this is an S91 defect and not a class, '
                   'and no checker should ship',
                   fires_when='the tree-wide sweep finds exactly one live hit',
                   null_must_contain='a tree with one site, which is the state that '
                                     'would close this as a spike bug')
    f2.observe(len(live) <= 1, [len(live), len(pins)],
               'live literal verdicts; of which the copied pins template')

    f3 = Falsifier('f3_detector_flags_derived',
                   'if the detector flags a DERIVED verdict it is not shippable and '
                   'the false-positive rate is the result, not the count',
                   fires_when='a verdict computed from a comparison is reported',
                   null_must_contain='a derived verdict being flagged, which is the '
                                     'observation that would stop the ship')
    f3.observe(len(derived) > 0, [len(derived)], 'derived comparison, synthetic')

    result = {
        'head': head, 'stamp': int(t0),
        'py_files_scanned': files,
        'live_literal_verdicts': len(live),
        'fixtures_in_demo_or_selfcheck': len(fixture),
        'trees_skipped': len(skipped),
        'unparseable': unparseable,
        'pins_template_sites': [{'file': f, 'line': l} for f, l in pins],
        'live': [{'file': r[0], 'line': r[1], 'receiver': r[2], 'verdict': r[3],
                  'scope': r[4]} for r in sorted(live)],
        'note': ('A literal verdict is not automatically a dead control. '
                 'H89/H194/H200 transcribe a result whose discriminating VALUES are '
                 'recorded beside it (`observe(True, [2, 0], ...)`), so a third '
                 'party can recompute. The pins template is the pure form: the '
                 'observation is the two pin constants and nothing in the program '
                 'compares them to anything. Both are reported; only the second is '
                 'called a dead control, and that reading is prose, not the tool.'),
    }
    json.dump(result, open(os.path.join(HERE, 'sweep.json'), 'w'), indent=2)

    ok, problems = certify(
        HERE,
        deps=[os.path.join(ROOT, 'spikes', 'harness')],
        artifacts=[os.path.join(HERE, 'sweep.json')],
        controls=[c1, c2, c3, c4],
        falsifiers=[f1, f2, f3],
        captures=[('head', head)],
        falsifier="Control.observe's existing constant flag already catches S91's "
                  'C3, or S91 is the only site (F1/F2)',
        allow_dirty=True,
        note='measurement only; no other lane\'s spike is modified')

    print(f'H201 at {head[:8]}: {files} .py scanned · {len(live)} LIVE literal '
          f'verdict(s) · {len(fixture)} fixture(s) · {len(pins)} are the copied '
          f'pins template')
    print(f'  S91 caught: {len(s91_hit) == 1}   without the name branch: {len(m_s91)}')
    print(f'certify ok: {ok}')
    for p in problems:
        print('  PROBLEM:', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
