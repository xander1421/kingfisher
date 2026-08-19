#!/usr/bin/env python3
"""ledgerlag.py v1 — H177. A spike that published a RESULT and has no LEDGER row.

THE DEFECT REMOVED
------------------
`out/LEDGER.md` calls itself *"what is actually true"* and had not been touched
since `af6c4e8`, **2026-08-17**, while the mission's headline numbers moved to
the knowledge-graph line. Measured 2026-08-19: the ledger's highest G-series id
was **G27**; 63 G spikes numbered above it existed and **all 63 were absent**,
including the whole official-split WN18RR series that publishes "0.3546 MRR"
and "10.0x lift". 176 of 262 spikes with a `RESULT.md` had no mention at all.

That is not an aesthetic gap. LEDGER standing rule 12 is *"a retraction must be
applied to every file that carries the claim"* — and when H165 refuted G91's
attribution there was **no ledger row to correct**, so the correction had
nowhere to land while `WORK_QUEUE.md` still read "10.0x MRR lift". A ledger that
lags is not merely incomplete: it silently converts rule 12 into a no-op.

WHY THIS IS A SET AND NOT A COUNT, WHICH IS THE WHOLE DESIGN
------------------------------------------------------------
H167, one day old when this was written: `idscope`'s ROWLESS count *"read 14 on
the day it was pinned and 24 today, and it could not tell a floor from an
arrival."* A pinned NUMBER cannot distinguish "someone ledgered two old spikes
and three new ones arrived" from "nothing happened". So the baseline here is
the explicit SET of ids accepted as lagging at pin time. The gate then answers
one question a count cannot:

    is there a spike with a RESULT.md that arrived AFTER the pin and still has
    no LEDGER mention?

Ledgering a baselined id shrinks the debt and is always allowed. Adding a new
unledgered result is what REFUSES.

AND IT DOES NOT FIRE ON THE KNOWN-ACCEPTED STATE, which is H14's rule: *"a gate
that fires on a known-accepted state every run is one everyone learns to
bypass."* 176 lagging spikes on the day of writing would do exactly that, so
they are pinned, printed as a floor on every run, and never silently dropped.

    python3 ledgerlag.py             exit 0 = no NEW unledgered result
    python3 ledgerlag.py --pin       rewrite the baseline (a deliberate act)
    python3 ledgerlag.py --selfcheck both directions, on a synthetic tree
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
BASELINE = os.path.join(HERE, 'ledgerlag_baseline.json')

# The shape this repo actually allocates: a prefix letter run, then digits,
# optionally `_<n>` (M1_9). Same reasoning as refcheck's ID_CELL -- a SHAPE rule
# cannot go stale the way a list of known prefixes does.
SPIKE_ID = re.compile(r'^([A-Z][A-Za-z0-9]*?\d+(?:_\d+)?)_')


def lagging(root):
    """ids of spikes that published a RESULT.md and are named nowhere in the LEDGER."""
    spikes = os.path.join(root, 'spikes')
    ledger_path = os.path.join(root, 'out', 'LEDGER.md')
    if not os.path.isdir(spikes):
        raise SystemExit(f'ledgerlag: no {spikes} -- REFUSING rather than reporting 0 (H30)')
    if not os.path.isfile(ledger_path):
        raise SystemExit(f'ledgerlag: no {ledger_path} -- REFUSING rather than reporting 0 (H30)')
    led = open(ledger_path, encoding='utf-8').read()
    out = set()
    for d in sorted(os.listdir(spikes)):
        if not os.path.isfile(os.path.join(spikes, d, 'RESULT.md')):
            continue
        m = SPIKE_ID.match(d)
        if not m:
            continue
        sid = m.group(1)
        if not re.search(r'\b' + re.escape(sid) + r'\b', led):
            out.add(sid)
    return out


def load_baseline():
    if not os.path.isfile(BASELINE):
        return None
    return set(json.load(open(BASELINE))['lagging'])


def main(argv):
    root = ROOT
    now = lagging(root)

    if '--pin' in argv:
        json.dump({'lagging': sorted(now),
                   'why': 'ids accepted as lagging at pin time; a NEW id refuses (H177)'},
                  open(BASELINE, 'w'), indent=1)
        print(f'ledgerlag: pinned {len(now)} lagging spike id(s)')
        return 0

    base = load_baseline()
    if base is None:
        print('ledgerlag: no baseline -- run --pin once. REFUSING rather than '
              'treating an absent baseline as "nothing is lagging" (H30, and the '
              'brief\'s absence-is-UNKNOWN-never-CLEAR rule).')
        return 2

    new = sorted(now - base)
    healed = sorted(base - now)
    print(f'ledgerlag: baseline floor {len(base)} lagging · now {len(now)} · '
          f'newly ledgered {len(healed)} · NEW unledgered {len(new)}')
    if healed:
        print('  ledgered since the pin (debt shrank, always allowed): '
              + ' '.join(healed[:12]) + (' ...' if len(healed) > 12 else ''))
    if not new:
        print('ledgerlag: no spike published a RESULT.md after the pin without a LEDGER row')
        return 0
    for sid in new:
        print(f'  NEW UNLEDGERED {sid}: spikes/{sid}_*/RESULT.md exists and '
              f'out/LEDGER.md never names it')
    print('\nREFUSE: a result was published with no row in the file that calls itself\n'
          '        "what is actually true". Standing rule 12 cannot reach a claim\n'
          '        that has no row, so this refuses rather than warns.')
    return 1


def selfcheck():
    """BOTH directions on a synthetic tree. A gate whose refusing arm is never
    exercised is a coincidence, not a control (A15)."""
    import tempfile
    global BASELINE
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, 'out'))
        os.makedirs(os.path.join(tmp, 'spikes', 'G10_alpha'))
        os.makedirs(os.path.join(tmp, 'spikes', 'G11_beta'))
        open(os.path.join(tmp, 'spikes', 'G10_alpha', 'RESULT.md'), 'w').write('x')
        open(os.path.join(tmp, 'spikes', 'G11_beta', 'RESULT.md'), 'w').write('x')
        open(os.path.join(tmp, 'out', 'LEDGER.md'), 'w').write('G10 is graded C here.\n')

        got = lagging(tmp)
        if got != {'G11'}:
            print(f'SELFCHECK FAILED: expected {{G11}} lagging, got {got}'); ok = False

        # a spike with NO RESULT.md must not count -- it published nothing
        os.makedirs(os.path.join(tmp, 'spikes', 'G12_gamma'))
        if 'G12' in lagging(tmp):
            print('SELFCHECK FAILED: G12 has no RESULT.md and must not count'); ok = False

        # the REFUSING direction: a new result after the pin
        open(os.path.join(tmp, 'spikes', 'G12_gamma', 'RESULT.md'), 'w').write('x')
        if lagging(tmp) != {'G11', 'G12'}:
            print('SELFCHECK FAILED: G12 gained a RESULT.md and must now count'); ok = False

        # ledgering a lagging id must clear it -- the healing direction
        open(os.path.join(tmp, 'out', 'LEDGER.md'), 'a').write('G11 graded INVALID.\n')
        if 'G11' in lagging(tmp):
            print('SELFCHECK FAILED: G11 is now named in the LEDGER and must clear'); ok = False

        # a substring must NOT satisfy the check: G1 is not G11
        open(os.path.join(tmp, 'out', 'LEDGER.md'), 'w').write('G120 and G1 appear here.\n')
        if 'G12' not in lagging(tmp):
            print('SELFCHECK FAILED: `G120` must not satisfy a lookup for G12'); ok = False

        # a missing input REFUSES rather than degrading to an empty set (H30)
        try:
            lagging(os.path.join(tmp, 'nonexistent'))
            print('SELFCHECK FAILED: a missing tree must REFUSE, not return 0'); ok = False
        except SystemExit:
            pass

    print('ledgerlag --selfcheck: ok' if ok else 'ledgerlag --selfcheck: FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main(sys.argv[1:]))
