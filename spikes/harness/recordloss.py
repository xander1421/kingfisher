#!/usr/bin/env python3
"""recordloss.py v3 — H94 (v1), H117 (v2), H123 (v3). A completed record must not leave an append-mostly
document, and every gate in this repo was blind to it.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **commit `10ed3f2` deleted 177 lines and four whole `## Cycle`
entries (cycles 8, 9, 10, 11) from `HANDOFF.ok-1.md` and passed `pre-commit`
(refcheck + journalcheck + githygiene) and `commit-msg` CLEAN.** Its author is
this module's author, and the four cycles were its own evidence.

Cause at the site: an edit script anchored on `s.index('## NEXT 3')` in a file
carrying **two** such headings, so it hit the stale cycle-7 one and truncated
everything after it. `edits.py::anchored_replace` already refuses exactly that
(`n != count`) — but the edits that actually mutate this repo's shared documents
are throwaway `python3 - <<PY` heredocs that no checker, no gate and no reviewer
ever sees. MEASURED: of every non-vendored `.py` in the tree, exactly 3 both
write a file and use a raw `index`/`find` anchor. The class is nearly empty in
TRACKED code, so "make people import edits.py" would gate the wrong half.

So the check moved DOWNSTREAM, to the artifact: **an entry key that records
COMPLETED work, present in a document's previous committed revision, must be
present in the next one.** It does not care how the file was edited.

TWO KEY FAMILIES, both stated in the row before the first run
------------------------------------------------------------
  * `HANDOFF*.md`   — `^## Cycle <N>`
  * `CHANNEL.md`    — `^(CLAIM|DONE) <id> <lane>`, verb included in the key,
                      because §14.2's fleet headline is literally
                      `grep -c '^DONE' CHANNEL.md`: losing one silently changes
                      the number the operator watches.

IT READS THE INDEX, NOT THE TREE, AND THAT IS THE H35/H72 LESSON APPLIED FIRST
-----------------------------------------------------------------------------
`refcheck.py` and `journalcheck.py` read the tree with plain `open()`, so one
lane's uncommitted edit refuses every other lane's commits (H72) and a staged
blob can differ from what was judged (H35, F1). This module compares
`git show HEAD:<path>` against `git show :<path>` — the blob that is about to
become the commit. A co-lane's uncommitted deletion is invisible to it, and
`--selfcheck` arms 5 and 6 drive that in both directions rather than asserting it.

**AND THE COMMIT-SCOPING IS NOT WHAT BUYS THAT, WHICH v1 CLAIMED BEFORE ITS OWN
FALSIFIER SAID OTHERWISE.** Restricting the walk to `git diff --cached
--name-only` was written up as the H72 defence; the falsifier's COMMIT-SCOPE arm
then could not be made to fire, because it is a NO-OP: a covered path whose index
copy equals HEAD has identical keys either way, and `--only` builds its temp
index from HEAD plus the named paths. The scoping is kept as a cost decision (6
`git show`s per commit instead of 12) and the safety claim is withdrawn — what
defends H72 is reading the INDEX, and nothing else.

WHAT THE HISTORY SAYS, AND IT IS THE H14 QUESTION ANSWERED WITH NUMBERS
-----------------------------------------------------------------------
`--history` replays every committed revision of all five journals and of
`CHANNEL.md`, and finds **2 refusals — both read, both real** (below). The
DENOMINATOR is not quoted here: it was 265 when this module was written and 270
forty minutes later, because two other lanes committed while the run that
published it was going. §7 already says a citation to a number that changes is
stale by construction, so `--history` prints its own count next to the HEAD it
was taken at (`at afcf3a5: 270 revisions judged`) and this docstring cites the
command instead. H84 is this lane's own row for getting that wrong once.

  * `10ed3f2` — the defect above. Real, and the reason the module exists.
  * `48c9059` — `DONE H76 AGENT-1` rewritten in place to `DONE H77 AGENT-1`
    after an id collision. Its own commit message says *"CHANNEL.md is
    append-only, so the original DONE line keeps its text and the correction is
    appended beneath it."* **The diff does not do that.** A reader looking for
    `DONE H76` — including `idscope.py`, which reconciles the log against the
    queue — finds nothing. Read and judged one by one, which is what H14 asks:
    both refusals are records that left the document.

So there is no backlog and no baseline: this is a per-commit check, green on a
tree with no history, and it can only fire on the commit in front of it.

PRIOR ART RESOLVED, NOT RECALLED. ATOM-3's `d278d01` measured that a LINE-level
deletion check fires falsely here — CHANNEL.md lines are legitimately rewritten
in place and grow (1,547 -> 2,145 bytes, identical tail), which git renders as
delete-plus-add. A key-PREFIX rule is quiet on exactly that, and `--selfcheck`
arm 3 is that case as a fixture rather than as an assurance.

v2, H117 — DEFECT REMOVED: **A RENAME CARRIED EVERY RECORD OUT OF THE MODULE'S
VIEW.** `git diff --cached --name-only` reports a rename as the DESTINATION path
alone, so v1 never walked the source: `git mv` on a journal, with a cycle dropped
in the same commit, was QUIET. v2 pairs source and destination from
`--name-status -M` and judges the old content against the new path, so a rename
is quiet because the records MOVED and not because nothing was looked at. Found
by this lane's own H117 attack, behind a positive control that a pure deletion
still refuses -- without that control the silence reads as correctness.

v3, H123 — DEFECT REMOVED: a rename to a path OUTSIDE the covered set was quiet,
because the keys were still in the blob. They are not in any document a reader or
a gate looks at: `git mv HANDOFF.OTHER-9.md notes.md` deletes a journal as far as
every consumer is concerned, and it is the shape that also walked another lane's
journal past `commit-msg.hook`'s H19 ownership gate.

  python3 recordloss.py               gate: HEAD vs the index, commit paths only
  python3 recordloss.py --commit REV  replay one commit (F1: 10ed3f2 refuses)
  python3 recordloss.py --history     every revision of every covered document
  python3 recordloss.py --selfcheck   six arms in a throwaway repo
"""
import os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CYCLE = re.compile(r'^#{2,}\s*Cycle\s+(\d+)', re.M)
LOGLINE = re.compile(r'^(CLAIM|DONE)\s+(\S+)\s+(\S+)', re.M)


