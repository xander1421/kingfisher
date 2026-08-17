#!/usr/bin/env python3
"""ATTACK on S20, two cycles old, mine, and already load-bearing for S24 and S27.

§2: instruments before conclusions, self-authored data first. Two angles, both
aimed at the sentence S20's row leads with -- *"absence extends S84's membership
band 1.06-1.16x"*.

A1 -- THE DENOMINATOR. **The accusation this angle was built on is WRONG and is
withdrawn here rather than quietly dropped.** I read `verifycost.json`'s raw
ratio list (1.223 / 1.161 / 1.065 -- auth-path denominated) and concluded S20 had
compared its witness-denominated ratios against a path-denominated band. S84's
RESULT.md says otherwise in its own C27 changelog: *"Counting the leaf
descriptor, the operating points are 1.16 / 1.13 / 1.06x, so the range on real
key sets is 1.06-1.16x"* -- already corrected, already witness-denominated. The
JSON is the pre-correction artifact; the page is the claim. **I attacked the
artifact and did not read the page, which is CLAUDE.md's "correct numbers, wrong
attribution" committed inside an attack cycle.**
    WHAT THE ANGLE PRODUCES ANYWAY, and it is worth the cycle: membership and
    absence measured in the SAME run on the SAME denominator, which is a sharper
    comparison than "lands in a band" and dissolves the one band-edge miss S20
    reported.

A2 -- THE COUNTER. `CountingHashlib` now carries S84, S20, S24 and S27. A shared
helper makes agreement worthless -- the test is not whether four spikes agree but
whether they COULD have disagreed. S27 validated it for the completeness path
against an independent traversal that hashes nothing (0.000%). The membership and
absence paths have never had that check.
    THE TEST: model the bytes those two verifiers must hash, straight from
    `fold` and `desc_hash`, in code that shares nothing with the counter, and
    compare.

Certification writes `provenance.attack.json`, NOT `provenance.json` -- H49: an
attack that certifies into its target's directory replaces that target's
controls and artifact digests and leaves a file reading `ok: true`.

  python3 attack.py
"""
import os, sys, json, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import verify_kinds as S20M                                               # noqa: E402
from trie_witness import (build, prove_membership, verify_membership,     # noqa: E402
                          prove_non_membership, verify_non_membership,
                          witness_bytes, auth_path_bytes)
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                              # noqa: E402
from provenance import Control, Falsifier                                # noqa: E402
from absence import absent_probes, child_map                             # noqa: E402

DIGEST = 32
PROBES = 60
BAND = (1.06, 1.16)          # S84's band, on S84's denominator
TOL_PCT = 1.0                # A2: model vs counter, on a quantity that is 0 or a bug


def model_bytes(pf):
    """What `verify_membership` / `verify_non_membership` must feed sha256.

    `fold` recomputes each step as `node_hash(prefix, term, sorted(pairs +
    [(b, child_hash)]))` -- one MORE edge than the proof transmits, because the
    taken child is in the hashed input. Then `desc_hash` hashes the terminal
    descriptor exactly once: the leaf for membership, the divergence node for
    absence. Written from those two functions' definitions, sharing no code with
    the counting hashlib.
    """
    n = 0
    for (prefix, _term, pairs), _b in pf['steps']:
        n += 1 + 2 + len(prefix) + 1 + 2 + (len(pairs) + 1) * (1 + DIGEST)
    d = pf.get('leaf') if 'leaf' in pf else pf.get('node')
    if d is not None:
        prefix, _term, pairs = d
        n += 1 + 2 + len(prefix) + 1 + 2 + len(pairs) * (1 + DIGEST)
    return n


