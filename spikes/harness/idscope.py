#!/usr/bin/env python3
"""idscope.py v4 — H27, H52, H103, H167. The queue and the append-only log must
not disagree about whether a row is closed — in EITHER direction.

v4 CHANGELOG (H167, AGENT-2, 2026-08-19; §5 — corrected in place, nothing below
this block edited).
DEFECT REMOVED: **A DEFECT COUNTER PUBLISHED WITHOUT ITS BASELINE REPORTS GROWTH
AS FLOOR.** v3 printed one number — `ROWLESS: N id(s). REPORTED, NOT GATED ...
the floor is other lanes' rows and no committer can clear it` — and that
sentence was measured true of 14 NAMED ids on 2026-08-18. MEASURED AGAIN on
2026-08-19 (`spikes/H167_rowless_baseline/probe.py`):

  * the live set is **24**, and the justification is asserted over a set **15 of
    whose members did not exist when it was written**;
  * the printed number moved **14 -> 24** while **15 ids landed and 5 were
    cleared** — one figure, hiding 20 movements, and it cannot distinguish an
    accumulated floor from an incoming instance.

SECOND HALF OF THE CLASS, and it is why the count could never reach the 0 its
own stated ceiling requires before it may gate: **v3 merged CLAIM-only ids with
DONE ids under one total.** A CLAIM-only rowless id is the SANCTIONED
intermediate state of §2's own SELECT step — *"Post `CLAIM <item> <CALLSIGN>` to
CHANNEL.md first"* — so a correct lane MANUFACTURES one every cycle; a
DONE-rowless id is terminal and never reconciled. Live split: **11 CLAIM-only,
13 DONE.**

**MEASURED WITHOUT INTENDING TO, AND IT IS THE SHARPEST DATUM HERE: during the
single cycle that wrote this fix, CLAIM-only went 6 -> 11 while DONE-rowless
stayed at 13.** Four other lanes claimed H123/H165/H166/H168 and this lane
claimed H167, all correct §2 behaviour, all of it landing in the number v3 had
just declared un-gateable. So the merged total does not merely fail to reach 0 —
it is driven by the rate at which lanes obey the loop contract. v3's own
selfcheck asserts the merge ("an id CLAIMED with no queue row" / "an id DONE
with no queue row" both assert `ROWLESS`, and one asserts the exit code does NOT
move): the module TESTED that it could not tell them apart.

WHY THE GATE LANDS ON THE AUTHOR AND NOT ON THE NEXT COMMITTER, which is H52/H72
and is the reason v3 refused to gate at all. Measured, not argued — for each of
the 13 DONE-rowless ids, the commit that introduced its `DONE <id>` line:

     8 of 13   did NOT carry WORK_QUEUE.md in that commit
     2 of 13   carried it and still filed no row (G45, H76)
     3 of 13   are UNCOMMITTED, in the working tree right now (G92, H161, H163)

So the incoming set IS clearable — by the lane posting the DONE, in the commit
that posts it — while the accumulated set is not. v3 read one property off the
other. Two mechanisms, each with one job:

  1. `BASELINE_ROWLESS_DONE` pins the 13 accumulated ids BY NAME, the pattern
     `refcheck.BASELINE_ROW_SHAPE` already ships here. It can only shrink; the
     selfcheck asserts a member of it does not gate.
  2. The gate is scoped to a DONE line THIS TREE INTRODUCES (`prior_done`, read
     from `HEAD:CHANNEL.md` via the one `recordloss.blob` helper the harness
     already shares). Without it a new id refuses every OTHER lane's commit for
     a row it cannot write — H72 exactly, and the backlog v3 was right to fear.

NOT NARROWED: every rowless id is still found and still printed, CLAIM and DONE
alike. What changed is what COUNTS toward the refusal.

CEILING, STATED: with no git context (`HEAD:CHANNEL.md` absent — a fresh clone)
`prior_done` is None and UNFILED reports without gating. That is a degrade to
v3's behaviour rather than to a false green, and `--selfcheck` asserts it, so it
is a decision and not H30's silent narrowing.

FALSIFIERS, stated in CHANNEL.md before this directory existed, all four quiet:
F1 no checker pinned a rowless baseline or branched its VERDICT on CLAIM vs DONE
(`refcheck` baselines row SHAPE, a different subject). F2 the live set is 19,
not the docstring's 14. F3 a lane posting CLAIM before its row exists is NOT
refused — asserted in `--selfcheck`. F4 the incoming set is clearable by its
author, measured above, so gating it is not H52 again.

v3 CHANGELOG (H103, ATTACKER-1, 2026-08-18; §5 — corrected in place, nothing
above this line edited).
DEFECT REMOVED: **A TWO-SIDED INVARIANT CHECKED ON ONE SIDE ONLY.** v2's whole
comparison was `for rid in sorted(d): if q.get(rid) != 'OPEN': continue`, where
`d` came from `log_done()` — DONE lines and nothing else. Two consequences, and
both were live:

  * a CLAIM was never read at all, so an id could be claimed and worked on with
    no queue row in existence;
  * `q.get(rid)` returns None for an id the queue does not carry, and
    `None != 'OPEN'` is TRUE, so the id was SKIPPED. **ABSENT READ AS CLEAR** —
    the third time in this harness after H40's `-1` lock reading and H88's
    missing fail counter, and the second time in a module of mine.

MEASURED at pinned `10ed3f2`, before the author repaired his own instance by
hand (`spikes/H103_onesided_join/probe.py`): **14 ids appear in `CHANNEL.md`
with no `WORK_QUEUE.md` row of any kind** — G26 G32 G43 H39 H42 H76 H86 H88 H89
H93 S29 S81 S82 S83, spanning three series and four lanes. v2 reported 0 of
them, and so did `refcheck.py`, `journalcheck.py` and `recordloss.py`; the F1
falsifier was "if any checker already names one, this is a non-finding" and it
did not fire. Two of the fourteen were this module's author's, one of them
carrying a fix that was live on the fleet at the time.

CEILING, STATED RATHER THAN PAPERED OVER: **ROWLESS does not change the exit
code.** The floor is 14 pre-existing ids across four lanes and nobody can clear
another lane's; a checker that refuses on a permanent floor is bypassed as
thoroughly as a flaky one (H14, H52 — this module's own previous row). It is
reported, counted, and printed on every run. If the floor ever reaches 0, making
it refuse is a one-line change and its selfcheck asserts the current choice so
the change cannot be silent.

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

# THE 13 ACCUMULATED DONE-ROWLESS IDS, PINNED BY NAME (H167, AGENT-2,
# 2026-08-19). BASELINED, NOT GRANDFATHERED SILENTLY -- the pattern is
# `refcheck.BASELINE_ROW_SHAPE`, and the reason is the same one v3 gave for not
# gating at all: these belong to four lanes, 11 of the 13 were introduced by a
# commit that never carried WORK_QUEUE.md, and no committer today can write
# another lane's verdict into a row. What v3 could not do is tell them from an
# id arriving NOW, whose author is holding the commit that introduces it.
#
# THIS LIST MAY ONLY SHRINK. Filing a row for any of these removes it from the
# printed report automatically; deleting it from here without filing the row
# makes the gate fire, which is the intended direction. Adding to it is how a
# baseline becomes an escape hatch (H52's words), so the selfcheck asserts both
# that a member does not gate and that a non-member does.
BASELINE_ROWLESS_DONE = frozenset((
    'G40', 'G45', 'G92', 'H42', 'H76', 'H161', 'H163',
    'M1.14', 'S41', 'S81', 'S82', 'S83', 'W9',
))


def prior_done(root=None):
    """Ids the log ALREADY declared DONE at HEAD, or None meaning NO GIT CONTEXT.

    None is not an empty set and the difference is the whole scoping rule: empty
    would make every accumulated id read as introduced-by-this-tree and refuse
    the next lane to commit anything, which is H72. Absent (a fresh clone, no
    HEAD) degrades to v3's report-without-gating -- the safe direction, asserted
    in --selfcheck so it is a decision and not H30's silent narrowing.
    """
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from recordloss import blob            # the one git helper, not two
    text = blob('HEAD:' + LOG, root or ROOT)
    if text is None:
        return None
    return {i for i, p in log_ids(text).items() if 'DONE' in p}


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


ID = re.compile(r'^[A-Z]\d+$|^[A-Z]\d+\.\d+$')


def log_ids(text):
    """Every ID-SHAPED subject the log names, whatever the prefix.

    v2 read DONE lines only, which is half of a two-sided invariant. This reads
    CLAIM too — a row worked on without ever being filed is the case the module
    was blind to.

    ID-SHAPED IS THE WHOLE PREDICATE, and it is the F2 falsifier of H103 rather
    than a nicety: 33 prefix lines in the live log name a subject that is not an
    id at all (`attacker-lane`, `H73-RECONCILE`, `S20-ATTACK`, `prompts/`). A
    naive "every CLAIM needs a row" accuses all of them, which is this repo's
    correct-numbers-wrong-attribution failure. §14.3's `VERDICT <candidate>
    <APPROVE|REJECT|ABSTAIN> <atom>` puts its subject first as well and is
    deliberately NOT read here: a candidacy is not a queue row.
    """
    out = {}
    for line in text.split('\n'):
        m = re.match(r'^(CLAIM|DONE)\s+(\S+)', line)
        if not m:
            continue
        tok = m.group(2).strip('*` ')
        if ID.match(tok):
            out.setdefault(tok, set()).add(m.group(1))
    return out