def git(args, cwd=None):
    p = subprocess.run(['git'] + args, capture_output=True, text=True, cwd=cwd)
    return p.stdout if p.returncode == 0 else None


def blob(spec, cwd=None):
    """The content at `<rev>:<path>`, or None meaning ABSENT at that revision.

    Absence is confirmed with `git cat-file -e`, never inferred from a non-zero
    `git show`. v1's first draft allowed rc 128 through and returned the empty
    stdout that came with it, so a `git show` that FAILED was indistinguishable
    from a document with no records in it -- family B, an error read as data,
    and the `e3b0c442` case in a checker rather than in a capture. It was found
    by `falsify.py`'s WHOLE-FILE arm coming back MISSED against a selfcheck that
    was green: the deleted-document path could not be reached at all.
    """
    if subprocess.run(['git', 'cat-file', '-e', spec],
                      capture_output=True, cwd=cwd).returncode != 0:
        return None
    return git(['show', spec], cwd)          # None here = broken repo, and the
                                             # caller refuses rather than guesses


def covered(path):
    """Which key family a path belongs to, or None. Name-based on purpose: a new
    lane's journal is covered the moment it is created, with no roster to update
    — a hardcoded list is the defect this repo keeps paying for (selfcheckall)."""
    base = os.path.basename(path)
    if re.fullmatch(r'HANDOFF(\.[\w.-]+)?\.md', base):
        return 'cycle'
    if base == 'CHANNEL.md':
        return 'log'
    return None


def keys(text, kind):
    if kind == 'cycle':
        return {'## Cycle ' + n for n in CYCLE.findall(text)}
    return {f'{v} {i} {l}' for v, i, l in LOGLINE.findall(text)}


def compare(before, after, kind):
    """Keys present before and absent after. `after is None` = the document was
    deleted outright, which loses every record in it."""
    if before is None:
        return set()                      # no previous revision: nothing to lose
    return keys(before, kind) - (keys(after, kind) if after is not None else set())


def report(losses):
    for path, lost in sorted(losses.items()):
        print(f'  {path}')
        for k in sorted(lost):
            print(f'      LOST  {k}')
    print('A completed record present in the previous revision is absent in this')
    print('one (H94). If the removal is deliberate, say so in the commit message')
    print('and use: git commit --no-verify')


def pairs(status_text):
    """(source, destination) for each changed path, renames paired.

    v1 walked `git diff --cached --name-only`, which collapses a rename to the
    DESTINATION path only -- so `git mv HANDOFF.ok-1.md HANDOFF.ok-2.md` deleted
    fifteen `## Cycle` records from a path this module never looked at, and the
    gate was silent. Found by H117's FA2c against a positive control (FA2b, a
    pure deletion, refuses), which is the arm that separated "quiet because the
    records moved" from "quiet because the source was never walked".
    """
    out = []
    for line in status_text.split('\n'):
        f = line.split('\t')
        if len(f) < 2:
            continue
        if f[0].startswith('R') and len(f) >= 3:
            out.append((f[1], f[2]))      # renamed: judge old content vs new path
        else:
            out.append((f[1], f[1]))
    return out


