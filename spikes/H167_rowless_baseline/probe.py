#!/usr/bin/env python3
"""H167 — a defect counter published without its baseline reports growth as floor.

Run: python3 spikes/H167_rowless_baseline/probe.py

SUBJECT: `spikes/harness/idscope.py` v3, ATTACKER-1's module, attacked by
AGENT-2 under MISSION_LOOP §12.9 (either rower may take a class-H row) and §2
(ATTACK targets instruments before conclusions).

THE CLAIM UNDER TEST is one sentence v3 prints on every run:

    ROWLESS: N id(s). REPORTED, NOT GATED -- see the v3 ceiling in the
    docstring; the floor is other lanes' rows and no committer can clear it.

C1 — THE BASELINE IS EXTRACTED FROM THE v3 DOCSTRING, NEVER RETYPED. Retyping it
here would let the comparison agree with a number I had chosen, which is the
A22 shape (a party supplying the input to a check on itself) inside the probe
that exists to catch it.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'spikes', 'harness'))
import idscope                                            # noqa: E402
from provenance import Control, Falsifier                 # noqa: E402
from kfcheck import certify                               # noqa: E402

IDSCOPE = os.path.join(ROOT, 'spikes', 'harness', 'idscope.py')


def baseline_from_docstring():
    """The 14 ids v3 NAMED, read out of the module's own v3 changelog block.

    Anchored on v3's sentence so a future edit that moves the list breaks this
    loudly instead of silently comparing against nothing -- `re.findall` on a
    missing anchor returns [], and an empty baseline would make every live id
    look NEW, which is the exact failure this probe accuses v3 of.
    """
    src = open(IDSCOPE, encoding='utf-8').read()
    m = re.search(r'with no `WORK_QUEUE\.md` row of any kind\*\*\s*—(.*?)'
                  r'spanning three series', src, re.S)
    if not m:
        raise SystemExit('probe: the v3 baseline sentence is gone from '
                         'idscope.py -- refusing to compare against nothing')
    ids = re.findall(r'\b[A-Z]+\d+\b', m.group(1))
    if not ids:
        raise SystemExit('probe: baseline sentence matched but named no ids')
    return sorted(set(ids))


def live_rowless():
    """id -> {'CLAIM','DONE'}, from the module's own readers on the live tree."""
    q = idscope.queue_rows(open(os.path.join(ROOT, 'WORK_QUEUE.md'),
                                encoding='utf-8').read())
    l = open(os.path.join(ROOT, 'CHANNEL.md'), encoding='utf-8').read()
    return {i: p for i, p in idscope.log_ids(l).items() if i not in q}


def introducing_commit(rid):
    """(sha, carried_WORK_QUEUE) for the commit that added `DONE <rid>` to the
    log, or (None, None) when the line is uncommitted."""
    p = subprocess.run(['git', 'log', '--format=%H', '-S', f'DONE {rid} ',
                        '--', 'CHANNEL.md'], capture_output=True, text=True,
                       cwd=ROOT)
    shas = [s for s in p.stdout.split() if s]
    if not shas:
        return None, None
    sha = shas[-1]
    files = subprocess.run(['git', 'show', '--name-only', '--format=', sha],
                           capture_output=True, text=True, cwd=ROOT).stdout
    return sha, 'WORK_QUEUE.md' in files.split()


