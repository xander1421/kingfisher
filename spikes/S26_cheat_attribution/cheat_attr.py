#!/usr/bin/env python3
"""S26 — the quorum catches a cheat. Can it name the cheater?

M1-DEMO (§8) item 5 is *"byte-compare verdicts incl. one injected cheat caught
and one deterministic-fault job agreed and 'paid' in points"*. The
deterministic-fault half exists: `(flip)` is the corpus's own positive control
and M1.8 records it refused. The injected-cheat half has never been run.

WHAT READING THE CODE SAYS BEFORE ANY MEASUREMENT
-------------------------------------------------
`q3.py::adjudicate` returns `(verdict, key, agree_count, dispatched, returned,
domains)`. It computes the majority key with `Counter(live).most_common(1)[0]`
and **never returns which envelope disagreed**. `test_adjudicate.py` asserts
`adj([ok, ok, bad])[0] == 'MAJORITY'` -- the verdict, not the defendant. A
protocol that pays or slashes cannot act on a verdict with no defendant.

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If the dissenting worker IS identifiable from what the pipeline already
    records, then the gap is REPORTING and not evidence, and the fix is a field
    rather than a protocol change.

`result.json` rows carry the whole `envelopes` list with a `worker` field on
each, so this is decidable on committed artifacts -- no device, no timing, and
`quiet.sh` refuses on this host anyway.

THE SECOND MEASUREMENT, BECAUSE THE TWO THREAT MODELS GET CONFLATED
-------------------------------------------------------------------
A LYING MEMBER (this spike: an envelope altered after execution) and a WRONG
REPLICA (M1.9: a binary whose `<` is wrong at every boundary) are different
attacks. Byte compare is certain against the first and, as M1.9 measured, blind
to the second at 0/64. Both numbers belong in one table, because "quorum catches
cheats" is said about both and is true of one.

NO POINTS ARITHMETIC IS PUBLISHED HERE. `specs/D3_economics.md` deliberately
carries no stake floor, no `R` and no price per job, so any slashing number
would be invented and not derived -- A26, a knob is not a mechanism.

  python3 cheat_attr.py
"""
import os, sys, json, copy
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
Q3 = os.path.join(ROOT, 'spikes', 'M1_8_quorum3')
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402

# THE ARTIFACT IS PINNED, because the working-tree copy is not the committed one.
# `spikes/M1_8_quorum3/` has 256 modified files right now -- another lane's run
# in flight -- and `certify` refuses a dirty dependency (A24). So the source is
# `result.head.json`, a byte-pin of blob e1d3bf85 taken with `git show HEAD:...`,
# and `C_worktree_delta` reports what the working-tree copy differs by rather
# than either trusting it or pretending it is not there.
RESULT = os.path.join(HERE, 'result.head.json')
RESULT_WORKTREE = os.path.join(Q3, 'result.json')
# M1.9's measured detection rates for a WRONG REPLICA, quoted from its RESULT.md
# rather than recomputed here: this spike does not re-run mutation testing.
M1_9 = {'wrong_minus': 4, 'wrong_less_than': 0, 'resolver_message': 24,
        'extra_stdlib_rule': 0, 'of': 64}


def load_q3(path):
    """q3.py's OWN `key` function, executed rather than reimplemented.

    The first version of this file reimplemented the agreement key from reading
    the code and got it wrong on all 64 rows -- `key()` prefers a CANONICALISED
    `results_text` and falls back to `sorted_hash` only when there is none, and
    it returns None for an empty result member under a non-failed status.
    `C_key_matches_committed` caught it, which is why that control is gating.

    `q3.py` ends in a bare `main()` call, so a plain import would dispatch jobs
    to a phone. The trailing call is stripped and the ANCHOR IS ASSERTED: a
    strip that matched nothing would exec the pipeline instead (CLAUDE.md's
    editing rule). `ALPHA` is then set from the artifact's own
    `normalisation` field rather than from this file's opinion.
    """
    src = open(path).read()
    anchor = '\nmain()\n'
    if not src.endswith(anchor):
        raise SystemExit('S26: q3.py does not end in a bare main() call -- the '
                         'strip anchor is gone, and exec would run the pipeline')
    ns = {'__name__': 'q3_loaded', '__file__': os.path.join(Q3, 'q3.py')}
    sys.path.insert(0, Q3)
    exec(compile(src[:-len(anchor)], path, 'exec'), ns)
    return ns


