#!/usr/bin/env python3
"""What could the 64-program corpus actually have detected?

`64/64 agree byte-identically` is only evidence of cross-architecture
determinism for programs that EVALUATED. This classifies every envelope and
reports how many could have exhibited a divergence at all.

    python3 classify.py            # host-a by default
    python3 classify.py phone
"""
import collections
import glob
import json
import sys

# sha256 of the empty string. An empty capture hashed as data is family B, and
# it is the value `instrument.check_nonempty` exists to refuse.
EMPTY = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


def classify(env):
    """Four outcomes, in the order they stop mattering.

    `import-failure` is the one worth naming separately: the program is
    syntactically fine and the run reports OK, but MeTTa never reached the code
    under test, so the result carries no information about evaluation.
    """
    text = env['results_text']
    if env['raw_hash'] == EMPTY or not text:
        return 'empty'
    if 'Failed to resolve module' in text:
        return 'import-failure'
    if '(Error' in text:
        return 'error-only'
    return 'evaluated'


def main(worker='host-a'):
    files = sorted(glob.glob(f'run/{worker}/out/*.env'))
    if not files:
        sys.exit(f'no envelopes under run/{worker}/out/')
    rows = [json.load(open(f)) for f in files]
    by = collections.Counter(classify(r) for r in rows)

    print(f'{worker}: {len(rows)} envelopes')
    for kind in ('empty', 'import-failure', 'error-only', 'evaluated'):
        grp = [r for r in rows if classify(r) == kind]
        if not grp:
            continue
        fuels = [int(r['fuel_used']) for r in grp]
        print(f'  {kind:15s} {len(grp):3d}  distinct_hashes={len({r["raw_hash"] for r in grp}):3d}'
              f'  fuel {min(fuels)}-{max(fuels)}')

    ran = by['evaluated'] + by['error-only']
    print(f'\nexecuted MeTTa:      {ran}/{len(rows)}')
    print(f'could NOT diverge:   {len(rows) - ran}/{len(rows)}'
          '   (no output, or died at first import!)')
    return by


def demo():
    """The classifier is the claim, so it is what gets tested."""
    e = lambda h, t: {'raw_hash': h, 'results_text': t, 'fuel_used': '1'}
    assert classify(e(EMPTY, '')) == 'empty'
    # an empty body must classify as empty even under a non-empty hash --
    # the guard that was wired for ABSENCE and not EMPTINESS keyed sha256('')
    # as if it were a result.
    assert classify(e('abc', '')) == 'empty'
    assert classify(e('abc', '0\t(Error (import! x agents) Failed to resolve module top:agents)')) \
        == 'import-failure'
    # an import failure is NOT merely an error: it must win over the (Error
    # branch, or the 24 programs that never ran get counted as evaluated.
    assert classify(e('abc', '0\t(Error (assertEqual a b) "no")')) == 'error-only'
    assert classify(e('abc', '0\t(A $x B)')) == 'evaluated'
    print('classify: all assertions pass')


if __name__ == '__main__':
    if '--demo' in sys.argv:
        demo()
    else:
        demo()
        print()
        main(sys.argv[1] if len(sys.argv) > 1 else 'host-a')
