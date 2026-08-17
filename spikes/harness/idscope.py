#!/usr/bin/env python3
"""idscope.py v2 — H27, H52. The queue and the append-only log must not disagree
about whether a row is closed.

v2 — DEFECT REMOVED: A PERMANENT NON-ZERO FLOOR (H52, filed by ATOM-3, fixed by
this module's author)
--------------------------------------------------------------------------
v1 refused on every divergence and **could not ever reach zero by its own stated
design** — an append-only log cannot be corrected when a namespace moves under
it, so `DONE H17` will name a renumbered row forever. A gate that is ALWAYS red
is bypassed exactly as thoroughly as one that is randomly red, and the cost was
measured rather than feared: the floor of 4 hid **H31 and H32**, genuinely
stale and a live SELECT hazard, for as long as the total sat at 6-8.

**This is my own H14 finding at a second site.** `githygiene.py` had the same
shape — a constant exit code — and I fixed it there, four cycles before shipping
v1 of this file with the defect. §12.2: fix the class, not the site.

THE CHECK IS NOT NARROWED. Every divergence is still found and still printed.
What changes is what COUNTS toward the refusal: an ADJUDICATED divergence is
listed informationally, an unadjudicated one still refuses.

    | H17 | … | OPEN — LOG-DONE-ADJUDICATED CHANNEL.md:122 (means H22) |

and the adjudication is a MECHANISM, not a marker, because a marker is an escape
hatch anyone can paste (H52's own words). To be honoured it must cite a line
number in the log, and **that line must exist and must begin `DONE <this row's
id>`**. A bare token fails. A wrong line number fails. A line that is some other
row's DONE fails. So the adjudicator has to have read the line it is explaining,
and a row whose id never appears in a DONE line cannot be silenced at all.
An adjudication that does not validate is printed as `BAD-ADJUDICATION` and
counts toward the refusal — louder than having written nothing.

Falsified in `--selfcheck`: all four forms above, on one fixture id, plus the
control that an unadjudicated divergence still refuses (without which "adjudicate
everything" would pass) and that a clean pair still exits 0.

WHY THIS EXISTS, AND IT IS A COST OF MY OWN FIX
-----------------------------------------------
H18 found four `WORK_QUEUE.md` row ids allocated twice and renumbered the later
allocation of each pair (`H17->H22`, `H18->H23`, `H19->H24`, `H20->H25`), with a
redirect written into both rows so an old citation still lands. **That repair
works for a human reader and not for a machine one.** `CHANNEL.md` is append-only
by design -- `refcheck.py` states the reason, it is a record of what a lane
believed at the time -- so the line `DONE H20 AGENT-1 provenance.py v2`, posted
before the renumber, cannot be corrected and now names a row whose id is H25.

Measured on the tree that shipped this module:

    WORK_QUEUE.md   H20 -> OPEN      (ATTACKER-1's falsify.py row, genuinely open)
    CHANNEL.md      DONE H20  x1     (AGENT-1's provenance.Control row = H25)
    CHANNEL.md      DONE H25  x0     (impossible: the DONE predates the renumber)

So **any staleness check that resolves an id against `CHANNEL.md` closes a row
the queue holds open**, and any check that resolves against `WORK_QUEUE.md` gets
it right. That is not hypothetical: it was found by building exactly the wrong
check first. A cross-scope extension to `journalcheck.py` was drafted, run, and
it falsely accused this lane's own live NEXT item. The check was wrong, the
journal was right, and the draft is what proved it.

THE RULE THIS ENFORCES
----------------------
An id-based check resolves DONE-ness against the namespace that carries a
UNIQUENESS GUARANTEE -- `WORK_QUEUE.md`, now enforced by `refcheck.py` check 5 --
and never against an append-only log, which by construction cannot be corrected
when a namespace moves under it. This module makes the disagreement itself
refuse, so a divergence is loud instead of being silently resolved differently by
whichever file a reader happens to grep.

ONE DIRECTION ONLY, and the asymmetry is the whole design:
  * CHANNEL says DONE, queue says OPEN  -> REFUSE. A reader of the log believes
    finished work that the authoritative queue still holds open.
  * queue says DONE, CHANNEL silent     -> fine. Not every closed row got a
    `DONE` line, and requiring one would fire on known-accepted items every run,
    which is H14's named failure mode.

  python3 idscope.py [--selfcheck]      exit 0 = the two records agree.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
QUEUE = 'WORK_QUEUE.md'
LOG = 'CHANNEL.md'


def queue_rows(text):
    """id -> DONE|OPEN, resolved by ROW IDENTITY (first cell), never by a line
    match. An earlier draft of this probe collected every id appearing on any
    line containing `**DONE` -- so an id merely MENTIONED inside another row's
    prose scored as closed, and `H8` came back DONE while its row reads OPEN.
    Correct numbers pointing at the wrong row is the failure CLAUDE.md names as
    unmechanisable-by-tooling, and it took a hand-check to notice.

    TWO MORE DEFECTS OF THIS FUNCTION, both live on the real queue and both
    invisible to the first selfcheck because its fixture constructed neither:

      * `line.split('|')` splits on ESCAPED pipes too. Several rows contain
        ``grep -E '...' \\| uniq -d`` inside the item cell, so cells[3] was not
        the status cell for them and `H18` -- closed minutes earlier -- read OPEN.
      * `re.search(r'\\*\\*DONE', cell)` requires the bold marks immediately
        before DONE, so `**REOPENED then DONE**` read OPEN. H1 and H2 both carry
        that form.

    The general question, and it is the one to ask of any suite: WHAT CASE DOES
    THIS FIXTURE NOT CONSTRUCT? Both are now in it.
    """
    rows = {}
    for line in text.split('\n'):
        if not line.startswith('| '):
            continue
        cells = re.split(r'(?<!\\)\|', line)
        if len(cells) < 4:
            continue
        rid = cells[1].strip().strip('*` ')
        if not re.fullmatch(r'[A-Z][A-Za-z0-9-]*\d[A-Za-z0-9-]*|[A-Z]-[A-Z0-9]+', rid):
            continue
        # The VERDICT is the leading run of a cell, up to its first dash --
        # everything after is evidence, and evidence routinely says "DONE" about
        # OTHER rows. Reading whole cells would score `OPEN -- deliberately NOT
        # done live` as closed.
        #
        # AND IT IS NOT ALWAYS cells[3]. `N1` is a TWO-column row whose verdict
        # sits inside the item cell (`~~re-derive ...~~ **DONE** — evidence`), so
        # position-based reading found an empty status cell and DEFAULTED TO
        # OPEN -- a silent wrong answer, and the third defect this module had
        # from assuming a cell shape. A verdict is therefore SEARCHED FOR, and a
        # row with none is reported UNPARSEABLE rather than defaulted: guessing
        # OPEN is exactly how a checker manufactures a divergence that is its own.
        # LAST verdict-bearing cell, not the first: an ITEM cell routinely names
        # a verdict in prose ("blocked behind H91, which is DONE"), so a forward
        # search reads the item and calls the row closed. Reverse order takes the
        # status cell where one exists and falls back to the item cell only for a
        # two-column row like N1, which is exactly the intended precedence.
        verdict = None
        for cell in reversed(cells[2:]):
            head = re.split(r'—|--', cell)[0]
            if re.search(r'\b(DONE|OPEN|BLOCKED\w*|PARKED|GATED|CANCELLED|REOPENED)\b', head):
                verdict = head
                break
        if verdict is None:
            rows[rid] = 'UNPARSEABLE'
        else:
            rows[rid] = 'DONE' if re.search(r'\bDONE\b', verdict) else 'OPEN'
    return rows


def log_done(text):
    """ids a `DONE <id> ...` line in the append-only log declares closed."""
    return {m.group(1) for m in
            re.finditer(r'^DONE\s+([A-Za-z][A-Za-z0-9._-]*)', text, re.M)}


ADJ = re.compile(r'LOG-DONE-ADJUDICATED\s+' + re.escape(LOG) + r':(\d+)')


def adjudications(text):
    """id -> cited log line number, for rows carrying the adjudication token.

    Parsed by ROW IDENTITY like everything else here, so a token sitting in one
    row's prose cannot adjudicate a neighbour. The number is NOT trusted at this
    point -- `scan` resolves it against the log, which is the half that makes
    this a mechanism instead of a marker.
    """
    out = {}
    for line in text.split('\n'):
        if not line.startswith('| '):
            continue
        cells = re.split(r'(?<!\\)\|', line)
        if len(cells) < 4:
            continue
        rid = cells[1].strip().strip('*` ')
        m = ADJ.search(line)
        if m:
            out[rid] = int(m.group(1))
    return out


def scan(queue_text=None, log_text=None):
    qtext = (queue_text if queue_text is not None
             else open(os.path.join(ROOT, QUEUE), encoding='utf-8').read())
    ltext = (log_text if log_text is not None
             else open(os.path.join(ROOT, LOG), encoding='utf-8').read())
    q = queue_rows(qtext)
    d = log_done(ltext)
    adj = adjudications(qtext)
    lines = ltext.split('\n')

    problems, settled = [], []
    for rid in sorted(d):
        if q.get(rid) != 'OPEN':
            continue
        base = (f'{LOG} declares `DONE {rid}` while {QUEUE} holds row {rid} OPEN '
                f'-- a reader of the log closes a row the queue still owns')
        n = adj.get(rid)
        if n is None:
            problems.append(('DISAGREE', base))
        elif not (1 <= n <= len(lines)
                  and re.match(r'^DONE\s+' + re.escape(rid) + r'\b', lines[n - 1])):
            # An adjudication that does not resolve is worse than none: it reads
            # as settled. Counted, and named as the reason.
            problems.append(('BAD-ADJUDICATION',
                             f'row {rid} cites {LOG}:{n}, which is not a '
                             f'`DONE {rid}` line -- ' + base))
        else:
            settled.append(f'row {rid} adjudicated against {LOG}:{n}')

    for s in settled:
        print('  ADJUDICATED ' + s)
    for kind, p in problems:
        print(f'  {kind} ' + p)
    if problems:
        print(f'\nREFUSE: {len(problems)} UNADJUDICATED id(s) resolve to a '
              f'different status depending on which file you read '
              f'({len(settled)} adjudicated, not counted).\n'
              f'        An append-only log cannot be corrected when a namespace '
              f'moves under it, so the divergence has to be loud rather than\n'
              f'        silently resolved. Adjudicate one with '
              f'`LOG-DONE-ADJUDICATED {LOG}:<line>` in its queue row -- the line '
              f'must be that row\'s own DONE.')
        return 1
    print(f'idscope: {QUEUE} and {LOG} agree on every id the log declares DONE '
          f'({len(d)} declared, {len(q)} rows, {len(settled)} adjudicated)')
    return 0


def selfcheck():
    """Both directions, because a check only ever seen firing is as
    uninformative as one only ever seen passing."""
    # Assembled rather than written as literals: a literal `DONE H99` line in
    # this source would be picked up by anything grepping the tree for DONE
    # lines, and exempting a checker from its own subject matter is the
    # H-HOOKREG blind spot.
    stale, agreed, silent = 'H' + '90', 'H' + '91', 'H' + '92'
    piped, reopened, cited = 'H' + '93', 'H' + '94', 'H' + '95'
    merged = 'H' + '96'
    queue = ('| id | item | status |\n|---|---|---|\n'
             f'| {stale} | held open by the queue | OPEN |\n'
             f'| {agreed} | closed in both | **DONE** — evidence |\n'
             f'| {silent} | closed, never announced | **DONE** — evidence |\n'
             # the two cases the first fixture did not construct, and both were
             # live on the real queue while this module reported them wrongly
             f'| {piped} | an item cell containing `grep x \\| uniq -d` | **DONE** — evidence |\n'
             f'| {reopened} | closed after being reopened | **REOPENED then DONE** — evidence |\n'
             # and the inverse: an OPEN row whose EVIDENCE cites a closed
             # neighbour. Reading the whole status cell scores this DONE.
             f'| {cited} | open, and its note mentions a DONE row | OPEN — blocked behind {agreed}, which is DONE |\n'
             # N1's shape: TWO columns, verdict inside the item cell. Position-
             # based reading found an empty status cell and defaulted to OPEN.
             f'| {merged} | ~~superseded~~ **DONE** — evidence |\n')
    log = (f'DONE {stale} LANE-1 the log closes what the queue holds open\n'
           f'DONE {agreed} LANE-1 both records agree\n'
           f'DONE {piped} LANE-1 both agree, and the row has an escaped pipe\n'
           f'DONE {reopened} LANE-1 both agree, and the row was reopened first\n'
           f'DONE {cited} LANE-1 the log closes a row the queue holds open\n'
           f'DONE {merged} LANE-1 both agree; the verdict is inside the item cell\n')

    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = scan(queue, log)
    out, bad = buf.getvalue(), []

    def check(cond, good, note):
        print(f'  {"CATCHES" if cond else "MISSES "} {note}' if good
              else f'  {"FALSE-POSITIVE" if cond else "QUIET  "} {note}')
        if cond != good:
            bad.append(note)

    check(f'`DONE {stale}`' in out, True,
          'the log closing a row the queue holds OPEN')
    check(f'`DONE {cited}`' in out, True,
          'an OPEN row whose EVIDENCE cites a DONE neighbour')
    check(agreed in out, False,
          'on a row both records close')
    check(silent in out, False,
          'on a row the queue closed and the log never announced')
    check(piped in out, False,
          'on a closed row whose item cell contains an escaped pipe')
    check(reopened in out, False,
          'on a row closed as "REOPENED then DONE"')
    check(merged in out, False,
          'on a two-column row whose verdict sits in the item cell')
    if rc == 0:
        print('  MISSES  it did not refuse at all'); bad.append('refusal')
    else:
        print('  REFUSES on a real divergence')

    # ---- v2, H52: the adjudication must be a MECHANISM, not a marker --------
    # One fixture id, four token forms, so no new id has to be reserved (H64:
    # fixture ids live in the same namespace as real allocations).
    def mini(extra, log_text):
        queue = ('| id | item | status |\n|---|---|---|\n'
                 f'| {stale} | held open by the queue | OPEN{extra} |\n')
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            r = scan(queue, log_text)
        return r, b.getvalue()

    donel = f'DONE {stale} LANE-1 the log closes what the queue holds open\n'
    log_2 = 'NOTE LANE-1 filler so the DONE is not on line 1\n' + donel
    log_o = f'DONE {agreed} LANE-1 a DIFFERENT row\'s DONE\n' + donel

    r, o = mini(f' -- LOG-DONE-ADJUDICATED {LOG}:2', log_2)
    check(r == 0 and 'ADJUDICATED' in o, True,
          'a VALID adjudication (cited line is that row\'s own DONE) stops the refusal')
    # Without this, "adjudicate everything" satisfies the check above (H68).
    r, o = mini('', log_2)
    check(r == 1 and 'DISAGREE' in o, True,
          'an UNADJUDICATED divergence still refuses')
    r, o = mini(' -- LOG-DONE-ADJUDICATED', log_2)
    check(r == 1 and 'DISAGREE' in o, True,
          'a BARE marker with no line citation does not silence anything')
    r, o = mini(f' -- LOG-DONE-ADJUDICATED {LOG}:1', log_2)
    check(r == 1 and 'BAD-ADJUDICATION' in o, True,
          'a citation to a line that is not a DONE line is named and counted')
    r, o = mini(f' -- LOG-DONE-ADJUDICATED {LOG}:1', log_o)
    check(r == 1 and 'BAD-ADJUDICATION' in o, True,
          "a citation to ANOTHER row's DONE line is named and counted")
    r, o = mini(f' -- LOG-DONE-ADJUDICATED {LOG}:99', log_2)
    check(r == 1 and 'BAD-ADJUDICATION' in o, True,
          'a citation past the end of the log is named and counted')
    # F3, anti-inversion: the exit code must still be able to be 0. A checker
    # whose floor moved from "always 1" to "always 1 unless you paste a token"
    # is a different constant, not a fix.
    r, _ = mini('', f'DONE {agreed} LANE-1 unrelated, and {stale} is not closed\n')
    check(r == 0, True, 'a pair with no divergence at all still exits 0')

    if bad:
        print(f'SELFCHECK FAILED: {bad}')
        return 1
    print('selfcheck: the one refusing direction fires, both quiet directions '
          'stay quiet, and it refuses')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv else scan())
