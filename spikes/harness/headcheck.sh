#!/usr/bin/env bash
# headcheck.sh v2 — H60 (v1), H70 (v2). ATOM-3, 2026-08-17.
#
# ============================ v2, H70 — the defect removed ==================
# CLASS: A DIFFERENTIAL CHECK THAT VARIES TWO THINGS BETWEEN ITS ARMS -- THE
# DATA *AND* THE INSTRUMENT -- AND ATTRIBUTES 100% OF THE DIFFERENCE TO THE DATA.
#
# v1 ran HEAD's `refcheck.py` over HEAD's files and compared that to what a lane
# sees: the TREE's `refcheck.py` over the TREE's files. `refcheck.py` is itself a
# harness file and can itself be uncommitted. On 2026-08-17 it was -- one line of
# ok-1's, widening the not-a-citation charset -- so 2 of v1's 13 refusals were
# caused by a fix that EXISTS AND IS NOT COMMITTED, and v1 called both of them
# `ABSENT`, whose remedy text reads "the citation is genuinely dangling: file the
# missing thing as OPEN".
#
# That remedy was actively dangerous for those two. The path is `prompts/L"6.md`,
# ok-1's deliberate injection fixture; I had posted to `livechat.log` 40 minutes
# earlier that it must NOT be created, because it would put a file named after an
# injection payload in the brief directory `run_loop.sh` reads to authorise a
# launch -- and `test_loop_gate.sh:548` `rm -f`s that path, so a tracked stub
# would be deleted by the suite. **My own checker's remedy prescribed the action
# I had just told another lane to refuse.**
#
# MEASURED, three arms, falsifier preregistered in `CHANNEL.md` before the run:
#   A  HEAD checker + HEAD data  13 refusals   (what v1 reported)
#   B  TREE checker + HEAD data  11 refusals   (A\B = 2, caused by the INSTRUMENT)
#   C  TREE checker + TREE data   0 refusals   (B\C = 11, caused by the DATA)
# The falsifier was "if A == B the instrument is not a variable and this is
# withdrawn". It did not fire.
#
# Arm B relocates the ARTIFACT, not the caller: `refcheck.py:111` derives ROOT
# from `__file__`, so running the tree copy in place would scan the TREE and
# measure nothing (AGENT-1's rule, `livechat.log`, H57 ATTACK).
#
# RESIDUAL, stated rather than silently dropped: only A\B is reported. A refusal
# in B and not A -- your uncommitted checker being STRICTER than HEAD's -- is a
# real finding and this does not surface it, because the question here is "does a
# clean clone go green", which arm A alone answers. `diff` the two arms by hand if
# you want the other direction; no code here pretends to.
# ===========================================================================
#
# THE DEFECT IT EXISTS FOR
# ------------------------
# `refcheck.py` refused on HEAD with 7 unresolved citations while EVERY LANE'S
# LOCAL RUN WAS GREEN, for hours, and no lane could see it. The checkers read
# files with plain `open()`, so their verdict is a function of the WORKING TREE;
# the tree contains every lane's uncommitted work; a clean clone contains none of
# it. That is H35's class (a checker reading the TREE while its verdict is
# attributed to the COMMIT) and H36 is still open on an earlier site.
#
# AND THE FINDING UNDERNEATH IT IS NOT "BROKEN CITATIONS". Measured 2026-08-17
# 16:2x: 3 of the 7 paths EXISTED ON DISK AND HAD NEVER BEEN COMMITTED --
# `spikes/S85_verify_vs_reexec/` (RESULT.md + generator + 2 JSON, finished 15:32)
# and `spikes/W6_incremental_witness/` (16:11) are FINISHED SPIKES, and
# `spikes/harness/net.kingfisher.fleet.plist` was mine. The citations were right
# and the RECORD was incomplete. §13: *an uncommitted result is indistinguishable
# from one that was never run, and it is invisible to every other agent.*
#
# CLASS: WORK THAT EXISTS ON DISK AND WAS NEVER COMMITTED, CITED BY FILES THAT
# WERE. The lane that did the work is the one lane that cannot see the problem.
#
# WHAT THIS ADDS over `python3 spikes/harness/refcheck.py`
# -------------------------------------------------------
# It runs the SAME checkers, unchanged, against a clean materialisation of HEAD,
# and then splits the refusals into the two cases that need opposite actions:
#
#   CHECKER-UNCOMMITTED  the refusal disappears under YOUR copy of the checker
#                -> the fix is written and not committed. `git commit --only` the
#                CHECKER. Never touch the cited path: creating it is the stub the
#                rails forbid, and here it would be an injection-payload filename
#                in `prompts/`. Asked FIRST, because attributing to the data while
#                the instrument moved is the whole of H70.
#   UNCOMMITTED  the path exists in your tree -> `git commit --only <path>`.
#                Yours to fix, and only you can: it is not in anyone else's tree.
#   ABSENT       the path is nowhere, under EITHER checker -> genuinely dangling.
#                File the missing thing as OPEN; never write a stub to go green.
#
# refcheck.py is NOT modified and NOT narrowed. It is ok-1's, it is correct, and
# a checker that goes green by shrinking its own scope is H26b.
#
# NO WRITE OUTSIDE THE WORKSPACE and no write to the tree: scratch lives under
# `spikes/harness/.headcheck.$$` and is removed on exit. A read-only diagnostic
# that writes is H44's defect.
#
# usage:
#   sh spikes/harness/headcheck.sh              # judge HEAD, classify refusals
#   sh spikes/harness/headcheck.sh --selfcheck  # prove both branches can fire
# exit 0 = HEAD is clean. 1 = HEAD refuses. 2 = could not materialise HEAD.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)

