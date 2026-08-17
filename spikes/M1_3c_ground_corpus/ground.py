#!/usr/bin/env python3
"""M1.3c — is "which is the entire corpus" true?

THE SENTENCE UNDER TEST
-----------------------
`spikes/M1_3_worker/WORKER_RESULT.md:73`, closing what `WORK_QUEUE.md` M1.1 calls
the largest open M1 issue -- process-per-job against WorkManager's process reuse:

    "Process reuse is safe for GROUND-RESULT jobs, which is the entire corpus.
     It remains unsafe for the aliasing class, whose admission gate is still open."

The load-bearing clause is the parenthetical one. Derivation (2) of the
process-per-job requirement is that `NEXT_VARIABLE_ID` is process-global, so job
N occupies a different variable-id space than job 1. If a result is ground it
contains no variable, so no printed id, so nothing for the id space to move --
and `canon` at the comparison boundary handles the rest. If ANY admitted job can
produce a non-ground result, that derivation is live and the requirement stands.

The sentence is self-authored, was never measured, and `HANDOFF.md` NEXT 3 says
in as many words: *verify before spending a cycle.*

THE FALSIFIER, STATED BEFORE THE RUN
------------------------------------
    If any admitted program's recorded result is NON-GROUND -- contains a token
    whose printed form comes from the process-global variable counter -- then
    process reuse is not safe for this corpus and M1.1's largest open issue is
    NOT closed by M1.3b.

AND THE SECOND QUESTION, WHICH IS THE ONE CORPUS_COMPOSITION ALREADY TAUGHT
---------------------------------------------------------------------------
`spikes/M1_8_quorum3/CORPUS_COMPOSITION.md` refuted "64/64 agreement is evidence
of determinism" by counting what the corpus COULD have shown: 38 of 64 never
execute the code under test. The same question has to be asked here before the
answer is believed. A program that dies at its first `import!` produces the
resolver's error string; that string is ground whatever the program would have
returned, so it is not evidence that the PROGRAM is ground-result. So this
measures two different things and refuses to merge them:

    observed_ground   -- the recorded result contains no variable
    could_be_observed -- the program actually executed, so its result is
                         evidence about the program rather than about the
                         module resolver

WHAT COUNTS AS A VARIABLE
-------------------------
MeTTa prints an unbound variable as `$name`, and a fresh one produced by the
interpreter as `$_<n>` / `$v<n>` where <n> comes from the process-global counter.
The scan is for a `$` beginning a token, and the SOURCE scan is separate from the
RESULT scan because a program can mention variables in rules that never survive
into a result -- which is exactly the distinction that makes the claim non-
obvious, and getting it wrong in either direction is A30 (a name grep cannot tell
a word from a concept). So the source scan is reported as an upper bound and
never as the verdict.

  python3 ground.py
"""
import os, sys, re, json, glob
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'harness'))
from kfcheck import certify                                               # noqa: E402
from provenance import Control, Falsifier                                 # noqa: E402

Q3 = os.path.join(HERE, '..', 'M1_8_quorum3')
RESULT_JSON = os.path.join(Q3, 'result.json')
STORE = os.path.join(Q3, 'run', 'store', 'blobs')

# A token that STARTS with $ -- MeTTa's variable sigil. Anchored on a token
# boundary so `a$b` and a `$` inside a string literal's middle do not count.
VAR = re.compile(r'(?<![\w$])\$[A-Za-z_][\w-]*|(?<![\w$])\$_?\d+')
RESOLVER_ERR = 'Failed to resolve module'


def blob_for(cid):
    hits = glob.glob(os.path.join(STORE, '*', cid))
    return hits[0] if hits else None


