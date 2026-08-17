#!/usr/bin/env python3
"""H77-ATTACK — `demo8.py` calls a spike CLAIMED on a green record that may
describe code the spike no longer has.

TARGET: `spikes/harness/demo8.py`, written by AGENT-1 two cycles earlier (§2:
self-authored data first).

THE SUSPICION, WRITTEN INTO `HANDOFF.md` BEFORE THIS FILE EXISTED
------------------------------------------------------------------
    `CLAIMED` requires only that a green provenance record EXISTS in the
    directory -- it never checks the record is CURRENT. So a spike whose code
    changed after its last green certify still reads CLAIMED.

THE FALSIFIER
-------------
    If demo8's verdict MOVES when a claimed spike's source is modified after its
    last green certify, the suspicion is wrong and the tool already resolves
    currency.

It fires if the verdict does not move.

WHY THIS IS FAMILY C AND WORTH A CYCLE
---------------------------------------
`demo8.py` exists because §7 gates `LOOP-DONE` on §8 and §8 was resolved by eye.
A tool that answers "is this line closed?" from an artifact that need not
describe the current code is **the artifact is not what you think**, sitting in
the instrument built to stop that class. A24 is the same shape one layer down: a
digest pins WHICH artifact, not what is in it.

AND THE RECORD ITSELF CANNOT ANSWER IT, WHICH IS THE PART I GOT WRONG FIRST
----------------------------------------------------------------------------
The first plan here was "read `source_mtimes` from the record, it is already
stored." Measured instead of assumed: `spikes/S38_runbook/provenance.json` has
`source_mtimes: {}` and `repos: false`, because `certify(deps=[])` -- which every
`no_deps_reason` spike passes -- **disables the entire staleness path** (that is
A28's own text). So the data this fix wanted is empty in exactly the spikes that
would need it, and the check has to come from the tree.

THE FIX MEASURED HERE
---------------------
Compare each spike's CODE files (`*.py`, `*.sh`) against the mtime of its
provenance record. Code newer than the record means the record describes a run of
different code -> **STALE**, which is a distinct verdict from CLAIMED and from
BROKEN, because a stale record is not a wrong claim, it is an unrefreshed one and
its owner clears it by re-running.

Prose is deliberately NOT included. `RESULT.md` is edited after a run every time
a correction lands -- S36's was, one cycle after publishing -- and calling that
staleness would make the verdict red for doing the thing this repo most wants
done.

  python3 attack.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import demo8                                                        # noqa: E402
from kfcheck import certify                                         # noqa: E402
from provenance import Control, Falsifier                           # noqa: E402

CODE = ('.py', '.sh')


def _commit_time(rel):
    """Committer time of the newest commit touching `rel`, or None if untracked."""
    t = subprocess.run(['git', 'log', '-1', '--format=%ct', '--', rel],
                       capture_output=True, text=True, cwd=ROOT).stdout.strip()
    return int(t) if t.isdigit() else None


def newest_code_vs_record(d):
    """(stale_files, record_name), decided from GIT rather than from mtime.

    MTIME WAS THE FIRST RULE HERE AND IT IS WITHDRAWN, by this file's own probe:
    the probe edits a file and reverts it byte-for-byte, and a byte-identical
    revert still bumps mtime -- so the mtime rule reported `check_runbook.py`
    STALE with the content unchanged. A staleness rule that fires on a rewrite
    that changed nothing is A24's shape one level up: it pins WHEN a file was
    written, not WHAT is in it, which is the property the verdict is about.

    The rule instead: a code file is stale if it is MODIFIED RELATIVE TO HEAD, or
    if the newest commit touching it is newer than the newest commit touching the
    provenance record. Both are content-derived and neither moves when a file is
    rewritten identically.
    """
    ap = os.path.join(ROOT, d)
    recs = [f for f in sorted(os.listdir(ap)) if f.startswith('provenance') and
            f.endswith('.json')]
    if not recs:
        return [], None
    # THE NEWEST RECORD, and "the oldest is binding" is WITHDRAWN by the survey
    # it produced. That rule flagged `spikes/S36_witnessed_job/attack.py` stale
    # against `provenance.json` -- but attack.py is certified by
    # `provenance.attack.json`, its own record, which H49 requires it to write
    # separately. Comparing every code file to the OLDEST record makes any spike
    # carrying both a run and its attack permanently stale, which is a property
    # of my rule and not of the spike. A false positive that lands on every
    # attacked spike would train lanes to ignore the verdict (H14).
    #
    # The cost of the newer rule, stated: a spike that refreshes only its attack
    # record masks stale main code. That is a weaker check and it is the one that
    # does not cry wolf; pairing each record to the code it certifies needs the
    # record to say what it ran, which it does not currently store.
    rec = max(recs, key=lambda r: _commit_time(f'{d}/{r}') or 0)
    rt = _commit_time(f'{d}/{rec}') or 0
    dirty = set(subprocess.run(['git', 'status', '--porcelain', '--', d],
                               capture_output=True, text=True,
                               cwd=ROOT).stdout.split())
    stale = []
    for f in sorted(os.listdir(ap)):
        if not f.endswith(CODE):
            continue
        rel = f'{d}/{f}'
        ct = _commit_time(rel)
        if rel in dirty or ct is None or ct > rt:
            stale.append(f)
    return stale, rec


def main():
    ev = demo8.evidence()
    dirs = [r['dir'] for r in ev]

    # ---- THE PROBE: modify a claimed spike's source, ask demo8, revert.
    target = 'spikes/S38_runbook/check_runbook.py'
    tp = os.path.join(ROOT, target)
    orig = open(tp, encoding='utf-8').read()

    def verdict():
        out = subprocess.run([sys.executable,
                              os.path.join(ROOT, 'spikes/harness/demo8.py')],
                             capture_output=True, text=True, cwd=ROOT).stdout
        line = [l for l in out.splitlines() if 'CLAIMED' in l and '·' in l]
        return line[0].strip() if line else '(no summary line)'

    # THE SURVEY RUNS FIRST. In the first version it ran after the probe, and the
    # probe's own revert made `check_runbook.py` look stale -- I nearly published
    # a live-tree finding that was an artifact of my measurement (A23: the
    # instrument perturbs what it observes).
    survey = {}
    for d in dirs:
        stale, rec = newest_code_vs_record(d)
        survey[d] = {'record': rec, 'stale_code': stale}

    before = verdict()
    try:
        open(tp, 'w', encoding='utf-8').write(
            orig + '\n# H77-ATTACK probe: source changed after the last green certify\n')
        after = verdict()
        stale_now, _rec = newest_code_vs_record('spikes/S38_runbook')
    finally:
        open(tp, 'w', encoding='utf-8').write(orig)

    moved = before != after
    fired = not moved

    out = {'probe_target': target,
           'demo8_before_edit': before,
           'demo8_after_edit': after,
           'verdict_moved': moved,
           'fix_detects_the_edit': bool(stale_now),
           'stale_code_seen_by_fix_during_probe': stale_now,
           'survey_of_claimed_spikes': survey,
           'falsifier_fired': fired}
    with open(os.path.join(HERE, 'attack.json'), 'w') as f:
        json.dump(out, f, indent=2, sort_keys=True)

    C = []
    c = Control('C_the_edit_is_real',
                'the probe must actually change the file, or "the verdict did '
                'not move" is a statement about nothing (A29)',
                null_must_contain='an edit that leaves the bytes identical, '
                                  'which no verdict could be expected to see',
                can_fail_because='the proposed staleness check not seeing the '
                                 'edit either, which would mean nothing changed')
    c.observe(bool(stale_now), {'stale_during_probe': stale_now})
    C.append(c)

    c = Control('C_file_is_restored',
                'the probe edits a COMMITTED file in the live tree and must '
                'leave it byte-identical, or this attack has damaged the thing '
                'it is measuring',
                null_must_contain='a probe that writes and does not revert, '
                                  'which git would report as modified',
                can_fail_because='git reporting the target as modified after '
                                 'this run')
    dirty = subprocess.run(['git', 'status', '--porcelain', target],
                           capture_output=True, text=True, cwd=ROOT).stdout.strip()
    c.observe(dirty == '', {'git_status': dirty or '(clean)'})
    C.append(c)

    c = Control('C_fix_survives_an_identical_rewrite',
                'the staleness rule must NOT fire on a byte-identical rewrite. '
                'The mtime rule this file started with did, and would have '
                'reported the live tree stale for a probe that changed nothing',
                null_must_contain='an mtime-based rule, which any rewrite trips',
                can_fail_because='the target showing stale after the revert, '
                                 'with git reporting it unmodified')
    post_stale, _r = newest_code_vs_record('spikes/S38_runbook')
    c.observe('check_runbook.py' not in post_stale,
              {'after_revert': post_stale})
    C.append(c)

    c = Control('C_fix_does_not_flag_everything',
                'the staleness check must NOT report every claimed spike as '
                'stale -- a check that is red on everything carries no '
                'information (H14) and would make CLAIMED unreachable',
                null_must_contain='a rule that flags any file newer than the '
                                  'record, which prose corrections trip every '
                                  'time a retraction lands',
                can_fail_because='every claimed spike showing stale code')
    all_stale = [d for d, v in survey.items() if v['stale_code']]
    c.observe(len(all_stale) < len(survey),
              {'claimed_dirs': len(survey), 'stale': all_stale})
    C.append(c)

    F = Falsifier('F_demo8_already_resolves_currency',
                  refutes='this attack: if demo8 moves its verdict when a claimed '
                          "spike's source changes after its last green certify, "
                          'the tool already resolves currency',
                  fires_when='the verdict does not move',
                  null_must_contain='a source edit the proposed check DOES see, '
                                    'which is what makes the non-movement a gap '
                                    'rather than a no-op')
    F.observe(fired, {'before': before, 'after': after, 'moved': moved})

    ok, problems = certify(
        HERE, deps=[],
        no_deps_reason='the instrument is `spikes/harness/demo8.py`, imported '
                       'from the tree under test on purpose -- this attack is '
                       'about what that file does NOW, and pinning it to HEAD '
                       'would measure a different question',
        artifacts=[os.path.join(HERE, 'attack.json')],
        controls=C, falsifiers=[F],
        record_name='provenance.attack.json',
        falsifier="demo8's verdict moving when a claimed spike's source changes, "
                  'which would mean currency is already resolved')

    print(json.dumps({k: v for k, v in out.items()
                      if k != 'survey_of_claimed_spikes'}, indent=2, sort_keys=True))
    print('survey:')
    for d, v in sorted(survey.items()):
        print(f'  {d:36s} record={v["record"]} stale_code={v["stale_code"]}')
    print('certify ok=%s' % ok)
    for p in problems:
        print('  PROBLEM', p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