# PINNED, for the same reason result.head.json is: `q3.py` is uncommitted-
# modified in the working tree. The in-flight edit is inside `main()` (two
# argparse options and a `preflight.Policy` call) and does not touch `key()` --
# but "I read the diff and it looked unrelated" is not evidence, so
# `C_worktree_key_agrees` re-derives all 64 keys with the working-tree copy and
# they must match.
Q3_PIN = os.path.join(HERE, 'q3_head.py')
Q3NS = load_q3(Q3_PIN)


def envkey(e):
    return Q3NS['key'](copy.deepcopy(e)) if e is not None else None


def majority(envs):
    ks = [envkey(e) for e in envs]
    live = [k for k in ks if k is not None]
    if not live:
        return None, 0, ks
    k, n = Counter(live).most_common(1)[0]
    return k, n, ks


def dissenters(envs):
    """WHO disagreed -- the field adjudicate does not return."""
    k, _n, ks = majority(envs)
    return [e.get('worker') for e, kk in zip(envs, ks) if kk != k]


def cheat(env):
    """A lying member: same worker, same status, one byte flipped in the field
    the agreement key actually reads.

    `key()` prefers `results_text` and falls back to `sorted_hash`, so flipping
    the hash alone would leave the key untouched on the 200 envelopes that carry
    text -- a cheat the quorum cannot see is not a cheat that went undetected,
    it is a probe that missed (A29). `C_cheat_moves_the_key` counts the ones
    where nothing can be flipped instead of skipping them silently.

    It does not touch the binary, so this is the LIAR threat model, not M1.9's
    wrong-replica one.
    """
    bad = copy.deepcopy(env)
    txt = bad.get('results_text')
    if txt:
        bad['results_text'] = ('X' + txt[1:]) if txt[0] != 'X' else ('Y' + txt[1:])
        return bad
    h = bad.get('sorted_hash')
    if h:
        bad['sorted_hash'] = ('0' if h[0] != '0' else '1') + h[1:]
        return bad
    return None


