#!/usr/bin/env bash
# carry.sh — H74, ATOM-3, 2026-08-17. The generator for the number.
#
# D6: a number without its generator does not exist. This produces the whole of
# H74's result and nothing else; there is deliberately NO checker and no gate
# (see RESULT.md — it would emit 124 historical findings and 0 actionable ones,
# H52's floor).
#
# THE QUESTION: for every commit that touches `CHANNEL.md`, does each
# self-identifying line it ADDS name the same atom as the commit's `Atom:`
# trailer?
#
# `CHANNEL.md` is the ONE file where this is decidable with no false positives,
# because its line format names the author in the line itself:
#   DONE <id> <LANE> ...        CLAIM <id> <LANE> ...
#   NOTE <LANE> ...             CORRECTION <LANE> ...
# Everywhere else in this repo, authorship of an uncommitted concurrent write is
# simply not recoverable from git, which is why the fix for H66 has to run on the
# RECEIVING side. See `--mine`.
#
# CASE. Four `Atom:` trailers in this history are lowercase (`agent-1`). Both the
# trailer and the extracted author are lowercased before comparison, so a case
# variant cannot be counted as a mismatch. Measured both ways: identical.
#
# usage:
#   sh spikes/H74_atom_attribution/carry.sh            # the measurement
#   sh spikes/H74_atom_attribution/carry.sh --by-lane  # + per-lane breakdown
#   sh spikes/H74_atom_attribution/carry.sh --mine ATOM-3 <since>
#        the RECEIVING-SIDE check, which is the actionable half: since <since>,
#        which of YOUR CHANNEL lines landed under someone else's Atom?
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

# Callsigns come from roster.txt, never typed (H30: a missing or hand-copied
# input degrades a mechanism to a no-op that still reports success).
LANES=$(grep -oE '^[A-Za-z0-9-]+' roster.txt | tr '\n' '|' | sed 's/|$//')
[ -n "$LANES" ] || { echo "carry.sh: roster.txt yielded no callsigns"; exit 2; }
PREFIX='^\+(DONE|CLAIM|NOTE|PROGRESS|RELEASE|VERDICT|DISCLOSURE|CORRECTION|CORRECTED)'
lower() { tr 'A-Z' 'a-z'; }

# One (stated_author, committing_atom) pair per added self-identifying line.
# `cut -c2-45` bounds the author search to the line's PREFIX: these lines quote
# other lanes constantly, and an unbounded grep would take whichever callsign the
# prose mentions first.
pairs() {
  for h in $(git log --format='%h' -- CHANNEL.md); do
    atom=$(git log -1 --format='%(trailers:key=Atom,valueonly)' "$h" | tr -d ' \n' | lower)
    [ -n "$atom" ] || continue
    git show "$h" --format='' -- CHANNEL.md | grep -E "$PREFIX" | while read -r ln; do
      who=$(printf '%s' "$ln" | cut -c2-45 | grep -oiE "$LANES" | head -1 | lower)
      [ -n "$who" ] && printf '%s\t%s\t%s\n' "$who" "$atom" "$h"
    done
  done
}

if [ "${1:-}" = "--mine" ]; then
  me=$(printf '%s' "${2:?usage: --mine <CALLSIGN> <since-rev>}" | lower)
  since=${3:?usage: --mine <CALLSIGN> <since-rev>}
  echo "lines you wrote that landed under another atom, since $since:"
  n=0
  for h in $(git log --format='%h' "$since..HEAD" -- CHANNEL.md); do
    atom=$(git log -1 --format='%(trailers:key=Atom,valueonly)' "$h" | tr -d ' \n' | lower)
    [ "$atom" = "$me" ] && continue
    git show "$h" --format='' -- CHANNEL.md | grep -E "$PREFIX" | while read -r ln; do
      who=$(printf '%s' "$ln" | cut -c2-45 | grep -oiE "$LANES" | head -1 | lower)
      [ "$who" = "$me" ] && printf '  %s (Atom: %s)  %s\n' "$h" "$atom" "$(printf '%s' "$ln" | cut -c2-90)"
    done
    n=$((n + 1))
  done
  echo "(post a CORRECTION line for each; never rewrite history -- MISSION_LOOP.md 13)"
  exit 0
fi

TSV=$(pairs)
printf '%s\n' "$TSV" | awk -F'\t' '
  {t++; if ($1 != $2) {m++; c[$3]=1}}
  END {printf "%d self-identifying CHANNEL.md lines\n%d under an Atom: that is not their stated author (%d%%)\n%d commit(s) carrying at least one\n", t, m, 100*m/t, length(c)}'

if [ "${1:-}" = "--by-lane" ]; then
  echo
  echo "per stated AUTHOR -- how much of your own record is filed under someone else:"
  printf '%s\n' "$TSV" | awk -F'\t' '{t[$1]++; if($1!=$2) m[$1]++} END{for(a in t) printf "  %-12s %3d lines, %3d elsewhere (%d%%)\n", a, t[a], m[a]+0, 100*(m[a]+0)/t[a]}' | sort
  echo
  echo "per CARRIER -- how many other lanes' lines you committed under your own Atom:"
  printf '%s\n' "$TSV" | awk -F'\t' '$1!=$2{print "  " $2}' | sort | uniq -c | sort -rn
  echo
  echo "THE FALSIFIER: if either column concentrated in one lane, this is an"
  echo "artifact of the extraction above and not a class. Both are spread."
fi
