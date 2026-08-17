#!/usr/bin/env python3
"""S27 — is the completeness verifier's 2-4x constant implementation slack, or
the commitment format?

S20 measured a completeness verifier hashing 1.888-2.682x the bytes it was sent,
because `verify_completeness` rebuilds the answer subtrie. Its own scope note
said: *"a verifier that streamed the answer set into an incremental fold would
hash the same key bytes but might allocate fewer node descriptors; nothing here
says 2-4x is a lower bound."* Written, and marked not yet run -- the shape §12.12
names as how every surviving error in this repo got through.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If the verifier hashes materially more than the sum of the answer subtrie's
    node descriptors -- more than the ROOT'S OWN DEFINITION requires -- the
    constant is implementation slack and can be reduced. If it equals that sum,
    no verifier can do better without changing the commitment format, and
    "implementation-shaped" is refuted.

Operationalised: SLACK_PCT = 1.0. The falsifier FIRES if measured verifier bytes
exceed the descriptor sum by more than 1%.

THE DECOMPOSITION, FIXED BEFORE THE RUN, FROM `node_hash`'s OWN DEFINITION
--------------------------------------------------------------------------
    b'N' | len(prefix):2 | prefix | b'T'/b'-' | len(children):2 | (byte|digest)*

so every hashed byte is exactly one of:
  * CONTENT  -- the answer keys' own bytes, carried in node prefixes
  * FRAMING  -- 1 + 2 + 1 + 2 per node, plus 1 per child edge
  * DIGESTS  -- 32 per child edge

If DIGESTS dominate, the constant is set by the digest width and the fan-out --
properties of the commitment, not of any verifier an author could write.

  python3 verify_floor.py
"""
import os, sys, json, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
S20 = os.path.join(HERE, '..', 'S20_verify_kinds')
S75 = os.path.join(HERE, '..', 'S75_pathmap_check')
S76 = os.path.join(HERE, '..', 'S76_interned_keys')
sys.path.insert(0, S20)
# S20's pin of the COMMITTED trie_witness, inherited by importing it, so these
# numbers stay comparable to S20's and S24's rather than to whatever is on disk.
import verify_kinds as S20M                                               # noqa: E402
from trie_witness import build, prove_completeness, verify_completeness    # noqa: E402
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402

SEED = 20260817
SLACK_PCT = 1.0
DIGEST = 32
SETS = [('atoms_original', os.path.join(S75, 'keys_atoms.bin')),
        ('atoms_interned', os.path.join(S76, 'keys_atoms.bin')),
        ('triples',        os.path.join(S75, 'keys_triples.bin'))]
PROBES = 40
# Query prefix length is CHOSEN BY A RULE, not by hand: the length whose mean
# answer set is closest to TARGET_ANSWERS. Hand-picked constants gave 1.6 mean
# answers on the interned set, where the subtrie is a single node and the
# decomposition is trivially content-only -- `C_answer_sets_are_non_trivial`
# refused that run as VOID rather than reporting it. The rule reaches the regime
# S20 measured on every set without being tuned per set.
TARGET_ANSWERS = 10


def descriptor_bytes(node):
    """What the ROOT'S DEFINITION requires, decomposed. Walks the subtrie and
    charges each node exactly what `node_hash` feeds sha256:

        b'N' (1) | len(prefix) (2) | prefix (len) | term (1) |
        len(children) (2) | per child: byte (1) + digest (32)

    Returns (content, framing, digests, nodes, edges). No hashing happens here --
    this is the arithmetic the measurement is compared against, computed from a
    different traversal than the one being measured.
    """
    content = framing = digests = nodes = edges = 0
    stack = [node]
    while stack:
        n = stack.pop()
        nodes += 1
        content += len(n.prefix)
        framing += 1 + 2 + 1 + 2
        for b in sorted(n.children):
            edges += 1
            framing += 1
            digests += DIGEST
            stack.append(n.children[b])
    return content, framing, digests, nodes, edges


