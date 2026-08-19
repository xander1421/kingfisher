#!/usr/bin/env python3
r"""statuscheck.py v3 — H114 (v1), H117 (v2), H261 (v3). A row's status is asserted in one place: the queue.

v3 RATIONALE (§12.7) — ok-1, H261, 2026-08-19. DEFECT REMOVED: **the SELECT
command this module's own docstring quotes could not read the queue.**
`prompts/ok-1.md` §6 replaced a stale hand-written list of open rows with
`awk -F'|' ...` — and `awk -F'|'` splits on the ESCAPED pipe, while `\|` is
H82's documented remedy for an unreadable status column. Measured: 40 of 344
rows carry one; the command OFFERS 14 CLOSED rows as work and HIDES 7 OPEN ones
(H1, H2, H17, H29, H41, H226, H233 — a row whose ITEM text contains the word
DONE puts it in field 4 after the naive split). `--open` uses `queue_status`,
which already masks `\|`, so the brief now points at the parser rather than at a
second one-liner. Arm 0 of `--selfcheck` asserts both directions.

WHY THIS EXISTS (§12.7 rationale)
---------------------------------
DEFECT REMOVED: **the one section of `prompts/ok-1.md` that directs `SELECT` —
"Open H rows... These are the ones nobody holds" — offered H15, H14 and H32, and
`WORK_QUEUE.md` records all three DONE.** A live peer message carried the same two
claims the same hour. I selected H14 off that section, and it cost a SELECT step;
it was caught only because §2 says read the row before taking it.

CLASS: a status assertion living outside `WORK_QUEUE.md`, which §4 calls
authoritative. This is CLAUDE.md's FIRST unmechanisable failure — claim decay
across documents — and the honest claim for this module is that it mechanises one
EDGE of it, the same way `idscope.py` mechanises the queue-vs-CHANNEL edge. A
green run is not a current document.

TWO ASSERTION FORMS, and the first rule shipped could not see the case that
earned the row
-------------------------------------------------------------------------------
  * SENTENCE  `<ID> ... is|are|stays|remains ... OPEN|DONE|BLOCKED|PARKED`
  * OFFER     an id in a block under a heading that OFFERS work ("open rows",
              "nobody holds", "unclaimed", "available") — asserted OPEN

The sentence rule alone was measured over every tracked `.md` first: 256 hits,
almost all of them `DONE <id>` lines in `CHANNEL.md` (which is the RECORD of a
DONE, not a stale claim, and is `idscope.py`'s edge) and withdrawn FINDINGS in
`RESULT.md` files, which are not row statuses. It also found **zero** hits in
`prompts/`, because the brief states its offer as a LIST UNDER A HEADING and not
as a sentence — so F3 fired against the first rule and the OFFER form exists
because of it.

IT IS COMMIT-SCOPED, AND THAT IS THE H72 LESSON RATHER THAN A PREFERENCE
-----------------------------------------------------------------------
Every journal in the tree goes stale the moment a row closes, without being
touched. A tree-wide gate would therefore refuse every lane for every other
lane's untouched document — H72 exactly. So the gate judges the assertions in the
files THIS COMMIT carries: you fix what you touch. `--all` reports the whole tree
and never gates.

A MALFORMED ROW IS NOT A MISMATCH. `WORK_QUEUE.md` carries ten rows whose status
column is not where a reader looks (H82, baselined there), so a row whose field
count differs from the file's modal width is reported UNREADABLE and never
counted as a disagreement — otherwise this module would inherit H82's defect and
report it as other lanes' errors.

v2, H117 — DEFECT REMOVED: **THE GATE READ THE QUEUE FROM HEAD AND SO REFUSED THE
COMMONEST COMMIT SHAPE HERE** — a row moving OPEN -> DONE in the same commit as the
journal recording it. It had not fired only because this lane's NEXT lists do not
phrase verdicts as `Hnn is DONE`. And the reason no suite caught it: `--selfcheck`
drives `check_text()`, a seam, while `pre-commit` runs `gate()`, which no arm of
any suite touched. THE TESTED PATH WAS NOT THE EXECUTED PATH.

  python3 statuscheck.py              gate: assertions in the commit's own files
  python3 statuscheck.py --all        every tracked brief and journal NEXT block
  python3 statuscheck.py --selfcheck  both forms, both directions
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from recordloss import git, blob          # noqa: E402  one git helper, not two

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
ID = r'[A-Z]{1,2}\d+(?:\.\d+)?[a-z]?'
STATUSES = ('OPEN', 'DONE', 'BLOCKED', 'PARKED', 'WITHDRAWN', 'RETRACTED')
# `is in BLOCKED.log` is a PATH, not a status. Found by the first run reporting
# H17 as claimed-BLOCKED off exactly that sentence.
SENTENCE = re.compile(
    r'\b(' + ID + r')\b[^.\n]{0,40}?\b(?:is|are|stays?|remains?)\b[^.\n]{0,30}?'
    r'\**(' + '|'.join(STATUSES) + r')\b(?!\.\w)', re.I)
OFFER_HEAD = re.compile(r'(?i)(open\b.*rows?|rows?\b.*open|nobody holds|unclaimed|available)')
NEXT_HEAD = re.compile(r'(?m)^(?:#{2,}\s*NEXT[^\n]*|\*\*NEXT[^\n]*)$')


def queue_status(text):
    """id -> status word, or None when the row's own shape makes it unreadable."""
    raw = [l for l in text.split('\n') if re.match(r'\|\s*' + ID + r'\s*\|', l)]
    widths = [len(re.sub(r'\\\|', 'E', l).split('|')) for l in raw]
    modal = max(set(widths), key=widths.count) if widths else 5
    out = {}
    for line, w in zip(raw, widths):
        f = [x.strip() for x in re.sub(r'\\\|', 'E', line).split('|')]
        rid = f[1].strip()
        if rid in out:                     # first allocation wins (H18)
            continue
        if w != modal:
            out[rid] = None                # H82: unreadable, never a mismatch
            continue
        cell = f[3].upper() if len(f) > 3 else ''
        out[rid] = next((s for s in STATUSES if s in cell[:60]), 'OTHER')
    return out


