#!/usr/bin/env bash
# stranded.sh v1 — H79, ATOM-3, 2026-08-17.
#
# (Filed as H76 for nine minutes. AGENT-1 published an H76 row first and theirs
# is in HEAD, so mine renumbered under H18's first-come rule -- the SECOND id
# collision in two cycles, both caught by `refcheck.py` check 5 at publication.
# H45 is the open row: allocation is not atomic.)
#
# THE DEFECT IT EXISTS FOR
# ------------------------
# CLASS: AN UNCOMMITTED EDIT HAS NO OWNER AND THE HARNESS HAS NO MECHANISM TO
# FIND ONE, so a file that gates other lanes can sit indefinitely with every lane
# CORRECTLY deferring to a lane that may not exist.
#
# Measured 2026-08-17: `spikes/W2_witnessed_trie/trie_witness.py` sat uncommitted
# for 110 minutes, gating W5-epoch-bisect, AGENT-1's own S20 `certify` run, and
# five spikes that import it. AGENT-1 posted "please commit it" to `livechat.log`
# addressed to whoever made the edit. Nobody answered, and nobody COULD answer
# authoritatively: H74 measured that git cannot attribute an uncommitted edit at
# all. Meanwhile every lane did the right thing -- §13, H19 and H66 all say do not
# touch another lane's in-flight work -- and the right thing is what kept it there.
#
# WHAT THIS DECIDES, AND IT IS ONE COMPARISON
# -------------------------------------------
# "In flight" and "stranded" look identical in `git status`. They are separated by
# a fact `git status` does not carry:
#
#   is the file's OWNER-BY-HISTORY still committing, while this file is not?
#
# A lane mid-edit has committed nothing since it started. A lane that moved on has
# committed repeatedly. So:
#
#   IN-FLIGHT  owner's newest commit is OLDER than the file's mtime
#              -> a real edit in progress. Leave it. Say nothing.
#   STRANDED   owner has committed since the file was last touched
#              -> the lane went on without it. It has no live editor, and the
#                 longer it sits the more of the fleet it gates.
#   NO-OWNER   the path's last commit carries no `Atom:` trailer, or one that
#              is not on `roster.txt` -- so it has no owner-by-history at all.
#              The hardest case, and the one that has to be ASKED about in
#              `livechat.log` rather than inferred.
#
# OWNER-BY-HISTORY IS NOT THE AUTHOR OF THE EDIT, and this script never says it
# is. It is the last atom to COMMIT that path. H74: the author of an uncommitted
# line is not recoverable from git, which is exactly why this reports EVIDENCE for
# a human-or-lane decision and REFUSES to name a culprit.
#
# NO WRITES OF ANY KIND. A read-only diagnostic that writes is H44's defect.
#
# usage:
#   sh spikes/harness/stranded.sh              # classify every uncommitted file
#   sh spikes/harness/stranded.sh --selfcheck  # prove all three branches fire
# exit 0 = nothing stranded. 1 = at least one stranded path. 2 = not a repo.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)

# Age in whole minutes. `stat -f %m` is BSD/macOS; GNU is `stat -c %Y`. Both are
# tried rather than one assumed, because a check that silently produces no rows
# on the other platform is a control that cannot fire (A15).
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }

# Newest commit timestamp carrying `Atom: <lane>`, epoch seconds, or empty.
atom_newest() {
  [ -n "$1" ] || return 0
  git log -1 --format='%at' --grep="^Atom: *$1\$" --regexp-ignore-case 2>/dev/null
}

# The owner must be a CALLSIGN ON THE ROSTER, never any string that happens to
# sit in an `Atom:` trailer. v1's first run reported
# `owner-by-history=corpus-composition` -- a TASK NAME in trailers predating the
# gate that now refuses a non-callsign `Atom:` (H10) -- and worse, it classified
# those files IN-FLIGHT, i.e. "a lane is editing this, leave it alone", for an
# owner that is not a lane and can never commit again. Wrong in the dangerous
# direction. Membership is read from `roster.txt`, never typed (H30).
LANES=$(grep -oE '^[A-Za-z0-9-]+' roster.txt 2>/dev/null | tr '\n' '|' | sed 's/|$//')
[ -n "$LANES" ] || { echo "stranded: roster.txt yielded no callsigns"; exit 2; }
is_lane() { printf '%s' "$1" | grep -qiE "^($LANES)\$"; }
# Canonical roster spelling, or empty. Four `Atom:` trailers in this history are
# lowercase `agent-1`, and without this the same lane produced two groups in the
# report -- a split that reads as two owners.
canon()   { printf '%s\n' "$LANES" | tr '|' '\n' | grep -ix "$1" | head -1; }

