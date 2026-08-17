#!/usr/bin/env python3
"""refcheck.py v5 — H4/H18/H33/H41. Every §N / guardrail / file / ROW-ID citation resolves.

v5 RATIONALE (§12.7) — TWO DEFECTS REMOVED, and H41 named only one of them:
  (a) only INLINE backticked paths were matched, so a path inside a ```sh fence
      -- the form a lane copies and runs -- was never read.
  (b) a dot-slash path was skipped by check 4's first-segment rule, because the
      first segment of a dot-slash token is `.`, not a listdir entry.
MEASURED BEFORE WRITING ANYTHING, on all 45 harness files, because "a real
false-positive surface" was the row's stated reason nobody had taken it: (a)
alone flags NOTHING AT ALL — including the live instance the row itself cites —
(b) alone flags 2, together 4, zero false positives at either half. So shipping
the half the row named would have been a green checker over the row's own
evidence: §12.2 at my own site, in the module whose v4 block is about that.
THE FIRST RUN FLAGGED THIS FILE THREE TIMES: a rationale block naming an absent
path is indistinguishable from a broken citation of it, which is the trap
selfcheck() builds every fixture out of string parts to avoid. Noted at check 4.
SCOPE, and it is a narrowing with a cost stated: `HANDOFF.<lane>.md` journals
leave the PATH check and stay in every other. A journal has ONE legal writer
(H10) and this module gates every lane's commit, so a broken path in one can be
tripped only by lanes forbidden to fix it — a fleet stop whose remedy is
forbidden, which is H33 again and mine again. Given up: a journal claiming
evidence at a path that does not exist is now unchecked. Filed as its own row,
not folded in here.
LIVE INSTANCE CLOSED BY ANOTHER LANE MID-CYCLE: `peers.sh` was created at 14:16
while this was being written, so the tree is green for a reason that is not this
change. Selfcheck is therefore the only evidence v5 works, and it drives both
halves in both directions. Falsified: revert either half on a copy and
`--selfcheck` goes red naming which. (ok-1, H41.)

v4 RATIONALE (§12.7) — THE DEFECT REMOVED: a path carrying an unexpanded variable
is a TEMPLATE, not a citation, and check 4 skipped `$` only as a LEADING
character. So `$CLAUDE_PROJECT_DIR/...` passed and `prompts/$CALLSIGN.md` did
not. That is v3(a)'s own class -- the site, not the class -- in the module whose
v3 rationale is about scoping a fix to the site that needed it. It was a LIVE
FLEET-STOP: `pre-commit.hook` gates this module, so three CORRECT citations of
that template refused every lane's commits at rc=1. Scoped, not loosened --
`git ls-files | grep -c '$'` is 0, so the character appears in no tracked path.
Selfcheck asserts the template stays quiet WHILE `nope.py` still fires, because
a checker that skipped every path would be quiet on the template too. Falsified:
restore the leading-only skip on an isolated copy and `--selfcheck` goes red with
`['template path refused']`. Full block at check 4. (ok-1, H33.)

v3 RATIONALE (§12.7) — TWO DEFECTS REMOVED, both found by attacking v2 with a
falsifier that FAILED TO FIRE, against a live control in the same fixture:

  (a) THE FIX FOR A FALSE ACCUSATION WAS APPLIED GLOBALLY INSTEAD OF AT THE ONE
      SITE THAT NEEDED IT. v1 reported `HANDOFF.ATTACKER-1.md` citing a broken
      §0; that line reads "per §12 and the brief's §0" and the brief really does
      define one, so the retraction was right. But the repair resolved every §N
      in every harness file against the UNION of MISSION_LOOP and every per-lane
      brief -- so `§0` in `CLAUDE.md`, where §N can only mean MISSION_LOOP,
      resolved silently off `prompts/ATTACKER-1.md`. A false positive was traded
      for a false negative. MEASURED, not asserted: the briefs define §0-§9 and
      MISSION_LOOP §1-§14, so TODAY'S EXPOSURE IS EXACTLY ONE NUMBER, §0. The
      durable defect is that the exposure is whatever the briefs happen to define
      and moves whenever any lane edits one. Brief sections are now offered only
      to a file that IS a brief or that discusses one.

  (b) THE SCAN SILENTLY NARROWED ITS OWN SCOPE. `harness_files()` skipped any
      HARNESS entry that did not exist, so deleting `.claude/hooks/loop_gate.sh`
      and `run_loop.sh` took the scan from 8 files to 6 and it still printed
      "every citation resolves" at exit 0. Family B -- the instrument reports
      fiction, confidently and well-formed. A named harness file that is missing
      is now a REFUSAL. `.claude/settings.json` was also absent from the list
      while §12 names it as harness, and that is the H-HOOKREG file exactly.


v2 RATIONALE (§12.7) — THE DEFECT REMOVED: an id could be allocated twice and
nothing said so. v1 resolved a citation to a DOCUMENT and never asked whether it
resolved to ONE THING. `WORK_QUEUE.md` had four ids allocated twice (H17, H18,
H19, H20) and three of those four were allocated by TWO DIFFERENT LANES minutes
apart, with 73 citations of them across 12 files, every one ambiguous. The
namespace with no allocator is a class this repo has already paid for twice --
two lanes signed the callsign `AGENT-2` (§12, H8), two lanes created `G25`
(§13.3) -- and both times the rule written afterwards was PROSE. This is the
same rule, mechanised, for the third namespace. Check 5 below.

§12.4: "A reference to a section, spec, or file is resolved MECHANICALLY, never
by eye." The H4 row records three regressions inside one hour -- CLAUDE.md citing
§10 for publishing after it moved to §11, MISSION_LOOP carrying two §9, and §13
pointing at a `CLAUDE.md §2` a rewrite had deleted -- and notes that **all three
were found by eye**, which is the thing §12.4 forbids. Its own row says
`grep -E '^## [0-9]+ ·' | uniq -d` is a third of this check. This is the rest.

WHY A CONTRACT THAT CITES A MISSING ARTIFACT IS WORSE THAN ONE THAT CITES NOTHING
--------------------------------------------------------------------------------
It reads as satisfied. §7 gated LOOP-DONE on "D1-D6 as written specs" while D4
and D6 did not exist, and the gate looked met. That is family A: the instrument
cannot produce the answer.

WHAT IS CHECKED
---------------
  1. `§N` and `§N.M` -> MISSION_LOOP.md must carry that section / bullet.
  2. duplicate section numbers -- two `## 9 ·` is what made every "§9" ambiguous.
  3. `A<n>` guardrail citations -> `### A<n>` in analysis/GUARDRAILS.md.
  4. backticked repo paths -> the file or directory exists.
  5. duplicate table ROW IDS -- two rows numbered `H20` is what made every
     "H20" citation resolve to two rows with opposite statuses.

WHAT IS NOT, AND SAYING SO IS PART OF THE CHECK
-----------------------------------------------
It cannot tell whether a section says what the citation claims it says. §12.12
already names that class as unmechanisable, and pretending otherwise would be its
own defect. It resolves POINTERS, not meanings.

  python3 refcheck.py [--selfcheck]     exit 0 = every citation resolves.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ML = os.path.join(ROOT, 'MISSION_LOOP.md')
GR = os.path.join(ROOT, 'analysis', 'GUARDRAILS.md')

# The harness, per §12's own enumeration, plus this module's neighbours. CHANNEL
# and livechat are DELIBERATELY EXCLUDED: they are append-only logs where a stale
# pointer is a historical record of what a lane believed at the time, and
# rewriting history to satisfy a checker is the opposite of the point.
HARNESS = ['MISSION_LOOP.md', 'CLAUDE.md', 'WORK_QUEUE.md', 'HANDOFF.md',
           'analysis/GUARDRAILS.md', 'run_loop.sh', '.claude/hooks/loop_gate.sh',
           # §12 names "every settings.json that registers it" as harness and
           # this list omitted it -- the H-HOOKREG file, left out of the checker
           # written to catch H-HOOKREG's class.
           '.claude/settings.json']


def harness_files(missing=None):
    """v3: a HARNESS entry that does not exist is REPORTED, not skipped.

    v2 skipped it. That made the scope of the scan depend on the tree it was
    scanning, so a harness file could be renamed or deleted and this would print
    "every citation resolves" over the gap -- fewer files, same green verdict.
    """
    out = []
    for rel in HARNESS:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            out.append(rel)
        elif missing is not None:
            missing.append(rel)
    for d in ('spikes/harness', 'prompts'):
        dp = os.path.join(ROOT, d)
        if not os.path.isdir(dp):
            continue
        for fn in sorted(os.listdir(dp)):
            if fn.endswith(('.py', '.sh', '.md')):
                out.append(os.path.join(d, fn))
    for fn in sorted(os.listdir(ROOT)):
        if re.match(r'HANDOFF\..+\.md$', fn):
            out.append(fn)
    return out


def sections(text):
    """Top-level `## N ·` numbers, in order, so duplicates are visible."""
    return re.findall(r'^##\s+(\d+)\s+·', text, re.M)


def subsections(text):
    return set(re.findall(r'^-?\s*\*\*(\d+\.\d+)\s+·', text, re.M))


# An id is the shape this repo ACTUALLY allocates: starts upper-case, and carries
# a digit or a hyphen -- `H1`, `H-CLOCK`, `D1+`, `M1.7`, `S45`, `H-A28`. Requiring
# one of those two marks is what separates an id cell from a header cell (`id`,
# `item`, `status`) and from a prose cell, WITHOUT a list of known prefixes that
# would go stale the first time a lane opens a new series. Same reasoning as
# commit-msg.hook's `is_callsign`: a SHAPE rule cannot go stale, a registry can.
ID_CELL = re.compile(r'[A-Z][A-Za-z0-9]*(?:[-.][A-Za-z0-9]+)*\+?$')


def row_ids(text):
    """First-cell ids of markdown table rows, in order, so duplicates are visible."""
    out = []
    for line in text.splitlines():
        if not line.startswith('|'):
            continue
        cell = line.split('|')[1].strip().strip('*`').strip()
        if ID_CELL.match(cell) and (any(c.isdigit() for c in cell) or '-' in cell):
            out.append(cell)
    return out


def main():
    # DISPATCH ONLY. The first draft had main() re-read sys.argv and selfcheck()
    # call main(), so --selfcheck recursed until the stack blew -- a checker that
    # cannot run its own check is the shape this module exists to catch.
    if '--selfcheck' in sys.argv:
        return selfcheck()
    return scan()


def scan():
    ml = open(ML).read() if os.path.exists(ML) else ''
    gr = open(GR).read() if os.path.exists(GR) else ''
    secs, subs = sections(ml), subsections(ml)
    # §N DOES NOT ALWAYS MEAN MISSION_LOOP, and assuming it did made this tool
    # file a FALSE ACCUSATION against another lane on its first run. It reported
    # `HANDOFF.ATTACKER-1.md` citing a broken §0; that line reads "per §12 and
    # THE BRIEF'S §0", and `prompts/ATTACKER-1.md:8` is `## 0 · Claim your
    # identity before you claim any work`. The citation was perfect and the
    # checker was wrong -- a resolver that resolves against one document while
    # the repo cites several is the same defect it exists to find.
    # Sections are therefore resolved against every harness document that DEFINES
    # them. The duplicate check below stays MISSION_LOOP-only: two `## 9 ·` there
    # is what made every §9 ambiguous, and briefs are per-lane.
    # v3 (a): the brief sections are kept SEPARATE from MISSION_LOOP's and handed
    # out per file, instead of unioned into one set for the whole harness. v2
    # unioned them, which is why `§0` resolved in CLAUDE.md -- a file where §N
    # cannot mean anything but MISSION_LOOP. The retraction that caused the union
    # was correct about ITS site and the repair was applied everywhere.
    ml_secs, ml_subs = set(secs), set(subs)
    brief_secs, brief_subs = set(), set()
    missing = []
    files = harness_files(missing)
    for rel in files:
        if rel.startswith('prompts/') and rel.endswith('.md'):
            try:
                other = open(os.path.join(ROOT, rel), encoding='utf-8').read()
            except (UnicodeDecodeError, OSError):
                continue
            brief_secs |= set(sections(other))
            brief_subs |= subsections(other)
    guards = set(re.findall(r'^###\s+A(\d+)', gr, re.M))
    problems = []

    # v3 (b): a harness file named in §12 that is not on disk is a REFUSAL. The
    # scan reporting clean over a file it never opened is family B.
    for rel in missing:
        problems.append(f'harness file `{rel}` is named in §12 and IS NOT ON '
                        f'DISK -- the scan narrowed itself to {len(files)} files '
                        f'and would have reported clean over it')

    # 2 · duplicate section numbers, the defect that made "§9" ambiguous
    dupes = {n for n in secs if secs.count(n) > 1}
    for n in sorted(dupes):
        problems.append(f'MISSION_LOOP.md has {secs.count(n)} sections numbered '
                        f'"{n}" -- every §{n} citation is ambiguous')

    for rel in files:
        path = os.path.join(ROOT, rel)
        try:
            text = open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue

        # A file may resolve §N against a per-lane brief only if it IS one, or if
        # it talks about one -- `HANDOFF.ATTACKER-1.md`'s "per §12 and the brief's
        # §0" is the case the retraction was about, and it says "brief". Kept at
        # FILE level rather than line level on purpose: a citation wrapped away
        # from the word would be flagged, and filing a second false accusation
        # against another lane is a worse failure here than one §0 unchecked in a
        # file that discusses briefs. Residual stated rather than hidden.
        cites_brief = rel.startswith('prompts/') or re.search(r'brief', text, re.I)
        sec_set = ml_secs | brief_secs if cites_brief else ml_secs
        sub_set = ml_subs | brief_subs if cites_brief else ml_subs

        # 1 · §N and §N.M
        for ref in set(re.findall(r'§\s*(\d+(?:\.\d+)?)', text)):
            if '.' in ref:
                if ref not in sub_set and ref.split('.')[0] not in sec_set:
                    problems.append(f'{rel}: §{ref} does not resolve -- '
                                    f'MISSION_LOOP.md has no such bullet')
            elif ref not in sec_set:
                problems.append(f'{rel}: §{ref} does not resolve -- no document '
                                f'THIS FILE may cite defines it; known: '
                                f'{sorted(sec_set, key=int)}')

        # 1b · `§N` in GUARDRAILS.md cites EXTERNAL documents (a standard's section 46,
        #      a paper's section), not this repo's loop contract, so § resolution
        #      is not applied there. Stated rather than silently skipped: a
        #      checker that quietly drops a file is one nobody can audit.
        if rel == 'analysis/GUARDRAILS.md':
            problems = [x for x in problems if not x.startswith(f'{rel}: §')]

        # 3 · guardrail citations
        for ref in set(re.findall(r'\bA(\d{1,2})\b', text)):
            if ref not in guards and rel != 'analysis/GUARDRAILS.md':
                problems.append(f'{rel}: guardrail A{ref} is cited and '
                                f'analysis/GUARDRAILS.md has no "### A{ref}"')

        # 4 · backticked repo paths. `<...>` placeholders, globs, `~` and URLs are
        # not citations of a file that should exist.
        # A CITATION TO SOMETHING OUTSIDE THIS REPO IS NOT A BROKEN REFERENCE.
        # GUARDRAILS cites `boinc/sched/credit.cpp:284-289` and
        # `hyperon-experimental/.../Cargo.toml:17` -- upstream sources, with line
        # numbers, in trees that are gitignored (`elders/`) or not present at all.
        # Flagging those would make this fire on known-good items every run, which
        # is H14's named failure mode: a checker everyone learns to ignore.
        # The rule that separates them cheaply: a repo path's FIRST SEGMENT is an
        # existing top-level entry. `spikes/...` is checked, `boinc/...` is not.
        # v4, 2026-08-17 (ok-1, H33). A PATH CARRYING AN UNEXPANDED VARIABLE IS A
        # TEMPLATE, NOT A CITATION -- it names a family of files and cannot
        # resolve by construction. `$` was skipped only as a LEADING character,
        # so `$CLAUDE_PROJECT_DIR/...` passed and `prompts/$CALLSIGN.md` did not:
        # the site, not the class (§12.2), in the checker whose own v3 rationale
        # block is about scoping a fix to the site that needed it (H26).
        # LIVE FLEET-STOP, not a hypothetical: `pre-commit.hook` gates this
        # module, so when AGENT-1's H30 work cited `prompts/$CALLSIGN.md` in
        # WORK_QUEUE.md and test_loop_gate.sh, and I cited it in prompts/ok-1.md,
        # every lane's commits were refused -- rc=1, measured -- for three
        # citations that were all correct.
        # SCOPED, not a loosening: `git ls-files | grep -c '\$'` is 0, so no
        # tracked path in this repo contains the character and nothing real is
        # hidden by skipping it. The other three named skips (external trees,
        # `.git/`, placeholders) each carry their reason the same way.
        # v5, 2026-08-17 (ok-1, H41). TWO DEFECTS, and the row named only one.
        # (a) only INLINE backticks were matched, so a path inside a ```sh fence
        #     -- the form a lane copies and runs -- was unchecked.
        # (b) a dot-slash path was skipped by the first-segment rule above,
        #     because the first segment of ./peers.sh is `.` and `.` is not a
        #     listdir entry. `./` is the one prefix that STATES the path is in
        #     this repo, so it is the one case where the external-tree rule must
        #     not apply.
        #     NOTE THE BACKTICKS THIS BLOCK DOES NOT USE. v5's first run flagged
        #     THIS FILE three times, because a rationale block naming an absent
        #     path is indistinguishable from a broken citation of it -- the same
        #     trap selfcheck() below builds its fixtures out of string parts to
        #     avoid, walked into by the author of that note within the hour.
        # MEASURED BEFORE WRITING, on all 45 harness files, because "false
        # positives" was the row's stated reason nobody had taken it: (a) alone
        # flags NOTHING AT ALL -- including the live instance the row cites --
        # (b) alone flags 2, together 4, and all four are the same real defect:
        # a dot-slash peers.sh is prescribed by two briefs, HANDOFF.ATTACKER-1.md
        # and WORK_QUEUE.md, and does not exist. Zero false positives at either
        # half. Fixing only the half the row named would have shipped a green
        # checker over the row's own evidence, which is §12.2 at my own site.
        # SCOPED: fences are read in `.md` only. A `.sh` harness file's fences
        # are its own code, and the dot-slash gate.sh in test_loop_gate.sh names
        # a file the suite creates in its scratch ROOT -- real there, absent
        # here, and not a citation.
        top = set(os.listdir(ROOT))

        def unresolved(tok):
            """None if `tok` is not a repo-path citation or resolves; else the path."""
            if tok.startswith(('~', 'http', '/', '<')) or any(
                    c in tok for c in '<>*?:\\$'):
                return None
            tok = tok.rstrip('.,;:')
            body = tok[2:] if tok.startswith('./') else tok
            if not body:
                return None
            if not tok.startswith('./') and body.split('/')[0] not in top:
                return None
            # `.git/hooks/...` is INSTALLED STATE, not tracked content, and the
            # harness cites it both ways -- MISSION_LOOP names a hook that exists
            # and WORK_QUEUE's H15 row names one BECAUSE IT DOES NOT. A citation
            # asserting absence cannot be told from a broken one by any check
            # here, so this does not pretend to.
            if body.startswith('.git/'):
                return None
            return None if os.path.exists(os.path.join(ROOT, body)) else tok

        # SCOPE, v5: journals are OUT of the path check and stay in every other
        # check. A `HANDOFF.<lane>.md` is a past-tense record with ONE legal
        # writer (H10), so a broken path in it can only be tripped by a lane
        # that is not allowed to fix it -- and this module gates every lane's
        # commit. v5's first run proved that live: 4 red, and 3 of the 4 were
        # lanes REPORTING this very defect, one of them inside a journal I may
        # not edit. A gate whose only remedy is forbidden is a fleet stop, which
        # is H33 again and mine again.
        # WHAT THIS GIVES UP, stated rather than buried: a journal claiming
        # evidence at a path that does not exist is now unchecked, and that is a
        # real defect class. It needs a check that reports to the journal's own
        # lane instead of to the shared gate -- filed, not folded in here.
        # §N and A<n> citations in journals are UNAFFECTED: those resolve against
        # documents any lane can read, and H26's retraction turned on one.
        cited = set()
        if not re.match(r'HANDOFF\..+\.md$', rel):
            cited = set(re.findall(r'`([^`\s]+/[^`\s]*)`', text))
            if rel.endswith('.md'):
                for blk in re.findall(r'^```[^\n]*\n(.*?)^```', text, re.M | re.S):
                    cited |= set(re.findall(r'[^\s`\'"|;()]+/[^\s`\'"|;()]*', blk))
        for tok in cited:
            bad = unresolved(tok)
            if bad:
                problems.append(f'{rel}: `{bad}` does not exist')

        # 5 · duplicate row ids. A citation that resolves to TWO rows is worse
        # than one that resolves to none, for §12.4's stated reason: it reads as
        # satisfied. Measured on the queue this check was written against --
        # `H20` was simultaneously OPEN (falsify.py, ATTACKER-1, 12:21) and DONE
        # (provenance.Control, AGENT-1, 12:40), so a lane grepping its own NEXT
        # item found someone else's closed row. Per FILE, because ids are
        # namespaced by document; a `D4` in WORK_QUEUE and a `D4` in a spike's
        # own table are not a collision.
        ids = row_ids(text)
        for n in sorted({i for i in ids if ids.count(i) > 1}):
            problems.append(f'{rel}: {ids.count(n)} table rows are numbered '
                            f'"{n}" -- every {n} citation resolves to more than '
                            f'one row')

    for p in sorted(set(problems)):
        print('  UNRESOLVED ' + p)
    if problems:
        print(f'\nREFUSE: {len(set(problems))} citation(s) in the harness do not '
              f'resolve. A contract citing a missing artifact reads as satisfied,\n'
              f'        which is why this refuses rather than warns.')
        return 1
    print(f'refcheck: every §N, guardrail and path citation in '
          f'{len(files)} harness files resolves')
    return 0


def selfcheck():
    """§12.3: the check ships a check, and it must fail on planted breakage.

    Each of the four checks is driven with a citation that CANNOT resolve, and
    with one that can, because a checker only ever seen failing is as
    uninformative as one only ever seen passing.
    """
    import tempfile, shutil
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, 'analysis'))
        os.makedirs(os.path.join(tmp, 'spikes', 'harness'))
        open(os.path.join(tmp, 'MISSION_LOOP.md'), 'w').write(
            '## 1 · one\n## 2 · two\n## 2 · two again\n- **1.1 · a bullet**\n')
        open(os.path.join(tmp, 'analysis', 'GUARDRAILS.md'), 'w').write('### A1\ntext\n')
        # BUILT FROM PARTS, deliberately: written as literals, this file would
        # carry four broken citations of its own and refcheck would flag itself
        # on every run. Excluding the checker from its own scan was the other
        # option and it is the H-HOOKREG blind spot -- a suite that exempts
        # itself is one nobody checks.
        bad_sec, bad_g = '\u00a7' + '99', 'A' + '77'
        bad_path = 'spikes/' + 'harness/nope.py'
        # v4's fixture (H33). A template path: same first segment as a real
        # citation, an unexpanded variable in a LATER segment, so the leading-`$`
        # skip never saw it. It must stay QUIET while bad_path above still fires
        # -- one direction alone would pass for a checker that skipped every path.
        tmpl_path = 'prompts/' + '$' + 'CALLSIGN.md'
        # Check 5's fixture. Interpolated rather than written literally for the
        # same reason as the others: two literal `| H99 |` rows in this source
        # would make refcheck flag ITSELF on every run, since it scans
        # spikes/harness/. dup is allocated twice (the defect); uniq once (the
        # control that proves the check is not simply reporting every id).
        dup, uniq = 'H' + '99', 'H' + '98'
        # v5 (H41). Four path fixtures in two PAIRS, because each half of v5 has
        # a direction that a checker skipping every path would also satisfy.
        fence_bad = 'spikes/' + 'harness/fenced_nope.sh'    # fenced, absent
        fence_good = '.claude/' + 'settings.json'           # fenced, present
        dot_bad = '.' + '/nosuch.sh'                        # dot-slash, absent
        dot_good = '.' + '/run_loop.sh'                     # dot-slash, present
        journal_bad = 'spikes/' + 'harness/journal_nope.py'  # broken, in a journal
        open(os.path.join(tmp, 'WORK_QUEUE.md'), 'w').write(
            '| id | item | status |\n|---|---|---|\n'
            f'| {dup} | first allocation, lane A | OPEN |\n'
            f'| {uniq} | only allocation | OPEN |\n'
            f'| {dup} | second allocation, lane B | DONE |\n')
        # v3 (a)'s fixture. A per-lane brief defines a section MISSION_LOOP does
        # not. `CLAUDE.md` is not a brief and does not discuss one, so its
        # \u00a7{brief_sec} must be FLAGGED; `HANDOFF.md` says "brief", which is the
        # retracted-false-accusation case, so its \u00a7{brief_sec} must stay QUIET.
        # Both directions, because v2 was quiet on BOTH and that is the defect.
        brief_sec = '0'
        os.makedirs(os.path.join(tmp, 'prompts'))
        open(os.path.join(tmp, 'prompts', 'ATTACKER-1.md'), 'w').write(
            f'## {brief_sec} \u00b7 claim your identity\n')
        open(os.path.join(tmp, 'CLAUDE.md'), 'w').write(
            'cite \u00a71 and \u00a71.1 and A1 and `MISSION_LOOP.md` -- all fine.\n'
            f'now cite {bad_sec} and {bad_g} and `{bad_path}` -- none exist.\n'
            f'and `{tmpl_path}`, a template that names a family of files.\n'
            # This line must NOT contain the word the scoping rule looks for --
            # the first draft of this fixture wrote "which only a per-lane brief
            # defines" and thereby handed CLAUDE.md the very permission the case
            # exists to deny. The fixture passed and tested nothing.
            f'and \u00a7{brief_sec}, which MISSION_LOOP does not define.\n'
            # v5's fixtures (H41). Assembled from parts for the same reason as
            # every fixture above, and v5's FIRST RUN proved the reason live: the
            # rationale block for this change backticked three absent paths and
            # refcheck flagged its own source three times.
            f'```sh\n{fence_bad}   # inside a fence, which v4 never read\n'
            f'cat {fence_good}     # inside a fence and REAL\n```\n'
            f'run `{dot_bad}` and `{dot_good}` -- one exists, one does not.\n')
        open(os.path.join(tmp, 'HANDOFF.md'), 'w').write(
            f"per \u00a71 and the brief's \u00a7{brief_sec}.\n")
        # v5's SCOPE fixture: a per-lane journal, single-writer under H10, whose
        # path citation is broken. It must stay QUIET -- and its \u00a7 citation must
        # still be judged, because the scope narrows ONE check and not the file.
        open(os.path.join(tmp, 'HANDOFF.' + 'L9' + '.md'), 'w').write(
            f'ran `{journal_bad}` last cycle; cites {bad_sec} which does not exist.\n')
        # v3 (b)'s fixture: every remaining HARNESS entry EXISTS in this pass, so
        # the missing-file check is shown quiet here and driven separately below.
        os.makedirs(os.path.join(tmp, '.claude', 'hooks'))
        open(os.path.join(tmp, 'run_loop.sh'), 'w').write('#!/bin/sh\n')
        open(os.path.join(tmp, '.claude', 'hooks', 'loop_gate.sh'), 'w').write('#!/bin/sh\n')
        open(os.path.join(tmp, '.claude', 'settings.json'), 'w').write('{}\n')
        global ROOT, ML, GR
        keep = (ROOT, ML, GR)
        ROOT = tmp
        ML = os.path.join(tmp, 'MISSION_LOOP.md')
        GR = os.path.join(tmp, 'analysis', 'GUARDRAILS.md')
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = scan()
        out = buf.getvalue()
        # SECOND PASS for v3 (b): delete one named harness file and nothing else.
        # Driven as its own run because the check is about what the scan DOES NOT
        # LOOK AT, and a check for an absence cannot share a pass with the
        # presence it contradicts.
        os.remove(os.path.join(tmp, 'run_loop.sh'))
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            scan()
        out2 = buf2.getvalue()
        ROOT, ML, GR = keep
        # Same reason as the fixtures: assembled, so this file contains no
        # literal broken citation for its own scan to trip over.
        want = [(bad_sec, 'unresolved section'), (bad_g, 'unresolved guardrail'),
                ('nope.py', 'missing path'), ('numbered "2"', 'duplicate section'),
                (f'numbered "{dup}"', 'duplicate row id'),
                (fence_bad, 'absent path inside a ```sh fence (v5a)'),
                (dot_bad, 'absent dot-slash path (v5b)')]
        bad = [w for w, _d in want if w not in out]
        for w, d in want:
            print(f"  {'CATCHES' if w in out else 'MISSES '} {d} ({w})")
        # THE OTHER HALF, and it was dead code in the first draft: a loop that
        # computed nothing and asserted nothing. A checker only ever seen firing
        # is as uninformative as one only ever seen passing, so the RESOLVABLE
        # citations must be shown NOT to be reported.
        for good, d in ((bad_sec[0] + '1', 'valid section'),
                        ('A' + '1', 'valid guardrail')):
            if f'{good} does not resolve' in out or f'guardrail {good} is cited' in out:
                print(f'  FALSE-POSITIVE on a {d} ({good})')
                bad.append(d)
            else:
                print(f'  QUIET   on a {d} ({good})')
        # v4 (H33), and it is only evidence PAIRED with `nope.py` CATCHES above:
        # a checker that skipped every path would be quiet here too.
        if tmpl_path in out:
            print(f'  FALSE-POSITIVE on a template path ({tmpl_path})')
            bad.append('template path refused')
        else:
            print(f'  QUIET   on a template path ({tmpl_path})')
        # v5's three QUIET directions. Each is the half a checker that simply
        # flagged every slash-bearing token would fail, and `nope.py` CATCHES
        # above is what stops "quiet everywhere" from reading as a pass.
        for tok, d in ((fence_good, 'a REAL path inside a fence'),
                       (dot_good, 'a REAL dot-slash path'),
                       (journal_bad, "a broken path in a per-lane JOURNAL (H10 scope)")):
            if f'`{tok}` does not exist' in out:
                print(f'  FALSE-POSITIVE on {d} ({tok})')
                bad.append(d)
            else:
                print(f'  QUIET   on {d} ({tok})')
        # ...and the scope narrows ONE check, not the file: the same journal's
        # broken § citation must still be reported, or v5 silenced a document.
        if f'HANDOFF.L9.md: §{bad_sec[1:]} does not resolve' in out:
            print('  CATCHES a broken § citation in that same journal')
        else:
            print('  MISSES  a broken § citation in that same journal')
            bad.append('journal section citation')
        # Check 5's other direction, and it is the one that matters: a check that
        # flagged EVERY id would also "catch" the duplicate and be useless.
        if f'numbered "{uniq}"' in out:
            print(f'  FALSE-POSITIVE on a singly-allocated row id ({uniq})')
            bad.append('unique row id')
        else:
            print(f'  QUIET   on a singly-allocated row id ({uniq})')
        # v3 (a), both directions.
        if f'CLAUDE.md: §{brief_sec} does not resolve' in out:
            print(f'  CATCHES a brief-only section cited by a non-brief file (§{brief_sec})')
        else:
            print(f'  MISSES  a brief-only section cited by a non-brief file (§{brief_sec})')
            bad.append('brief-scoped section')
        if f'HANDOFF.md: §{brief_sec}' in out:
            print(f"  FALSE-POSITIVE on a file that names the brief (§{brief_sec})")
            bad.append('brief citation refused')
        else:
            print(f"  QUIET   on a file that names the brief (§{brief_sec})")
        # v3 (b), both directions.
        if 'IS NOT ON DISK' in out:
            print('  FALSE-POSITIVE reported a missing harness file while all exist')
            bad.append('spurious missing file')
        else:
            print('  QUIET   on a complete harness')
        if '`run_loop.sh` is named in §12 and IS NOT ON DISK' in out2:
            print('  CATCHES a named harness file deleted from the tree')
        else:
            print('  MISSES  a named harness file deleted from the tree')
            bad.append('missing harness file')
        if rc == 0:
            print('  MISSES  it did not refuse at all'); bad.append('refusal')
        if bad:
            print(f'SELFCHECK FAILED: {bad}')
            return 1
        # NOT "all four checks": §7 records that a citation to a number that
        # changes is stale by construction, after this repo carried "15 checks"
        # through four different counts in one day. The line said "four" while
        # five ran.
        # NO COUNT. v2 printed "all four checks" while five ran; v3 replaced that
        # with len(want) and it went stale INSIDE ONE CYCLE, because the two v3
        # cases are asserted outside `want`. §7: cite the artifact, not its size.
        # The per-case lines above are the count, and they cannot disagree with
        # themselves.
        print('selfcheck: every planted breakage fires, every resolvable '
              'citation stays quiet, and it refuses')
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
