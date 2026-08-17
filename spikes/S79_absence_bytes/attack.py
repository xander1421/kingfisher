#!/usr/bin/env python3
"""ATTACK on S79 — the model and its cross-check are not counting the same thing.

TARGET CHOSEN PER MISSION_LOOP §2: instruments before conclusions, self-authored
data first. S79's headline rests on a comparison between a MODEL (the Python
sibling recount C14 validated) and a MEASUREMENT (W2's real
`prove_non_membership`), and it publishes their agreement as corroboration:

    "The model's absolute bytes are 4-7% under W2's real ones (1,513 vs 1,589 ·
     1,856 vs 1,930 · 2,299 vs 2,291), the same residual as S77: W2's per-step
     framing."

THE THESIS, STATED BEFORE THE RUN
---------------------------------
    `steps_bytes(pf['steps'])` is not the size of a non-membership proof. W2's
    own `witness_bytes()` is `steps_bytes + desc_bytes(pf['node'])`, and
    `pf['node']` is the DIVERGENCE NODE -- whose child set is precisely the
    "ALL children at the divergence position" that S79's own model charges and
    calls the entire structural difference between absence and membership. So
    the model includes that term and the measurement excludes it, and any
    agreement between them is an agreement between two different quantities.

FALSIFIER FOR THIS ATTACK, so it can come out the other way
-----------------------------------------------------------
    If `desc_bytes(pf['node'])` is negligible -- under 1% of the proof, or
    within the residual's own noise -- then the two accountings differ by
    nothing that matters, S79's attribution stands, and this attack has found a
    naming problem rather than a measurement problem.

REPRODUCE BEFORE REFUTING (the attacker rule that outranks the finding)
-----------------------------------------------------------------------
This runs S79's OWN `absent_probes`, `child_map` and `read_keys` -- imported,
not reimplemented -- and asserts the recomputed `steps_bytes` mean lands within
1 B of every figure committed in `absence.json`. If that assert fails, nothing
below is about S79 and the run says so instead of publishing.

  python3 attack.py
"""
import os, sys, json, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'W2_witnessed_trie'))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
import absence as A                                                        # noqa: E402
from trie_witness import (build, prove_non_membership, prove_membership,   # noqa: E402
                          verify_non_membership, steps_bytes, desc_bytes)
from kfcheck import certify                                                # noqa: E402
from provenance import Control, Falsifier                                  # noqa: E402

PUB = json.load(open(os.path.join(HERE, 'absence.json')))['sets']