def assertions(path, text):
    """(line_no, id, claimed_status, form) for every status claim in `text`."""
    found = []
    base = 'prompts/' in path or path.startswith('prompts')
    for n, line in enumerate(text.split('\n'), 1):
        for m in SENTENCE.finditer(line):
            found.append((n, m.group(1), m.group(2).upper(), 'sentence'))
    if base:
        # OFFER form: ids listed under a heading that hands out work.
        for m in re.finditer(r'(?m)^#{1,6}[^\n]*$', text):
            if not OFFER_HEAD.search(m.group(0)):
                continue
            block = text[m.end():]
            block = re.split(r'(?m)^#{1,6} ', block)[0]
            start = text[:m.end()].count('\n') + 1
            for k, bl in enumerate(block.split('\n'), start):
                for rid in re.findall(r'\*\*(' + ID + r')\b', bl):
                    found.append((k, rid, 'OPEN', 'offer'))
    return found


def scope(text, path):
    """Journals are HISTORY: only their NEXT blocks are forward-looking claims.
    A cycle entry saying `H29 is BLOCKED` was true when it was written, and
    rewriting history to keep a checker quiet is the opposite of the rule."""
    if re.fullmatch(r'HANDOFF(\.[\w.-]+)?\.md', os.path.basename(path)):
        out = []
        for m in NEXT_HEAD.finditer(text):
            # A NEXT block whose own heading says it is superseded is HISTORY,
            # kept because §12.5 says a journal may not contradict itself and a
            # vanished NEXT list is how that starts. Narrow on purpose: the
            # marker must be in the HEADING, not anywhere in the block, or
            # "mark it stale" becomes a one-word way to silence this module.
            if re.search(r'(?i)\b(stale|superseded)\b', m.group(0)):
                continue
            # From m.end(), not m.start(): a block starting AT the `## NEXT`
            # heading splits on `^## ` into an empty first element, so v1's
            # NEXT arm scanned an empty string and its own selfcheck said so.
            blk = re.split(r'(?m)^## ', text[m.end():])[0]
            out.append((text[:m.end()].count('\n'), blk))
        return out
    if path.startswith('prompts/'):
        return [(0, text)]
    return []


def check(paths, qs, root=None):
    bad = []
    for p in paths:
        try:
            text = open(os.path.join(root or ROOT, p), encoding='utf-8').read()
        except OSError:
            continue
        for offset, chunk in scope(text, p):
            for n, rid, claimed, form in assertions(p, chunk):
                actual = qs.get(rid, 'NO-ROW')
                if actual is None or actual == 'NO-ROW' or actual == 'OTHER':
                    continue                     # unreadable / not a queue row
                if actual != claimed:
                    bad.append((p, offset + n, rid, claimed, actual, form))
    return bad