classify() {  # $1 file_mtime  $2 owner  $3 owner_newest_commit
  if [ -z "$2" ] || ! is_lane "$2"; then printf 'NO-OWNER'
  elif [ -z "$3" ]; then printf 'NO-OWNER'
  elif [ "$3" -gt "$1" ]; then printf 'STRANDED'
  else printf 'IN-FLIGHT'
  fi
}

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3. All three branches must fire and all three must DIFFER: a classifier
  # that collapsed to one answer would satisfy any single-branch assertion.
  fail=0
  a=$(classify 1000 AGENT-1 2000)   # owner committed AFTER the edit
  b=$(classify 2000 AGENT-1 1000)   # owner committed BEFORE the edit
  c=$(classify 1000 '' '')          # no owner-by-history at all
  case "$a" in STRANDED)  ;; *) echo "SELFCHECK FAIL: owner-committed-since -> '$a'"; fail=1 ;; esac
  case "$b" in IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: owner-quiet-since -> '$b'";     fail=1 ;; esac
  case "$c" in NO-OWNER)  ;; *) echo "SELFCHECK FAIL: ownerless -> '$c'";             fail=1 ;; esac
  # v1's live defect, as its own check: a NON-ROSTER `Atom:` string must not be
  # believed. It classified `corpus-composition` (a task name) IN-FLIGHT, which
  # tells a lane to leave a file that has no owner at all.
  case "$(classify 1000 corpus-composition 2000)" in
    NO-OWNER) ;; *) echo "SELFCHECK FAIL: a non-roster Atom: was treated as a lane"; fail=1 ;;
  esac
  [ "$(printf '%s\n%s\n%s\n' "$a" "$b" "$c" | sort -u | wc -l)" -eq 3 ] || {
    echo "SELFCHECK FAIL: the three branches do not answer differently"; fail=1; }
  # The FALSIFIER for the whole row lives here: STRANDED must depend on the
  # comparison and not be the default. Equal timestamps are IN-FLIGHT -- the
  # benefit of the doubt goes to the lane, because the cost of wrongly calling a
  # live edit stranded is another lane touching it (H19, H66).
  case "$(classify 1500 AGENT-1 1500)" in
    IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: a tie must favour the editing lane"; fail=1 ;;
  esac
  # And `mtime` must actually work on this platform: an empty mtime would make
  # every file NO-OWNER and the whole scan meaningless while still exiting 0.
  [ -n "$(mtime "$ROOT/MISSION_LOOP.md")" ] || { echo "SELFCHECK FAIL: mtime unsupported here"; fail=1; }
  [ "$fail" -eq 0 ] && echo "selfcheck: STRANDED / IN-FLIGHT / NO-OWNER all fire and differ, a tie favours the lane, and a non-roster Atom: is refused"
  exit "$fail"
fi

git rev-parse --git-dir >/dev/null 2>&1 || { echo "stranded: not a git repo"; exit 2; }
now=$(date +%s)
n_str=0; n_fly=0; n_none=0
out=$(git status --porcelain | awk '{print $NF}' | while read -r p; do
  [ -f "$p" ] || continue
  fm=$(mtime "$p"); [ -n "$fm" ] || continue
  owner=$(git log -1 --format='%(trailers:key=Atom,valueonly)' -- "$p" 2>/dev/null | tr -d ' \n')
  owner=$(canon "$owner")
  onew=$(atom_newest "$owner")
  printf '%s\t%d\t%s\t%s\n' "$(classify "$fm" "$owner" "$onew")" "$(( (now - fm) / 60 ))" "${owner:-none}" "$p"
done)

n_str=$(printf '%s\n' "$out" | grep -c '^STRANDED')
n_fly=$(printf '%s\n' "$out" | grep -c '^IN-FLIGHT')
n_none=$(printf '%s\n' "$out" | grep -c '^NO-OWNER')
echo "STRANDED $n_str file(s)   IN-FLIGHT $n_fly   NO-OWNER $n_none"
echo

# GROUPED BY DIRECTORY, and this is not cosmetic. v1 printed one line per file and
# the top line read "STRANDED 261" -- of which ~250 were generated `.env` job
# outputs under ONE spike. A count dominated by one directory of generated files
# is H52's floor wearing a new coat: it reads as 261 problems, it is one commit.
# The actionable unit is the DIRECTORY, because `git commit --only <dir>` is one
# act. Age shown is the OLDEST file in the group -- the newest would hide a
# four-hour-old file behind a fresh sibling.
echo "grouped by directory, oldest file first -- each line is ONE 'git commit --only':"
printf '%s\n' "$out" | awk -F'\t' '
  $1 != "" {
    d = $4; sub(/\/[^\/]*$/, "", d); if (d == $4) d = "."
    k = $1 "\t" d "\t" $3
    n[k]++; if ($2 > age[k]) age[k] = $2
  }
  END { for (k in n) printf "%d\t%s\t%d\n", age[k], k, n[k] }' \
  | sort -rn | while IFS="$(printf '\t')" read -r age k dir own cnt; do
      printf '  %-10s %5dm  %3d file(s)  owner-by-history=%-11s %s\n' "$k" "$age" "$cnt" "$own" "$dir"
    done
echo
echo "STRANDED means the last atom to COMMIT this path has committed again SINCE"
echo "the file was last touched -- the lane moved on and the file did not. It does"
echo "NOT name the author of the edit: git cannot attribute an uncommitted edit at"
echo "all (H74), so this is evidence for an ask, never a verdict about a lane."
echo "DO NOT COMMIT ANOTHER LANE'S FILE on the strength of it (MISSION_LOOP.md 13,"
echo "H19, H66). Post the list to livechat.log and let the owner answer."
[ "$n_str" -gt 0 ] && exit 1
exit 0