def gate(cwd=None):
    """HEAD vs the INDEX, for the paths this commit carries."""
    status = git(['diff', '--cached', '--name-status', '-M'], cwd) or ''
    losses = {}
    for src, dst in [(a, b) for a, b in pairs(status) if covered(a)]:
        before = blob(f'HEAD:{src}', cwd)
        if before is None:                # new file: no previous revision
            continue
        # A rename OUT of the covered corpus is a loss even though the bytes
        # survive: nothing reads `notes.md` as a journal, §14.2's headline greps
        # `^DONE` in CHANNEL.md, and `git mv HANDOFF.OTHER-9.md notes.md` is the
        # shape that walked another lane's journal past the H19 gate (H123 arm B).
        after = blob(f':{dst}', cwd) if covered(dst) else None
        lost = compare(before, after, covered(src))
        if lost:
            losses[src if src == dst else f'{src} -> {dst}'] = lost
    if losses:
        print('recordloss REFUSED — a record in HEAD is not in the commit:')
        report(losses)
        return 1
    return 0


def replay(rev, cwd=None):
    """One commit, judged as the gate would have judged it."""
    status = git(['show', '--pretty=', '--name-status', '-M', rev], cwd) or ''
    losses = {}
    for src, dst in [(a, b) for a, b in pairs(status) if covered(a)]:
        before = blob(f'{rev}^:{src}', cwd)
        if before is None:                # added by this commit
            continue
        lost = compare(before, blob(f'{rev}:{dst}', cwd), covered(src))
        if lost:
            losses[src] = lost
    return losses


def history(cwd=None):
    """F2, the H14 question: replay every revision and read the refusals."""
    tracked = (git(['ls-files'], cwd) or '').split('\n')
    docs = sorted(p for p in tracked if p and covered(p))
    total = bad = 0
    for path in docs:
        revs = (git(['rev-list', '--reverse', 'HEAD', '--', path], cwd) or '').split()
        total += max(0, len(revs) - 1)
        for rev in revs[1:]:
            lost = replay(rev, cwd).get(path)
            if lost:
                bad += 1
                subj = (git(['log', '-1', '--format=%h %s', rev], cwd) or '').strip()
                print(f'REFUSES  {path}  {subj}')
                for k in sorted(lost):
                    print(f'         LOST  {k}')
    # The count carries its operating point or it is a figure that quietly moves:
    # two lanes committed during the run that first published it and 265 became
    # 270 in forty minutes (H84, this lane's own error, one row earlier).
    head = (git(['rev-parse', '--short', 'HEAD'], cwd) or '?').strip()
    print(f'\nat {head}: {len(docs)} documents, {total} revisions judged, '
          f'{bad} refusals.')
    return bad


