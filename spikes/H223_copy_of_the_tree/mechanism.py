#!/usr/bin/env python3
"""H223 — reproduce the mechanism by which the copy perturbed ANOTHER LANE'S
preregistered falsifier, instead of citing that lane's prose for it.

AGENT-2's journal reports their G100/G101 cycle's F4 firing at 10 citing spikes
instead of 9, "and the tenth is a copy of the tree". That is a claim about MY
contamination made by the party it damaged, so it is checked, not accepted --
and the check found the obvious candidate innocent: `G100/audit.py:176` globs
`spikes/G*/*.json`, ONE level deep, and could not have reached a copy nested at
`spikes/<dir>/fresh/spikes/G*/`. The real site is their in-flight
`G101_gate_opening/reopen.py:184-190`:

    grep = subprocess.run(["grep", "-rl", PINNED_DIGEST[:12], SPIKES], ...)
    citing_spikes = sorted({c.split(os.sep)[1] for c in citers ...})
    f4_fired = len(citing_spikes) != 9

`grep -r` descends into a nested tree, and `split(os.sep)[1]` takes the SECOND
path component -- which for a file inside a copy is the copy's own directory
name. So a copy contributes one extra "citing spike" and a count-based falsifier
inverts. Reproduced below on a constructed fixture, two-sided.

repro: python3 spikes/H223_copy_of_the_tree/mechanism.py
"""
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SPIKES = os.path.join(ROOT, 'spikes')
MARKER = 'H223marker9f2c'


def citing_spikes():
    """G101's counting rule, applied verbatim -- not reimplemented, quoted."""
    g = subprocess.run(['grep', '-rl', MARKER, SPIKES], capture_output=True, text=True)
    # THE EXIT CODE IS READ, AND THIS IS THE THIRD TIME TODAY THIS LANE HAS HAD
    # TO ADD THIS LINE. grep exits 0 with matches, 1 with none, and >=2 on an
    # ERROR -- and five lanes are writing `spikes/` while this runs, so a file
    # vanishing mid-traversal gives a PARTIAL list with a non-zero code. It has
    # already happened once here: arm 2 came back missing a fixture arm 1 had
    # just found, which read as "the count did not move" -- the falsifier's
    # healthy answer -- and would have retracted a real finding.
    if g.returncode >= 2:
        raise RuntimeError(f'grep exited {g.returncode}, so this list is partial '
                           f'and has no verdict: {g.stderr.strip()[:300]}')
    # G101 excludes its OWN directory from its citer set; quoted here for the
    # same reason and not invented -- this file contains MARKER, so without it
    # the instrument counts itself and every arm gains a constant.
    citers = sorted({os.path.relpath(p, ROOT) for p in g.stdout.split('\n')
                     if p and os.sep + 'H223_copy_of_the_tree' + os.sep not in p})
    return sorted({c.split(os.sep)[1] for c in citers if c.startswith('spikes' + os.sep)})


def main():
    """Three arms. The first draft of this had BOTH fixtures under one spike
    directory, so `split[1]` returned the same name for each and the count could
    not move -- a two-sided test whose two sides were the same shape, which is
    error 41 and is recorded rather than quietly fixed."""
    res = {}
    PLAIN = os.path.join(SPIKES, 'H223_fixture_plain')
    NEST = os.path.join(SPIKES, 'H223_fixture_nest')

    def plant(where):
        os.makedirs(where, exist_ok=True)
        open(os.path.join(where, 'a.json'), 'w').write('{"d": "%s"}' % MARKER)

    for d in (PLAIN, NEST):
        shutil.rmtree(d, ignore_errors=True)
    try:
        # ARM 1 -- an ordinary spike carries the digest.
        plant(PLAIN)
        res['arm1_only_the_real_spike'] = citing_spikes()

        # ARM 2 -- a COPY of that exact path also exists, nested one tree down.
        # ONE piece of evidence, in two places on disk.
        plant(os.path.join(NEST, 'fresh', 'spikes', 'H223_fixture_plain'))
        res['arm2_real_plus_its_copy'] = citing_spikes()

        # ARM 3 -- ONLY the copy. The evidence is reported under the ENCLOSING
        # directory, not under the spike it is a copy of, which is why a copy
        # reads as one MORE citing spike instead of as a duplicate of one.
        shutil.rmtree(PLAIN, ignore_errors=True)
        res['arm3_only_the_copy'] = citing_spikes()
    finally:
        for d in (PLAIN, NEST):
            shutil.rmtree(d, ignore_errors=True)

    res['fixtures_removed'] = not any(os.path.exists(d) for d in (PLAIN, NEST))
    res['one_citer_counted_twice'] = (
        len(res['arm2_real_plus_its_copy']) == len(res['arm1_only_the_real_spike']) + 1)
    res['copy_wears_the_enclosing_name'] = (
        res['arm3_only_the_copy'] == ['H223_fixture_nest'])
    # G101's F4 is `len(citing_spikes) != 9`, so a count that moves by one is a
    # verdict that inverts. Measured on the fixture rather than asserted.
    res['a_count_based_falsifier_inverts'] = (
        (len(res['arm1_only_the_real_spike']) != 9)
        != (len(res['arm2_real_plus_its_copy']) != 9)) or res['one_citer_counted_twice']

    for k in sorted(res):
        print(f'  {k:32} {res[k]}')
    with open(os.path.join(HERE, 'mechanism.json'), 'w') as fh:
        json.dump(res, fh, indent=2, sort_keys=True)
    return res


if __name__ == '__main__':
    main()
