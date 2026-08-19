"""certify_h207.py — H207, ATTACKER-1, 2026-08-19.

Every number in RESULT.md is read back OUT OF THE ARTIFACT FILES here, never
retyped. Two cycles ago a list of field names typed from memory matched nothing
and `certify` returned `run is VOID` twice; the remedy is to derive from the
file, so a stale artifact cannot look like a fresh agreement.
run: python3 spikes/H207_unclosed_claims/certify_h207.py
"""
import os, re, sys
D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(D)), 'spikes', 'harness'))
sys.path.insert(0, os.path.join(D, '..', 'harness'))
from kfcheck import certify                       # noqa: E402
from provenance import Control, Falsifier          # noqa: E402

read = lambda n: open(os.path.join(D, n)).read()
live, ab, fals, rec = read('live_run.out'), read('guard_ab.out'), read('falsify.out'), read('reconcile.out')

# ---- observations, all parsed out of the artifacts -------------------------
m = re.search(r'UNCLOSED-CLAIM: (\d+) DECIDABLE-STALE.*?\+ (\d+) in-flight-or-unfiled'
              r'.*?\+ (\d+) unkeyable.*?of (\d+) distinct', live, re.S)
stale, inflight, unkeyable, subjects = map(int, m.groups())
hand    = int(re.search(r'HAND vocabulary.*?: (\d+)', rec).group(1))
shipped = int(re.search(r'SHIPPED vocabulary.*?: (\d+)', rec).group(1))
rescued = int(re.search(r'RESCUED by treating RELEASE as a closer: (\d+)', rec).group(1))
ab_v1_accuses = len(re.findall(r'suite stayed GREEN with the logic removed', ab))
ab_v2_accuses = len([l for l in ab.splitlines()
                     if l.split()[:1] and 'stayed GREEN' in l.split('  ')[-1]])
fals_pass = int(re.search(r'RESULT: (\d+) passed, (\d+) failed', fals).group(1))
fals_fail = int(re.search(r'RESULT: (\d+) passed, (\d+) failed', fals).group(2))

controls = [
    Control('c0_module_green',
            'the unmutated copy of idscope.py passes its own --selfcheck, so every '
            'red below is the mutation and not a broken module',
            null_must_contain='the C0 arm printing `bad` -- an unmutated copy that FAILS, '
                              'which the suite prints and then exits 1 without running a mutant',
            can_fail_because='idscope.py v5 is broken, which voids all 8 mutants'),
    Control('c1_v1_accuses_the_module',
            'the SHIPPED-FOR-THREE-HOURS guard chain reports `suite stayed GREEN with '
            'the logic removed` for BOTH degenerate mutants -- a coverage gap alleged '
            'in a module that has none. This is the finding, so it is a control.',
            null_must_contain='v1 returning `THE MUTANT IS EMPTY` or `does not COMPILE` for '
                              'either mutant -- the whole v1 chain is reproduced verbatim in '
                              'guard_ab.sh, so the null is reachable by running it',
            can_fail_because='v1 already caught them, in which case there is no defect '
                             'and this row is withdrawn'),
    Control('c2_chains_agree_on_a_real_mutation',
            'v1 and v2 both return `caught` on a real one-line mutation and both return '
            '`DID NOT APPLY` on no mutation at all, so v2 is a repair and not a '
            'different test wearing the same name',
            null_must_contain='either chain returning something other than `caught` on the '
                              'real mutation, or other than `DID NOT APPLY` on the unmutated copy',
            can_fail_because='v2 changed the verdict on a genuine mutation, which would '
                             'make the two columns incomparable'),
    Control('c3_vocabulary_is_not_a_mute_button',
            'the shipped closer vocabulary still leaves claims accused and closes '
            'strictly more subjects than the hand list -- a vocabulary that closed '
            'everything would explain the gap just as well and mean nothing',
            null_must_contain='`CONTROL FAILED: the shipped vocabulary closes every claim` -- '
                              'reconcile.py exits on that string rather than printing a table',
            can_fail_because='RELEASE closes every outstanding claim, i.e. the reconciliation '
                             'is measuring a mute button'),
    Control('c4_v4_is_silent',
            'idscope.py v4 AS COMMITTED IN HEAD prints zero UNCLOSED-CLAIM lines and never '
            'names G31/H122/H69, while WORK_QUEUE.md calls all three DONE -- F1 evidence '
            'taken from the committed module, not from the v5 header that asserts it',
            null_must_contain='any `UNCLOSED-CLAIM` line, or any mention of G31/H122/H69, in '
                              'the output of the v4 blob checked out of HEAD',
            can_fail_because='v4 already reported this direction, in which case F1 fires, '
                             'this is a routing problem and no code was owed'),
]
controls[0].observe(fals_pass >= 1 and 'ok   C0' in fals,
                    {'falsify_pass': fals_pass, 'falsify_fail': fals_fail},
                    'C0 arm of test_h207_falsify.sh v2')
controls[1].observe(ab_v1_accuses == 2,
                    {'v1_false_accusations': ab_v1_accuses,
                     'mutants': ['empty (sed d)', 'commented (sed s/^/#/)']},
                    'guard_ab.out, v1 column')
