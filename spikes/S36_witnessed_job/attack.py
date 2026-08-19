#!/usr/bin/env python3
"""S36-ATTACK — the omission the completeness verifier accepts, and it forges nothing.

TARGET: my own `spikes/S36_witnessed_job/`, committed one cycle ago (§2: ATTACK
targets the last three cycles' outputs, self-authored data first). S36 published

    two non-independent liars -> replication 0/37 caught, witnessed 37/37 caught

and, beside it, *"all three tamper classes are rejected by the single verifier:
omit 37/37, add 37/37, alter 37/37. One class alone could be an accident of
encoding."* Three classes is not the class list. Every one of them rewrites
`pf['keys']` while KEEPING THE HONEST AUTHENTICATION PATH -- so all three are the
same attack shape, and S36 tested one shape three ways.

THE SHAPE IT DID NOT TEST
-------------------------
A liar that ships a DIFFERENT HONEST PROOF. `verify_completeness` re-walks the
query against the proven descriptions in its non-COVER branch and NOT in its
COVER branch, while `verify_membership` and `verify_non_membership` both do it
unconditionally, with the reason written in the source:

    # re-walk the query against the PROVEN descriptions, so a proof of a
    # different key cannot be replayed for this one.

So for a range query the answer is authenticated against the ROOT but never bound
to the QUERY. A prover asked for prefix q can return the complete, genuine,
byte-for-byte honest proof for any strictly longer prefix q2 that it holds, and
it verifies: the keys all start with q (they start with q2), they are canonical,
and the subtrie folds to the root because it IS a real subtrie.

THE FALSIFIER, STATED BEFORE THE RUN AND FIXED IN THIS FILE
------------------------------------------------------------
    If the witnessed verifier REJECTS a complete, unforged proof for a deeper
    prefix presented as the answer to a shallower query, then the missing re-walk
    is compensated somewhere else and S36's 37/37 stands as a general claim about
    omission.

It fires if such a proof is ACCEPTED.

WHY THIS IS A SOUNDNESS FINDING AND NOT A TAMPER
------------------------------------------------
`C_replay_proof_is_honest` requires the replayed proof to be BYTE-IDENTICAL to
`prove_completeness(root, q2)`. Nothing is forged, no digest is flipped, no key
is edited. If the control fires, the cheat is a tamper wearing a different name
and the finding is worth less.

THE FIX IS MEASURED, NOT ASSERTED
---------------------------------
`verify_completeness_qbound` below adds the re-walk the other two verifiers
already have, and drops `pf['depth']` -- a prover-supplied integer -- in favour
of the path length the steps themselves imply. Both honest acceptance and cheat
rejection are re-measured under it, because a verifier that rejects everything
scores perfectly on every attack in this file.

  python3 attack.py
"""
import os, sys, json, copy, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
S20 = os.path.join(HERE, '..', 'S20_verify_kinds')
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
sys.path.insert(0, S20)
sys.path.insert(0, HERE)
# H195: THE PIN IS DELIBERATE HERE TOO, AND THE ROW THAT SAID OTHERWISE WAS MINE.
# `verify_kinds` installs S20's byte-pin of the COMMITTED `trie_witness` under the
# bare name, so everything below attacks THAT verifier. That is exactly right for
# this file: the soundness finding it records is ABOUT that verifier, and against
# the live module (post-S37) the replay is rejected and the finding cannot be
# reproduced at all. What was actually wrong is that the artifact never said WHICH
# verifier `committed_` referred to, so a reader after S37 could not tell "the fix
# never landed" from "this measures the code the fix replaced" -- claim decay, not
# a wrong number. `verifier_identity` in the output now answers it.
import verify_kinds as S20M                                               # noqa: E402
USES_S20_PIN = True   # H195: deliberate, and machine-readable
from trie_witness import (build, prove_completeness, verify_completeness,  # noqa: E402
                          prove_membership, verify_membership,
                          prove_non_membership, verify_non_membership,
                          node_hash, fold, desc_hash)
import witnessed_job as S36                                               # noqa: E402
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402

SEED = 20260817
PREFIX_LEN = S36.PREFIX_LEN
JOBS = S36.JOBS


# ------------------------------------------------------------------- the fix
def path_prefix(steps):
    """The key bytes the authentication path itself spells out. This is the
    quantity `pf['depth']` claims to be, derived from the proof instead of
    supplied beside it."""
    return b''.join(prefix + bytes([b]) for (prefix, _t, _p), b in steps)