def selfcheck():
    import tempfile, shutil
    fails = []

    def run(*a, cwd):
        subprocess.run(a, cwd=cwd, capture_output=True, text=True, check=True)

    def restore(cwd, path):
        """`git checkout -- <p>` restores the INDEX copy, which on these arms is
        the broken blob just staged. The first version of this fixture did that
        and arm 2 inherited arm 1's deletion — the check was right and the
        fixture manufactured the defect it then reported."""
        run('git', 'reset', '-q', cwd=cwd)
        run('git', 'checkout', '-q', 'HEAD', '--', path, cwd=cwd)

    def quiet_gate(cwd):
        """The gate prints its refusal by design; a passing selfcheck must be
        silent or nobody reads the one line that matters."""
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            return gate(cwd=cwd)

    # §10: fixtures under the WORKSPACE, never /tmp — the lane that wrote this
    # module's sibling broke that rail in two consecutive cycles.
    root = tempfile.mkdtemp(prefix='.recordloss_selfcheck.', dir=HERE)
    t = os.path.join(root, 'repo')
    os.makedirs(t)
    try:
        run('git', 'init', '-q', '.', cwd=t)
        run('git', 'config', 'user.email', 'a@b', cwd=t)
        run('git', 'config', 'user.name', 'a', cwd=t)
        j = os.path.join(t, 'HANDOFF.x.md')
        c = os.path.join(t, 'CHANNEL.md')
        open(j, 'w').write('## Cycle 1 — a\n\n## Cycle 2 — b\n\n## Cycle 3 — c\n')
        open(c, 'w').write('CLAIM H1 x — short\nDONE H1 x — done\n')
        run('git', 'add', 'HANDOFF.x.md', 'CHANNEL.md', cwd=t)
        run('git', 'commit', '-q', '-m', 'base', cwd=t)

        # 1 — the defect itself: a completed cycle entry disappears.
        open(j, 'w').write('## Cycle 1 — a\n\n## Cycle 3 — c\n')
        run('git', 'add', 'HANDOFF.x.md', cwd=t)
        if quiet_gate(t) != 1:
            fails.append('a deleted `## Cycle 2` must REFUSE — the gate is inert')
        restore(t, 'HANDOFF.x.md')

        # 2 — appending must be silent, or every cycle is refused.
        open(j, 'a').write('\n## Cycle 4 — d\n')
        run('git', 'add', 'HANDOFF.x.md', cwd=t)
        if quiet_gate(t) != 0:
            fails.append('appending a new cycle must be QUIET')
        run('git', 'commit', '-q', '-m', 'append', cwd=t)

        # 3 — F3, and it is ATOM-3's d278d01 measurement as a fixture: a log line
        # rewritten IN PLACE and grown is delete-plus-add to git, and must be quiet.
        open(c, 'w').write('CLAIM H1 x — short, then much longer text added later\n'
                           'DONE H1 x — done\n')
        run('git', 'add', 'CHANNEL.md', cwd=t)
        if quiet_gate(t) != 0:
            fails.append('a log line rewritten in place and grown must be QUIET')
        run('git', 'commit', '-q', '-m', 'rewrite', cwd=t)

        # 4 — the operator's headline: a DONE line vanishing from the log.
        open(c, 'w').write('CLAIM H1 x — short, then much longer text added later\n')
        run('git', 'add', 'CHANNEL.md', cwd=t)
        if quiet_gate(t) != 1:
            fails.append('a deleted DONE line must REFUSE')
        restore(t, 'CHANNEL.md')

        # 5 — H72: the gate reads the INDEX, so a CO-LANE's uncommitted deletion
        # in the tree must not refuse a commit that does not carry that path.
        open(j, 'w').write('## Cycle 1 — a\n')          # dirty tree, not staged
        open(os.path.join(t, 'other.md'), 'w').write('x\n')
        run('git', 'add', 'other.md', cwd=t)
        if quiet_gate(t) != 0:
            fails.append("another lane's uncommitted deletion must not refuse me")
        restore(t, 'HANDOFF.x.md')

        # 6 — H35: staged good, tree bad. The commit is clean and must pass; a
        # tree-reading checker would refuse it. This is the arm that proves the
        # module judges the artifact it claims to judge.
        open(j, 'a').write('\n## Cycle 5 — e\n')
        run('git', 'add', 'HANDOFF.x.md', cwd=t)
        open(j, 'w').write('## Cycle 1 — a\n')          # tree gutted AFTER staging
        if quiet_gate(t) != 0:
            fails.append('a clean staged blob must pass while the tree is gutted')
        restore(t, 'HANDOFF.x.md')

        # 7 — deleting a covered document outright loses every record in it.
        run('git', 'rm', '-q', 'HANDOFF.x.md', cwd=t)
        if quiet_gate(t) != 1:
            fails.append('deleting a journal outright must REFUSE')
        restore(t, 'HANDOFF.x.md')

        # 8/9 — H117: a RENAME carried every record out of v1's view, because
        # `--name-only` reports only the destination. A rename that preserves the
        # records must be QUIET; a rename that drops one must still REFUSE, and
        # without the second arm the first is satisfied by a module that looks at
        # nothing at all.
        run('git', 'mv', 'HANDOFF.x.md', 'HANDOFF.y.md', cwd=t)
        if quiet_gate(t) != 0:
            fails.append('a rename that preserves every record must be QUIET')
        y = os.path.join(t, 'HANDOFF.y.md')
        text = open(y, encoding='utf-8').read()
        open(y, 'w', encoding='utf-8').write(text.replace('## Cycle 1 — a\n\n', ''))
        run('git', 'add', 'HANDOFF.y.md', cwd=t)
        if quiet_gate(t) != 1:
            fails.append('a rename that DROPS a record must REFUSE (H117 FA2c)')
        run('git', 'reset', '-q', '--hard', 'HEAD', cwd=t)   # throwaway repo

        # 10 — H123: a rename OUT of the covered set. The bytes survive and the
        # records do not: nothing reads `notes.md` as a journal, and this is the
        # shape that walked another lane's journal past the H19 ownership gate.
        run('git', 'mv', 'HANDOFF.x.md', 'notes.md', cwd=t)
        if quiet_gate(t) != 1:
            fails.append('a rename OUT of the covered set must REFUSE (H123 arm B)')
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in fails:
        print(f'  FAIL  {f}')
    if not fails:
        print('recordloss selfcheck: loss refuses (cycle, DONE, whole file, and '
              'under a rename), append/in-place-growth/clean-rename quiet, '
              'index-not-tree in both directions')
    return 1 if fails else 0


def main(argv):
    if '--selfcheck' in argv:
        return selfcheck()
    if '--history' in argv:
        return 1 if history() else 0
    if '--commit' in argv:
        rev = argv[argv.index('--commit') + 1]
        losses = replay(rev)
        if losses:
            print(f'recordloss REFUSES {rev}:')
            report(losses)
            return 1
        print(f'{rev}: no record lost')
        return 0
    return gate()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
