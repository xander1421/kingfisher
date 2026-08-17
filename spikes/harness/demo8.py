#!/usr/bin/env python3
"""demo8 — resolve MISSION_LOOP §8's acceptance checklist MECHANICALLY.

WHY THIS EXISTS
---------------
§7 gates `LOOP-DONE` on *"M1-DEMO (§8) passes"*. §8 is seven `- [ ]` boxes and
**nothing ticks them**. Five lanes have been running spikes all day and no lane
can say which of the seven are closed without reading the whole tree by eye.

That is §12.4's class sitting in the loop's own exit condition, and this repo has
already paid for it once: §7 also gated `LOOP-DONE` on *"D1-D6"* while D4 and D6
had never been written, and a contract citing a missing artifact **reads as
satisfied**. Seven unticked boxes read the other way -- as "nothing is done" --
which is just as wrong and costs a lane a rediscovery instead of a false pass.

WHAT IT DOES, AND THE THREE VERDICTS
-------------------------------------
The items are PARSED from `MISSION_LOOP.md`, never hardcoded, so editing §8
changes this tool's input rather than requiring it to be edited in step. Each
item is matched against `demo8_evidence.tsv`, which is an EXPLICIT, reviewable,
self-authored mapping of item -> the artifact that closes it.

    STALE     the artifact is green, but its CODE has moved since -- modified
              relative to HEAD, or last committed after the newest provenance
              record. The record describes a run of different code (v2, H77)
    CLAIMED   the claimed artifact exists, is TRACKED IN GIT, and carries a
              provenance record with ok=true. **NOT "this item is done"** --
              see the A22 note below; the verdict is deliberately named for
              what is mechanically true
    BROKEN    an artifact is claimed and it is missing, untracked, or red
    UNPROVEN  no artifact is claimed for this item

EXIT CODE: 1 on any BROKEN, 0 otherwise. **Neither CLAIMED nor UNPROVEN gates**, because an
unfinished demo is the honest state of this project and a checker that is red
until the mission completes carries no information -- H14's failure mode, where
`githygiene.py` sat at permanent exit 1 on 16 accepted binaries and everyone
learned to ignore it.

And it is a gate the tripped party CAN clear (H73): BROKEN means a row in the TSV
names something wrong, and whoever wrote that row can fix it.

THE A22 EXPOSURE, STATED RATHER THAN HIDDEN
--------------------------------------------
The mapping is self-authored -- I decided which spike closes which §8 line, and a
party supplying the input to a check on itself is the defect four domain keys in
this repo already paid for. Three things narrow it, none of them removes it:

  * the TSV carries WHO asserted each row, so the claim is attributed
  * a row must name the artifact's directory, and the artifact must carry its own
    `certify` record -- this tool never judges whether a spike is CORRECT, only
    whether the thing claimed to close a line exists and certified green
  * an item with no row is UNPROVEN, never "probably fine"

**This tool cannot tell you that S36 closes item 6. It can tell you that
somebody claimed it does, in a file with their name on it, and that the artifact
they named is real, committed, and green.** That is a strictly weaker statement
and it is the one that is mechanically true.

  python3 spikes/harness/demo8.py
  python3 spikes/harness/demo8.py --selfcheck
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ML = os.path.join(ROOT, 'MISSION_LOOP.md')
TSV = os.path.join(HERE, 'demo8_evidence.tsv')


def sh(*args, cwd=ROOT):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True).stdout


def items(text):
    """§8's checklist, in order. A continuation line is joined to its item --
    two of the seven wrap, and splitting on newlines alone gave nine items."""
    out, cur = [], None
    inside = False
    for line in text.splitlines():
        if re.match(r'^## 8 ', line):
            inside = True
            continue
        if inside and re.match(r'^## \d+ ', line):
            break
        if not inside:
            continue
        m = re.match(r'^- \[( |x)\] (.*)$', line)
        if m:
            if cur:
                out.append(cur)
            cur = m.group(2).strip()
        elif cur is not None and line.startswith('      '):
            cur += ' ' + line.strip()
        elif cur and not line.strip():
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out


def evidence():
    """key<TAB>dir<TAB>who<TAB>what the artifact itself claims. `key` is a
    distinctive substring of the §8 item, matched rather than an index, because
    an index silently re-points at a different line when §8 gains a bullet."""
    rows = []
    if not os.path.exists(TSV):
        return rows
    for line in open(TSV, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 4:
            continue
        rows.append({'key': parts[0], 'dir': parts[1], 'who': parts[2],
                     'claim': parts[3]})
    return rows


def _commit_time(rel):
    t = sh('git', 'log', '-1', '--format=%ct', '--', rel).strip()
    return int(t) if t.isdigit() else None


def stale_code(d):
    """v2, H77. Code files the newest provenance record cannot describe.

    DEFECT REMOVED: v1 called a spike CLAIMED on a green record that need not
    describe the code the spike currently has. Measured in
    `spikes/H77_demo8/attack.py`: editing a claimed spike's source moved demo8's
    verdict NOT AT ALL. That is family C -- the artifact is not what you think --
    inside the tool written to stop §8 being resolved by eye.

    GIT, NOT MTIME, and the mtime version is withdrawn by the probe that found
    this: a byte-identical revert bumps mtime, so an mtime rule reports STALE on
    a rewrite that changed nothing.

    THE NEWEST record, not the oldest: `provenance.attack.json` certifies the
    attack and `provenance.json` the run (H49 requires them separate), so pairing
    all code against the oldest makes every attacked spike permanently stale.
    The cost, stated: a spike refreshing only one record masks the other's code.
    """
    ap = os.path.join(ROOT, d)
    recs = [f for f in sorted(os.listdir(ap))
            if re.match(r'provenance.*\.json$', f)]
    if not recs:
        return []
    rt = _commit_time(f'{d}/{max(recs, key=lambda r: _commit_time(f"{d}/{r}") or 0)}') or 0
    dirty = set(sh('git', 'status', '--porcelain', '--', d).split())
    out = []
    for f in sorted(os.listdir(ap)):
        if not f.endswith(('.py', '.sh')):
            continue
        rel = f'{d}/{f}'
        ct = _commit_time(rel)
        if rel in dirty or ct is None or ct > rt:
            out.append(f)
    return out


def certified(d):
    """(ok, detail) for a spike directory: a provenance record with ok true."""
    import json
    ap = os.path.join(ROOT, d)
    if not os.path.isdir(ap):
        return False, 'directory does not exist'
    tracked = sh('git', 'ls-files', d).strip()
    if not tracked:
        return False, 'nothing under it is tracked in git — an uncommitted ' \
                      'result is indistinguishable from one never run (§13)'
    recs = [f for f in sorted(os.listdir(ap)) if re.match(r'provenance.*\.json$', f)]
    if not recs:
        return False, 'no provenance record — not certified'
    # EVERY record must be ok, not ANY. The first version returned True on the
    # first green one, so a directory holding one green record and three red ones
    # read as certified -- an existential quantifier where the property is
    # universal, which is the same defect ATTACKER-1 hit hours earlier asserting a
    # COUNT where the property was PRESENCE. A spike that certified green once and
    # red twice has not certified green.
    bad = []
    for r in recs:
        try:
            rec = json.load(open(os.path.join(ap, r)))
        except (ValueError, OSError) as e:
            return False, f'{r} unreadable: {e}'
        # `ok` is written explicitly by `provenance.record`; a record without it
        # is not a record this tool knows how to read, and it fails closed rather
        # than passing on the absence of a complaint.
        if rec.get('ok') is not True:
            bad.append(f'{r} ok={rec.get("ok")!r} problems={len(rec.get("problems") or [])}')
    if bad:
        return False, f'{len(bad)} of {len(recs)} record(s) not ok: {"; ".join(bad)}'
    return True, f'{len(recs)} record(s), all ok'


def main():
    if not os.path.exists(ML):
        print('MISSION_LOOP.md not found')
        return 2
    its = items(open(ML, encoding='utf-8').read())
    ev = evidence()
    if not its:
        print('§8 parsed to ZERO items — the section moved or its format changed. '
              'REFUSING rather than reporting 0/0, which reads as pass.')
        return 2

    used, broken, claimed, unproven, stale = set(), [], [], [], []
    print(f'MISSION_LOOP §8 — {len(its)} acceptance items\n' + '=' * 72)
    for it in its:
        row = next((r for r in ev if r['key'].lower() in it.lower()), None)
        if row is None:
            unproven.append(it)
            print(f'  UNPROVEN  {it[:66]}')
            print('              no artifact claimed')
            continue
        used.add(row['key'])
        ok, detail = certified(row['dir'])
        moved = stale_code(row['dir']) if ok else []
        if ok and moved:
            stale.append((it, row, moved))
            print(f'  STALE     {it[:66]}')
            print(f'              {row["dir"]}: code moved since the newest '
                  f'record — {moved}')
            print('              green, but the record describes different code. '
                  'Re-run to clear.')
        elif ok:
            claimed.append((it, row))
            print(f'  CLAIMED   {it[:66]}')
            print(f'              {row["dir"]} ({detail}), claimed by {row["who"]}')
            print(f'              it claims: {row["claim"]}')
        else:
            broken.append((it, row, detail))
            print(f'  BROKEN    {it[:66]}')
            print(f'              {row["dir"]}: {detail} — claimed by {row["who"]}')

    # A TSV row matching no §8 item is a dangling claim, and it is BROKEN rather
    # than ignored: it means §8 was edited under the mapping, which is exactly the
    # drift this tool exists to catch.
    for r in ev:
        if r['key'] not in used:
            broken.append((f'(no §8 item matches key {r["key"]!r})', r,
                           'the mapping points at a line §8 no longer has'))
            print(f'  BROKEN    mapping key {r["key"]!r} matches no §8 item')

    print('=' * 72)
    print(f'  CLAIMED {len(claimed)} · STALE {len(stale)} · UNPROVEN {len(unproven)}'
          f' · BROKEN {len(broken)}   of {len(its)}')
    print('  CLAIMED means an artifact was named for this line, and that artifact is')
    print('  real, committed and green. It does NOT mean the line is closed — read the')
    print('  claim text, which is where each row says what it does NOT cover.')
    print('  UNPROVEN does NOT gate: an unfinished demo is the honest state, and a')
    print('  checker that is red until the mission completes carries no information.')
    if broken:
        print(f'\nREFUSE: {len(broken)} claimed artifact(s) are missing, untracked '
              f'or not certified.\n        A claim of evidence that does not '
              f'resolve is worse than no claim,\n        because it reads as '
              f'satisfied (§12.4).')
        return 1
    return 0


def selfcheck():
    """The runnable check §12.3 requires. Every case is a way this tool could
    report a comfortable number that is not true."""
    fails = []

    def ck(name, cond, detail=''):
        print(f'  {"PASS" if cond else "FAIL"}  {name}{"" if cond else "  " + detail}')
        if not cond:
            fails.append(name)

    # 1 · THE PARSER, on the real §8. Seven items and two of them WRAP -- the
    #     first draft split on newlines and reported NINE, which would have made
    #     two items permanently UNPROVEN with no way to claim them.
    real = items(open(ML, encoding='utf-8').read())
    ck('parses the real §8 into 7 items', len(real) == 7, f'got {len(real)}')
    ck('the wrapped items are rejoined',
       any('coordinator' in i and 'Quorum-3' in i for i in real),
       'the Quorum-3 item lost its continuation line')

    # 2 · A section that parses to nothing must REFUSE, not report 0/0. A tool
    #     that says "0 of 0 broken" over a moved section is the silence-that-
    #     reads-as-success failure this repo ran through all day.
    ck('an empty §8 parses to zero items', items('## 8 · nothing here\n\n## 9 · x') == [])

    # 3 · The certification check must reject each way an artifact can be absent.
    ok, _d = certified('spikes/definitely_not_a_real_spike_dir')
    ck('a missing directory is not CLAIMED', not ok)
    ok, d = certified('elders')
    ck('a directory with no provenance record is not CLAIMED', not ok, d)

    # 4 · POSITIVE CONTROL. Without it, "rejects everything" passes every case
    #     above -- which is the shape githygiene.py was in when it sat at
    #     permanent exit 1 (H14).
    ok, d = certified('spikes/S36_witnessed_job')
    ck('a real certified spike IS claimed-and-green', ok, d)

    # 5 · H77 · STALENESS. v1 called a spike CLAIMED on a record that need not
    #     describe its current code, and the probe that found it moved demo8's
    #     verdict NOT AT ALL. These two cases are the fix and its false-positive
    #     guard, and the second is the one that matters: an mtime rule reported
    #     STALE on a byte-identical revert, and pairing code to the OLDEST record
    #     made every attacked spike permanently stale.
    ck('a clean committed spike is NOT stale',
       stale_code('spikes/S26_cheat_attribution') == [],
       str(stale_code('spikes/S26_cheat_attribution')))
    ck('a spike carrying BOTH a run and its attack record is not stale',
       stale_code('spikes/S36_witnessed_job') == [],
       'pairing against the oldest record flags every attacked spike')
    ck('an uncommitted code file IS stale',
       'attack.py' in stale_code('spikes/H77_demo8') or
       not os.path.isdir(os.path.join(ROOT, 'spikes/H77_demo8')),
       str(stale_code('spikes/H77_demo8')))

    # 6 · A mapping key that matches no item must be caught, because that is what
    #     happens when §8 is edited and the TSV is not.
    ck('a dangling mapping key is detectable',
       not any(r['key'].lower() in i.lower() for r in
               [{'key': 'a line that is not in section 8'}] for i in real))

    print()
    if fails:
        print(f'demo8 selfcheck: {len(fails)} FAILED — {", ".join(fails)}')
        return 1
    print('demo8 selfcheck: all checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
