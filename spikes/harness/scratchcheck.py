#!/usr/bin/env python3
# scratchcheck.py v5 — H89 (v1, v2), H194 (v3), H254 (v4), H213 (v5).
# ATTACKER-1, then ok-1, then AGENT-1.
#
# ==== v5, H213 — THE CENSUS COULD NOT SEE THE ONE FILE A CYCLE IS WRITING =====
# DEFECT REMOVED: `--scan` with no explicit targets seeded from
# `git ls-files '*.sh' '*.py' '*.hook'` — TRACKED paths only. A cycle's own new
# probe is UNTRACKED BY CONSTRUCTION until that cycle commits, so the file most
# likely to be carrying a fresh §10 violation was the one file the census could
# not look at, and its absence read as clean.
#
# MEASURED TWO-SIDED, and the classifier was never the problem — the census was:
# `--scan` over the tracked tree reported no write position in
# `spikes/H209_carries_toctou/probe.sh`; the IDENTICAL classifier handed that
# path explicitly reported FOUR. `git ls-files --error-unmatch` on it: "did not
# match any file(s) known to git".
#
# LIVE, NOT LATENT, AND THAT IS WHY v5 EXISTS. Run over the untracked half of
# this tree the same classifier finds FOUR write positions in FOUR files that
# the tracked census has never once reported:
#   fixtures/run_all.sh:30                          /tmp/kf_trace_verifier
#   fixtures/webgrok-pack/run_all.sh:20             /tmp/kf_trace_verifier
#   spikes/H185_launcher_generation/sandbox/bringup.sh:418   $HOME/Library/...
#   spikes/H236_retirement_undone/sandbox/bringup.sh:492     $HOME/Library/...
# 138 untracked `.sh`/`.py`/`.hook` files against 544 tracked — 20% of the
# population was invisible.
#
# THIS IS `allocid.sh` v1's CLASS IN A SECOND MODULE — an instrument whose
# BOOTSTRAP reads fewer sources than the thing it is deciding about lives in.
# There it cost duplicate ids; here it cost a rail.
#
# F2 WAS THE ONE THAT COULD HAVE KILLED THE FIX AND IT WAS RUN FIRST: adding
# untracked files must not drag in `.scratch/`, `elders/` or build trees, or the
# census becomes unreadable and gets ignored, which is worse than blind.
# MEASURED: `--exclude-standard` already honours `.gitignore`, so `.scratch/`
# contributes 0 and `elders/` contributes 0; the untracked set is 95 kitchen,
# 21 fixtures, 18 spikes, 2 .github, 1 .codex, 1 root script — all real source.
# The explicit `elders/` filter is kept anyway rather than trusted to
# `.gitignore`, because a rail should not depend on a file any lane can edit.
#
# Check: python3 spikes/H213_census_scope/probe.py
# ==== v4, H254 (ok-1, 2026-08-19) ====
# DEFECT REMOVED: AN OPERATOR CHARACTER INSIDE QUOTES WAS READ AS AN OPERATOR, so
# a word inside a SEARCH PATTERN was classified as a command. Measured, and it is
# this gate refusing a read of its own subject:
#
#     grep -nE 'git |cp |mktemp|TMP' spikes/harness/test_h219_falsify.sh
#     -> §10 REFUSED: this writes outside the workspace.   mktemp  $TMPDIR
#
# The `|` before `mktemp` is a regex alternation; `MKTEMP`'s anchor set treats any
# `|` as a pipe. v3 already carries three commands of its author's that this gate
# refused, under the heading "a gate that refuses the investigation of its own
# rail is unusable" -- and all three are clean only because their token has a
# SPACE before it, not because quoting is understood. This is the same class
# reached by a pattern with no space.
#
# NOT A MASK OVER QUOTED SPANS. `_in_quotes`'s docstring records why that would
# delete true positives: the PATH of a real write is very often quoted. v4 looks
# only at the OPERATOR that puts a keyword in command position, and only at
# whether that operator is live -- a backtick or `$(` inside DOUBLE quotes still
# is, and `ls | mktemp` and `echo "$(mktemp -d)"` are asserted to keep firing.
#
# Check: `python3 spikes/harness/scratchcheck.py --selfcheck` (53 arms; three new
# negatives, and the POSITIVES are what stop this being a widening).
# ==== v3 ====
# H194, AND IT IS AN ATTACK ON v2 BY ITS OWN AUTHOR FIFTEEN MINUTES AFTER
# SHIPPING IT. DEFECT CLASS REMOVED: A PRECISION FIX MEASURED ONLY IN THE
# DIRECTION IT WAS MADE. v2 was five rounds of false-positive work (census
# 29->16, every removal individually verified) and NOT ONE round constructed a
# write the gate SHOULD catch and does not. Recall was never measured. Measured
# now over 12 constructed commands: v2 caught 7 of 12.
#   D1 · `_in_quotes` ignored BACKSLASH ESCAPES, so a `\"` inside a double-quoted
#        string desynced quote state and a following redirect read as quoted --
#        MISSED WRITE. Now escape-aware, and single quotes take no escapes,
#        which is what the shell does.
#   D2 · A COMMENT LINE IN A MULTI-LINE COMMAND poisoned quote state for every
#        line after it (`# don't` opens a span that never closes). v2 put the
#        comment skip in `scan_source` ONLY, on my written reasoning that "a
#        comment cannot reach the hook, which is handed a whole command". THAT
#        REASONING WAS WRONG: a multi-line Bash command carries comment lines and
#        they reach the hook. Running it is what showed that; reading it back
#        three times did not.
#   D3 · `cd <outside> && <relative write>` was invisible. Not residue I had
#        named -- a plain, natural way to write outside the tree.
#   D4 · `mktemp` matched as a bare WORD, so any command merely MENTIONING it
#        was refused -- `grep -v mktemp scan.out` is a read. Pre-existing since
#        v1 and found the only way it could be: the gate refused my own command
#        while I was investigating its own census. Now command-position only.
#        Note what this says about D1-D3's evidence: recall was measured on 12
#        CONSTRUCTED commands and precision on source lines plus nine
#        hand-written negatives, and NEITHER corpus contained the commands this
#        lane actually types. Both numbers are floors.
# D1 AND D2 WERE DRILLED BY v2's OWN QUOTE-AWARENESS FIX: neutralise
# `_in_quotes` and the misses drop 5 -> 3. The fix that removed a false positive
# introduced two false negatives, and only one direction was ever measured.
# D3's rule was measured BEFORE adoption against 6,454 real command lines from
# the tracked tree plus every negative control: ZERO false positives. That
# REFUTES my own recorded prediction that it would cost some.
# ==== v2 ====
# THIS HEADER IS DUPLICATED AS A `#` COMMENT ON PURPOSE, and the reason is a
# defect found by trying to bump this file's version: `versioncheck.py` matches
# `^#\s*(\S+?)\s+v(\d+)`, a COMMENT line, so a version declared in a DOCSTRING is
# invisible to it and skipped as "no version header is not a defect". MEASURED:
# 18 of the 34 versioned modules in spikes/harness/ declare their version in a
# docstring and versioncheck sees NONE of them — INCLUDING versioncheck.py
# ITSELF. Filed as H193 with the measurement; NOT fixed here, because fixing the
# site while naming the class is what §12.1 forbids. These two lines make THIS
# file's bump checkable now; they are not the remedy.
"""scratchcheck.py v3 — H89 (v1, v2), H194 (v3). ATTACKER-1, 2026-08-19.

==== v2, H89 — THE GATE REFUSED THE WRITE OF ITS OWN RESULT.md ==============
D1 · A HEREDOC BODY IS DATA, NOT COMMANDS. v1 was handed the whole Bash command
     `cat > RESULT.md <<'EOF' ... EOF`, whose body QUOTES this gate's refusal
     text, and classified the quoted paths as live writes. The row's own write-up
     was unwritable. Not hypothetical and not found by reading: it fired on me,
     twice, mid-cycle.
     SECOND TIME THIS TREE HAS PAID FOR THIS DEFECT, 40 MINUTES APART, SAME LANE.
     `versioncheck.py` v1 (H180, mine) flagged its own test suite because heredoc
     FIXTURES read as that file's version blocks; it grew `strip_heredocs` and a
     check that keeps it so. I wrote that fix and then did not reuse it here.
     §12.2 is "fix the CLASS, never the site", and this is the site I left.
     Fixed by IMPORTING `versioncheck.strip_heredocs`, never copying it, because
     a copy is the second site the rule is about. If that import ever fails the
     module cannot classify safely, so it sets `_STRIPPER = False` and the hook
     stops blocking rather than becoming silently permissive — asserted in
     `--selfcheck`, so the launchd sweep goes RED instead of the gate going quiet.
D2 · `scan_source` read files LINE BY LINE and so could not see the heredoc a
     line sat in — that is how `<string>/bin/bash</string>` inside bringup.sh's
     plist was reported as a redirect. It now strips heredocs over the whole file
     first. The `'</' in line` special case v1 carried for that symptom is GONE:
     it was the symptom's patch, and D1's fix is the cause's.
Both are mutation-covered: the two new negative controls are the exact commands
v1 refused, assembled from parts rather than written as literal multi-line
fixtures — because a literal fixture in a source file is this same defect one
level up, which is how `versioncheck.py` v1 flagged itself.
============================================================================


§10 / CLAUDE.md say "Nothing is written outside the workspace." Until this file
there was no checker in `spikes/harness/` that named that rail, and
`.claude/settings.json` registered exactly ONE hook (`Stop`), so at the layer
where every recorded violation happened there was no mechanism at all.

WHY THIS IS A TOOL-LAYER GATE AND NOT THE SOURCE SCAN H89 PREREGISTERED
=======================================================================
H89's own F3 asks for "a detector that flags a planted writer", and every reader
of that row — including the lane that wrote it, me — read it as a scan of
committed source. MEASURED BEFORE BUILDING (`spikes/H89_workspace_rail/probe.py`,
F4): of the 8 §10 instances this fleet has recorded, **7 were an agent typing a
path at a shell and left no committed artifact whatsoever.** A source scan is
blind to 7 of the 8 instances the row exists for — family A, the instrument that
cannot produce the answer, inside the row about unenforced rails.

So this module has two mouths and the SECOND one is the point:

  --scan    the source half. Finds the 1-in-8 that lives in a tracked file.
  --hook    a PreToolUse gate. Finds the 7-in-8 as they are about to happen.

WHAT IT CANNOT DO, STATED BEFORE THE CODE
=========================================
It classifies a shell command by WRITE POSITION — a redirect target, a `tee`
argument, the destination of `cp`/`mv`, an `-o`/`-F` output flag. It does not
parse shell. A write reached through a variable, a subshell, a heredoc body or a
program's own internal path is INVISIBLE to it, and `python3 -c 'open("/tmp/x","w")'`
is invisible to it. The residue is named rather than papered over: this is a gate
on the COMMON PATH, which is what all 8 recorded instances took, and not a proof.

IT FAILS OPEN ON ERROR AND CLOSED ONLY ON A CONFIDENT MATCH. Deliberate, and it
is the one design choice here that is about the live fleet rather than about
correctness: five lanes route every Bash call through this hook, and H124
recorded a 2m16s fleet-wide outage from a gate that became unparseable. An
internal exception must not be able to stop five lanes, so any failure inside
this module exits 0. A gate that can take the fleet down is worse than the rail
it guards being unenforced for another hour.

READ POSITIONS ARE NOT FLAGGED, AND THAT IS LOAD-BEARING RATHER THAN LAZY.
`grep -rn /tmp/foo .` mentions an out-of-workspace path and writes nothing. The
measurement that produced this module ran exactly such commands, so a classifier
keyed on "the string /tmp appears" would have refused the investigation of the
rail it enforces. That case is control C3 and it must stay green.

usage:
  python3 spikes/harness/scratchcheck.py --selfcheck
  python3 spikes/harness/scratchcheck.py --scan [path ...]
  python3 spikes/harness/scratchcheck.py --hook      # PreToolUse JSON on stdin
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))

# A HEREDOC BODY IS DATA, NOT COMMANDS -- and this is the second time this exact
# defect has been paid for in this tree, by the same lane, one cycle apart.
# `versioncheck.py` (H180, mine) v1 flagged its own test suite because heredoc
# FIXTURES read as that file's version blocks; it grew `strip_heredocs` and a
# check that keeps it so. I did not reuse it here, and v1 of this module REFUSED
# THE WRITE OF ITS OWN RESULT.md -- a `cat > RESULT.md` heredoc whose body quotes
# the refusal text, so the paths named in the prose were read as live commands.
# 12.2: fix the CLASS, not the site, and the class was already solved 40 minutes
# away in a file I wrote. IMPORTED, NEVER COPIED -- a copy is the second site.
sys.path.insert(0, HERE)
try:
    from versioncheck import strip_heredocs
    _STRIPPER = True
except Exception:                                     # pragma: no cover
    # No stripper means this module CANNOT classify safely, so it must not
    # block. `--selfcheck` asserts the import, so the launchd sweep goes RED
    # rather than this becoming a silently permissive gate.
    _STRIPPER = False

    def strip_heredocs(lines):
        return lines

# The sanctioned location. Inside the workspace, so it is compliant with §10 AS
# WRITTEN — this module does not amend the rail and could not: `railguard.py`
# (H112/H118) gates `MISSION_LOOP.md ## 10 ·`, a lane may not authorise its own
# rail change (A22), and H89 explicitly leaves "is ephemeral scratch an
# exception?" on H17 as not this lane's to decide. Naming a COMPLIANT location
# decides nothing; it removes the cause. CHANNEL.md:726 is the evidence that the
# cause is real: two of ATOM-3's six instances were backups taken to be careful
# before editing a shared file — "the caution produced the violation" — because a
# lane reaching for scratch had nowhere sanctioned to reach.
SCRATCH = os.path.join(ROOT, '.scratch')

# Not filesystem writes, or not host writes.
#   /dev/*        — not a workspace object.
#   /data/local/tmp, /sdcard — ANDROID DEVICE paths. Inherited from H89's own
#     preregistered F2, not decided here. MEASURED in the same cycle:
#     `grep -rno '/data/local/tmp' spikes/harness/ scripts/ .claude/ run_loop.sh`
#     = 0, against 47 tree-wide, so F2 cannot fire in the harness scope and this
#     entry is carried for the device spikes rather than to excuse a host write.
ALLOW_PREFIXES = ('/dev/null', '/dev/stdout', '/dev/stderr', '/dev/fd/',
                  '/dev/tty', '/data/local/tmp', '/sdcard')

# A path token, as it appears in a command line. Stops at shell metacharacters.
# The stop set excludes `{}<=` and a backtick DELIBERATELY, and the reason is a
# measurement rather than taste: the first form of this regex reported 29 write
# positions across the tracked tree and EIGHT were awk programs (`awk -F
# '/^verdict=/{print'`), XML inside a heredoc (`</string><string>`) and a
# backticked path in a comment. None of those characters can occur in a path this
# fleet writes, so excluding them raises PRECISION and permits nothing new — every
# positive control still fires through the same rule it fired through before. The
# eight are kept below as negative controls, real values from this repo, so the
# narrowing cannot silently widen later.
_P = r"""[\'"]?((?:/|~/|\$TMPDIR|\$\{TMPDIR\}|\$HOME|\$\{HOME\})[^\s;|&\'")<>{}=`]*)"""

# WRITE POSITIONS. Each entry: (name, compiled regex, group index of the path).
# `>&` and `2>&1` do not match because `&` is not a path start.
WRITE_POSITIONS = [
    ('redirect', re.compile(r'>>?\s*' + _P), 1),
    ('tee', re.compile(r'\btee\b(?:\s+-\S+)*\s+' + _P), 1),
    ('outflag', re.compile(r'(?:^|\s)(?:-o|--output|--output-file|--file)[=\s]+' + _P), 1),
    # `-F` is SCOPED TO git and not listed above, because the flag is overloaded
    # and the generic form measured a false positive on this repo's own awk:
    # `awk -F '/^verdict=/{print $2}'` (H120_orphan_quorum/run.sh:16) reads the
    # field separator as an output file. `-F` earns its place here only because
    # `git commit -F <file>` is the exact form of TWO of the eight recorded §10
    # instances (ATOM-3's /tmp/kfmsg.txt, AGENT-1's d717518 message file), so the
    # rule is kept and narrowed rather than dropped.
    ('git-msgfile', re.compile(r'\bgit\b[^;|&]*?\s-F[=\s]+' + _P), 1),
    ('dd', re.compile(r'\bof=' + _P), 1),
    # touch/mkdir/rmdir write EVERY path argument.
    ('mkpath', re.compile(r'\b(?:touch|mkdir|rmdir)\b(?:\s+-\S+)*\s+' + _P), 1),
]
# cp/mv/rsync/ln/install write only their LAST argument; the earlier ones are
# reads. `cp /tmp/a ./b` copies OUT of /tmp and violates nothing, so flagging
# every argument would be the read/write confusion C3 exists to prevent.
LAST_ARG_WRITERS = re.compile(r'\b(?:cp|mv|rsync|ln|install)\b((?:\s+[^\s;|&<>]+)+)')
# `mktemp` with no in-workspace template resolves to $TMPDIR, which on macOS is
# /var/folders/... — outside. Three sites in this tree already pass a template
# under the workspace (`test_h75_routing.sh`, `test_h66.sh`, `fleetcensus.sh`),
# so the compliant form is not hypothetical: it is in use here, unremarked.
# D4 (v3, H194). `mktemp` must be in COMMAND POSITION. The rule used to be a
# bare word match, so ANY command merely MENTIONING the word was refused --
# `grep -v mktemp scan.out` is a read and was rejected as a write. Found by the
# gate refusing my own investigation of its own census, which is precisely what
# C2 ("reads are not writes") exists to prevent, at the one rule C2's corpus
# never covered. PRE-EXISTING SINCE v1, not introduced by v3: the precision
# corpus was source lines plus nine hand-written negatives, and not one of them
# mentioned the word as an argument. That is H194's own thesis one level down --
# a corpus that does not contain the commands anyone actually types.
MKTEMP = re.compile(r'(?:^|[;&|`(]|\$\()\s*mktemp\b([^;|&]*)')
# D3 (v3, H194): a directory change out of the workspace, and any write operator.
# Split into two patterns rather than one, because the `cd` target and the write
# are in different clauses and a single regex spanning them would be unreadable
# and would silently depend on their order.
# Lifted to a module flag ONLY so `--selfcheck` can mutate it. v3's first form
# had the comment drop inline, which meant NO mutation could reach it -- and a
# fix whose control cannot be constructed is the shape this lane keeps finding
# in other lanes' suites.
_DROP_COMMENTS = True
CD_OUT = re.compile(r'(?:^|[;&|]|\s)cd\s+' + _P)
WRITE_OP = re.compile(r'(?:>>?[^&]|\btee\b|\bcp\b|\bmv\b|\btouch\b|\bmkdir\b|\bof=)')


def outside(path):
    """True if `path` names a location outside the workspace.

    Read at call time from the module globals on purpose: `--selfcheck` mutates
    ALLOW_PREFIXES, and a default argument would bind at definition time and the
    mutation would never reach here. That exact defect is recorded in
    MISSION_LOOP §13.2 as a thing this repo has already paid for.
    """
    if not path or path.strip('\'"') in ('/', '~/', '$HOME', '$TMPDIR'):
        # A bare `/` is what an awk program's leading slash looks like once the
        # stop set has eaten the rest. It is not a write target.
        return False
    p = path.strip('\'"')
    for a in ALLOW_PREFIXES:
        if p.startswith(a):
            return False
    if p.startswith('~/') or p.startswith('$HOME') or p.startswith('${HOME}'):
        return True
    if p.startswith('$TMPDIR') or p.startswith('${TMPDIR}'):
        return True
    if not p.startswith('/'):
        return False
    return os.path.abspath(p) != ROOT and not os.path.abspath(p).startswith(ROOT + os.sep)


def _in_quotes(cmd):
    """Offsets of characters inside a quoted span.

    ONLY the redirect rule consults this, and the asymmetry is the finding.
    `printf %s "<string>/bin/bash</string>"` (bringup.sh:425) puts a literal `>`
    immediately before a path, and at the character level that is
    indistinguishable from a redirect — the tightened stop set could not fix it
    because `/bin/bash` is a perfectly well-formed outside path. A `>` inside
    quotes is not an operator. But the PATH of a real write is very often quoted
    (`mkdir -p "$HOME/Library/LaunchAgents"`, bringup.sh:418), so masking quoted
    spans for every rule would delete a true positive to remove a false one.
    Operator position is quote-sensitive; argument position is not.
    """
    inside, q, esc = [False] * len(cmd), None, False
    for i, c in enumerate(cmd):
        if esc:
            esc = False
        elif c == chr(92) and q != chr(39):
            # A backslash escapes the next character -- EXCEPT inside single
            # quotes, where the shell gives it no special meaning. v2 ignored
            # escapes entirely, so a doubled-quote inside a double-quoted string
            # desynced the state and every redirect after it read as quoted.
            esc = True
        elif q is None and c in '"' + chr(39):
            q = c
        elif q == c:
            q = None
        inside[i] = q is not None
    return inside


def _quote_kinds(cmd):
    """Per character: the quote char it sits inside, or None. Same scanner as
    `_in_quotes`, which returns only a boolean and cannot answer the question the
    anchor rule needs: a backtick or `$(` inside DOUBLE quotes is still a command
    substitution, and inside SINGLE quotes nothing is."""
    kinds, q, esc = [None] * len(cmd), None, False
    for i, c in enumerate(cmd):
        if esc:
            esc = False
        elif c == chr(92) and q != chr(39):
            esc = True
        elif q is None and c in '"' + chr(39):
            q = c
        elif q == c:
            kinds[i] = q
            q = None
            continue
        kinds[i] = q
    return kinds


def _anchor_quoted(cmd, start, kinds):
    """True when the operator that puts a keyword in COMMAND POSITION is itself
    inside quotes (H254, ok-1, 2026-08-19).

    MEASURED, and it is this gate refusing a READ of its own subject:

        grep -nE 'git |cp |mktemp|TMP' spikes/harness/test_h219_falsify.sh
        -> §10 REFUSED: this writes outside the workspace.  mktemp $TMPDIR

    The `|` before `mktemp` is a regex alternation inside a quoted pattern, and
    `MKTEMP`'s anchor set treats any `|` as a pipe -- so a word inside a search
    pattern was read as a command. The module already carries three such cases
    from H194 under the same heading ("a gate that refuses the investigation of
    its own rail is unusable") and this is the fourth: the earlier three are clean
    only because their token has a SPACE before it, not because quoting is
    understood.

    NOT a mask over quoted spans: `_in_quotes`'s docstring records why that would
    delete true positives, since the PATH of a real write is very often quoted.
    This looks only at the OPERATOR, and only at whether the operator is live.
    """
    if start >= len(kinds):
        return False
    q = kinds[start]
    if q is None:
        return False
    if q == '"' and cmd[start] in '`$':
        return False        # command substitution IS live inside double quotes
    return True


_in_quotes_real = _in_quotes


def write_targets(cmd):
    """[(kind, path)] for every out-of-workspace WRITE position in `cmd`."""
    if chr(10) in cmd:
        lines = strip_heredocs(cmd.split(chr(10)))
        # D2 (v3, H194). DROP WHOLE-COMMENT LINES BEFORE ANY CLASSIFICATION.
        # v2 did this in `scan_source` alone and I wrote down why: "a comment
        # cannot reach the hook, which is handed a whole command." A multi-line
        # Bash command carries comment lines and they DO reach the hook, and an
        # apostrophe in one (`# don't`) opened a quote span that never closed,
        # so every redirect below it read as quoted and was missed. The
        # reasoning was wrong, not the placement -- so the skip belongs in BOTH,
        # and `scan_source` keeps its own for the separate reason that it never
        # sees a hook payload at all.
        if _DROP_COMMENTS:
            lines = [l for l in lines if not l.lstrip().startswith('#')]
        cmd = chr(10).join(lines)
    hits = []
    quoted = _in_quotes(cmd)
    for name, rx, gi in WRITE_POSITIONS:
        for m in rx.finditer(cmd):
            if name == 'redirect' and m.start() < len(quoted) and quoted[m.start()]:
                continue
            if outside(m.group(gi)):
                hits.append((name, m.group(gi).strip('\'"')))
    for m in LAST_ARG_WRITERS.finditer(cmd):
        args = [a for a in m.group(1).split() if not a.startswith('-')]
        if args and outside(args[-1]):
            hits.append(('copy-dest', args[-1].strip('\'"')))
    kinds = _quote_kinds(cmd)
    for m in MKTEMP.finditer(cmd):
        if _anchor_quoted(cmd, m.start(), kinds):
            continue                      # H254: a `|` inside quotes is not a pipe
        tail = m.group(1)
        tmpl = [a for a in tail.split() if not a.startswith('-')]
        if not tmpl:
            hits.append(('mktemp', '$TMPDIR (no template)'))
        elif outside(tmpl[0]):
            hits.append(('mktemp', tmpl[0].strip('\'"')))
    # D3 (v3, H194). `cd <outside> && <relative write>`. Needs WHOLE-COMMAND
    # context, so it cannot be a WRITE_POSITIONS entry: the path that lands
    # outside never appears in the command at all. Adopted only after measuring
    # it against 6,454 real command lines from the tracked tree and every
    # negative control -- ZERO false positives, which REFUTED my prediction that
    # it would cost some and is the only reason it is a rule rather than a
    # documented limitation.
    m = CD_OUT.search(cmd)
    if m and _anchor_quoted(cmd, m.start(), kinds):
        m = None                          # H254: `cd` inside a search pattern
    if m and outside(m.group(1)) and WRITE_OP.search(cmd):
        hits.append(('cd-then-write', m.group(1).strip(chr(39) + '"')))

    # dedupe, order-preserving
    seen, out = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out


def scan_source(paths):
    """The source half, SHELL ONLY. [(file, lineno, kind, path)].

    Returns `(rows, skipped)` via `scan_source_counted`; this name keeps the
    plain list for callers that only want rows.
    """
    return scan_source_counted(paths)[0]


def scan_source_counted(paths):
    found, skipped = [], []
    for p in paths:
        if not p.endswith(('.sh', '.hook')):
            skipped.append(p)
            continue
        try:
            with open(p, errors='replace') as f:
                # Whole file, then heredoc bodies blanked, THEN line by line.
                # Reading line by line cannot see the heredoc a line sits in,
                # which is how the plist XML in bringup.sh was read as a redirect.
                # D5 (v3, H194). THE STRIPPER IS A SHELL LEXER AND ONLY SHELL
                # GETS IT -- and the same is true of the classifier above it,
                # which is why `--scan` now takes only `.sh`/`.hook` and SAYS SO.
                # Working through it in order, because both wrong answers look
                # right from the total:
                #   * stripping heredocs from `.py` blanked 1,048 non-blank
                #     Python lines tree-wide (91.3% of THIS file, 95.9% of
                #     `recordloss.py`), because a PROSE MENTION of `<<'EOF'` in a
                #     docstring opens a heredoc that never closes. Census read 17
                #     where 28 positions were reachable;
                #   * NOT stripping them surfaced 7 rows, every one of them this
                #     module's own docstring prose and FIXTURE LISTS -- which is
                #     `versioncheck.py` v1 flagging its own test suite, the
                #     defect `strip_heredocs` was written for;
                #   * skipping Python string literals via `ast` would work and is
                #     wrong: a shell command embedded in a `.py` IS a string
                #     literal, so it would blind the scan to Python entirely
                #     while still reporting a number.
                # The instrument is a SHELL classifier. On a `.py` it can only
                # ever find shell embedded in strings, and in this tree that is
                # fixtures. So Python is EXCLUDED AND COUNTED IN THE OUTPUT
                # rather than silently mis-scanned -- H186's distinction, that a
                # thing absent from a sweep's own "N excluded" line cannot be
                # told from a thing that is not there. WHAT THIS DOES NOT COVER,
                # named rather than left implied: `open(p,'w')`,
                # `tempfile.mkdtemp()` and `os.makedirs` in Python are invisible
                # to any shell classifier, filed as H198. Python has no heredocs, so on a `.py` the pattern
                # `<<-?\s*['\"]?(\w+)` matches a PROSE MENTION of one inside a
                # docstring and blanks every line to the end of file. MEASURED
                # over the tracked tree: 1,048 non-blank Python lines blanked,
                # including 91.3% of THIS FILE (triggered by my own v2 rationale
                # block describing the heredoc defect) and 95.9% of
                # `recordloss.py`. The census read 17 while 28 write positions
                # were reachable -- an under-report that looks exactly like
                # compliance. Same class as D2 and as `versioncheck.py`'s own
                # origin defect: a lexer for one language applied to another
                # deletes content, and the checker reports clean over the hole.
                lines = strip_heredocs(f.read().split(chr(10)))
                for i, line in enumerate(lines, 1):
                    # SKIPPED HERE AND NOT IN `write_targets`, DELIBERATELY.
                    # These two are artifacts of reading SOURCE line by line; the
                    # hook is handed a real command and has neither problem. Had
                    # I put them in the shared classifier — which is where they
                    # first went — a precision fix for the CENSUS would have
                    # silently narrowed the live GATE, which is §12.2's class
                    # with the sign flipped: the right fix at the wrong site.
                    #   * a comment is not a command (`# at <arm>/spikes/...`,
                    #     test_autoloop_local.sh:7; `touch ~/Library/...  §10 --
                    #     that is outside the workspace`, test_h58:23 — a line
                    #     WARNING about the rail, reported as breaking it);
                    #   * `</string>` closes a tag, and the `>` before a path in
                    #     `<string>/bin/bash</string>` (bringup.sh:425) is not a
                    #     redirect. Per-line scanning cannot see the heredoc it
                    #     sits in, so quote state does not reach it.
                    if line.lstrip().startswith('#'):
                        continue
                    for kind, tgt in write_targets(line):
                        found.append((p, i, kind, tgt))
        except (IsADirectoryError, FileNotFoundError, PermissionError):
            continue
    return found, skipped


REFUSAL = """§10 REFUSED: this writes outside the workspace.

  {hits}

CLAUDE.md safety rails and MISSION_LOOP §10: "Nothing is written outside the
workspace." Eight instances are on record and seven were exactly this shape — a
scratch path typed at a shell because there was nowhere sanctioned to put one.

Sanctioned location, inside the workspace and gitignored:

  {scratch}/

Re-run with the path under {scratch}/ . If you believe this is a false positive,
say so in DECISIONS.log and use the path anyway via a form this gate does not
classify — do NOT widen the gate to pass it (brief §9, MISSION_LOOP §5).
"""


def hook(stream=None):
    """PreToolUse. Exit 2 refuses; ANY internal failure exits 0 (fails open).

    Fails open because five lanes route every Bash call through here and H124
    recorded a fleet-wide outage from a gate that stopped parsing. The asymmetry
    is deliberate and it is the residue: a write this module cannot classify
    proceeds.
    """
    try:
        payload = json.load(stream or sys.stdin)
        ti = payload.get('tool_input') or {}
        tool = payload.get('tool_name') or ''
        if tool == 'Bash':
            hits = write_targets(ti.get('command') or '')
        elif tool in ('Write', 'Edit', 'NotebookEdit'):
            fp = ti.get('file_path') or ti.get('notebook_path') or ''
            hits = [('file_path', fp)] if outside(fp) else []
        else:
            hits = []
    except Exception:
        return 0
    if not hits:
        return 0
    body = '\n  '.join('%-11s %s' % (k, p) for k, p in hits)
    sys.stderr.write(REFUSAL.format(hits=body, scratch=SCRATCH))
    return 2


# ---------------------------------------------------------------- selfcheck --
POSITIVE = [
    # Every one of these is a REAL command from this repo's own record.
    ('git commit -F /tmp/kfmsg.txt', 'CHANNEL.md:726, ATOM-3'),
    ('cp .github/autoloop/config.json /tmp/config.json.bak', 'CHANNEL.md:726'),
    ("printf '%s\\n' \"$3\" > /tmp/_cm.$$", 'test_commit_msg.sh:8, live at HEAD'),
    ('mkdir -p "$HOME/Library/LaunchAgents"', 'bringup.sh:418, live at HEAD'),
    ('T=$(mktemp -d)', 'ten sites in spikes/harness/'),
    ('echo hi | tee /tmp/out.txt', 'tee position'),
    ('dd if=/dev/zero of=/tmp/blob bs=1', 'dd of= position'),
    # H194 (v3). THE THREE v2 MISSED. Each is a write §10 forbids that the gate
    # returned clean on, measured through the live hook and not only through
    # this function. D1 and D2 were drilled by v2's own quote-awareness fix.
    ('echo "a' + chr(92) + '"b" > /tmp/x', 'H194 D1 — backslash-escaped quote desynced quote state'),
    ("# note: don't forget" + chr(10) + 'echo x > /tmp/y',
     'H194 D2 — an apostrophe in a COMMENT line poisoned every line below it'),
    ('cd /tmp && echo x > y', 'H194 D3 — cwd change makes a relative write land outside'),
]
NEGATIVE = [
    # C3. These MENTION an out-of-workspace path and write nothing. The commands
    # that measured this row are in here on purpose: a gate that refuses the
    # investigation of its own rail is unusable.
    ("grep -rno '/tmp/[A-Za-z]*' spikes/harness/", 'the measurement that built this'),
    ('cat /tmp/somebody_elses.log', 'read'),
    ('ls -la /tmp', 'read'),
    ('cp /tmp/downloaded.tar ./corpus/', 'copies INTO the workspace'),
    ('sh "$H" /tmp/_cm.$$ >/dev/null 2>&1', 'argument is READ; 2>&1 is not a path'),
    ('T=$(mktemp -d "$ROOT/spikes/.h75routing.XXXXXX")', 'the compliant form, in use here'),
    ('echo done > "$ROOT/out/x.txt"', 'inside the workspace'),
    ('python3 x.py --out /dev/null', 'allowlisted'),
    ('adb shell "cat /data/local/tmp/fuelrun"', 'device path, H89 F2'),
    # D4 (H194). Real commands from this cycle that the gate refused as writes.
    ('python3 scratchcheck.py --scan | grep -v mktemp', 'H194 D4 — my own command, refused'),
    ('grep -rn "mktemp -d" spikes/harness/', 'H194 D4 — mktemp inside a search pattern'),
    # H254 (v4). THE FOURTH COMMAND OF MY OWN THIS GATE REFUSED, and the three
    # above are clean only because their token has a SPACE before it: an
    # alternation with none puts `mktemp` immediately after a `|` that the
    # anchor set reads as a pipe.
    ("grep -nE 'git |cp |mktemp|TMP' spikes/harness/test_h219_falsify.sh",
     'H254 — a regex alternation is not a pipe'),
    ("grep -n 'x|cd /etc && touch y' f.sh", 'H254 — the same for the cd rule'),
    ("awk -F'|' '$2 ~ /mktemp/' WORK_QUEUE.md", 'H254 — awk field separator'),
    ('echo "use mktemp under .scratch" >> notes.md', 'H194 D4 — the word in in-workspace prose'),
    # H194 (v3). The `cd` rule must not fire without a write, or it becomes a
    # ban on changing directory. Measured at 0 false positives over 6,454 real
    # command lines; these keep the narrowness that made that true.
    ('cd /tmp && ls -la', 'H194 — cd to a read, no write operator'),
    ('cd /tmp && grep -r pattern .', 'H194 — cd to a search'),
    ('cd "$ROOT" && echo x > out/y', 'H194 — cd INSIDE the workspace, then write'),
    # The eight false positives the FIRST form of this classifier reported over
    # the tracked tree. Real lines, cited by file, kept so the precision fix
    # cannot regress into the widening it looks like.
    ("awk -F '/^verdict=/{print $2}' x", 'H120_orphan_quorum/run.sh:16 — awk -F'),
    ("awk '/CPU_Speed_Limit/{print $NF}'", 'spikes/quiet.sh:204 — awk -F'),
    ("awk '/^BEGIN/{f=1} f'", 'S62_llm_backend_determinism/extract.sh:4'),
    ('printf %s "<string>/bin/bash</string><string>$(pwd)</string>"',
     'bringup.sh:425 — XML in a heredoc read as a redirect'),
    ('# see `spikes/harness/` for the suite', 'test_autoloop_local.sh:7 — backtick in prose'),
    # THE ONE v1 OF THIS FILE REFUSED: a heredoc whose BODY quotes the gate's own
    # refusal message. Assembled from parts rather than written as a literal,
    # because a literal multi-line fixture in a source file is the same defect
    # one level up -- and that is exactly how `versioncheck.py` v1 flagged itself.
    (chr(10).join(["cat > RESULT.md <<'XEOF'",
                  'mkdir -p "$HOME/Library/LaunchAgents"',
                  'echo x > /tmp/h89_liveness_probe.txt', 'XEOF']),
     "the write of this row's own RESULT.md, refused by v1 of this file"),
    (chr(10).join(["cat > x.sh <<'XSH'", 'T=$(mktemp -d)', 'XSH']),
     'a heredoc body containing the very form the gate exists to catch'),
]


def selfcheck():
    global ALLOW_PREFIXES, WRITE_POSITIONS
    p = f = 0

    def t(ok, label):
        nonlocal p, f
        if ok:
            p += 1
        else:
            f += 1
            print('  FAIL  %s' % label)

    for cmd, why in POSITIVE:
        t(bool(write_targets(cmd)), 'positive: %s   (%s)' % (cmd, why))
    for cmd, why in NEGATIVE:
        t(not write_targets(cmd), 'negative: %s   (%s)' % (cmd, why))

    # C1 · the hook actually refuses, end to end, through the JSON it will really
    # be handed — not through write_targets(), which the checks above already use.
    import io
    ev = json.dumps({'tool_name': 'Bash',
                     'tool_input': {'command': 'echo x > /tmp/y'}})
    t(hook(io.StringIO(ev)) == 2, 'C1 hook refuses a Bash write (exit 2)')
    ev = json.dumps({'tool_name': 'Bash',
                     'tool_input': {'command': 'echo x > out/y'}})
    t(hook(io.StringIO(ev)) == 0, 'C1 hook permits an in-workspace write')
    t(hook(io.StringIO('not json at all')) == 0, 'C2 hook FAILS OPEN on garbage')
    ev = json.dumps({'tool_name': 'Write',
                     'tool_input': {'file_path': '/tmp/x.md'}})
    t(hook(io.StringIO(ev)) == 2, 'C1 hook refuses a Write tool file_path')

    # C4 · MUTATION. A check that cannot fail against the defect it was written
    # for is not evidence the defect is gone (H186). Two mutations, each of which
    # must take a DIFFERENT control red — and each asserts the patch REACHED the
    # code, because a mutation that does not land looks exactly like a robust
    # module (G97, and H167's inert selfcheck arm).
    saved_allow, saved_pos = ALLOW_PREFIXES, WRITE_POSITIONS

    # M1: widen the allowlist to everything. The positives must collapse.
    ALLOW_PREFIXES = ('/', '~', '$')
    landed = not write_targets('echo x > /tmp/y')
    t(landed, 'C4/M1 mutation LANDED (allowlist widened, positive went quiet)')
    ALLOW_PREFIXES = saved_allow
    t(bool(write_targets('echo x > /tmp/y')), 'C4/M1 restored')

    # M2: drop the write-position restriction — match a bare path anywhere. The
    # NEGATIVES must break. This is the mutation that proves C3 is load-bearing
    # rather than decorative: without write positions, the read commands refuse.
    WRITE_POSITIONS = [('any', re.compile(_P), 1)]
    broke = [c for c, _ in NEGATIVE if write_targets(c)]
    t(len(broke) >= 4,
      'C4/M2 mutation LANDED (write-position dropped: %d/%d negatives now refuse)'
      % (len(broke), len(NEGATIVE)))
    WRITE_POSITIONS = saved_pos
    t(not any(write_targets(c) for c, _ in NEGATIVE), 'C4/M2 restored')

    # C7 · MUTATION FOR EACH v3 FIX (H194). Every one reverts a specific defect
    # and must take THAT defect's case red and leave the others alone -- a single
    # mutation that reddens everything proves only that the module runs.
    global _DROP_COMMENTS, CD_OUT
    esc_case = 'echo "a' + chr(92) + '"b" > /tmp/x'
    cmt_case = "# note: don't forget" + chr(10) + 'echo x > /tmp/y'
    cd_case = 'cd /tmp && echo x > y'

    # M3 · D1 reverted: quote scanning without escape awareness, which is exactly
    # what the committed v2 blob does.
    def _v2_in_quotes(cmd):
        inside, q = [False] * len(cmd), None
        for i, c in enumerate(cmd):
            if q is None and c in '"' + chr(39):
                q = c
            elif q == c:
                q = None
            inside[i] = q is not None
        return inside
    g = globals()
    g['_in_quotes'] = _v2_in_quotes
    t(not write_targets(esc_case), 'C7/M3 D1 reverted -> escaped-quote write goes MISSED')
    t(bool(write_targets(cd_case)), 'C7/M3 leaves the cd case alone')
    g['_in_quotes'] = _in_quotes_real

    # M6 · v4 REVERTED (H254): the anchor rule off, i.e. an operator inside
    # quotes is an operator again. The three H254 negatives must refuse, and the
    # true positives must be untouched -- a mutation that reddens everything would
    # prove only that the module runs.
    alt_case = "grep -nE 'git |cp |mktemp|TMP' f.sh"
    g6 = globals()
    _real_anchor = g6['_anchor_quoted']
    g6['_anchor_quoted'] = lambda cmd, start, kinds: False
    t(bool(write_targets(alt_case)),
      'C7/M6 v4 reverted -> a regex alternation refuses again (the reported defect)')
    t(bool(write_targets('ls | mktemp')), 'C7/M6 leaves the real pipe firing')
    g6['_anchor_quoted'] = _real_anchor
    t(not write_targets(alt_case), 'C7/M6 restored')

    # M4 · D2 reverted: comment lines no longer dropped.
    _DROP_COMMENTS = False
    t(not write_targets(cmt_case), 'C7/M4 D2 reverted -> comment-apostrophe write goes MISSED')
    _DROP_COMMENTS = True
    t(bool(write_targets(cmt_case)), 'C7/M4 restored')

    # M5 · D3 reverted: the cd rule cannot match.
    saved_cd = CD_OUT
    CD_OUT = re.compile(r'(?!x)x')
    t(not write_targets(cd_case), 'C7/M5 D3 reverted -> cd-then-write goes MISSED')
    t(bool(write_targets(esc_case)), 'C7/M5 leaves the escaped-quote case alone')
    CD_OUT = saved_cd
    t(bool(write_targets(cd_case)) and bool(write_targets(cmt_case))
      and bool(write_targets(esc_case)), 'C7 all three restored')

    # C5 · the sanctioned location must itself pass. A gate whose own remedy is
    # refused is the always-red gate H14/H52/H73 were each bypassed for.
    t(not write_targets('echo x > %s/tmp.txt' % SCRATCH),
      'C5 the sanctioned .scratch/ path is PERMITTED')
    t(not write_targets('T=$(mktemp -d "%s/x.XXXXXX")' % SCRATCH),
      'C5 mktemp under .scratch/ is PERMITTED')

    # C6 · the heredoc stripper is REACHABLE. Without it this module cannot
    # classify a multi-line command safely and `hook()` must not block; a silent
    # fallback that kept blocking would be a gate refusing prose, and a silent
    # fallback that stopped blocking without saying so would be a gate that had
    # quietly become decoration. Either way the sweep must see it.
    t(_STRIPPER, 'C6 versioncheck.strip_heredocs is importable (v2 D1)')

    print('scratchcheck: %d passed, %d FAILED' % (p, f))
    return 1 if f else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == '--selfcheck':
        sys.exit(selfcheck())
    if a and a[0] == '--hook':
        sys.exit(hook())
    if a and a[0] == '--scan':
        targets = a[1:]
        if not targets:
            import subprocess
            # H213: `-c` AND `-o --exclude-standard` — tracked AND untracked.
            # The cycle writing a new probe has not committed it yet, and that
            # is exactly the file worth scanning. `--exclude-standard` honours
            # .gitignore so `.scratch/` and build trees stay out; the `elders/`
            # filter is kept explicitly because a rail must not depend on a
            # file any lane can edit.
            seen, targets = set(), []
            for t in subprocess.run(
                    ['git', 'ls-files', '-c', '-o', '--exclude-standard',
                     '*.sh', '*.py', '*.hook'], cwd=ROOT,
                    capture_output=True, text=True).stdout.split():
                if t.startswith('elders/') or t in seen:
                    continue
                seen.add(t)
                targets.append(os.path.join(ROOT, t))
        rows, skipped = scan_source_counted(targets)
        for fpath, ln, kind, tgt in rows:
            print('%s:%d: %-11s %s' % (os.path.relpath(fpath, ROOT), ln, kind, tgt))
        print('scratchcheck --scan: %d write position(s) outside the workspace '
              'in %d shell file(s)' % (len(rows), len(targets) - len(skipped)))
        if skipped:
            print('  NOT SCANNED: %d non-shell file(s). This is a SHELL '
                  'classifier; Python writes (`open(p,%sw%s)`, '
                  '`tempfile.mkdtemp()`, `os.makedirs`) are invisible to it and '
                  'are filed as H198. Counted here so absent cannot be mistaken '
                  'for clean (H186).' % (len(skipped), chr(39), chr(39)))
        sys.exit(0)
    print(__doc__)
    sys.exit(0)