def report(bad):
    for p, n, rid, claimed, actual, form in bad:
        print(f'  {p}:{n} [{form}] {rid} is asserted {claimed}; '
              f'WORK_QUEUE.md says {actual}')


def gate(cwd=None):
    """`cwd` exists so this function is DRIVEABLE. v1's selfcheck exercised
    `check_text()`, a seam, while `pre-commit` runs THIS -- so the HEAD-vs-index
    defect H117 found sat in the one function no arm of any suite touched. The
    tested path was not the executed path, and a `cwd` parameter is what made the
    difference between a fixture and a test of the thing that runs."""
    root = cwd or ROOT
    # THE QUEUE THIS COMMIT CARRIES, not HEAD's. v1 read HEAD and therefore
    # refused the commonest commit in this repo: a row moving OPEN -> DONE
    # together with the journal that records it, judged against the row's
    # PREVIOUS status. Reproduced by H117 FA1 behind a positive control. `:path`
    # is the index, which under `git commit --only` is HEAD plus your paths --
    # so a lane not committing the queue still gets HEAD's answer.
    qs = queue_status(blob(':WORK_QUEUE.md', root) or blob('HEAD:WORK_QUEUE.md', root) or
                      open(os.path.join(root, 'WORK_QUEUE.md')).read())
    staged = (git(['diff', '--cached', '--name-only'], root) or '').split('\n')
    paths = [p for p in staged if p and scope('', p) is not None
             and (p.startswith('prompts/') or re.fullmatch(
                 r'HANDOFF(\.[\w.-]+)?\.md', os.path.basename(p)))]
    bad = check(paths, qs, root)
    if bad:
        print('statuscheck REFUSED — a document in this commit contradicts the queue:')
        report(bad)
        print('WORK_QUEUE.md is the authority (§4). Fix the sentence, or fix the row.')
        return 1
    return 0


def scan_all():
    qs = queue_status(open(os.path.join(ROOT, 'WORK_QUEUE.md')).read())
    tracked = (git(['ls-files'], ROOT) or '').split('\n')
    paths = [p for p in tracked if p and (p.startswith('prompts/') or re.fullmatch(
        r'HANDOFF(\.[\w.-]+)?\.md', os.path.basename(p)))]
    bad = check(paths, qs)
    unreadable = sum(1 for v in qs.values() if v is None)
    print(f'{len(paths)} briefs and journals, {len(qs)} queue rows '
          f'({unreadable} unreadable, H82 — never counted as a mismatch)')
    if bad:
        print(f'{len(bad)} contradiction(s):')
        report(bad)
    else:
        print('no document contradicts the queue')
    return len(bad)


