#!/usr/bin/env bash
# headcheck.sh v1 — H60, ATOM-3, 2026-08-17.
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
#   UNCOMMITTED  the path exists in your tree -> `git commit --only <path>`.
#                Yours to fix, and only you can: it is not in anyone else's tree.
#   ABSENT       the path is nowhere -> the citation is genuinely dangling.
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
classify() {
  if [ -e "$ROOT/$1" ]; then
    if git -C "$ROOT" ls-files --error-unmatch "$1" >/dev/null 2>&1; then
      printf 'TRACKED-BUT-STALE %s\n' "$1"    # in the index at a different path/case
    else
      printf 'UNCOMMITTED %s\n' "$1"
    fi
  else
    printf 'ABSENT %s\n' "$1"
  fi
}

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3: the check ships a check, and BOTH branches must fire. A classifier
  # that only ever answers one way is the shape that let refcheck's tree-reading
  # verdict pass as a commit verdict for hours.
  sc="$ROOT/spikes/harness/.selfcheck-head.$$"
  mkdir -p "$sc" || { echo "SELFCHECK FAIL: no scratch"; exit 1; }
  fail=0
  : > "$sc/exists_untracked"
  a=$(ROOT="$sc" classify exists_untracked)
  b=$(ROOT="$sc" classify nothing_here)
  case "$a" in UNCOMMITTED*) ;; *) echo "SELFCHECK FAIL: on-disk-untracked classified '$a'"; fail=1 ;; esac
  case "$b" in ABSENT*)      ;; *) echo "SELFCHECK FAIL: absent path classified '$b'";      fail=1 ;; esac
  # And the two must DIFFER: identical answers would pass both cases above if
  # the classifier ever collapsed to one string.
  [ "${a%% *}" != "${b%% *}" ] || { echo "SELFCHECK FAIL: both branches answer the same"; fail=1; }
  rm -rf "$sc"
  [ "$fail" -eq 0 ] && echo "selfcheck: UNCOMMITTED and ABSENT are distinguished, and both branches fire"
  exit "$fail"
fi

SC="$ROOT/spikes/harness/.headcheck.$$"
cleanup() { rm -rf "$SC"; }
trap cleanup EXIT
mkdir -p "$SC" || { echo "headcheck: cannot create scratch"; exit 2; }
git archive HEAD 2>/dev/null | tar -x -C "$SC" 2>/dev/null || {
  echo "headcheck: could not materialise HEAD (no commits?)"; exit 2; }

out=$(cd "$SC" && python3 spikes/harness/refcheck.py 2>&1)
if (cd "$SC" && python3 spikes/harness/refcheck.py >/dev/null 2>&1); then
  echo "headcheck: refcheck resolves against HEAD -- a clean clone is green"
  exit 0
fi

echo "$out" | grep -E 'UNRESOLVED|REFUSE'
echo
echo "classified against your working tree (this is what a clean clone cannot see):"
# Pull the backticked path out of each UNRESOLVED line. Trailing `/` kept: it is
# how refcheck cites a directory and `-e` is happy either way.
# Strip the trailing slash BEFORE `sort -u`, not after: refcheck cites the same
# directory both ways and with the strip afterwards `spikes/S85_verify_vs_reexec`
# printed three times. A duplicate in an action list reads as three separate
# things to fix.
echo "$out" | sed -n 's/.*UNRESOLVED [^`]*`\([^`]*\)`.*/\1/p' | sed 's|/$||' | sort -u | while read -r p; do
  printf '  %s\n' "$(classify "$p")"
done
echo
echo "UNCOMMITTED is yours and only you can fix it -- the path is in no one else's"
echo "tree. 'git commit --only <path>' (never 'git add' then 'git commit': the"
echo "index is shared, H19). ABSENT means the citation is genuinely dangling: file"
echo "the missing thing as OPEN, never a stub written to make a gate green."
exit 1
