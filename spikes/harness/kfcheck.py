#!/usr/bin/env python3
"""One entry point for every mechanical check, organised by FAILURE FAMILY.

Several of this project's errors were the same bug wearing different clothes.
Grouping them by family is what makes the catalogue usable rather than a list.

  A  the instrument cannot produce the answer   A15 / A20 / A21  -> provenance, power
  B  the instrument is reporting fiction                          -> instrument
  C  the artifact is not what you think         A24               -> provenance
  D  self-reported / self-flattering inputs     A22               -> provenance, callers
  E  the number is real, the model is wrong     A18               -> units

Three failures in this project were caught by READING and cannot be mechanised:
claim decay across documents, correct numbers pointing at the wrong cause, and a
measurement that answered a different question than the one asked. For those the
rule is A20's: state the falsifier before running, then run it. `certify` will
ask whether you did; it cannot check that you were honest.
"""
import os
import instrument as _inst
import units as _units
from provenance import record, Control          # noqa: F401  (re-exported)


def certify(spike_dir, deps=(), artifacts=(), controls=(),
            measurements=(), captures=(), instrument_texts=(),
            falsifier=None, allow_dirty=False, no_deps_reason=None, note=''):
    """(ok, problems). Refuses rather than warns.

    measurements     [{'name':…, 'points':[(x,y)…], 'as_rate':bool,
                       'intercept':float, 'components':{…}}]
    captures         [(name, value)]        -- family B, empty/empty-hash
    instrument_texts [(name, text)]         -- family B, frozen override
    falsifier        str; what result would have refuted the claim
    """
    ok, prov = record(spike_dir, deps=deps, artifacts=artifacts,
                      controls=controls, allow_dirty=allow_dirty,
                      no_deps_reason=no_deps_reason, note=note)
    problems = list(prov.get('problems', []))

    for name, text in instrument_texts:
        good, why = _inst.check_not_frozen(text, name=name)
        if not good:
            problems.append(f'INSTRUMENT: {why}')
    for name, val in captures:
        good, why = _inst.check_nonempty(val, name)
        if not good:
            problems.append(f'CAPTURE: {why}')

    for m in measurements:
        nm = m.get('name', '?')
        pts = m.get('points') or []
        if m.get('as_rate'):
            try:
                _units.fit_or_refuse(pts)
            except _units.ModelRefused as e:
                problems.append(f'MODEL {nm}: {e}')
            good, why = _units.check_affine(pts)
            if not good:
                problems.append(f'MODEL {nm}: reported as a rate but {why}')
        if 'intercept' in m:
            good, why = _units.attribute_intercept(
                m['intercept'], m.get('components', {}))
            if not good:
                problems.append(f'INTERCEPT {nm}: {why}')

    if not falsifier:
        problems.append(
            'NO FALSIFIER DECLARED: state what result would have refuted this '
            'claim, before running. The errors that survived here are the ones '
            'whose falsifier was written and marked "not yet run".')

    prov['falsifier'] = falsifier
    prov['problems'] = problems
    prov['ok'] = not problems
    import json
    with open(os.path.join(spike_dir, 'provenance.json'), 'w') as f:
        json.dump(prov, f, indent=1)
    return prov['ok'], problems


def demo():
    import tempfile
    d = tempfile.mkdtemp()
    NR = 'synthetic'
    c = Control('posctl', 'must vary', null_must_contain='identical hashes',
                can_fail_because='a deterministic program gives identical hashes')
    c.observe(True, [f'h{i}' for i in range(5)], '5/5 distinct')
    base = dict(spike_dir=d, controls=[c], no_deps_reason=NR,
                falsifier='if all 5 hashes matched, the claim is refuted')

    ok, probs = certify(**base)
    assert ok, probs

    # family E: the real WiFi curve reported as a rate must be refused
    wifi = [(4, 14.4), (64, 31.6), (1024, 130.9), (16384, 719.3)]
    ok, probs = certify(**base, measurements=[
        {'name': 'wifi', 'points': wifi, 'as_rate': True}])
    assert not ok and any('NOT affine' in p for p in probs), probs

    # family B: a frozen instrument
    ok, probs = certify(**base, instrument_texts=[
        ('dumpsys battery', 'x\n  (UPDATES STOPPED -- use reset)\n  status: 5')])
    assert not ok and any('OVERRIDDEN' in p for p in probs), probs

    # family B: an empty-hash capture
    ok, probs = certify(**base, captures=[
        ('result_hash', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')])
    assert not ok and any('empty string' in p for p in probs), probs

    # unattributed intercept
    ok, probs = certify(**base, measurements=[
        {'name': 'xfer', 'points': [(1, 2)], 'intercept': 63.2,
         'components': {'guess': 5.0}}])
    assert not ok and any('unexplained' in p for p in probs), probs

    # no falsifier declared
    ok, probs = certify(spike_dir=d, controls=[c], no_deps_reason=NR)
    assert not ok and any('NO FALSIFIER' in p for p in probs), probs
    print('kfcheck: 6 families exercised, all refusals fire')


if __name__ == '__main__':
    demo()
