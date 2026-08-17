#!/usr/bin/env python3
"""journalcheck.py v1 — H5. Nothing in both a DONE list and a NEXT list (§12.5).

HANDOFF is what an agent reads first after a restart, so a stale NEXT costs a
whole cycle to rediscovered work. §12.5 was earned when HANDOFF's NEXT 1
(residency feedback) and NEXT 2 (M1.7 transport) were both recorded DONE higher
in the same file, and it has since been violated twice more by the lane that
wrote the rule -- NEXT 1 "intern atom keys" was DONE as S76 in the cycle after it
was listed, and NEXT 2 "history binding for the epoch chain" had been DONE as S74
in the previous span and survived a HALT and a relaunch still standing.

TWO TIERS, DELIBERATELY UNEQUAL
-------------------------------
  * COLLISION -- an identifier that is the SUBJECT of a NEXT title and is
                 recorded DONE. Decidable. **Refuses.**
  * SUSPECT   -- an identifier CITED in a NEXT title, or a title sharing most of
                 its rare vocabulary with a DONE title. Printed, NOT gating.

The split is measured, not chosen: `--history` replays every committed revision
of every journal, and a whole-headline id match refuses on three distinct cases
of which only one is real (`D4 and D6 as written specs`, against `the symbol
table against S74's chain` and `the retro-fit D6 owes`). A gate that refuses two
thirds falsely is the checker everyone learns to bypass -- H14 -- and the bypass
then covers the certain third too.

THE HALF WORTH READING: THE MECHANISED HALF IS NOT THE HALF THAT FIRES
----------------------------------------------------------------------
Measured 2026-08-17 on the tree that shipped this module:

  * `--history`, 45 committed journal revisions: **1 distinct real violation**
    caught (`D6`, recorded DONE above a NEXT that still listed it).
  * the live tree: **exit 0, green** -- while **4 real §12.5 violations stood in
    `HANDOFF.md`** (NEXT "physical-node accounting" = S78 DONE; NEXT "absence and
    completeness" = S79/S80 DONE; NEXT "completeness proofs" = S80 DONE; NEXT
    "explain no_death +5059" = G25 DONE). **None shares an identifier with its
    DONE entry**, so none is visible to this module. All four were found by
    reading and are fixed in the same commit.

So of 5 §12.5 violations this repo can evidence, this checker sees 1. It is worth
running -- that one is real and it recurred across two commits -- but §12.5 is
NOT mechanised by it, and a green run is not a clean journal. §12.12 already
names this class: three failure modes are not mechanisable, and claiming
otherwise is its own defect. The fix a lane can actually rely on is §7's --
state the falsifier, then run it -- and for a journal that means rereading the
NEXT list at the end of every cycle, which is what §6 asks for anyway.

One more limit, found by running it on the journal it had just corrected: `C21`
is a CYCLE label and `C2`/`C3` are QUEUE ROWS, one namespace, and nothing in the
text distinguishes them -- so a NEXT title mentioning its own cycle number trips
the SUSPECT tier. Reported here rather than special-cased, because a rule that
ignores `C\\d+` would go blind to two live P3 rows.

  python3 journalcheck.py                exit 0 = no DONE id heads a NEXT
  python3 journalcheck.py --selfcheck    both tiers, and the uncovered case
  python3 journalcheck.py --history      what it would have caught, per revision
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Identifiers this project uses for work items: spike/queue ids, not prose.
ID = re.compile(r'\b((?:[A-Z]{1,2}|M)\d+(?:\.\d+)?[a-z]?)\b')
DONE = re.compile(r'(?<![-\w])DONE\b')


def stem(w):
    """Crude suffix strip. Needed, and the selfcheck is why it exists: the first
    run of case 2 failed because `interned`/`intern` and `symbol`/`symbols` are
    the SAME work under two inflections, which is precisely how a NEXT and its
    DONE differ when nobody shares an identifier."""
    for suf in ('ings', 'ing', 'ies', 'ed', 'es', 's'):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)]
    return w


# Vocabulary too common to mean two entries are about the same work. Stemmed by
# the same function as the text, or the list silently stops matching what it names.
STOP = _RAW_STOP = '''the a an and or of to in on for with is are was were be been it its
this that these those not no yes as at by from into over under after before
next done open blocked parked run runs ran cycle cycles item items row rows
spike spikes lane lane's agent one two three first second still now then than
which what when where who why how all any each both same other another more most
less least new old real true false per via but so if then else while because
work working works number numbers proof proofs key keys set sets test tests
check checks control controls result results measure measured measurement'''
STOP = {stem(w) for w in _RAW_STOP.split()}


def is_done_header(line):
    """A line that RECORDS a verdict of DONE.

    Both guards were earned by `--history`, not by reading, and each produced
    false refusals on real committed revisions:

      * `(?<![-\\w])` -- a bare `\\bDONE\\b` matches inside **LOOP-DONE**, which
        is a §7 terminal signal and not a verdict. `- **NEXT 2**: D4 and D6 as
        written specs. They gate LOOP-DONE (§7)` therefore became its own DONE
        header, and the checker reported that NEXT as colliding with ITSELF.
        Four revisions, eight refusals, every one of them fictional.
      * a NEXT line is never a DONE header, whatever it quotes.
    """
    return (DONE.search(line) and 'NOT DONE' not in line
            and not re.match(r'^\s*-?\s*\*\*NEXT', line))


def blocks(text, header_re):
    """Text blocks introduced by a header, up to the next header or blank-ish gap."""
    out, cur = [], None
    for line in text.splitlines():
        if header_re.search(line):
            if cur:
                out.append('\n'.join(cur))
            cur = [line]
        elif cur is not None:
            if line.startswith('#') or re.match(r'^\s*-\s+\*\*NEXT', line):
                out.append('\n'.join(cur))
                cur = None
            else:
                cur.append(line)
    if cur:
        out.append('\n'.join(cur))
    return out


def rare(text):
    ws = {stem(w.lower().strip('`*_.,;:()[]"\''))
          for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text)}
    return {w for w in ws if len(w) > 4 and w not in STOP}


def subject_ids(head):
    """Ids the NEXT is ABOUT, as opposed to ids it cites.

    The leading noun phrase only: ids at the head of the title, plus any joined
    to them by `and` / `,` / `/`. Everything after the first ordinary word is a
    citation.

    MEASURED, not chosen. `--history` over 44 committed journal revisions gives
    three distinct headline collisions, and scoping to the whole headline gets
    ONE of the three right:

      REAL      `D4 and D6 as written specs`      -- D6 was recorded DONE above
      CITATION  `the symbol table against S74's chain`
      CITATION  `the retro-fit D6 owes`

    A gate that refuses two thirds falsely is the checker everyone learns to
    bypass (H14), and the bypass then covers the certain third as well. So the
    two citations are demoted to SUSPECT rather than argued away: they ARE both
    ids appearing in a DONE list and a NEXT list, which is what §12.5 forbids by
    the letter, and they are not what its rationale is about.
    """
    toks = re.findall(r"[A-Za-z0-9.'-]+|,|/", re.sub(r'[*`]', '', head))
    out, i = set(), 0
    while i < len(toks) and toks[i].lower() in ('the', 'a', 'an'):
        i += 1
    while i < len(toks):
        t = toks[i]
        if ID.fullmatch(t):
            out.add(t)
        elif not (out and t.lower() in ('and', ',', '/', '+', '&')):
            break
        i += 1
    return out


def headline(block):
    """A NEXT entry's subject: its first line with the `**NEXT n**:` marker cut."""
    first = block.strip().splitlines()[0]
    return re.sub(r'^\s*-?\s*\*\*NEXT[^:*]*\*\*?\s*:?', '', first).strip()


