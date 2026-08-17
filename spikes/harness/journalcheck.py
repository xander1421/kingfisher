#!/usr/bin/env python3
"""journalcheck.py v1 — H5. Nothing in both a DONE list and a NEXT list (§12.5).

HANDOFF is what an agent reads first after a restart, so a stale NEXT costs a
whole cycle to rediscovered work. §12.5 was earned when HANDOFF's NEXT 1
(residency feedback) and NEXT 2 (M1.7 transport) were both recorded DONE higher
in the same file, and it has since been violated twice more by the lane that
wrote the rule -- NEXT 1 "intern atom keys" was DONE as S76 in the cycle after it
was listed, and NEXT 2 "history binding for the epoch chain" had been DONE as S74
in the previous span and survived a HALT and a relaunch still standing.

WHAT THIS CATCHES, AND IT REFUSES ON IT
---------------------------------------
An IDENTIFIER (`S76`, `W2`, `M1.7`, `H16`, `D6`) appearing in both a DONE context
and a NEXT context. That is the original violation exactly, and it is decidable.

WHAT IT DOES NOT CATCH, WHICH IS THE HALF WORTH READING
--------------------------------------------------------
**It would NOT have caught either of my two violations.** Both named the same
work under different names: the NEXT entries described the task in prose while
the DONE entries named a spike number, and no identifier was shared. Matching
those needs to know that "re-encode atom keys to fixed-width interned ids" and
"S76" are the same thing, which is semantic, and §12.12 says claiming a class is
mechanised when it is not is its own defect.

So there are two tiers, deliberately unequal:

  * COLLISION -- a shared identifier. Mechanical, certain, **refuses**.
  * SUSPECT   -- a NEXT block sharing rare vocabulary with a DONE block. A
                 heuristic, printed and NOT gating, because a checker that
                 refuses on a guess trains people to bypass it, and the bypass
                 then covers the certain half too.

The SUSPECT tier is what would have flagged both of mine ("interned", "epoch
chain"), and it is stated as a hint, not a verdict.

  python3 journalcheck.py [--selfcheck]     exit 0 = no shared identifier.
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
            for i in sorted(set(ID.findall(head)) & done_ids):
                collisions.append(f'{jf}: NEXT is headed by {i}, which is recorded '
                                  f'DONE — "{label}"')
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
                  '- **NEXT 1**: finish S99, which is above as DONE\n'})
    assert c and 'S99' in c[0], c
    print('  CATCHES  a shared identifier (S99 in both DONE and NEXT)')

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