def main():
    res = json.load(open(RESULT))
    rows = res['rows']
    workers = res['workers']

    # --- C1 gating: re-derive every committed row's key and verdict inputs ----
    key_ok, agree_ok, checked = 0, 0, 0
    for r in rows:
        envs = r['envelopes']
        k, n, _ks = majority(envs)
        checked += 1
        if (list(k) if k else None) == r['key']:
            key_ok += 1
        if n == r['agree']:
            agree_ok += 1

    # --- the measurement -----------------------------------------------------
    per_worker = {w: {'cheats_injected': 0, 'named': 0, 'unnamed': 0}
                  for w in workers}
    expressible, inexpressible, verdict_moved = 0, 0, 0
    detail = []
    for r in rows:
        envs = r['envelopes']
        for i, e in enumerate(envs):
            if e is None:
                continue
            w = e.get('worker')
            bad = cheat(e)
            if bad is None or envkey(bad) == envkey(e):
                # A cheat that does not move the key proves nothing about
                # detection -- A29, the probe must reach its target.
                inexpressible += 1
                continue
            expressible += 1
            per_worker.setdefault(w, {'cheats_injected': 0, 'named': 0,
                                      'unnamed': 0})
            per_worker[w]['cheats_injected'] += 1
            tampered = list(envs)
            tampered[i] = bad
            k0, n0, _ = majority(envs)
            k1, n1, _ = majority(tampered)
            if n1 < n0:
                verdict_moved += 1
            named = dissenters(tampered)
            if named == [w]:
                per_worker[w]['named'] += 1
            else:
                per_worker[w]['unnamed'] += 1
                detail.append({'program': r['program'], 'worker': w,
                               'named': named, 'agree_before': n0,
                               'agree_after': n1})

    total = sum(v['cheats_injected'] for v in per_worker.values())
    named = sum(v['named'] for v in per_worker.values())
    fired = named < total            # falsifier: attribution NOT derivable

    out = {
        'source': os.path.relpath(RESULT, ROOT),
        'programs': len(rows), 'workers': workers,
        'reproduced': {'rows_checked': checked, 'key_matches': key_ok,
                       'agree_matches': agree_ok},
        'cheats': {'injected': total, 'attributed_to_exactly_one_worker': named,
                   'not_attributed': total - named,
                   'agreement_count_dropped': verdict_moved,
                   'envelopes_where_a_cheat_is_inexpressible': inexpressible},
        'per_worker': per_worker,
        'unattributed_detail': detail[:10],
        'wrong_replica_for_comparison_M1_9': M1_9,
        'falsifier_fired': fired,
    }
    with open(os.path.join(HERE, 'cheat_attr.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []

    c = Control('C_key_matches_committed',
                'every committed row\'s key and agreement count must be '
                're-derived here before any tampering, or this spike is '
                'adjudicating with a different key function than the pipeline '
                'that produced the artifact',
                null_must_contain='a key function differing in any field -- '
                                  'status, fuel, hash or result count -- would '
                                  'show up as a mismatched row',
                can_fail_because='any of the 64 rows disagrees on key or on '
                                 'agreement count')
    c.observe(key_ok == checked and agree_ok == checked and checked == 64,
              out['reproduced'])
    C.append(c)

    c = Control('C_cheat_moves_the_key',
                'A29: a cheat that leaves the agreement key unchanged tests '
                'nothing. Every injected cheat must change the envelope key, '
                'and envelopes where it cannot are counted rather than skipped '
                'silently',
                null_must_contain='an envelope with no hash to flip, which is '
                                  'counted as inexpressible instead of passing',
                can_fail_because='no cheat was expressible on any envelope, or '
                                 'a tampered envelope keyed identically to its '
                                 'original')
    c.observe(total > 0, {'expressible': expressible, 'inexpressible': inexpressible,
                          'injected': total})
    C.append(c)

    c = Control('C_agreement_drops',
                'a lying member must cost the quorum an agreeing seat -- if the '
                'majority count did not move, byte compare did not see the lie '
                'and "caught" would be a claim about nothing',
                null_must_contain='a tampered envelope that still keys with the '
                                  'majority, which is what a cheat on a field '
                                  'outside the key would give',
                can_fail_because='the agreement count is unchanged for any '
                                 'injected cheat')
    c.observe(verdict_moved == total,
              {'agreement_dropped': verdict_moved, 'injected': total})
    C.append(c)

    # C4 -- the pinned instrument against the working-tree one.
    wt_ns = load_q3(os.path.join(Q3, 'q3.py'))
    wt_keys = []
    for r in rows:
        ks = [wt_ns['key'](copy.deepcopy(e)) if e is not None else None
              for e in r['envelopes']]
        live = [k for k in ks if k is not None]
        wt_keys.append(Counter(live).most_common(1)[0][0] if live else None)
    pinned_keys = []
    for r in rows:
        k, _n, _ks = majority(r['envelopes'])
        pinned_keys.append(k)
    c = Control('C_worktree_key_agrees',
                'the published numbers come from a byte-pin of the COMMITTED '
                'q3.py because the working-tree copy is uncommitted-modified. '
                'The working-tree key function must return the same 64 majority '
                'keys, or the two are not the same adjudicator and reading the '
                'diff was not evidence',
                null_must_contain='an in-flight edit that touched key() or its '
                                  'canonicalisation would move these keys',
                can_fail_because='any of the 64 majority keys differs between '
                                 'the pinned and working-tree q3.py')
    c.observe(wt_keys == pinned_keys,
              {'rows': len(rows),
               'identical': sum(1 for a, b in zip(wt_keys, pinned_keys) if a == b),
               'pinned': os.path.relpath(Q3_PIN, ROOT)})
    C.append(c)

    F = Falsifier('F_attribution_needs_a_protocol_change',
                  refutes='the reading that the pipeline cannot name a cheater: '
                          'if every injected cheat is attributable from the '
                          'recorded envelopes, the gap is reporting and the fix '
                          'is a field',
                  fires_when='any injected cheat cannot be attributed to exactly '
                             'one worker from what result.json already records',
                  null_must_contain='a corpus where two workers key identically '
                                    'to each other and not to the majority, '
                                    'which would name two defendants for one lie')
    F.observe(fired, {'injected': total, 'attributed': named,
                      'unattributed': total - named})

    ok, problems = certify(
        HERE, deps=[],
        no_deps_reason='both inputs are BYTE-PINNED into this directory and '
                       'hashed as artifacts -- q3_head.py (blob of HEAD\'s '
                       'q3.py) and result.head.json (blob e1d3bf85) -- because '
                       'spikes/M1_8_quorum3 has 256 modified files from another '
                       'lane\'s in-flight run and a dep-dir staleness check '
                       'would be judging their work, not this run\'s inputs. '
                       'C_worktree_key_agrees measures the working-tree copy '
                       'rather than assuming the difference is irrelevant.',
        artifacts=[os.path.join(HERE, 'cheat_attr.json'),
                   os.path.join(HERE, 'result.head.json'),
                   os.path.join(HERE, 'q3_head.py')],
        controls=C, falsifiers=[F],
        falsifier='an injected cheat that cannot be attributed to exactly one '
                  'worker from the envelopes result.json already records, which '
                  'would make attribution a protocol change rather than a field')

    print(json.dumps({k: out[k] for k in
                      ('reproduced', 'cheats', 'per_worker',
                       'wrong_replica_for_comparison_M1_9', 'falsifier_fired')},
                     indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