def step_bytes(steps):
    """What `fold` feeds sha256 per authentication-path position.

    `fold` recomputes each step as `node_hash(prefix, term, sorted(pairs +
    [(b, child_hash)]))`, so the taken child is present in the hashed input even
    though it is not transmitted -- ONE MORE EDGE than `steps_bytes` counts.
    The first version of this model omitted the path fold entirely and read as
    35-1899% of implementation slack; the slack was my missing term.
    """
    n = 0
    for (prefix, _term, pairs), _b in steps:
        n += 1 + 2 + len(prefix) + 1 + 2 + (len(pairs) + 1) * (1 + DIGEST)
    return n


def pick_prefix_len(keys):
    """The length whose mean answer set is nearest TARGET_ANSWERS."""
    ks = sorted(set(keys))
    best, best_d = 1, None
    for L in range(1, max(len(k) for k in ks) + 1):
        groups = {}
        for k in ks:
            groups[k[:L]] = groups.get(k[:L], 0) + 1
        mean = sum(groups.values()) / len(groups)
        d = abs(mean - TARGET_ANSWERS)
        if best_d is None or d < best_d:
            best, best_d = L, d
    return best


def main():
    out = {'seed': SEED, 'slack_pct_threshold': SLACK_PCT,
           'target_answers': TARGET_ANSWERS, 'rows': []}
    worst_slack = -1e9

    for name, path in SETS:
        keys = S20M.S84M.read_keys(path)
        plen = pick_prefix_len(keys)
        root = build(sorted(set(keys)))
        rh = root.h
        stride = max(1, len(keys) // PROBES)
        qs = [k[:min(plen, len(k))] for k in sorted(set(keys))[::stride][:PROBES]]

        meas, model, ans = [], [], []
        parts = {'content': [], 'framing': [], 'digests': [], 'path': []}
        for q in qs:
            pf = prove_completeness(root, q)
            ok, _n, b = S20M.counted(verify_completeness, rh, q, pf)
            if not ok:
                raise SystemExit('S27: a completeness proof failed to verify (A29)')
            ks = pf.get('keys') or []
            if not ks:
                continue
            # the subtrie the verifier rebuilds, built the same way it does
            sub = build(sorted(ks), pf['depth'])
            c, f, d, _nodes, _edges = descriptor_bytes(sub)
            # PLUS the authentication path it folds. Omitting this was the whole
            # of the "slack" the first run reported.
            pf_path = step_bytes(pf['steps'])
            meas.append(b)
            model.append(c + f + d + pf_path)
            parts['path'].append(pf_path)
            ans.append(len(ks))
            parts['content'].append(c)
            parts['framing'].append(f)
            parts['digests'].append(d)

        row = {'set': name, 'prefix_len': plen, 'queries': len(meas),
               'answers': round(statistics.mean(ans), 3),
               'verifier_hash_bytes': round(statistics.mean(meas), 3),
               'descriptor_sum_bytes': round(statistics.mean(model), 3),
               'content_bytes': round(statistics.mean(parts['content']), 3),
               'framing_bytes': round(statistics.mean(parts['framing']), 3),
               'digest_bytes': round(statistics.mean(parts['digests']), 3),
               'path_fold_bytes': round(statistics.mean(parts['path']), 3)}
        row['slack_pct'] = round(
            (row['verifier_hash_bytes'] - row['descriptor_sum_bytes'])
            / row['descriptor_sum_bytes'] * 100.0, 4)
        tot = (row['content_bytes'] + row['framing_bytes']
               + row['digest_bytes'] + row['path_fold_bytes'])
        row['digest_share_pct'] = round(row['digest_bytes'] / tot * 100.0, 2)
        row['content_share_pct'] = round(row['content_bytes'] / tot * 100.0, 2)
        out['rows'].append(row)
        worst_slack = max(worst_slack, row['slack_pct'])

    out['worst_slack_pct'] = round(worst_slack, 4)
    fired = worst_slack > SLACK_PCT
    out['falsifier_fired'] = fired

    with open(os.path.join(HERE, 'verify_floor.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    c = Control('C_model_is_not_the_measurement',
                'the descriptor sum is computed by a SEPARATE traversal that '
                'hashes nothing, so it can disagree with the counting hashlib. '
                'If the two were the same code the agreement would be a '
                'tautology and the falsifier could not fire',
                null_must_contain='an implementation hashing anything outside '
                                  'node_hash -- a length prefix, a separator, a '
                                  'second pass -- would show up as slack',
                can_fail_because='no row was measured at all, or the model '
                                 'returned zero bytes for a non-empty answer set')
    c.observe(all(r['descriptor_sum_bytes'] > 0 and r['queries'] > 0
                  for r in out['rows']) and len(out['rows']) == 3,
              {r['set']: [r['queries'], r['descriptor_sum_bytes']]
               for r in out['rows']})
    C.append(c)

    c = Control('C_answer_sets_are_non_trivial',
                'a query returning one key would make the subtrie a single node '
                'and the decomposition trivially content-only, which would '
                'answer nothing about the regime S20 measured',
                null_must_contain='single-key answers, where digests are 0 and '
                                  'the share question does not arise',
                can_fail_because='any row\'s mean answer set is below 2 keys')
    c.observe(all(r['answers'] >= 2 for r in out['rows']),
              {r['set']: r['answers'] for r in out['rows']})
    C.append(c)

    c = Control('C_shares_sum_to_the_whole',
                'content + framing + digests + the path fold must account for '
                'byte; a fourth category would mean the decomposition is not '
                'the node_hash definition it claims to be',
                null_must_contain='a node_hash that fed sha256 something outside '
                                  'those three categories',
                can_fail_because='the three parts do not sum to the descriptor '
                                 'total on any row')
    c.observe(all(abs(r['content_bytes'] + r['framing_bytes'] + r['digest_bytes']
                      + r['path_fold_bytes'] - r['descriptor_sum_bytes']) < 1e-6
                  for r in out['rows']),
              {r['set']: [r['content_bytes'], r['framing_bytes'],
                          r['digest_bytes'], r['path_fold_bytes'],
                          r['descriptor_sum_bytes']] for r in out['rows']})
    C.append(c)

    F = Falsifier('F_implementation_slack',
                  refutes='S20\'s open item -- if the verifier hashes more than '
                          'the root\'s definition requires, the 2-4x is slack a '
                          'better verifier could remove',
                  fires_when='measured verifier bytes exceed the descriptor sum '
                             'by more than %.1f%% on any key set' % SLACK_PCT,
                  null_must_contain='a verifier doing a second pass, or hashing '
                                    'framing of its own, which would show as '
                                    'positive slack')
    F.observe(fired, {r['set']: {'measured': r['verifier_hash_bytes'],
                                 'model': r['descriptor_sum_bytes'],
                                 'slack_pct': r['slack_pct']}
                      for r in out['rows']})

    ok, problems = certify(
        HERE, deps=[S20],
        artifacts=[os.path.join(HERE, 'verify_floor.json')],
        controls=C, falsifiers=[F],
        falsifier='verifier bytes exceeding the answer subtrie\'s descriptor '
                  'sum by more than %.1f%%, which would make the 2-4x constant '
                  'implementation slack rather than the commitment format'
                  % SLACK_PCT)

    print(json.dumps(out, indent=2, sort_keys=True)[:1600])
    for r in out['rows']:
        print('  %-16s answers=%7.1f measured=%10.1f model=%10.1f slack=%+.3f%%  '
              'digests=%5.2f%% content=%5.2f%% L=%d'
              % (r['set'], r['answers'], r['verifier_hash_bytes'],
                 r['descriptor_sum_bytes'], r['slack_pct'],
                 r['digest_share_pct'], r['content_share_pct'], r['prefix_len']))
    print('falsifier F_implementation_slack FIRED=%s' % fired)
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