def verify_completeness_qbound(root_hash, q, pf):
    """`verify_completeness` + the re-walk its two sibling verifiers already do.

    Two changes, both removing a prover-controlled degree of freedom:

      1. the path must spell a PREFIX OF q and must not overshoot it, and the
         rebuilt node's own compressed prefix must carry the REST of q. Together
         these pin the proof to the single node `walk(root, q)` reaches, which is
         what makes the answer set an answer to *this* query.
      2. `pf['depth']` is not read. The build depth is `len(path_prefix(steps))`,
         which the steps already determine.

    The non-COVER branch is delegated unchanged -- it already re-walks.
    """
    if pf is None:
        return False
    if pf.get('kind') != 'cover':
        return verify_completeness(root_hash, q, pf)
    ks = pf['keys']
    if not ks:
        return False
    if any(not k.startswith(q) for k in ks):
        return False
    if list(ks) != sorted(set(ks)):
        return False
    pre = path_prefix(pf['steps'])
    if len(pre) > len(q) or q[:len(pre)] != pre:
        return False                       # the path overshot or diverged from q
    rebuilt = build(sorted(ks), len(pre))
    if not (pre + rebuilt.prefix).startswith(q):
        return False                       # the node does not cover q
    return fold(pf['steps'], rebuilt.h) == root_hash


# --------------------------------------------------------------- the cheat
def deeper_prefix(ks, q, true_answer):
    """The shortest strictly longer prefix whose key set is a STRICT, non-empty
    subset of the answer to q. Returns None when none exists -- which is the
    honest outcome for a query already sitting on a leaf, and those jobs are
    counted rather than skipped silently (A29)."""
    k0 = true_answer[0]
    for L in range(len(q) + 1, len(k0) + 1):
        q2 = k0[:L]
        sub = [k for k in ks if k.startswith(q2)]
        if 0 < len(sub) < len(true_answer):
            return q2, sub
    return None, None