# Classify one cited path. Deliberately takes the path as an ARGUMENT and does
# not consult a captured list: the two branches must be decided by `ls` and
# `git ls-files` on the thing itself, never by re-reading the citation that
# named it -- which is the mistake that produced the citations in the first
# place (H44: a prose claim about an artifact, restated instead of re-measured).
#
# v2: `$2` is 1 when this refusal is in the INSTRUMENT set (present under HEAD's
# checker, gone under yours) and 0 otherwise. Asked before anything about the
# path, because a refusal your own tree has already fixed is not a fact about
# the path at all -- that inversion is H70.
classify() {
  if [ "${2:-0}" = 1 ]; then
    printf 'CHECKER-UNCOMMITTED %s\n' "$1"
  elif [ -e "$ROOT/$1" ]; then
    if git -C "$ROOT" ls-files --error-unmatch "$1" >/dev/null 2>&1; then
      printf 'TRACKED-BUT-STALE %s\n' "$1"    # in the index at a different path/case
    else
      printf 'UNCOMMITTED %s\n' "$1"
    fi
  else
    printf 'ABSENT %s\n' "$1"
  fi
}

# Lines present in $1 and absent from $2. Factored out so `--selfcheck` can fire
# it on controlled input: the differ is the part that decides ATTRIBUTION, and a
# differ that always returns empty would make CHECKER-UNCOMMITTED unreachable
# while every classify() assertion still passed (A15, a control that cannot fire).
only_in_a() { comm -23 "$1" "$2"; }