def scan(queue_text=None, log_text=None, seen_done=None):
    qtext = (queue_text if queue_text is not None
             else open(os.path.join(ROOT, QUEUE), encoding='utf-8').read())
    ltext = (log_text if log_text is not None
             else open(os.path.join(ROOT, LOG), encoding='utf-8').read())
    q = queue_rows(qtext)
    d = log_done(ltext)
    rowless = {i: p for i, p in log_ids(ltext).items() if i not in q}
    # THE SPLIT v3 DID NOT MAKE, and it is why its count could never reach the 0
    # its own ceiling required. A CLAIM-only rowless id is §2 SELECT's sanctioned
    # intermediate state -- "Post `CLAIM <item> <CALLSIGN>` to CHANNEL.md first"
    # -- so a correct lane produces one every cycle and it must never gate. A
    # DONE-rowless id is terminal: the work is finished and invisible to the
    # authoritative file.
    done_rowless = {i for i, p in rowless.items() if 'DONE' in p}
    claim_only = set(rowless) - done_rowless
    # Scoped to what THIS TREE INTRODUCES. `seen_done is None` means no git
    # context, and it reports without gating rather than treating every
    # accumulated id as new (H72).
    if seen_done is None:
        unfiled = set()
    else:
        unfiled = done_rowless - BASELINE_ROWLESS_DONE - seen_done
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

    for rid in sorted(rowless, key=lambda r: (r[0], int(re.sub(r'\D', '', r) or 0))):
        seen = '/'.join(sorted(rowless[rid]))
        print(f'  ROWLESS {rid} is {seen} in {LOG} and has NO {QUEUE} row -- '
              f'the queue is authoritative (§2 SELECT reads it), so this work is '
              f'invisible to every lane that has not read the log')
    if rowless:
        print(f'  ROWLESS: {len(rowless)} id(s) = {len(claim_only)} CLAIM-only '
              f'(§2 SELECT posts CLAIM before the row exists -- sanctioned, never '
              f'gated) + {len(done_rowless)} DONE '
              f'({len(BASELINE_ROWLESS_DONE & done_rowless)} baselined accumulated, '
              f'{len(unfiled)} introduced by this tree and GATED).\n'
              f'          A bare total cannot tell an accumulated floor from an '
              f'incoming instance, and the CLAIM-only side is manufactured by '
              f'lanes OBEYING §2 SELECT.\n'
              f'          Churn is cited, never quoted: '
              f'spikes/H167_rowless_baseline/rowless.json, regenerated by its '
              f'probe.py (H167 -- a number in a message goes stale, an artifact '
              f'does not).\n')

    for s in settled:
        print('  ADJUDICATED ' + s)
    for rid in sorted(unfiled):
        problems.append(('UNFILED',
                         f'{LOG} declares `DONE {rid}` in THIS tree and {QUEUE} '
                         f'carries no row for it -- the queue is authoritative '
                         f'(§4), so finished work is invisible to every lane that '
                         f'has not read the log. File the row in the commit that '
                         f'posts the DONE; it is not in the H167 baseline, so its '
                         f'author is the committer holding it'))
    for kind, p in problems:
        print(f'  {kind} ' + p)
    if problems:
        nun = sum(1 for k, _ in problems if k == 'UNFILED')
        print(f'\nREFUSE: {len(problems) - nun} UNADJUDICATED id(s) resolve to a '
              f'different status depending on which file you read, and {nun} '
              f'DONE id(s) this tree introduces have no row at all '
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
    fresh, carried = 'H' + '97', 'H' + '98'
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

    # ---- v3, H103: the OTHER side of the invariant -------------------------
    # v2's fixture could not construct this case at all: every fixture id it
    # built had a queue row, so "the log names an id the queue does not carry"
    # was unreachable from the suite. That is the standing question -- WHAT CASE
    # DOES THIS FIXTURE NOT CONSTRUCT -- answered against itself.
    rowq = ('| id | item | status |\n|---|---|---|\n'
            f'| {stale} | held open by the queue | OPEN |\n')

    def rowscan(log_text, seen_done=None):
        b = io.StringIO()
        with contextlib.redirect_stdout(b):
            r = scan(rowq, log_text, seen_done=seen_done)
        return r, b.getvalue()

    r, o = rowscan(f'CLAIM {agreed} LANE-1 claimed, never filed\n')
    check(f'ROWLESS {agreed}' in o, True, 'an id CLAIMED with no queue row')
    check(r != 0, False, 'and ROWLESS alone does NOT change the exit code '
                         '(the v3 ceiling: the floor is other lanes\' rows)')
    # ---- H167. THE FOUR ARMS THE MERGED COUNT COULD NOT EXPRESS -------------
    # F3, and it is the arm that decides whether this gate is H52 again: a lane
    # doing exactly what §2 SELECT tells it -- post the CLAIM before the row
    # exists -- must not be refused. Driven WITH a git context, because without
    # one nothing gates and the arm would pass on a disabled gate. Measured on
    # the live tree while this was written: 11 concurrent CLAIM-only ids.
    r, o = rowscan(f'CLAIM {fresh} LANE-1 §2 says claim first\n', seen_done=set())
    check(r == 0 and 'UNFILED' not in o, True,
          'F3: a CLAIM posted before its row exists is NOT gated')
    # THE GATE FIRES. Same id, same empty prior set, DONE instead of CLAIM -- so
    # the only difference between the arm above and this one is the property the
    # module claims to read. A control that cannot fail is not a control.
    r, o = rowscan(f'DONE {fresh} LANE-1 finished, no row filed\n', seen_done=set())
    check(r == 1 and f'UNFILED' in o and fresh in o, True,
          'a DONE-rowless id THIS tree introduces refuses')
    # H72 SCOPING: the same line, already at HEAD, is another lane's accumulated
    # row and must not refuse this committer. Without this arm the fix would
    # refuse every lane for a row it cannot write, which is what v3 feared.
    r, o = rowscan(f'DONE {fresh} LANE-1 finished, no row filed\n',
                   seen_done={fresh})
    check(r == 0, True, 'an accumulated DONE-rowless id does NOT gate the next '
                        'committer (H72 scoping)')
    # THE BASELINE IS A LOOKUP AND NOT AN ESCAPE HATCH: a member does not gate,
    # and the arm above proves a NON-member does, so the list is load-bearing in
    # both directions. `carried` is injected rather than taken from the real
    # frozenset, so shrinking that list cannot silently disarm this arm.
    # `globals()`, NOT `import idscope` -- run as __main__ that import builds a
    # SECOND module object and the injection never reaches the namespace scan()
    # actually reads, so this arm shipped INERT and passed. Caught by it failing
    # the moment it was pointed at a real assertion. Same family as statuscheck
    # v2's row: THE TESTED PATH WAS NOT THE EXECUTED PATH.
    g = globals()
    saved = g['BASELINE_ROWLESS_DONE']
    try:
        g['BASELINE_ROWLESS_DONE'] = frozenset((carried,))
        r, o = rowscan(f'DONE {carried} LANE-1 baselined accumulated\n',
                       seen_done=set())
        check(r == 0, True, 'a BASELINED DONE-rowless id does not gate')
        # and the SAME injected list must still refuse a non-member, or "does
        # not gate" above is satisfied by a gate that never fires at all.
        r, o = rowscan(f'DONE {fresh} LANE-1 not in the injected baseline\n',
                       seen_done=set())
        check(r == 1, True, 'and a NON-member of that same baseline still gates')
    finally:
        g['BASELINE_ROWLESS_DONE'] = saved
    # THE STATED CEILING, asserted so the degrade is a decision and not H30's
    # silent narrowing: no git context (`HEAD:CHANNEL.md` absent) reports and
    # does not gate.
    r, o = rowscan(f'DONE {fresh} LANE-1 no git context here\n', seen_done=None)
    check(r == 0 and f'ROWLESS {fresh}' in o, True,
          'with no git context UNFILED reports without gating (v3 behaviour)')
    r, o = rowscan(f'DONE {silent} LANE-1 finished, never filed\n')
    check(f'ROWLESS {silent}' in o, True, 'an id DONE with no queue row')
    r, o = rowscan(f'CLAIM {stale} LANE-1 claimed, and the row exists\n')
    check('ROWLESS' in o, False, 'on an id the queue does carry')
    # F2 of H103: 33 live prefix lines name a subject that is not an id. A naive
    # predicate accuses every one of them.
    r, o = rowscan('CLAIM attacker-lane LANE-1 a role, not a row\n'
                   f'CLAIM {stale}-RECONCILE LANE-1 a suffixed subject\n'
                   'DONE prompts/ LANE-1 a path\n'
                   'VERDICT LANE-9 REJECT LANE-1 a candidacy, and §14.3 puts the '
                   'CANDIDATE first, which is why VERDICT is not read here\n')
    check('ROWLESS' in o, False, 'on prefix lines whose subject is not id-shaped')
    # No trade: the direction v2 already had must still refuse while the new one
    # is reporting. A fix that swaps one blind side for the other reads as green.
    r, o = rowscan(f'DONE {stale} LANE-1 the log closes what the queue holds open\n'
                   f'CLAIM {agreed} LANE-1 and an unfiled id in the same log\n')
    check(r == 1 and 'DISAGREE' in o and f'ROWLESS {agreed}' in o, True,
          'both directions reported from one pass, and the old one still refuses')

    if bad:
        print(f'SELFCHECK FAILED: {bad}')
        return 1
    print('selfcheck: both refusing directions fire, every quiet direction stays '
          'quiet, ROWLESS reports without gating, and it refuses')
    return 0


if __name__ == '__main__':
    sys.exit(selfcheck() if '--selfcheck' in sys.argv
             else scan(seen_done=prior_done()))