def queue_done():
    """Ids whose WORK_QUEUE row is DONE -- the authoritative status (§4)."""
    p = os.path.join(ROOT, 'WORK_QUEUE.md')
    if not os.path.exists(p):
        return set()
    out = set()
    for line in open(p, encoding='utf-8'):
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3 and re.search(r'\bDONE\b', cells[-1]):
            out |= set(ID.findall(cells[0]))
    return out


def journals():
    return [f for f in sorted(os.listdir(ROOT))
            if f == 'HANDOFF.md' or re.match(r'HANDOFF\..+\.md$', f)]


def scan(docs=None):
    """docs: {name: text} for the selfcheck; None reads the real journals.

    In-memory rather than a `mktemp -d` fixture on purpose. H17 is OPEN and
    undecided -- §10 says nothing outside the workspace is written and two
    harness suites write to /tmp -- so a new module does not add a third
    instance to a rail question it is not entitled to settle.
    """
    collisions, suspects = [], []
    qdone = set() if docs is not None else queue_done()
    for jf in (docs or {f: None for f in journals()}):
        text = docs[jf] if docs is not None else \
            open(os.path.join(ROOT, jf), encoding='utf-8').read()
        done = blocks(text, DONE)
        nxt = blocks(text, re.compile(r'\*\*NEXT\s+\d'))
        if not nxt:
            continue
        # Ids from the DONE HEADER LINES only, never from the block body. A block
        # runs to the next header, so body prose citing finished work ("S77 counts
        # siblings at logical positions") would otherwise enter done_ids and let a
        # citation masquerade as a verdict -- the same subject-vs-citation error
        # that made the first draft report 34 collisions.
        done_ids = {i for ln in text.splitlines() if is_done_header(ln)
                    for i in ID.findall(ln)} | qdone
        done_words = [rare(b) for b in done]
        for nb in nxt:
            label = nb.strip().splitlines()[0][:78]
            # THE HEADLINE ONLY, and the first draft got this wrong in a way worth
            # keeping visible: it searched the WHOLE NEXT block and reported 34
            # collisions, essentially all legitimate. A NEXT that CITES finished
            # work by id ("the physical-node accounting. S77 counts siblings at
            # logical positions") is not a NEXT that IS that work, and a checker
            # that cannot tell a subject from a citation would have taught every
            # lane to ignore it inside a day -- H14's failure mode, arrived at by
            # over-claiming decidability. Scoped to the headline, this catches the
            # violation §12.5 was written for -- "NEXT 2 (M1.7 transport)" where
            # M1.7's queue row is DONE -- and stays quiet on citation.
            head = re.split(r'[.—]|\s-\s', headline(nb))[0]
            subj = subject_ids(head)
            for i in sorted(subj & done_ids):
                collisions.append(f'{jf}: NEXT is headed by {i}, which is recorded '
                                  f'DONE — "{label}"')
            for i in sorted((set(ID.findall(head)) - subj) & done_ids):
                suspects.append(f'{jf}: NEXT cites {i} in its title and {i} is '
                                f'recorded DONE — subject or citation, read it — '
                                f'"{label}"')
            # HEADLINE against HEADLINE, and by RATIO. Comparing whole blocks by
            # an absolute count produced 70 suspects on a healthy journal, on
            # words like "against" and "committed" -- a heuristic that fires on
            # everything is H14's failure mode, and shipping it would have been
            # shipping the thing this module's own comments criticise. A NEXT is
            # suspect when MOST of what its title is about also titles a finished
            # entry, not when two long paragraphs share English.
            nw = rare(head)
            if len(nw) >= 3:
                for db in done:
                    dh = rare(re.split(r'[.—]', db.strip().splitlines()[0])[0])
                    shared = nw & dh
                    if len(shared) >= 3 and len(shared) / len(nw) >= 0.5:
                        suspects.append(
                            f'{jf}: NEXT "{label}" — {len(shared)} of its {len(nw)} '
                            f'title words also title a DONE entry '
                            f'({", ".join(sorted(shared)[:6])})')
    return collisions, suspects