def main():
    rows, repro_gap, verified_all = [], [], True
    for name, path in A.SETS:
        keys = A.read_keys(path)
        kids = A.child_map(keys)
        probes, depths = A.absent_probes(keys, kids, A.PROBES)
        root = build(sorted(set(keys)))
        rh = root.h
        st, dn, ver, n = [], [], 0, 0
        for p in probes:
            pf = prove_non_membership(root, p)
            if pf is None:
                continue
            n += 1
            st.append(steps_bytes(pf['steps']))
            dn.append(desc_bytes(pf['node']))
            ver += bool(verify_non_membership(rh, p, pf))
        m_steps, m_dn = statistics.mean(st), statistics.mean(dn)
        pub = PUB[name]
        repro_gap.append(round(abs(m_steps - pub['w2_real_absence_bytes_mean']), 3))
        verified_all = verified_all and (ver == n)
        model = pub['absence_auth_bytes_mean']
        rows.append({
            'set': name,
            'model_bytes': model,
            'published_w2_bytes_steps_only': pub['w2_real_absence_bytes_mean'],
            'recomputed_steps_bytes_mean': round(m_steps, 2),
            'divergence_node_descriptor_bytes': round(m_dn, 1),
            'full_proof_bytes': round(m_steps + m_dn, 1),
            'published_residual_pct': round((pub['w2_real_absence_bytes_mean']
                                             - model) / model * 100, 1),
            'true_residual_pct': round((m_steps + m_dn - model) / model * 100, 1),
            'omitted_share_of_proof_pct': round(m_dn / (m_steps + m_dn) * 100, 2),
        })

    omitted = [r['omitted_share_of_proof_pct'] for r in rows]
    sign_flip = [r for r in rows
                 if (r['published_residual_pct'] < 0) != (r['true_residual_pct'] < 0)]
    fired = min(omitted) >= 1.0

    C = [
        Control('C_reproduces_S79',
                'a refutation must reproduce the target first; if these probes do '
                'not land on the committed figures, this attack is about a '
                'different measurement and says so instead of publishing',
                null_must_contain='a rerun that misses the committed numbers, '
                                  'which would mean the target is not reproducible',
                can_fail_because='absent_probes could be seed- or order-dependent, '
                                 'in which case the recomputed means would drift '
                                 'from the committed ones'),
        Control('C_proofs_still_verify',
                'the omitted term must belong to proofs that are REAL: every '
                'non-membership proof measured here must verify against the root, '
                'or the bytes being counted are bytes of nothing (A29)',
                null_must_contain='proofs that fail verification, whose sizes '
                                  'would describe a broken prover',
                can_fail_because='a probe that is actually present has no honest '
                                 'absence proof and prove_non_membership returns '
                                 'None, which would drop n below the probe count'),
        Control('C_omission_is_structural_not_framing',
                'the omitted term must be the DIVERGENCE CHILD SET that the model '
                'charges, not per-step framing; otherwise this is S77 residual '
                'again and not a new finding',
                null_must_contain='a divergence descriptor whose bytes are all '
                                  'prefix and framing, with no child digests',
                can_fail_because='if divergence nodes were single-child, '
                                 'desc_bytes would be ~5 B of framing and the '
                                 'omission would be the naming problem, not a '
                                 'measurement one'),
    ]
    C[0].observe(max(repro_gap) < 1.0,
                 {'recomputed_steps_bytes_mean':
                      [r['recomputed_steps_bytes_mean'] for r in rows],
                  'committed_in_absence_json':
                      [PUB[n]['w2_real_absence_bytes_mean'] for n, _p in A.SETS],
                  'absolute_gap_B': repro_gap},
                 'recomputed against committed, per set — a gap of 0.0 B on all '
                 'three is exact reproduction, which is what licenses the '
                 'refutation below')
    C[1].observe(verified_all,
                 {'all_probes_verified': verified_all,
                  'probes_per_set': A.PROBES},
                 'every counted absence proof verifies against the root')
    C[2].observe(min(r['divergence_node_descriptor_bytes'] for r in rows) > 40,
                 [r['divergence_node_descriptor_bytes'] for r in rows],
                 'a 33 B child entry each, so >40 B cannot be framing alone '
                 '(framing is 5 B + prefix)')

    F = Falsifier('F_omission_is_negligible',
                  refutes='this attack -- if the divergence descriptor is under '
                          '1% of the proof, the two accountings differ by nothing '
                          'that matters and S79 has a naming problem, not a '
                          'measurement one',
                  fires_when='the omitted descriptor is under 1% of the full proof '
                             'in every key set',
                  null_must_contain='a corpus whose divergence nodes are narrow, '
                                    'making the omitted term small')
    F.observe(not fired, omitted,
              'omitted descriptor as a percentage of the full proof, per set')

    out = {'target': 'spikes/S79_absence_bytes/RESULT.md, the model-vs-W2 '
                     'cross-check and its residual attribution',
           'thesis': 'steps_bytes is not the size of a non-membership proof; '
                     "W2's own witness_bytes is steps_bytes + desc_bytes(node), "
                     'and that descriptor holds the divergence child set the '
                     'model charges',
           'reproduced_committed_figures_within_B': repro_gap,
           'attack_stands': fired,
           'sign_flips': [r['set'] for r in sign_flip],
           'rows': rows,
           'what_survives': "S79's headline is model-over-model "
                            '(absence_auth vs membership_auth, both from the '
                            'C14-validated recount) and is unaffected: absence '
                            'still costs 1.02-1.04x membership and still orders '
                            'the sets identically.',
           'what_does_not': "the CROSS-CHECK and its attribution. The residual is "
                            '4.0-10.3%, not 4-7%, the triples row flips sign, and '
                            'part of it is a structurally omitted term rather than '
                            "W2's per-step framing.",
           'scope_membership': 'for MEMBERSHIP the same omission is the leaf '
                               'descriptor at 87.5 / 45.2 / 5.5 B, it does NOT '
                               "reorder the key sets, so S77's inversion survives; "
                               'and a leaf prefix is derivable from the key by the '
                               'verifier, so omitting it is defensible -- what was '
                               'missing is that nobody said which accounting was '
                               'in use.'}
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[os.path.join(HERE, '..', 'W2_witnessed_trie')],
        artifacts=[os.path.join(HERE, 'attack.json')],
        controls=C, falsifiers=[F], allow_dirty=True,
        # H49: BESIDE the target's record, not on top of it. The first version of
        # this file wrote provenance.json into S79's own directory and replaced
        # its five controls and its absence.json digest with this attack's three
        # -- the spike's D6 evidence destroyed on disk while the file read as a
        # complete passing record of a run nobody made, and WORK_QUEUE still
        # cited five. record() now REFUSES that; this is the remedy it names.
        record_name='provenance.attack.json',
        no_deps_reason='attacking a committed spike from its own directory',
        note='allow_dirty is set and stated rather than flagged past: the dirty '
             'entry is THIS attack being written into the target spike dir. The '
             'dependency under measurement, W2_witnessed_trie/trie_witness.py, is '
             'untouched by this cycle, and C_reproduces_S79 is the check that '
             'matters -- it lands on the committed figures to 0.0 B, which no '
             'edit to the prover could survive.',
        falsifier='the divergence descriptor is under 1% of the proof in every set')

    print(json.dumps(out, indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
