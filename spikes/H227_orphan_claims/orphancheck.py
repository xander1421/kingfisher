#!/usr/bin/env python3
"""orphancheck.py v1 — H227. A claim whose AUTHOR is dead.

THE DEFECT THIS EXISTS FOR (§12.7 rationale)
--------------------------------------------
CLASS: **a claim whose author is dead has nobody to defend it and nobody to
retract it, and no gate in this harness partitions claims by author liveness.**

Every existing checker asks a question about the ARTEFACT and treats all claims
as equally owned:

  recheck.py    does `provenance.json` still describe the tree?
  reprocheck.py does the LEDGER row name a repro path that exists?
  ledgerlag.py  did a spike that published a RESULT reach the ledger?
  depcheck.py   is a tracked file's dependency also tracked?
  stranded.sh   does an uncommitted edit have an owner?

None of them asks WHO WOULD ANSWER IF THE NUMBER WERE WRONG. That matters
because the mission's correction mechanism is a lane retracting its own claim
in the LEDGER (CLAUDE.md, "Correcting yourself"). A dead author cannot execute
it. So an orphaned claim is not merely unverified -- it is **unretractable**,
and LEDGER standing rule 12 silently becomes a no-op for it, exactly as
`ledgerlag` measured for a missing row.

Measured 2026-08-19: `fleetcensus.sh` reports 126 DONE lines across 7 callsigns
with no roster row, no brief and no live lock. `DONE G51 AGENT-COORDINATOR` is
one of them, and `scripts/autoloop.py --eval` publishes `g51_mrr` in the live
composite the same hour.

WHAT THIS REFUSES ON, AND WHAT IT DOES NOT
------------------------------------------
It refuses on **LOAD-BEARING orphans only** -- an orphaned claim whose id is
cited by a live gate, evaluator or the LEDGER. An orphan nobody depends on is
reported and does not refuse: H14's rule, a checker that fires on known-accepted
items every run is a checker everyone learns to ignore.

STATED LIMIT (A22/family A). This decides AUTHOR LIVENESS, not TRUTH. A green
run here means someone alive is answerable for the claim -- never that the claim
reproduces. Re-running it is a separate act and this module does not do it.
"""
import os
import re
import subprocess
import sys