def selfcheck():
    fails = []
    qs = {'H1': 'DONE', 'H2': 'OPEN', 'H3': None, 'H4': 'BLOCKED'}

    # 0 — H261. `--open` must not offer a CLOSED row whose text contains an
    #     escaped pipe, and the second half of this arm is what makes it
    #     load-bearing: the naive parse the brief used to hand every lane MUST
    #     list it, or the arm is asserting a property nothing threatened.
    import tempfile as _tf, os as _os, re as _re
    _fix = ('| id | item | status |\n|---|---|---|\n'
            '| H900 | a row citing `awk -F\'\\|\'` in its text | **DONE (fixture)** |\n'
            '| H901 | a plain open row | **OPEN** |\n')
    with _tf.TemporaryDirectory() as _d:
        _p = _os.path.join(_d, 'WORK_QUEUE.md')
        open(_p, 'w').write(_fix)
        _ids = [r for r, _ in open_rows('H', _p)]
        if _ids != ['H901']:
            fails.append(f'--open must exclude the escaped-pipe DONE row (got {_ids})')
        _naive = [l.split('|') for l in _fix.split('\n')
                  if _re.match(r'\|\s*H9', l)]
        _naive_open = [f[1].strip() for f in _naive
                       if len(f) > 3 and not _re.search(r'DONE|WITHDRAWN|RETRACTED|PARKED', f[3])]
        if 'H900' not in _naive_open:
            fails.append('the naive awk-equivalent parse must MIS-list H900, '
                         'or arm 0 is not testing anything')

    # 1 — the case that earned the row: an OFFER of a DONE row in a brief.
    brief = '## 6 · Open H rows, the ones nobody holds\n\n- **H1** — a thing\n- **H2** — another\n'
    got = check_text('prompts/x.md', brief, qs)
    if [(g[2], g[3], g[4]) for g in got] != [('H1', 'OPEN', 'DONE')]:
        fails.append(f'an offered DONE row must be caught, and only it (got {got})')

    # 2 — the form the first rule could not see must not be the only one: a
    #     sentence assertion in a journal NEXT block.
    jrnl = ('## Cycle 1 — H1 is DONE and that is history\n\n'
            '## NEXT 3\n1. **H4** stays OPEN and is mine\n')
    got = check_text('HANDOFF.z.md', jrnl, qs)
    if [(g[2], g[3], g[4]) for g in got] != [('H4', 'OPEN', 'BLOCKED')]:
        fails.append(f'a NEXT-block sentence must be caught (got {got})')

    # 3 — a journal's HISTORY must be quiet: the cycle entry above says `H1 is
    #     DONE`, which agrees, but a wrong one there must also not fire, or the
    #     checker asks lanes to rewrite the past.
    hist = '## Cycle 1 — H2 is DONE, as it was when I wrote this\n\n## NEXT 3\n1. nothing\n'
    if check_text('HANDOFF.z.md', hist, qs):
        fails.append('a cycle entry is HISTORY and must not be gated')

    # 4 — H82: a row whose own shape is unreadable is never a mismatch.
    if check_text('prompts/x.md', '## Open rows\n- **H3** — a thing\n', qs):
        fails.append('an UNREADABLE row (H82) must not be reported as a mismatch')

    # 5 — `is in BLOCKED.log` is a path, not a status. The first run reported it.
    if check_text('HANDOFF.z.md', '## NEXT\n1. H2, and the diagnosis is in BLOCKED.log\n', qs):
        fails.append('`BLOCKED.log` is a filename and must not read as a status')

    # 6 — an id with no row at all is not this module's business (H18 renumbers).
    if check_text('prompts/x.md', '## Open rows\n- **H99** — a thing\n', qs):
        fails.append('an id with no queue row must be quiet, not accused')

    # 8 — a NEXT block whose HEADING says STALE is history and must be quiet;
    #     the same text without the marker must still fire, or the exemption is
    #     untested and could be swallowing the live case too.
    stale = '## NEXT 3 (STALE — cycle 7\'s, superseded)\n1. **H4** stays OPEN\n'
    if check_text('HANDOFF.z.md', stale, qs):
        fails.append('a NEXT block marked STALE in its heading is history')
    if not check_text('HANDOFF.z.md', stale.replace(' (STALE — cycle 7\'s, superseded)', ''), qs):
        fails.append('the STALE exemption is swallowing the live case too')

    # 7 — the queue parser must find the status column, or every arm above is
    #     vacuous. Positive control on the real file.
    real = queue_status(open(os.path.join(ROOT, 'WORK_QUEUE.md')).read())
    if real.get('H94') != 'DONE' or real.get('H29') != 'OPEN':
        fails.append(f'queue parse control: H94={real.get("H94")} H29={real.get("H29")}, '
                     'want DONE and OPEN')
    # Arm 4 hands `None` to the consumer directly, so the PRODUCER of that None
    # -- the width rule -- would be untested without this. H82 baselines ten
    # malformed rows in this file; if that ever reaches zero the assertion is
    # what tells you, rather than the arm silently covering nothing.
    if not any(v is None for v in real.values()):
        fails.append('no row parses as UNREADABLE, so the width rule is untested '
                     'here — check H82 rather than deleting this arm')

    # 9/10 — THE EXECUTED PATH, in a throwaway repo (§10: under the workspace).
    #        Everything above drives `check_text`; `pre-commit` runs `gate()`,
    #        and H117 found a fleet-stop living in exactly that gap.
    import tempfile, shutil, subprocess
    root = tempfile.mkdtemp(prefix='.statuscheck_selfcheck.', dir=HERE)
    t = os.path.join(root, 'repo')
    os.makedirs(t)
    try:
        def run(*a):
            subprocess.run(a, cwd=t, capture_output=True, text=True, check=True)
        run('git', 'init', '-q', '.')
        run('git', 'config', 'user.email', 'a@b')
        run('git', 'config', 'user.name', 'a')
        q = os.path.join(t, 'WORK_QUEUE.md')
        j = os.path.join(t, 'HANDOFF.x.md')
        open(q, 'w').write('| id | what | status | who |\n|---|---|---|---|\n'
                           '| H90 | a thing | OPEN | x |\n')
        open(j, 'w').write('# j\n\n## NEXT 3\n1. **H90** is OPEN and mine\n')
        run('git', 'add', 'WORK_QUEUE.md', 'HANDOFF.x.md')
        run('git', 'commit', '-q', '-m', 'base')

        import io, contextlib

        def quiet_gate():
            with contextlib.redirect_stdout(io.StringIO()):
                return gate(cwd=t)

        # 9 — the commonest commit here: close the row AND record it. Must PASS.
        txt = open(q, encoding='utf-8').read().replace('| OPEN |', '| DONE (x) |')
        open(q, 'w', encoding='utf-8').write(txt)
        txt = open(j, encoding='utf-8').read().replace('is OPEN and mine', 'is DONE')
        open(j, 'w', encoding='utf-8').write(txt)
        run('git', 'add', 'WORK_QUEUE.md', 'HANDOFF.x.md')
        if quiet_gate() != 0:
            fails.append('a row closed IN THIS COMMIT must not refuse the journal '
                         'that records it (H117 FA1)')
        run('git', 'commit', '-q', '-m', 'done')

        # 10 — the journal contradicting a queue this commit does NOT touch.
        txt = open(j, encoding='utf-8').read().replace('is DONE', 'is OPEN')
        open(j, 'w', encoding='utf-8').write(txt)
        run('git', 'add', 'HANDOFF.x.md')
        if quiet_gate() != 1:
            fails.append('a journal contradicting the committed queue must REFUSE')
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in fails:
        print(f'  FAIL  {f}')
    if not fails:
        print('statuscheck selfcheck: offer and sentence forms caught, history quiet, '
              'unreadable rows and filenames and unknown ids quiet, queue parse controlled, '
              'and gate() driven in a repo for both directions')
    return 1 if fails else 0