def main():
    base = baseline_from_docstring()
    cur = live_rowless()
    done = sorted(i for i, p in cur.items() if 'DONE' in p)
    claim = sorted(set(cur) - set(done))
    gained, cleared = sorted(set(cur) - set(base)), sorted(set(base) - set(cur))

    print(f'v3 docstring baseline (2026-08-18): {len(base)}  {base}')
    print(f'live rowless now                  : {len(cur)}')
    print(f'  CLAIM-only (§2 SELECT sanctioned): {len(claim)}  {claim}')
    print(f'  DONE (terminal, unreconciled)    : {len(done)}  {done}')
    print(f'gained since baseline: {len(gained)}  {gained}')
    print(f'cleared since baseline: {len(cleared)}  {cleared}')
    print(f'=> the printed total moved {len(base)} -> {len(cur)} '
          f'(+{len(cur) - len(base)}) while {len(gained)} landed and '
          f'{len(cleared)} cleared\n')

    # C2 -- CLEARABILITY, the property v3 read off the wrong population. For each
    # terminal id, did the commit that introduced its DONE line also carry the
    # authoritative file? If it did not, the row was writable by that author in
    # that commit and by nobody more cheaply since.
    rows, uncommitted, no_wq = [], 0, 0
    for rid in done:
        sha, carried = introducing_commit(rid)
        if sha is None:
            uncommitted += 1
            rows.append((rid, 'UNCOMMITTED', 'in the working tree now'))
        else:
            no_wq += 0 if carried else 1
            rows.append((rid, sha[:8], 'carried WORK_QUEUE.md'
                         if carried else 'did NOT carry WORK_QUEUE.md'))
    for rid, sha, note in rows:
        print(f'  {rid:<7} {sha:<12} {note}')
    print(f'=> {no_wq}/{len(done)} introduced without the authoritative file; '
          f'{uncommitted} uncommitted right now\n')

    c1 = Control('baseline_extracted_not_retyped',
                 'the comparison must use the numbers v3 published, not mine',
                 null_must_contain='ids that are NO LONGER rowless. The v3 set '
                                   'names G43/H86/H88/H89/H93, all filed since, '
                                   'so the extractor demonstrably reads the '
                                   'PUBLISHED past and not the live present -- '
                                   'if it could only ever return today\'s set the '
                                   'comparison would be with itself',
                 can_fail_because='the v3 changelog sentence names no ids, or '
                                  'was edited away -- the extractor then raises '
                                  'rather than comparing against an empty set')
    c1.observe(len(base) > 0, base, f'{len(base)} ids parsed from idscope.py v3')

    c2 = Control('terminal_population_is_separable',
                 'the merged count is only a defect if the two populations '
                 'differ in kind, so both must be non-empty and disjoint',
                 null_must_contain='an empty side. A log of only CLAIM lines '
                                   'yields done=0 and a log of only DONE lines '
                                   'yields claim=0; both are reachable from the '
                                   'same reader, so a non-empty split is a '
                                   'measurement and not a property of the code',
                 can_fail_because='every rowless id is CLAIM-only, or every one '
                                  'is DONE -- then there is nothing to split '
                                  'and v3 merged nothing')
    c2.observe(bool(claim) and bool(done) and not (set(claim) & set(done)),
               [len(claim), len(done)],
               f'{len(claim)} CLAIM-only, {len(done)} DONE, disjoint')

    c3 = Control('gate_fires_and_is_scoped',
                 'the v4 gate must refuse an id THIS tree introduces and stay '
                 'quiet on an accumulated one, or it is decoration',
                 null_must_contain='both exit codes from the SAME fixture id. '
                                   'H99 is driven three ways and the only thing '
                                   'varying is the property under test, so the '
                                   'outcome space contains 0 and 1 by '
                                   'construction rather than by which id was '
                                   'chosen',
                 can_fail_because='both arms return the same exit code -- a gate '
                                  'that cannot distinguish them has not read '
                                  'the property it claims to')
    import io, contextlib
    fixture_q = '| id | item | status |\n|---|---|---|\n'
    probe_id = 'H' + '99'

    def run(log, seen):
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            return idscope.scan(fixture_q, log, seen_done=seen)
    fires = run(f'DONE {probe_id} LANE-1 introduced here\n', set())
    quiet = run(f'DONE {probe_id} LANE-1 already at HEAD\n', {probe_id})
    claimq = run(f'CLAIM {probe_id} LANE-1 §2 says claim first\n', set())
    c3.observe(fires == 1 and quiet == 0 and claimq == 0,
               [fires, quiet, claimq],
               'introduced=1 (refuses), accumulated=0, CLAIM-only=0')

    f1 = Falsifier('F1_already_mechanised',
                   'refutes the finding: another checker already pins a rowless '
                   'baseline or branches its verdict on CLAIM vs DONE',
                   fires_when='a grep of spikes/harness for a pinned rowless '
                              'baseline returns a module other than idscope',
                   null_must_contain='a non-idscope hit. The same grep pattern '
                                     'returns refcheck.py for BASELINE_ROW_SHAPE '
                                     'when widened to row shape, so the search '
                                     'can find another module -- it does not '
                                     'find one for THIS subject')
    hits = subprocess.run(
        ['grep', '-rlE', r'BASELINE_ROWLESS|rowless.*baseline'],
        capture_output=True, text=True,
        cwd=os.path.join(ROOT, 'spikes', 'harness')).stdout.split()
    others = [h for h in hits if 'idscope' not in h]
    f1.observe(bool(others), hits or ['(none)'],
               f'other modules pinning a rowless baseline: {others or "none"}')

    f2 = Falsifier('F2_no_decay',
                   'refutes the finding: the live set equals the 14 v3 named, '
                   'so the sentence is still true and a bare count is fine',
                   fires_when='set(live rowless) == set(v3 baseline)',
                   null_must_contain='equality. The two sets share 9 members, so '
                                     'the comparison is not structurally forced '
                                     'apart -- had the 15 gained ids never '
                                     'landed it would report equal')
    f2.observe(set(cur) == set(base), [len(cur), len(base)],
               f'live {len(cur)} vs baseline {len(base)}')

    f3 = Falsifier('F3_sanctioned_workflow_refused',
                   'refutes the FIX: a lane obeying §2 SELECT (post CLAIM before '
                   'the row exists) is gated, which recreates H52',
                   fires_when='scan() returns non-zero on a CLAIM-only rowless id',
                   null_must_contain='a refusal. The same scan() returns 1 on the '
                                     'same id posted as DONE, so non-zero is '
                                     'reachable on this fixture and the quiet '
                                     'verdict is about CLAIM, not about a gate '
                                     'that never fires')
    f3.observe(claimq != 0, [claimq, len(claim)],
               f'CLAIM-only exit={claimq} with {len(claim)} live CLAIM-only ids')

    f4 = Falsifier('F4_incoming_unclearable',
                   'refutes the FIX: the incoming ids are unclearable for the '
                   'same reason the floor is, so gating them is H52 again',
                   fires_when='every terminal id was introduced by a commit that '
                              'already carried WORK_QUEUE.md, leaving its author '
                              'no cheaper moment to file the row',
                   null_must_contain='commits that DID carry it. G45 and H76 are '
                                     'exactly that case, so the measurement can '
                                     'produce the refuting answer and 8/13 is an '
                                     'observation rather than a definition')
    f4.observe(no_wq == 0, [no_wq, uncommitted, len(done)],
               f'{no_wq} of {len(done)} introduced without the authoritative file')

    # THE ARTIFACT IS THE MEASUREMENT, NOT THE GENERATOR. Naming probe.py as
    # the artifact made the staleness check compare a SOURCE against its own
    # dep dir, so a concurrent lane writing any file under spikes/harness turned
    # this run red for a reason that had nothing to do with the result. Written
    # last, immediately before certify, so `mtime(artifact) > mtime(sources)`
    # means what A28 wants it to mean: this result was produced from this tree.
    out = os.path.join(HERE, 'rowless.json')
    json.dump({'v3_baseline_2026_08_18': base,
               'live_rowless': sorted(cur),
               'claim_only': claim, 'done_rowless': done,
               'gained_since_baseline': gained,
               'cleared_since_baseline': cleared,
               'introduced_without_work_queue': no_wq,
               'uncommitted_now': uncommitted,
               'terminal_total': len(done),
               'gate_exit_introduced': fires,
               'gate_exit_accumulated': quiet,
               'gate_exit_claim_only': claimq},
              open(out, 'w'), indent=1, sort_keys=True)

    ok, problems = certify(
        HERE,
        # THE DIRECTORY, not the three files: `repo_state` refuses a file
        # and A28 records that `deps=()` silently disables the whole staleness
        # path, so the dep that is wrong in the safe direction is the wide one.
        deps=[os.path.join(ROOT, 'spikes', 'harness')],
        artifacts=[out],
        controls=[c1, c2, c3],
        falsifiers=[f1, f2, f3, f4],
        allow_dirty=True,
        note='H167. idscope.py v3 printed one ROWLESS total and declared it '
             'ungateable because "the floor is other lanes\' rows". The floor '
             'was 14 NAMED ids on 2026-08-18; the sentence is now asserted over '
             'a set that has gained 10 and cleared 5, and it merges the '
             'CLAIM-only population that §2 SELECT creates on purpose with the '
             'DONE population that is terminal.',
        falsifier='If the live rowless set still equalled the 14 ids v3 named '
                  '(F2), or if a CLAIM-only id were gated by the fix (F3), or '
                  'if every terminal id had been introduced by a commit already '
                  'carrying WORK_QUEUE.md (F4), the finding or the fix would be '
                  'refuted.')
    print(f'\ncertify ok={ok}')
    for p in problems:
        print('  ' + p)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