def main():
    d = json.load(open(RESULT_JSON))
    rows = d['rows']

    per = []
    for r in rows:
        env = r['envelopes'][0]
        text = env.get('results_text', '') or ''
        src_path = blob_for(env.get('shard_cid', ''))
        src = open(src_path, encoding='utf-8', errors='replace').read() if src_path else None

        executed = bool(text.strip()) and RESOLVER_ERR not in text
        res_vars = sorted(set(VAR.findall(text)))
        src_vars = sorted(set(VAR.findall(src))) if src is not None else None

        per.append({
            'program': r['program'],
            'verdict': r['verdict'],
            'n_results': env.get('n_results'),
            'executed_metta': executed,
            'result_is_ground': not res_vars,
            'result_vars': res_vars[:8],
            'source_found': src is not None,
            'source_mentions_vars': (bool(src_vars) if src_vars is not None else None),
            'source_var_count': (len(src_vars) if src_vars is not None else None),
        })

    executed = [p for p in per if p['executed_metta']]
    non_ground = [p for p in per if not p['result_is_ground']]
    non_ground_exec = [p for p in non_ground if p['executed_metta']]
    src_seen = [p for p in per if p['source_found']]
    src_vars = [p for p in src_seen if p['source_mentions_vars']]
    # of the programs that did NOT execute, how many have a source that mentions
    # a variable at all -- i.e. how much of the claim is untested but at risk
    unexecuted_at_risk = [p for p in per
                          if not p['executed_metta'] and p['source_mentions_vars']]

    fired = bool(non_ground_exec)

    C = [
        Control('C_scanner_finds_variables',
                'the variable scanner must be able to see a variable at all; a '
                'regex that matched nothing would report a perfectly ground '
                'corpus and be indistinguishable from the claim being true',
                null_must_contain='a corpus whose sources mention no variables, '
                                  'against which the scanner cannot be exercised',
                can_fail_because='if VAR did not match MeTTa syntax, or the blobs '
                                 'were unreadable, source_var_count would be 0 '
                                 'everywhere and the scan would prove nothing'),
        Control('C_sources_resolve',
                'every program must be matched to its shard blob by CID, or the '
                'source half of this measurement is about a subset nobody named',
                null_must_contain='a store missing the shards, giving no sources',
                can_fail_because='the CIDs in result.json could name blobs this '
                                 'store does not hold, e.g. a run against a store '
                                 'that has since been pruned'),
        Control('C_execution_split_reproduces',
                'the executed/not-executed split must reproduce CORPUS_COMPOSITION '
                "'s independently published 26 of 64, or this file's own notion of "
                '"executed" is a second, unvalidated instrument',
                null_must_contain='a split that disagrees with the published one',
                can_fail_because='keying "executed" off the resolver error string '
                                 'could miscount the 4 error-only programs, which '
                                 'DID execute and whose result is an assertion Error'),
    ]
    C[0].observe(sum(p['source_var_count'] or 0 for p in src_seen) > 0,
                 {'programs_with_source': len(src_seen),
                  'sources_mentioning_a_variable': len(src_vars),
                  'total_distinct_vars_seen': sum(p['source_var_count'] or 0
                                                  for p in src_seen)},
                 'the scanner is exercised against real MeTTa source')
    C[1].observe(len(src_seen) == len(per) and len(per) > 0,
                 {'programs': len(per), 'sources_resolved': len(src_seen)},
                 'CID to blob resolution over the committed store')
    C[2].observe(len(executed) == 26,
                 {'executed_here': len(executed), 'published': 26,
                  'by_verdict': dict(Counter(p['verdict'] for p in per))},
                 'against CORPUS_COMPOSITION.md 26/64')

    F = Falsifier('F_corpus_not_all_ground',
                  refutes='the sentence "process reuse is safe for ground-result '
                          'jobs, WHICH IS THE ENTIRE CORPUS" -- and with it '
                          "M1.3b's closure of M1.1's largest open issue",
                  fires_when='any program that actually executed MeTTa recorded a '
                             'result containing a variable token',
                  null_must_contain='a corpus in which some executed program does '
                                    'produce a non-ground result')
    F.observe(fired,
              {'executed': len(executed),
               'non_ground_results': len(non_ground),
               'non_ground_among_executed': len(non_ground_exec),
               'examples': [p['program'] for p in non_ground_exec][:5]},
              'variables surviving into a recorded result')

    out = {
        'sentence_under_test': 'spikes/M1_3_worker/WORKER_RESULT.md:73 — '
                               '"Process reuse is safe for ground-result jobs, '
                               'which is the entire corpus."',
        'programs': len(per),
        'executed_metta': len(executed),
        'results_ground': len(per) - len(non_ground),
        'results_non_ground': len(non_ground),
        'non_ground_among_executed': len(non_ground_exec),
        'falsifier_fired': fired,
        'evidence_base': {
            'tested': len(executed),
            'untestable': len(per) - len(executed),
            'why_untestable': 'a program that never reached evaluation recorded '
                              'the module resolver error or nothing at all; that '
                              'string is ground whatever the program would have '
                              'returned, so it is evidence about the resolver and '
                              'not about the program (CORPUS_COMPOSITION.md, '
                              'family A)',
            'untested_whose_source_mentions_a_variable':
                len(unexecuted_at_risk),
            'untested_at_risk_examples': [p['program'] for p in unexecuted_at_risk][:10],
        },
        'source_scan_is_an_upper_bound': 'a source mentioning $x may bind it in a '
                                         'rule that never surfaces in a result; '
                                         'this count bounds exposure and is never '
                                         'the verdict (A30)',
        'sources_mentioning_a_variable': len(src_vars),
        'per_program': per,
    }
    with open(os.path.join(HERE, 'ground.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    ok, problems = certify(
        HERE, deps=[Q3],
        artifacts=[os.path.join(HERE, 'ground.json')],
        controls=C, falsifiers=[F],
        falsifier='any executed program records a result containing a variable')

    print(json.dumps({k: v for k, v in out.items() if k != 'per_program'},
                     indent=2, sort_keys=True))
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