def history():
    """Detection rate over this repo's own history, because a green run today
    says nothing about what the check would have caught (H17's lesson: coverage
    is MEASURED or it is prose). Replays every committed revision of every
    journal through scan() and prints the revisions where it would have refused.
    """
    import subprocess
    hits, seen = [], 0
    for jf in journals():
        revs = subprocess.run(['git', 'log', '--format=%h %ad', '--date=format:%H:%M',
                               '--', jf], cwd=ROOT, capture_output=True, text=True
                              ).stdout.split('\n')
        for line in [r for r in revs if r.strip()]:
            rev, when = line.split(' ', 1)
            text = subprocess.run(['git', 'show', f'{rev}:{jf}'], cwd=ROOT,
                                  capture_output=True, text=True).stdout
            if not text:
                continue
            seen += 1
            c, _ = scan({jf: text})
            for x in c:
                hits.append(f'{rev} {when}  {x}')
    for h in hits:
        print('  WOULD REFUSE  ' + h)
    print(f'journalcheck --history: {len(hits)} refusal(s) over {seen} committed '
          f'journal revision(s).')
    return 0


def main():
    if '--selfcheck' in sys.argv:
        return selfcheck()
    if '--history' in sys.argv:
        return history()
    collisions, suspects = scan()
    for s in sorted(set(suspects)):
        print('  SUSPECT    ' + s)
    for c in sorted(set(collisions)):
        print('  COLLISION  ' + c)
    if suspects and not collisions:
        print('\nsuspects are a HEURISTIC and do not gate: shared vocabulary is a '
              'hint that two entries are about\none piece of work, not proof. Read '
              'them; a stale NEXT costs a whole cycle to rediscovered work.')
    if collisions:
        print(f'\nREFUSE: {len(set(collisions))} identifier(s) appear in both a DONE '
              f'and a NEXT list (§12.5).')
        return 1
    print(f'journalcheck: no identifier appears in both a DONE and a NEXT list '
          f'across {len(journals())} journal(s)')
    return 0


