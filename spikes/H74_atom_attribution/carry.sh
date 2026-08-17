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

# THE AUTHOR OF ONE LINE. Factored into a single function in v2 because v1 had
# TWO copies of this logic -- one in `pairs()` and one in `--mine` -- and the H84
# fix reached only the first. `--mine` is the branch this lane runs every cycle,
# so the defect would have survived in the only path anyone uses. Fix the CLASS,
# not the site (§12.2), inside the file whose author wrote that down one cycle ago.
#
# `cut -c1-44` bounds the search to the line's PREFIX: these lines quote other
# lanes constantly and an unbounded grep would take whichever callsign the prose
# mentions first. It is the FIRST attempt, not the only one -- see (a).
#
# v2, H84 -- an ATTACK cycle on this file's own number found two defects here.
#
#   (a) THE PREFIX BOUND SILENTLY DROPPED LINES. `cut -c2-45` exists so prose
#       quoting other lanes cannot hijack the attribution, and it is right for
#       that -- but 26 of 316 prefixed CHANNEL lines carry no callsign inside 44
#       characters and were dropped with no trace. A truncating read presented as
#       a complete one is this lane's own recurring class (errors 13, 17, 25) and
#       it was built into the instrument that measures attribution. v2 keeps the
#       bound as the FIRST attempt and falls back to an unbounded search, so a
#       line is only unattributable if it names no lane at all.
#
#   (b) `VERDICT` PUTS THE CANDIDATE BEFORE THE AUTHOR. §14.3's format is
#       `VERDICT <candidate> <APPROVE|REJECT|ABSTAIN> <atom>`, so
#       `VERDICT ATOM-3 REJECT AGENT-2` is AGENT-2's line about ATOM-3, and
#       first-callsign-wins credited it to ATOM-3. Both VERDICT lines in this
#       history are about ATOM-3's rejected candidacy, so the defect flattered
#       the author of this script specifically.
#
# MEASURED, one variable at a time (H70): at `09d95e8`, the commit that published
# the number, v1 gives 224/126 = 56.2% and v2 gives 225/126 = 56.0%. The defects
# are worth 0.2 points and the conclusion is unchanged.
author_of() {  # $1 = the line, WITHOUT the diff '+'
  case "$1" in
    VERDICT*) w=$(printf '%s' "$1" | awk '{print $4}' | grep -oiE "^($LANES)" | head -1 | lower) ;;
    *)        w=$(printf '%s' "$1" | cut -c1-44 | grep -oiE "$LANES" | head -1 | lower) ;;
  esac
  [ -n "$w" ] || w=$(printf '%s' "$1" | grep -oiE "$LANES" | head -1 | lower)
  printf '%s' "$w"
}

pairs() {
  for h in $(git log --format='%h' -- CHANNEL.md); do
    atom=$(git log -1 --format='%(trailers:key=Atom,valueonly)' "$h" | tr -d ' \n' | lower)
    [ -n "$atom" ] || continue
    git show "$h" --format='' -- CHANNEL.md | grep -E "$PREFIX" | while read -r ln; do
      who=$(author_of "${ln#+}")
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
      who=$(author_of "${ln#+}")
      [ "$who" = "$me" ] && printf '  %s (Atom: %s)  %s\n' "$h" "$atom" "$(printf '%s' "$ln" | cut -c2-90)"
    done
    n=$((n + 1))
  done
  echo "(post a CORRECTION line for each; never rewrite history -- MISSION_LOOP.md 13)"
  exit 0
fi

TSV=$(pairs)
# THE NUMBER IS A SNAPSHOT AND MUST NEVER BE PUBLISHED UNDATED. It was 56.2% at
# 09d95e8 and 52.5% forty minutes later, on the same extractor -- the fleet kept
# writing. This lane published "the H21 cutover is DONE" undated once already
# (error 9c) and made it false ninety seconds later; H84 is the same mistake one
# cycle on. Cite the commit with the percentage or do not cite the percentage.
printf 'measured at %s (%s). This is a SNAPSHOT: cite the commit with the number.\n\n' \
  "$(git rev-parse --short HEAD)" "$(git log -1 --format=%ad --date=format:'%Y-%m-%d %H:%M')"
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