def run_set(name, path):
    keys = S20M.S84M.read_keys(path)
    root = build(sorted(set(keys)))
    rh = root.h
    kids = child_map(keys)
    step = max(1, len(keys) // PROBES)
    probes = sorted(set(keys))[::step][:PROBES]

    mem = {'hash': [], 'steps': [], 'witness': [], 'model': []}
    for k in probes:
        pf = prove_membership(root, k)
        if pf is None:
            continue
        ok, _n, b = S20M.counted(verify_membership, rh, k, pf)
        if not ok:
            raise SystemExit('ATTACK: a membership proof failed to verify (A29)')
        mem['hash'].append(b)
        mem['steps'].append(auth_path_bytes(pf))
        mem['witness'].append(witness_bytes(pf))
        mem['model'].append(model_bytes(pf))

    abs_ = {'hash': [], 'steps': [], 'witness': [], 'model': []}
    aprobes, _d = absent_probes(keys, kids, PROBES)
    for q in aprobes:
        pf = prove_non_membership(root, q)
        if pf is None:
            continue
        ok, _n, b = S20M.counted(verify_non_membership, rh, q, pf)
        if not ok:
            raise SystemExit('ATTACK: an absence proof failed to verify (A29)')
        abs_['hash'].append(b)
        abs_['steps'].append(auth_path_bytes(pf))
        abs_['witness'].append(witness_bytes(pf))
        abs_['model'].append(model_bytes(pf))

    def row(d, kind):
        H = statistics.mean(d['hash'])
        S = statistics.mean(d['steps'])
        W = statistics.mean(d['witness'])
        M = statistics.mean(d['model'])
        return {'set': name, 'kind': kind, 'n': len(d['hash']),
                'hash_bytes': round(H, 3),
                'per_auth_path_byte': round(H / S, 4),
                'per_witness_byte': round(H / W, 4),
                'model_bytes': round(M, 3),
                'model_slack_pct': round((H - M) / M * 100.0, 4)}

    return row(mem, 'membership'), row(abs_, 'absence')


def main():
    rows = []
    for name, path in S20M.SETS:
        m, a = run_set(name, path)
        rows.append(m)
        rows.append(a)

    by = {(r['set'], r['kind']): r for r in rows}
    published = json.load(open(os.path.join(HERE, 'verify_kinds.json')))
    pub = {k.split('/')[0]: v for k, v in published['work_per_witness_byte'].items()
           if k.endswith('/absence')}

    # A1 -- absence against MEMBERSHIP measured the same way, not against a band
    # computed on the other denominator.
    same_denom = {}
    for name, _p in S20M.SETS:
        m, a = by[(name, 'membership')], by[(name, 'absence')]
        same_denom[name] = {
            'membership_per_witness_byte': m['per_witness_byte'],
            'absence_per_witness_byte': a['per_witness_byte'],
            'absence_minus_membership': round(
                a['per_witness_byte'] - m['per_witness_byte'], 4),
            'membership_per_auth_path_byte': m['per_auth_path_byte'],
            'S20_published_absence': pub.get(name)}

    # A2 -- counter against an independent model, on the two paths S27 did not cover
    worst = max(abs(r['model_slack_pct']) for r in rows)

    out = {'rows': rows, 'same_denominator': same_denom,
           'band_on_S84_denominator': list(BAND),
           'model_worst_abs_slack_pct': round(worst, 4),
           'tolerance_pct': TOL_PCT}
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    c = Control('C_absence_reproduces_S20',
                'this attack must reproduce S20\'s published absence ratios '
                'before it is allowed to reinterpret them -- otherwise a '
                'disagreement could be the attack\'s own bug',
                null_must_contain='any drift in the instrument, key files or '
                                  'probe construction would move these',
                can_fail_because='a published absence ratio differs from the '
                                 'value recomputed here by more than 0.002')
    deltas = {n: round(by[(n, 'absence')]['per_witness_byte'] - pub[n], 5)
              for n, _p in S20M.SETS}
    c.observe(all(abs(v) <= 0.002 for v in deltas.values()),
              {'deltas_vs_published': deltas, 'published': pub})
    C.append(c)

    c = Control('C_two_denominators_differ',
                'the whole of A1 rests on the two denominators being different '
                'quantities. If auth-path and witness bytes were equal, the '
                'comparison S20 made would have been harmless and this angle '
                'would be empty',
                null_must_contain='a proof kind whose terminal descriptor is '
                                  'zero bytes, where the two coincide',
                can_fail_because='auth-path and witness bytes agree on every '
                                 'set, making the denominators interchangeable')
    diffs = {r['set'] + '/' + r['kind']:
             round(r['per_auth_path_byte'] - r['per_witness_byte'], 4)
             for r in rows}
    c.observe(any(abs(v) > 0.005 for v in diffs.values()), diffs)
    C.append(c)

    c = Control('C_model_shares_no_code',
                'A2: the byte model is written from `fold` and `desc_hash` and '
                'hashes nothing, so it can disagree with the counting hashlib '
                'that four spikes now depend on. S27 ran this check for the '
                'completeness path; membership and absence never had it',
                null_must_contain='a counter that missed an update, or a '
                                  'verifier hashing something outside node_hash',
                can_fail_because='model and counter disagree by more than '
                                 '%.1f%% on any row' % TOL_PCT)
    c.observe(worst <= TOL_PCT,
              {r['set'] + '/' + r['kind']: r['model_slack_pct'] for r in rows})
    C.append(c)

    # The attack's own accusation, tested rather than asserted. It is FALSE:
    # S84's page publishes the band on the witness denominator (its C27
    # changelog), and this run reproduces 1.16 / 1.13 / 1.06 to rounding.
    band_mismatch = not all(
        BAND[0] - 0.005 <= by[(n, 'membership')]['per_witness_byte'] <= BAND[1] + 0.005
        for n, _p in S20M.SETS)
    F = Falsifier('F_band_comparison_was_wrong',
                  refutes='THIS ATTACK\'s own A1 premise -- that S20 compared '
                          'against a band computed on a different denominator. '
                          'If membership under S20\'s denominator lands inside '
                          'S84\'s published band, the premise is refuted and '
                          'the accusation is withdrawn',
                  fires_when='membership measured on the witness denominator '
                             'falls OUTSIDE S84\'s published 1.06-1.16 band, '
                             'which is what a denominator mismatch would show',
                  null_must_contain='membership landing inside the band, i.e. '
                                    'the band and S20\'s ratios sharing a '
                                    'denominator and there being nothing to '
                                    'correct')
    F.observe(band_mismatch,
              {'S84_page_band': list(BAND),
               'S84_json_raw_ratios_are_path_denominated': [1.223, 1.161, 1.065],
               'membership_per_witness_byte': {
                   n: by[(n, 'membership')]['per_witness_byte']
                   for n, _p in S20M.SETS},
               'membership_per_auth_path_byte': {
                   n: by[(n, 'membership')]['per_auth_path_byte']
                   for n, _p in S20M.SETS}})

    ok, problems = certify(
        HERE, deps=[],
        no_deps_reason='the instrument is S20\'s pinned w2_head/trie_witness.py, '
                       'already hashed as an artifact by S20\'s own record; this '
                       'attack adds no new dependency and writes under its own '
                       'record name so it cannot overwrite that record (H49).',
        artifacts=[os.path.join(HERE, 'attack.json')],
        controls=C, falsifiers=[F],
        record_name='provenance.attack.json',
        falsifier='membership measured on S20\'s own denominator falling '
                  'outside S84\'s published band, which would have confirmed '
                  'this attack\'s A1 premise instead of refuting it; and, for '
                  'A2, the byte model disagreeing with the counting hashlib that '
                  'four spikes now share')

    print(json.dumps(out['same_denominator'], indent=2, sort_keys=True))
    for r in rows:
        print('  %-16s %-11s hash=%9.1f  /path=%.4f  /witness=%.4f  model_slack=%+.4f%%'
              % (r['set'], r['kind'], r['hash_bytes'], r['per_auth_path_byte'],
                 r['per_witness_byte'], r['model_slack_pct']))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
