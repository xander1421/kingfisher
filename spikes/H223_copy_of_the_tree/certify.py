#!/usr/bin/env python3
"""H223 certification. Reads the two probes' recorded JSON; measures nothing new.

Every control below OBSERVES a value that `probe.json` or `mechanism.json`
recorded during the run, rather than declaring a verdict (A22, and error 38 --
a literal verdict is the defect this lane's own `constcheck` reports).

repro: python3 spikes/H223_copy_of_the_tree/certify.py
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / 'spikes' / 'harness'))
import kfcheck                                     # noqa: E402
from provenance import Control, Falsifier          # noqa: E402

# `incident.json` is a CAPTURED OBSERVATION, not an artifact of this run, and it
# is passed to certify() as a capture for exactly that reason. The remedy for the
# incident was to delete the copy, so the contaminated state cannot be rebuilt --
# and an artifact that certify could not have produced from the tree recorded
# here is one it is right to call stale. `repro.json` is the re-runnable half.
probe = json.load(open(HERE / 'incident.json'))
INCIDENT_SHA = hashlib.sha256((HERE / 'incident.json').read_bytes()).hexdigest()

# THE TWO RE-RUNNABLE PROBES ARE RUN HERE, NOT READ FROM DISK, AND THE REASON IS
# A MEASURED DEFECT AND NOT TIDINESS. `deps` must be a DIRECTORY
# (`provenance.repo_state` raises on a file, deliberately -- naming a file once
# produced a fake dirty verdict), so this spike declares `spikes/harness`, and
# five lanes write that directory continuously: three certification attempts were
# refused as STALE against `spikes/harness/bringup.sh`, then
# `spikes/harness/test_h232_falsify.sh` -- neither of which this row reads.
# Running the probes inside the certifying process shrinks the window from
# "since I last ran them" to "the length of this run". It does not close it, and
# the residual is stated rather than hidden. The general question -- whether a
# dep declaration should be directory-granular at all on a shared tree -- is the
# second measured instance in this lane's record (H187's 10 churny-dep spikes was
# the first) and belongs to whoever owns `certify`.
sys.path.insert(0, str(HERE))
import mechanism as _mechanism                       # noqa: E402
import repro as _repro                               # noqa: E402
mech = _mechanism.main()
repro = _repro.main()
before, after = probe['before'], probe['after']
WALKERS = sorted(before)


def main():
    # C1 -- the guard from error 42, and it is not hypothetical here: the FIRST
    # run of this measurement used `timeout`, which macOS does not have, so all
    # seven modules exited 127 with ZERO output and reported stray_hits=0. Only
    # the size column said the instruments had not spoken.
    c1 = Control(
        'C1_size_asserted_before_hits',
        why='a module that printed nothing reports zero hits, and '
                          'zero hits is this row\'s healthy answer -- so absence '
                          'of output must be separated from absence of findings '
                          'before any hit count is read (error 42)',
        can_fail_because='any walker run in either phase produced 0 output lines '
                         'and was still scored; the first attempt at this exact '
                         'measurement did precisely that, seven times over',
        null_must_contain='a silent run, which this measurement has already '
                          'produced once on this machine')
    c1.observe(all(before[m]['ran'] and after[m]['ran'] for m in WALKERS),
               {'before_min_output_lines': min(before[m]['output_lines'] for m in WALKERS),
                'after_min_output_lines': min(after[m]['output_lines'] for m in WALKERS),
                'walkers': len(WALKERS)})

    # C2 -- two-sided on the remedy: contamination present, then absent, with the
    # instruments still speaking on BOTH sides.
    hit_before = {m: before[m]['stray_hits'] for m in WALKERS if before[m]['stray_hits']}
    hit_after = {m: after[m]['stray_hits'] for m in WALKERS if after[m]['stray_hits']}
    c2 = Control(
        'C2_contamination_present_then_absent',
        why='a clean AFTER proves nothing unless a dirty BEFORE was '
                          'measured by the same instruments in the same session',
        can_fail_because='no walker reported the copy before deletion (nothing was '
                         'contaminated), or any still reports it after (the remedy '
                         'did not work), or a walker went silent across the delete',
        null_must_contain='the BEFORE side, where three walkers name the copy')
    c2.observe(bool(hit_before) and not hit_after,
               {'before_hits': hit_before, 'after_hits': hit_after,
                'constcheck_output_lines': [before['constcheck']['output_lines'],
                                            after['constcheck']['output_lines']],
                'recheck_output_lines': [before['recheck']['output_lines'],
                                         after['recheck']['output_lines']]})

    # C3 -- the census predicate must separate a COPY from ordinary untracked
    # content, or F2's answer is an artefact of the threshold.
    by = {c['dir']: c for c in probe['census']}
    copy = by.get('spikes/H210_refutation_outlives_target/')
    c3 = Control(
        'C3_census_separates_a_copy_from_live_work',
        why='F2 is decided on this predicate, so it must score the '
                          'copy far from the ordinary untracked directories and '
                          'not merely above a threshold chosen to fit',
        can_fail_because='fixtures/ or kitchen/drafts/ -- 544 and 113 untracked '
                         'files of genuine content -- score anywhere near the copy',
        null_must_contain='two large untracked directories that are NOT copies, '
                          'both present in this tree by construction')
    c3.observe(copy is not None
               and copy['tracked_path_suffixes'] / copy['files'] > 0.9
               and by['fixtures/']['tracked_path_suffixes'] < 20
               and by['kitchen/drafts/']['tracked_path_suffixes'] < 20,
               {'copy': [copy['tracked_path_suffixes'], copy['files']] if copy else None,
                'fixtures': [by['fixtures/']['tracked_path_suffixes'], by['fixtures/']['files']],
                'kitchen_drafts': [by['kitchen/drafts/']['tracked_path_suffixes'],
                                   by['kitchen/drafts/']['files']]})

    # C4 -- the shipped check must fail when the shipped change breaks. Re-run
    # here rather than quoting the earlier session: a mutation result recorded in
    # prose is a claim, and this row already found one mutant surviving a check
    # whose arm tested the DISPLAY instead of the computation.
    # Mutate a COPY and point check.sh at it with CONSTCHECK. The obvious form
    # -- write the mutant over `spikes/harness/constcheck.py`, run, restore -- is
    # a tree-wide mutation of a module four live lanes import, for the length of
    # three check runs. That is the class this row reported to the fleet.
    target = ROOT / 'spikes' / 'harness' / 'constcheck.py'
    src = target.read_text()
    mutant_path = HERE / '_mutant_constcheck.py'
    mutants = {
        'D_git_failure_returns_empty':
            ('    if pr.returncode != 0:\n        return None',
             '    if pr.returncode != 0:\n        return []'),
        'C_suffix_match_instead_of_exact':
            ('    return sorted(r for r in scanned_rels if r not in tracked)',
             '    return sorted(r for r in scanned_rels if not any('
             'r.endswith(t) for t in tracked))'),
        'E_computation_replaced_by_constant':
            ('    ut = untracked_scanned(ROOT, scanned)', '    ut = []'),
    }
    killed = {}
    env = dict(os.environ)
    try:
        for name, (old, new_txt) in mutants.items():
            assert old in src, f'MUTATION ANCHOR ABSENT for {name}'
            mutant_path.write_text(src.replace(old, new_txt, 1))
            env['CONSTCHECK'] = str(mutant_path)
            r = subprocess.run(['sh', str(HERE / 'check.sh')], env=env,
                               capture_output=True, text=True, cwd=str(ROOT))
            killed[name] = r.returncode != 0 and 'check.sh: FAIL' in r.stdout
    finally:
        mutant_path.unlink(missing_ok=True)
    assert target.read_text() == src, 'the shared module was modified by this run'
    clean = subprocess.run(['sh', str(HERE / 'check.sh')],
                           capture_output=True, text=True, cwd=str(ROOT))
    c4 = Control(
        'C4_the_check_fails_when_the_change_breaks',
        why='§12.3 -- a harness component ships a check that fails '
                          'when it breaks, and "it passes" is not evidence of that',
        can_fail_because='any mutant survives, or the unmutated module does not '
                         'pass; an earlier arm of this very check DID let a mutant '
                         'through by testing the printed output instead of the '
                         'computation behind it',
        null_must_contain='the unmutated module, which must pass, so a check that '
                          'refuses everything cannot score green here')
    c4.observe(all(killed.values()) and clean.returncode == 0,
               {'mutants_killed': killed, 'unmutated_check_rc': clean.returncode})

    # C5 -- the peer-damage claim, reproduced rather than quoted from the lane
    # that reported it (A22 in the other direction: the party reporting damage to
    # itself is not the party who should be believed about my defect either).
    c5 = Control(
        'C5_peer_falsifier_perturbation_reproduced',
        why='AGENT-2 reports their preregistered F4 fired at 10 '
                          'citing spikes instead of 9 because of my copy; that is '
                          'a claim about my contamination and it is checked',
        can_fail_because='one piece of evidence present in two places on disk is '
                         'counted ONCE by G101\'s rule, in which case a copy adds '
                         'noise but cannot invert a count-based falsifier',
        null_must_contain='the single-copy arm, where the count does not move')
    c5.observe(mech['one_citer_counted_twice'] and mech['copy_wears_the_enclosing_name'],
               {'arm1_only_real': mech['arm1_only_the_real_spike'],
                'arm2_real_plus_copy': mech['arm2_real_plus_its_copy'],
                'arm3_only_copy': mech['arm3_only_the_copy']})

    # Falsifiers, preregistered in CHANNEL.md before any of them ran.
    f1 = Falsifier(
        'F1_gitignore_would_have_saved_it',
        refutes='the row: if the copy is gitignored, a .gitignore-driven '
                'exclusion is the whole remedy and there is no class',
        fires_when='`git check-ignore` calls the copy IGNORED',
        null_must_contain='an IGNORED verdict, which this same command returns '
                          'for `elders/` and `.scratch/` in this tree')
    f1.observe(probe['f1_fired'], {'check_ignore_rc': probe['f1_check_ignore_rc']})

    f2 = Falsifier(
        'F2_the_class_is_one_anecdote',
        refutes='the CLASS: one instance means the rate is the deliverable and '
                'no copy detector ships (ok-1 H23 precedent)',
        fires_when='the census finds no copy of the tree other than the one I made',
        null_must_contain='27 other untracked directories, any of which could '
                          'have scored as a copy and none of which did')
    f2.observe(probe['f2_fired'],
               {'copies': [c['dir'] for c in probe['copies']],
                'untracked_dirs_censused': len(probe['census'])})

    f3 = Falsifier(
        'F3_blast_radius_is_zero',
        refutes='my sub-claim that the copy perturbed another lane\'s measurement',
        fires_when='no document quotes a count from a contaminated module AND no '
                   'peer falsifier moved',
        null_must_contain='23 document mentions of the three modules, and a '
                          'three-arm reproduction whose count was free not to move')
    f3.observe(probe['f3_fired'] and not mech['one_citer_counted_twice'],
               {'numeric_document_mentions': probe['f3_numeric_mentions'],
                'peer_falsifier_moved': mech['one_citer_counted_twice']})

    # C6 -- the re-runnable half. The incident is a one-time event; this is the
    # mechanism, exercised against a SANDBOX ROOT so that reproducing the row
    # does not re-contaminate the tree it is about.
    c6 = Control(
        'C6_the_walk_descends_and_doubles_the_report',
        why='the incident cannot be re-run, so the claim that a walker descends '
            'into a nested copy and reports its contents needs a fixture that '
            'anyone can run',
        can_fail_because='the walker does not descend into the nested copy, or '
                         'descends and reports the same verdict count as without '
                         'it -- either would mean a copy adds files but not findings',
        null_must_contain='the without-copy arm, where exactly one defect is '
                          'written and exactly one is reported')
    c6.observe(repro['copy_is_walked'] and repro['one_defect_reported_twice']
               and repro['copy_path_named'] and repro['sandbox_removed'],
               {'without_copy': repro['without_copy']['live_verdicts'],
                'with_copy': repro['with_copy']['live_verdicts'],
                'files_without': repro['without_copy']['files'],
                'files_with': repro['with_copy']['files']})

    ok, problems = kfcheck.certify(
        str(HERE),
        deps=[str(ROOT / 'spikes' / 'harness'), str(HERE)],
        artifacts=[str(HERE / 'repro.json'), str(HERE / 'mechanism.json')],
        captures=[('incident_json_sha256', INCIDENT_SHA)],
        controls=[c1, c2, c3, c4, c5, c6],
        falsifiers=[f1, f2, f3],
        allow_dirty=True,
        note='H223: a materialised copy of the repo inside the tree the '
             'instruments walk. constcheck v3 states its denominator.',
        falsifier='the copy is gitignored so .gitignore is the whole fix (F1), or '
                  'a second copy exists so the shape recurs (F2), or nothing '
                  'anywhere was computed from a contaminated run (F3).')

    print(f'C1={c1.fired} C2={c2.fired} C3={c3.fired} C4={c4.fired} C5={c5.fired} C6={c6.fired}')
    print(f'F1 fired={f1.fired}  F2 fired={f2.fired}  F3 fired={f3.fired}')
    print(f'certify ok={ok} problems={problems}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