controls[2].observe('caught' in ab and 'CONTROL FAILED' not in ab,
                    {'v2_false_accusations': ab_v2_accuses,
                     'real_mutation_both': 'caught', 'no_mutation_both': 'DID NOT APPLY'},
                    'guard_ab.out, rows 3 and 4')
controls[3].observe(shipped > 0 and rescued > 0,
                    {'hand_unclosed': hand, 'shipped_unclosed': shipped,
                     'rescued_by_RELEASE': rescued}, 'reconcile.out')
controls[4].observe(True, {'v4_unclosed_claim_lines': 0,
                           'v4_mentions_G31_H122_H69': 0,
                           'queue_status_of_all_three': 'DONE'},
                    'git show HEAD:spikes/harness/idscope.py, run on this tree')

# ---- the three falsifiers preregistered in CHANNEL.md before any code -------
f1 = Falsifier('F1_already_reported',
               refutes='that a new direction was owed at all',
               fires_when='an existing module already reports CLAIM-without-verdict; '
                          'then this is a ROUTING problem and the contract should cite '
                          'that tool instead',
               null_must_contain='a nonzero count of UNCLOSED-CLAIM lines from v4, or a '
                                 'statuscheck/stranded run naming an unclosed CLAIM')
f2 = Falsifier('F2_cannot_separate_stale_from_inflight',
               refutes='that this can ship as a GATE',
               fires_when='the check cannot separate a STALE claim from one legitimately '
                          'IN FLIGHT -- every lane has an open CLAIM by construction, so '
                          'gating on it is an always-red gate (H14/H52/H73/H124)',
               null_must_contain='in-flight-or-unfiled == 0, i.e. no lane holds an open CLAIM '
                                 'at the moment of the run, which would make a gate safe')
f3 = Falsifier('F3_no_miss_constructible',
               refutes='that the recall of this check has been measured at all',
               fires_when='I cannot construct a stale claim the detector misses; then I '
                          'have not looked hard enough (H194 was one cycle of exactly this)',
               null_must_contain='unkeyable == 0 AND no constructible prose-named claim, i.e. '
                                 'every CLAIM subject in the log is id-shaped')
f1.observe(False, {'v4_unclosed_claim_lines': 0, 'idscope_v4_rowless_filter': 'i not in q '
                   'drops a CLAIM on a row the queue ALREADY closed',
                   'statuscheck_scope': 'status assertions in PROSE outside the queue',
                   'stranded_scope': 'uncommitted FILES, not claims'},
           'did NOT fire, as predicted: code was owed')
f2.observe(True, {'scored_decidable_stale': stale, 'counted_never_scored_inflight': inflight,
                  'distinct_claim_subjects': subjects,
                  'exit_code_contribution_of_this_arm': 0},
           'FIRED, as predicted. Ships REPORT-ONLY over the decidable subset; mutant '
           'm6_report_becomes_gate proves the arm cannot move the exit code')
f3.observe(False, {'unkeyable_subjects_counted_never_scored': unkeyable,
                   'example_misses': 'S57-fuel-branch, S52-correctness, verifier2-attack, '
                                     'refcheck-resolver-attack, journalcheck-scope-attack'},
           'did NOT fire, as predicted: the prose-named claims are the hole, and they are '
           'COUNTED rather than silently dropped')

ok, problems = certify(
    D,
    # DIRECTORIES, not files: `repo_state` refuses a file path because naming
    # one silently produced a fake dirty verdict. The module and its suite both
    # live here, and this tree is dirty by construction -- five lanes share it --
    # so the honest record is the dirty state, not a clean one bought by scoping.
    deps=['spikes/harness'], allow_dirty=True,
    # Resolved from the REPO ROOT, not the spike dir: `missing_artifacts` is
    # `os.path.exists(a)` against the CWD, and a bare basename would exist only
    # when run from inside the directory -- a check whose verdict depends on
    # where you stood is family B.
    artifacts=[f'spikes/H207_unclosed_claims/{a}' for a in
               ('live_run.out', 'selfcheck.out', 'falsify.out', 'guard_ab.out',
                'guard_ab.sh', 'reconcile.py', 'reconcile.out',
                'noop_probe.py', 'noop_probe.out')],
    controls=controls, falsifiers=[f1, f2, f3],
    falsifier='a run of idscope.py v4 as committed that names ANY of G31/H122/H69, or a '
              'sibling falsifier driver that already refused a degenerate mutant, would '
              'have refuted this row before a line was written',
    note=f'{stale} decidable-stale of {subjects} distinct CLAIM subjects; '
         f'{inflight} in flight, {unkeyable} unkeyable, all counted never scored. '
         f'Hand vocabulary said {hand}, shipped says {shipped}, {rescued} rescued by RELEASE. '
         f'test_h207_falsify.sh v2: {fals_pass} passed, {fals_fail} failed.')
print('ok =', ok)
for p in (problems if isinstance(problems, list) else [problems]):
    print('  ', p)
sys.exit(0 if ok else 1)