def main():
    keys = S20M.S84M.read_keys(S36.KEYS)
    ks = sorted(set(keys))
    root = build(ks)
    rh = root.h
    stride = max(1, len(ks) // JOBS)
    queries = [k[:PREFIX_LEN] for k in ks[::stride][:JOBS]]

    rows = []
    n_no_deeper = 0
    for q in queries:
        true_pf = prove_completeness(root, q)
        answer = true_pf.get('keys') or []
        if len(answer) < 3:
            continue
        q2, sub = deeper_prefix(ks, q, answer)
        if q2 is None:
            n_no_deeper += 1
            continue

        # THE CHEAT: the honest proof for q2, presented as the answer to q.
        # Built by the same prover call an honest worker would make.
        replay = prove_completeness(root, q2)
        reference = prove_completeness(root, q2)
        unforged = (replay == reference and replay['keys'] == sub)

        _b, h_true = S36.answer_bytes(answer)
        _b, h_liar = S36.answer_bytes(sub)

        honest_env = {'hash': h_true, 'proof': true_pf, 'n': len(answer)}
        liar_env = {'hash': h_liar, 'proof': replay, 'n': len(sub)}

        rows.append({
            'q': q.hex(), 'q2': q2.hex(),
            'answers_true': len(answer), 'answers_claimed': len(sub),
            'omitted': len(answer) - len(sub),
            'unforged': unforged,
            # committed verifier, as S36 ran it
            'witnessed_accepts_replay': S36.witness_verify(rh, q, liar_env),
            'witnessed_accepts_honest': S36.witness_verify(rh, q, honest_env),
            # replication, both worlds
            'replication_independent_catches':
                S36.replicate(honest_env, liar_env)[0] == 'DISAGREE',
            'replication_correlated_catches':
                S36.replicate(liar_env, copy.deepcopy(liar_env))[0] == 'DISAGREE',
            # the fix
            'qbound_accepts_replay':
                verify_completeness_qbound(rh, q, replay) and h_liar == h_liar,
            'qbound_accepts_honest': verify_completeness_qbound(rh, q, true_pf),
        })

    n = len(rows)
    accepted = sum(1 for r in rows if r['witnessed_accepts_replay'])
    omitted_total = sum(r['omitted'] for r in rows)
    answers_total = sum(r['answers_true'] for r in rows)

    # the three tamper classes S36 published, re-run under the FIX, so the fix is
    # not shown to close one hole by opening three.
    tampers_fixed = {}
    for c in ('omit', 'add', 'alter'):
        rej, tn = 0, 0
        for q in queries:
            pf = prove_completeness(root, q)
            if len(pf.get('keys') or []) < 3:
                continue
            tn += 1
            env = S36.make_env(root, q, pf['keys'], cheat=c)
            rej += 0 if verify_completeness_qbound(rh, q, env['proof']) else 1
        tampers_fixed[c] = {'n': tn, 'rejected': rej}

    # IS THE DEFECT SPECIFIC TO THE BRANCH MISSING THE RE-WALK? The same replay
    # shape against the two verifiers that DO re-walk. If those accept too, the
    # finding is about the commitment, not about the missing check.
    #
    # The absent keys are built by flipping the LAST byte of a real key, so each
    # diverges DEEP in the trie at its own node. The first draft of this probe
    # flipped the FIRST byte of two keys; both then diverged at the root, the
    # authentication path was empty, and one honest proof covered them both --
    # correctly. `C_sibling_verifiers_are_not_exposed` refused that run as VOID
    # rather than recording 20/20 as a second finding, which is what A29 is for:
    # the probe had not reached its target.
    kset = set(ks)

    def absent_near(k):
        a = k[:-1] + bytes([k[-1] ^ 0xFF])
        return a if a not in kset else None

    sib = {'membership_replayed': 0, 'membership_n': 0,
           'absence_replayed': 0, 'absence_n': 0,
           'absence_paths_differ': 0}
    for i, r in enumerate(rows[:20]):
        q = bytes.fromhex(r['q'])
        k_true = [k for k in ks if k.startswith(q)][0]
        k_other = [k for k in ks if not k.startswith(q)][0]
        pf_m = prove_membership(root, k_other)
        if pf_m is not None:
            sib['membership_n'] += 1
            # a genuine membership proof for a DIFFERENT key, replayed for k_true
            sib['membership_replayed'] += 1 if verify_membership(rh, k_true, pf_m) else 0
        a1, a2 = absent_near(k_true), absent_near(k_other)
        if a1 is None or a2 is None:
            continue
        pf_a = prove_non_membership(root, a1)
        if pf_a is None:
            continue
        sib['absence_n'] += 1
        # the two absent keys must diverge at DIFFERENT nodes, or one honest
        # proof covers both and nothing is being replayed
        if path_prefix(pf_a['steps']) != path_prefix(prove_non_membership(root, a2)['steps']):
            sib['absence_paths_differ'] += 1
        sib['absence_replayed'] += 1 if verify_non_membership(rh, a2, pf_a) else 0

    fired = accepted > 0
    # WHICH verifier every `committed_` field below is about. Read off the loaded
    # module rather than typed, so it cannot drift from what actually ran.
    import trie_witness as _tw_loaded
    _tw_path = os.path.abspath(_tw_loaded.__file__)
    verifier_identity = {
        'module_path': os.path.relpath(_tw_path, os.path.join(HERE, '..', '..')),
        'sha256': hashlib.sha256(open(_tw_path, 'rb').read()).hexdigest(),
        'is_s20_pin': os.path.realpath(_tw_path) == os.path.realpath(
            os.path.join(S20, 'w2_head', 'trie_witness.py')),
        'note': ('`committed_` here means the verifier THIS FILE ATTACKED, which '
                 'is S20\'s byte-pin of trie_witness at the time the finding was '
                 'made -- NOT whatever is at HEAD now. Against the live module '
                 'post-S37 the replay is rejected, which is the fix working and '
                 'not this measurement changing.'),
    }
    out = {'seed': SEED, 'prefix_len': PREFIX_LEN, 'jobs_attacked': n,
           'verifier_identity': verifier_identity,
           'jobs_with_no_deeper_node': n_no_deeper,
           'committed_verifier_accepts_replay': accepted,
           'committed_verifier_accepts_replay_rate': round(accepted / n, 4) if n else None,
           'answers_true_total': answers_total,
           'answers_omitted_total': omitted_total,
           'omitted_share': round(omitted_total / answers_total, 4) if answers_total else None,
           'worst_job': max(rows, key=lambda r: r['omitted']) if rows else None,
           'replication_independent_catches': sum(1 for r in rows if r['replication_independent_catches']),
           'replication_correlated_catches': sum(1 for r in rows if r['replication_correlated_catches']),
           'qbound_accepts_replay': sum(1 for r in rows if r['qbound_accepts_replay']),
           'qbound_accepts_honest': sum(1 for r in rows if r['qbound_accepts_honest']),
           'tampers_under_fix': tampers_fixed,
           'sibling_verifiers': sib,
           'falsifier_fired': fired,
           'rows': rows}
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    c = Control('C_replay_proof_is_honest',
                'the replayed proof must be BYTE-IDENTICAL to what an honest '
                'prover returns for q2 -- no forged digest, no edited key. If it '
                'is not, this is a tamper under a new name and S36 already '
                'covered tampers',
                null_must_contain='a proof with any field rewritten, which is '
                                  'what all three of S36 tamper classes are',
                can_fail_because='any row where the replay differs from a fresh '
                                 'prove_completeness(root, q2)')
    c.observe(n > 0 and all(r['unforged'] for r in rows),
              {'n': n, 'unforged': sum(1 for r in rows if r['unforged'])})
    C.append(c)

    c = Control('C_replay_actually_omits',
                'the replayed answer must be a STRICT subset of the true answer, '
                'or the probe never reached its target and "accepted" is a '
                'statement about nothing (A29)',
                null_must_contain='a deeper prefix selecting the same key set, '
                                  'which a path-compressed trie produces whenever '
                                  'the node does not branch',
                can_fail_because='any row with omitted == 0, or fewer than 10 '
                                 'jobs surviving the deeper-node filter')
    c.observe(n >= 10 and all(r['omitted'] > 0 for r in rows),
              {'n': n, 'no_deeper_node': n_no_deeper,
               'min_omitted': min((r['omitted'] for r in rows), default=None)})
    C.append(c)

    c = Control('C_fix_does_not_reject_honest',
                'the q-bound verifier must still ACCEPT every honest proof. A '
                'verifier that returns False unconditionally rejects every cheat '
                'in this file and is worthless',
                null_must_contain='a verifier that rejects everything, which '
                                  'scores 100% on the attack and 0% here',
                can_fail_because='any honest proof rejected under the fix')
    c.observe(n > 0 and all(r['qbound_accepts_honest'] for r in rows),
              {'n': n, 'accepted': sum(1 for r in rows if r['qbound_accepts_honest'])})
    C.append(c)

    c = Control('C_fix_keeps_the_three_published_tampers',
                'omit / add / alter must still be rejected under the fix, so the '
                'q-binding is shown not to have replaced one check with another',
                null_must_contain='a verifier that checks only the query binding '
                                  'and not the fold, which would accept all three',
                can_fail_because='any of the three tamper classes rejected < n '
                                 'under the fixed verifier')
    c.observe(all(v['rejected'] == v['n'] and v['n'] > 0
                  for v in tampers_fixed.values()), tampers_fixed)
    C.append(c)

    c = Control('C_sibling_verifiers_are_not_exposed',
                'the same replay shape against verify_membership and '
                'verify_non_membership -- the two that DO re-walk -- must be '
                'REJECTED. If they accepted, the defect would be in the '
                'commitment rather than in the missing check, and the fix would '
                'be aimed at the wrong layer',
                null_must_contain='a verifier that folds to the root and stops, '
                                  'which is exactly what the COVER branch does',
                can_fail_because='either sibling accepting a proof issued for a '
                                 'different key, or the two absent keys sharing '
                                 'a divergence node, where nothing is replayed')
    c.observe(sib['membership_n'] > 0 and sib['absence_n'] > 0 and
              sib['absence_paths_differ'] == sib['absence_n'] and
              sib['membership_replayed'] == 0 and sib['absence_replayed'] == 0, sib)
    C.append(c)

    F = Falsifier('F_missing_rewalk_is_compensated',
                  refutes='this attack: if a complete unforged proof for a deeper '
                          'prefix is REJECTED when presented as the answer to a '
                          'shallower query, S36 37/37 stands as a general claim '
                          'about omission',
                  fires_when='the committed verifier ACCEPTS such a proof',
                  null_must_contain='a genuine subtrie of the committed root, '
                                    'which folds correctly by construction')
    F.observe(fired, {'accepted': accepted, 'n': n,
                      'omitted_share': out['omitted_share']})

    ok, problems = certify(
        HERE, deps=[S20],
        artifacts=[os.path.join(HERE, 'attack.json')],
        controls=C, falsifiers=[F],
        record_name='provenance.attack.json',
        falsifier='the committed completeness verifier rejecting an unforged '
                  'proof for a deeper prefix, which would leave S36 37/37 intact')

    print(json.dumps({k: v for k, v in out.items() if k != 'rows'},
                     indent=2, sort_keys=True)[:2000])
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