ROOT = os.environ.get(
    'ORPHANCHECK_ROOT',
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# A DONE line's signer. Anchored: `$3` in awk terms, and it must look like a
# callsign. fleetcensus v3 shipped a defect where prose after DONE was read as a
# callsign; the same anchor is used here rather than a looser split.
DONE = re.compile(r'^DONE\s+(\S+)\s+([A-Za-z][A-Za-z0-9_-]*)\b')
CALLSIGN_OK = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')

# Where a live gate could depend on an orphan's id.
DEPENDENTS = [
    'scripts/autoloop.py',
    '.github/autoloop/config.json',
    '.github/autoloop/PROGRAM.md',
    '.github/autoloop/evaluators',
    'out/LEDGER.md',
    'spikes/harness',
]


def aliases():
    """Callsign renames, READ FROM `MISSION_LOOP.md`, never hardcoded here.

    v1 of this file reported `CLIENT-3`'s 5 claims as orphaned. They are not:
    `MISSION_LOOP.md:430` records *"`CLIENT-3` is the same identity as
    `ATOM-3`"*, and ATOM-3 is live and answerable for every one of them. **A
    rename made a LIVE author look dead** — the exact inverse of the defect this
    module exists to find, and the more dangerous direction, because it
    manufactures orphans that a lane would then waste a cycle re-testing.

    Parsed from the sentence rather than transcribed, so the next rename reaches
    this tool by being recorded where §14.1 already requires it to be recorded.
    """
    out = {}
    p = os.path.join(ROOT, 'MISSION_LOOP.md')
    if not os.path.exists(p):
        return out
    txt = open(p, encoding='utf-8', errors='replace').read()
    for old, new in re.findall(
            r'`([A-Za-z][A-Za-z0-9_-]*)`\s+is the same identity as\s+`([A-Za-z][A-Za-z0-9_-]*)`',
            txt):
        out[old] = new
    return out


def tracked():
    """Files git actually tracks. THE POPULATION, and it is not `find`.

    v1 counted `__pycache__/*.pyc` and a lane's untracked 5,066-file snapshot of
    the repo as citation sites, so `D2` looked cited by eleven files of which
    five were compiled bytecode and one was a frozen copy of this same tree.
    That is ATOM-3's H223 -- *a tree-wide checker scans a frozen snapshot as if
    it were live source* -- filed one hour before this file was written, and
    reproduced here by its author anyway. Recorded rather than quietly fixed:
    the class survives being named, which is the argument for a mechanism.
    """
    r = subprocess.run(['git', '-C', ROOT, 'ls-files'], capture_output=True, text=True)
    return {os.path.join(ROOT, f) for f in r.stdout.split('\n') if f.strip()}


def live_callsigns():
    """Alive == has a roster row AND a brief AND a lock whose pid answers.

    Deliberately the SAME three-column definition `fleetcensus.sh` uses, read
    from the same files, so the two instruments cannot disagree about who is
    alive while disagreeing about what that means.
    """
    roster = set()
    rp = os.path.join(ROOT, 'roster.txt')
    if os.path.exists(rp):
        for ln in open(rp, encoding='utf-8', errors='replace'):
            m = re.match(r'\s*([A-Za-z][A-Za-z0-9_-]*)\b', ln)
            if m and 'RETIR' not in ln.upper():
                roster.add(m.group(1))
    live = set()
    for cs in roster:
        if not os.path.exists(os.path.join(ROOT, 'prompts', cs + '.md')):
            continue
        lock = os.path.join(ROOT, '.loop_lock.' + cs)
        if not os.path.exists(lock):
            continue
        try:
            pid = int(open(lock, encoding='utf-8').read().strip())
            os.kill(pid, 0)
        except (ValueError, OSError):
            continue
        live.add(cs)
    return live


def orphans():
    """Every DONE line whose signer is not live. Returns [(lineno, id, signer)]."""
    live = live_callsigns()
    alias = aliases()
    out = []
    ch = os.path.join(ROOT, 'CHANNEL.md')
    for n, ln in enumerate(open(ch, encoding='utf-8', errors='replace'), 1):
        m = DONE.match(ln)
        if not m:
            continue
        rid, signer = m.group(1), m.group(2)
        if not CALLSIGN_OK.match(signer):
            continue
        # Resolve the rename BEFORE the liveness test, or a live author reads dead.
        if alias.get(signer, signer) in live:
            continue
        out.append((n, rid, signer))
    return out, live, alias


def cited_by(rid):
    """Live gates/evaluators/ledger that name this id. THE LOAD-BEARING TEST.

    Word-boundary anchored: `G5` must not match `G51`, and an unanchored grep
    reported exactly that on the first run of this file.

    Returns (hard, soft). **The split is the difference between a gate that
    CONSUMES the claim and a file that merely NAMES it.** v2 refused on 74
    orphans, of which the large majority were cited only by
    `ledgerlag_baseline.json` -- a DEBT INVENTORY listing ids that lack a LEDGER
    row. Being named in a list of known debt is not a dependency on the claim's
    number, and a gate that refuses on 74 items every run is one every lane
    learns to scroll past (H14). Hard sites are the autoloop config and its
    evaluators (they feed `_composite_score`), `out/LEDGER.md` (a live graded
    claim, and the file where a retraction would have to land), and harness
    modules that reference the id in logic.
    """
    hits = []
    pat = r'\b' + re.escape(rid) + r'\b'
    trk = tracked()
    for d in DEPENDENTS:
        p = os.path.join(ROOT, d)
        if not os.path.exists(p):
            continue
        r = subprocess.run(['grep', '-rlE', pat, p], capture_output=True, text=True)
        for f in r.stdout.split('\n'):
            f = f.strip()
            # TRACKED ONLY. Compiled bytecode and a lane's untracked snapshot of
            # this repo are not citations, and counting them inflates every
            # load-bearing verdict this module issues (H223).
            if f and os.path.abspath(f) in trk:
                hits.append(os.path.relpath(f, ROOT))
    hits = sorted(set(hits))
    soft = [h for h in hits if h.endswith('_baseline.json')]
    return [h for h in hits if h not in soft], soft


def main():
    orph, live, alias = orphans()
    by_cs = {}
    for n, rid, cs in orph:
        by_cs.setdefault(cs, []).append((n, rid))

    print('live callsigns (roster row + brief + answering lock): '
          + (' '.join(sorted(live)) if live else 'NONE'))
    if alias:
        print('renames honoured (MISSION_LOOP.md): '
              + ', '.join('%s -> %s' % kv for kv in sorted(alias.items())))
    print('orphaned DONE lines: %d across %d callsign(s)\n' % (len(orph), len(by_cs)))

    loadbearing, mentioned = [], 0
    for cs in sorted(by_cs):
        ids = sorted({rid for _, rid in by_cs[cs]})
        print('  %-20s %3d line(s), %d distinct id(s)' % (cs, len(by_cs[cs]), len(ids)))
        for rid in ids:
            hard, soft = cited_by(rid)
            if hard:
                loadbearing.append((cs, rid, hard))
            elif soft:
                mentioned += 1

    print('\nLOAD-BEARING ORPHANS — no live lane owns the id, and a live gate '
          'CONSUMES it:')
    if not loadbearing:
        print('  none')
    for cs, rid, c in sorted(loadbearing):
        print('  %-20s %-14s %s' % (cs, rid, ', '.join(c)))
    print('\n  (%d further orphan(s) are named only in a *_baseline.json debt '
          'inventory —\n   reported, not gated: being listed as known debt is '
          'not a dependency on the number.)' % mentioned)

    if loadbearing:
        print('\nREFUSE: %d orphaned claim(s) are consumed by live gates. Nobody '
              'is answerable for them\n        and no lane can execute a '
              'retraction against them. Re-test or reassign each.'
              % len(loadbearing))
        return 1
    print('\nOK: no orphaned claim is load-bearing. Orphans above are reported, '
          'not gated (H14).')
    return 0


def selfcheck():
    """THE NEGATIVE CONTROL. A gate never seen red is a green light with no wire.

    Every arm builds a FIXTURE REPO inside the workspace (§10) and runs this
    same file against it via `ORPHANCHECK_ROOT`. The fixture is a real git repo
    because `tracked()` shells out to `git ls-files` — a fixture that skipped
    that would test a different program than the one that ships.

    The arm that matters is F1. `fleetcensus.sh` shipped a defect for a day in
    which every selfcheck arm exercised one expression and the headline number
    came from a DIFFERENT one that no arm touched. So F1 here targets the
    tracked-only filter specifically, because that filter is what decides the
    load-bearing verdict, and it is not exercised by C1-C3.
    """
    import shutil
    import tempfile

    base = tempfile.mkdtemp(prefix='.orphan_sc.', dir=os.path.dirname(
        os.path.abspath(__file__)))
    fail = 0

    def build(channel, mission, extra_tracked=None, untracked=None):
        d = tempfile.mkdtemp(dir=base)
        os.makedirs(os.path.join(d, 'prompts'))
        os.makedirs(os.path.join(d, 'out'))
        open(os.path.join(d, 'CHANNEL.md'), 'w').write(channel)
        open(os.path.join(d, 'MISSION_LOOP.md'), 'w').write(mission)
        # LIVE-1 is live: roster row + brief + a lock holding OUR pid, which is
        # certainly alive. DARK-1 gets none of the three.
        open(os.path.join(d, 'roster.txt'), 'w').write('LIVE-1\n')
        open(os.path.join(d, 'prompts', 'LIVE-1.md'), 'w').write('brief\n')
        open(os.path.join(d, '.loop_lock.LIVE-1'), 'w').write(str(os.getpid()))
        for rel, body in (extra_tracked or {}).items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(body)
        subprocess.run(['git', 'init', '-q'], cwd=d, capture_output=True)
        subprocess.run(['git', 'add', '-A'], cwd=d, capture_output=True)
        for rel, body in (untracked or {}).items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, 'w').write(body)
        return d

    def run(d):
        env = dict(os.environ, ORPHANCHECK_ROOT=d)
        p = subprocess.run([sys.executable, os.path.abspath(__file__)],
                           capture_output=True, text=True, env=env)
        return p.stdout, p.returncode

    try:
        # C1 — a dark author's id CONSUMED by a tracked gate must refuse.
        d = build('DONE Z1 DARK-1 body\n', 'nothing\n',
                  extra_tracked={'out/LEDGER.md': 'row for Z1 graded B\n'})
        out, rc = run(d)
        if 'DARK-1' in out and 'Z1' in out and rc == 1:
            print('  RED   C1 a dark author\'s claim, cited by a tracked gate, refuses')
        else:
            print('  MISS  C1 dark+cited did NOT refuse (rc=%s)' % rc); fail += 1

        # C2 — a LIVE author's identical claim must NOT be reported at all.
        d = build('DONE Z1 LIVE-1 body\n', 'nothing\n',
                  extra_tracked={'out/LEDGER.md': 'row for Z1 graded B\n'})
        out, rc = run(d)
        if 'Z1' not in out and rc == 0:
            print('  GREEN C2 the same claim by a LIVE author is not an orphan')
        else:
            print('  MISS  C2 a live author\'s claim was reported (rc=%s)' % rc); fail += 1

        # C3 — the rename. DARK-1 renamed to LIVE-1 must stop being an orphan,
        # and the sentence is the one MISSION_LOOP actually uses.
        d = build('DONE Z1 DARK-1 body\n',
                  'blah `DARK-1` is the same identity as `LIVE-1` and the rename\n',
                  extra_tracked={'out/LEDGER.md': 'row for Z1 graded B\n'})
        out, rc = run(d)
        if 'Z1' not in out and rc == 0:
            print('  GREEN C3 a renamed author is resolved to the live callsign')
        else:
            print('  MISS  C3 rename not honoured — a live author reads dead (rc=%s)' % rc)
            fail += 1

        # F1 — THE FILTER THAT DECIDES THE VERDICT. An identical citation in an
        # UNTRACKED file must not make the claim load-bearing. This is the arm
        # that would have caught v1 counting __pycache__ and a lane's snapshot.
        d = build('DONE Z1 DARK-1 body\n', 'nothing\n',
                  untracked={'out/LEDGER.md': 'row for Z1 graded B\n'})
        out, rc = run(d)
        if 'Z1' not in out.split('LOAD-BEARING')[-1] and rc == 0:
            print('  GREEN F1 an UNTRACKED citation does not make a claim load-bearing')
        else:
            print('  MISS  F1 untracked citation counted — H223 is back (rc=%s)' % rc)
            fail += 1
    finally:
        shutil.rmtree(base, ignore_errors=True)

    if fail:
        print('SELFCHECK FAILED: %d arm(s)' % fail)
        return 1
    print('orphancheck selfcheck: dark+cited refuses, live does not, renames '
          'resolve, and an untracked citation does not count.\n'
          'NOTE: this proves the gate distinguishes AUTHOR LIVENESS. It does NOT '
          'prove any claim reproduces — that is a separate act (see RESULT.md).')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else main())