def selfcheck():
    """Both tiers driven, and the LIMIT asserted as explicitly as the capability.

    The third case is the one that matters: a violation whose NEXT and DONE share
    no identifier and no vocabulary is NOT caught, and asserting that here stops
    a future reader believing this module covers §12.5.
    """
    c, _s = scan({'HANDOFF.md':
                  '- **C1 DONE: S99** built the thing\n'
                  '- **NEXT 1**: S99 and S98 as written specs\n'})
    assert c and 'S99' in c[0], c
    print('  REFUSES  an id that is the SUBJECT of a NEXT and is recorded DONE')

    # The rule's own boundary, asserted rather than left to be discovered: an id
    # behind an imperative verb is not a leading subject, so it is DEMOTED to
    # SUSPECT, not dropped. This fixture was case 1 until `--history` showed a
    # whole-headline match refusing falsely on two of three real cases.
    c, s = scan({'HANDOFF.md':
                 '- **C1 DONE: S99** built the thing\n'
                 '- **NEXT 1**: finish S99, which is above as DONE\n'})
    assert not c and s and 'S99' in s[0], (c, s)
    print('  DEMOTES  "finish S99" — an id behind a verb reports, never refuses')

    c, s = scan({'HANDOFF.md':
                 '- **C1 DONE: S98** interned every symbol to fixed-width identifiers\n'
                 '  across the whole corpus, measuring depth afterwards\n'
                 '- **NEXT 1**: intern symbols to fixed-width identifiers and measure\n'
                 '  depth across the corpus afterwards\n'})
    assert not c, c
    assert s, 'the vocabulary heuristic did not fire on a paraphrase'
    print('  FLAGS    a paraphrase with no shared id, as a SUSPECT only')

    c, s = scan({'HANDOFF.md':
                 '- **C1 DONE: S97** rewrote the launcher\n'
                 '- **NEXT 1**: teach the supervisor to notice dead lanes\n'})
    assert not c and not s
    print('  MISSES   a genuine repeat with neither id nor vocabulary shared '
          '— asserted, because this module does NOT cover §12.5')

    c, s = scan({'HANDOFF.md':
                 '- **C1 DONE: S96** did a thing\n'
                 '- **NEXT 1**: an unrelated future thing\n'})
    assert not c and not s
    print('  QUIET    on an unrelated NEXT')
    print('selfcheck: both tiers fire, and the uncovered case is asserted uncovered')
    return 0


if __name__ == '__main__':
    sys.exit(main())