# The checkers headcheck EXECUTES, and therefore the files whose own dirtiness
# can move its verdict. Derived from the `python3 spikes/harness/...` lines in
# this file rather than typed, so adding a second checker below cannot leave the
# relocation list silently behind (H30: a missing input degrades a mechanism to a
# no-op and it still reports success).
checkers() {
  grep -oE 'python3 spikes/harness/[A-Za-z0-9_]+\.py' "$0" | awk '{print $2}' | sort -u
}

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3: the check ships a check, and BOTH branches must fire. A classifier
  # that only ever answers one way is the shape that let refcheck's tree-reading
  # verdict pass as a commit verdict for hours.
  sc="$ROOT/spikes/harness/.selfcheck-head.$$"
  mkdir -p "$sc" || { echo "SELFCHECK FAIL: no scratch"; exit 1; }
  fail=0
  : > "$sc/exists_untracked"
  a=$(ROOT="$sc" classify exists_untracked 0)
  b=$(ROOT="$sc" classify nothing_here 0)
  # C3, v2's falsifier: the SAME absent path, flagged as instrument-caused, must
  # NOT come back ABSENT. If it does, H70 is back -- an uncommitted checker fix
  # is being reported as a dangling citation, whose remedy is to create the file.
  c=$(ROOT="$sc" classify nothing_here 1)
  case "$a" in UNCOMMITTED*) ;; *) echo "SELFCHECK FAIL: on-disk-untracked classified '$a'"; fail=1 ;; esac
  case "$b" in ABSENT*)      ;; *) echo "SELFCHECK FAIL: absent path classified '$b'";      fail=1 ;; esac
  case "$c" in CHECKER-UNCOMMITTED*) ;; *) echo "SELFCHECK FAIL: instrument-caused refusal classified '$c' (H70 is back)"; fail=1 ;; esac
  # And the three must DIFFER: identical answers would pass every case above if
  # the classifier ever collapsed to one string.
  [ "$(printf '%s\n%s\n%s\n' "${a%% *}" "${b%% *}" "${c%% *}" | sort -u | wc -l)" -eq 3 ] || {
    echo "SELFCHECK FAIL: the three branches do not answer differently"; fail=1; }

  # C5 -- the DIFFER, on controlled input, both directions. classify() above is
  # only reached with a flag someone computed; a differ that always returned
  # empty would make CHECKER-UNCOMMITTED unreachable with every case above green.
  printf 'keep\nmoved\n' > "$sc/A"; printf 'keep\n' > "$sc/B"
  [ "$(only_in_a "$sc/A" "$sc/B")" = "moved" ] || { echo "SELFCHECK FAIL: differ missed an instrument-caused line"; fail=1; }
  [ -z "$(only_in_a "$sc/B" "$sc/A")" ]        || { echo "SELFCHECK FAIL: differ invented a line"; fail=1; }

  # C6 -- the relocation list is non-empty and every entry exists. An empty list,
  # or one naming a file that is not there, makes arm B identical to arm A by
  # construction: CHECKER-UNCOMMITTED could never fire and this whole selfcheck
  # would still be green (A15, a control that cannot fail).
  n=0
  for k in $(checkers); do
    n=$((n + 1))
    [ -f "$ROOT/$k" ] || { echo "SELFCHECK FAIL: relocation list names missing '$k'"; fail=1; }
  done
  [ "$n" -gt 0 ] || { echo "SELFCHECK FAIL: relocation list is EMPTY -- arm B cannot differ from arm A"; fail=1; }

  rm -rf "$sc"
  [ "$fail" -eq 0 ] && echo "selfcheck: CHECKER-UNCOMMITTED / UNCOMMITTED / ABSENT are distinguished, the differ fires both ways, and $n checker(s) are relocated"
  exit "$fail"
fi

SC="$ROOT/spikes/harness/.headcheck.$$"
cleanup() { rm -rf "$SC"; }
trap cleanup EXIT
mkdir -p "$SC" || { echo "headcheck: cannot create scratch"; exit 2; }
git archive HEAD 2>/dev/null | tar -x -C "$SC" 2>/dev/null || {
  echo "headcheck: could not materialise HEAD (no commits?)"; exit 2; }

# ARM A -- HEAD's checker over HEAD's files: exactly what a clean clone sees.
# v1 ran this twice, once for the text and once for the status; `$?` on one run
# is the same answer and one fewer thing to keep in step.
out=$(cd "$SC" && python3 spikes/harness/refcheck.py 2>&1); rcA=$?
if [ "$rcA" -eq 0 ]; then
  echo "headcheck: refcheck resolves against HEAD -- a clean clone is green"
  exit 0
fi

echo "$out" | grep -E 'UNRESOLVED|REFUSE'
cited() { sed -n 's/.*UNRESOLVED [^`]*`\([^`]*\)`.*/\1/p' | sed 's|/$||' | sort -u; }
printf '%s\n' "$out" | cited > "$SC/.armA"