def check_text(path, text, qs):
    """selfcheck seam: run the whole pipeline on text instead of on disk."""
    bad = []
    for offset, chunk in scope(text, path):
        for n, rid, claimed, form in assertions(path, chunk):
            actual = qs.get(rid, 'NO-ROW')
            if actual is None or actual in ('NO-ROW', 'OTHER'):
                continue
            if actual != claimed:
                bad.append((path, offset + n, rid, claimed, actual, form))
    return bad


CLOSED = ('DONE', 'WITHDRAWN', 'RETRACTED', 'PARKED')


def open_rows(prefix='H', path=None):
    r"""Rows whose status is not one of CLOSED, printed for SELECT (H261).

    THIS EXISTS BECAUSE THE COMMAND THE BRIEF HANDED LANES WAS WRONG, in the same
    section this module was written for. `prompts/ok-1.md` §6 replaced a stale
    hand-written list of open rows with

        awk -F'|' '$2 ~ /^ *H[0-9]+ *$/ && $4 !~ /DONE|WITHDRAWN|RETRACTED/ ...'

    and `awk -F'|'` splits on the ESCAPED pipe too -- while `\|` is exactly H82's
    documented remedy for a row whose status column is unreadable. Measured
    2026-08-19: 40 of 342 rows carry an escaped pipe, and for **14 H rows the
    command disagrees with a correct parse, every one of them CLOSED and shown as
    OPEN** -- including H82 itself, and H199 and H254 within an hour of their DONE
    lines being written.

    So the fix is not a better one-liner in the brief: it is to point the brief at
    the parser that already masks `\|` (`queue_status`, six lines above), which is
    the only one in the tree that agrees with `refcheck`'s row-shape rule.
    """
    text = open(path or os.path.join(ROOT, 'WORK_QUEUE.md')).read()
    qs = queue_status(text)
    out = []
    for rid, st in qs.items():
        if prefix and not rid.startswith(prefix):
            continue
        if st is None:                     # H82: unreadable shape, never silent
            out.append((rid, 'UNREADABLE-ROW-SHAPE'))
        elif st not in CLOSED:
            out.append((rid, st))
    return out


if __name__ == '__main__':
    if '--open' in sys.argv:
        a = sys.argv
        pref = a[a.index('--open') + 1] if len(a) > a.index('--open') + 1 and not a[a.index('--open') + 1].startswith('-') else 'H'
        rows = open_rows(pref)
        for rid, st in rows:
            print(f'{rid:8s} {st}')
        print(f'{len(rows)} open {pref}-row(s), parsed with the escaped-pipe rule (H261)')
        sys.exit(0)
    if '--selfcheck' in sys.argv:
        sys.exit(selfcheck())
    if '--all' in sys.argv:
        sys.exit(1 if scan_all() else 0)
    sys.exit(gate())