# ARM B -- YOUR checker over HEAD's files, which isolates the INSTRUMENT (H70).
# The ARTIFACT is relocated, not the caller: `refcheck.py:111` derives ROOT from
# `__file__`, so invoking the tree copy in place would scan the tree and measure
# nothing (AGENT-1's rule 2, `livechat.log`).
for k in $(checkers); do cp "$ROOT/$k" "$SC/$k" 2>/dev/null; done
outB=$(cd "$SC" && python3 spikes/harness/refcheck.py 2>&1)
if printf '%s\n' "$outB" | grep -qE '^(REFUSE:|refcheck: )'; then
  printf '%s\n' "$outB" | cited > "$SC/.armB"
else
  # A CRASHED checker emits no UNRESOLVED lines, and arm A minus arm B would then
  # blame the instrument for every refusal in the run -- family B, the instrument
  # reporting fiction, inside the fix for an attribution defect. Attribute nothing.
  cp "$SC/.armA" "$SC/.armB"
  echo "  CHECKER-BROKEN  your working-tree checker produced no refcheck verdict;"
  echo "                  nothing is attributed to the instrument. Fix it, re-run."
fi
only_in_a "$SC/.armA" "$SC/.armB" > "$SC/.instr"

# §12.2, fix the CLASS not the site. Arm B can only isolate the checkers this
# script RUNS. Every other harness checker can also be uncommitted while its
# verdict is read as a statement about the repo, and nothing anywhere told a lane
# that. Three lines, and it covers `journalcheck`, `idscope`, `cite`,
# `githygiene`, `rostercheck` — none of which arm B can reach.
dirty=$(cd "$ROOT" && git diff --name-only HEAD -- spikes/harness/ 2>/dev/null)
if [ -n "$dirty" ]; then
  echo
  echo "HARNESS FILES DIRTY IN YOUR TREE — every verdict you read from these is"
  echo "about YOUR copy, not about the repo. Only the relocated one(s) above are"
  echo "isolated by arm B; the rest are simply not comparable:"
  printf '%s\n' "$dirty" | sed 's/^/  /'
fi

echo
ni=$(wc -l < "$SC/.instr" | tr -d ' '); na=$(wc -l < "$SC/.armA" | tr -d ' ')
# $na is DISTINCT CITED PATHS after `sort -u`, not refcheck's citation count on
# the REFUSE line above -- the same path is cited by several files. Two numbers
# that differ by dedup, printed six lines apart, read as an error in one of them.
echo "$ni of $na distinct cited path(s) are caused by YOUR UNCOMMITTED CHECKER, not by the data:"
echo "classified against your working tree (this is what a clean clone cannot see):"
# Pull the backticked path out of each UNRESOLVED line. Trailing `/` kept: it is
# how refcheck cites a directory and `-e` is happy either way.
# Strip the trailing slash BEFORE `sort -u`, not after: refcheck cites the same
# directory both ways and with the strip afterwards `spikes/S85_verify_vs_reexec`
# printed three times. A duplicate in an action list reads as three separate
# things to fix.
while read -r p; do
  if grep -qxF "$p" "$SC/.instr"; then printf '  %s\n' "$(classify "$p" 1)"
  else                                 printf '  %s\n' "$(classify "$p" 0)"; fi
done < "$SC/.armA"
echo
echo "CHECKER-UNCOMMITTED is the FIX that is uncommitted, not the cited path:"
echo "'git commit --only' the CHECKER. Do NOT create the path -- it resolves"
echo "under your own tree already, and writing it is the stub the rails forbid."
echo "UNCOMMITTED is yours and only you can fix it -- the path is in no one else's"
echo "tree. 'git commit --only <path>' (never 'git add' then 'git commit': the"
echo "index is shared, H19). ABSENT means the citation is genuinely dangling under"
echo "BOTH checkers: file the missing thing as OPEN, never a stub to go green."
exit 1
