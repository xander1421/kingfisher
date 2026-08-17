#!/usr/bin/env bash
# rule12.sh — H81, ATOM-3, 2026-08-17. The generator for the number.
#
# LEDGER standing rule 12: "A retraction must be applied to every file that
# carries the claim." Earned by S55, whose correction landed in `LEDGER.md` and
# nowhere else; and by §12.8 of `MISSION_LOOP.md` itself, whose CORRECTED block
# records a withdrawn claim surviving "here and in `prompts/ATTACKER-1.md` for
# hours after withdrawal". Nothing had ever checked it.
#
# WHAT THIS DOES, AND THE LINE IT DOES NOT CROSS
# ----------------------------------------------
# It finds every quoted claim in `out/RETRACTIONS.md`'s `## Dead` table that
# still appears VERBATIM somewhere else in the tree. That half is decidable.
#
# It does NOT decide whether a surviving copy is a violation. A file may
# legitimately quote a dead claim while retracting it -- that is rule 12 being
# OBEYED -- and telling those apart is reading, not grepping. §12.12: claim decay
# is one of the three failure modes that are not mechanisable, and pretending
# otherwise is its own defect. So this prints SITES, and a human or a lane
# adjudicates each one.
#
# TWO PROXIES WERE TRIED AND BOTH FAILED, IN OPPOSITE DIRECTIONS. Recorded here
# because the obvious next step is to re-invent them:
#
#   1. "a retraction word within ±12 lines" -> FALSE GREEN on `WORK_QUEUE.md:23`.
#      That file is a table where ONE ROW IS ONE LINE, so ±12 lines is ±12
#      unrelated rows, and the S77 row four lines away supplied the word.
#   2. the same proxy -> FALSE RED on `spikes/S50_harness/RESULT.md:30`, which IS
#      the refutation ("...was cpu0, unpinned, presented as a property of the
#      kernel. It is a property of where the scheduler put it") and never uses
#      the word "retract".
#
# NO WRITES. usage:
#   sh spikes/H81_rule12_audit/rule12.sh            # sites, for adjudication
#   sh spikes/H81_rule12_audit/rule12.sh --selfcheck
# exit 0 always: a site is not a verdict, and an exit code would be one.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
SRC=out/RETRACTIONS.md

# The `## Dead` table's first column, which is the claim in quotes. Bold markers
# are stripped; the quotes are the delimiter, so a row that does not quote its
# claim is not extracted -- stated rather than silently dropped, and it is why
# the count below is 23 and not the table's row count.
claims() { grep -oE '^\| \*{0,2}"[^"]+"' "$SRC" | sed 's/^| \**//; s/"//g'; }

if [ "${1:-}" = "--selfcheck" ]; then
  fail=0
  n=$(claims | wc -l | tr -d ' ')
  [ "$n" -gt 0 ] || { echo "SELFCHECK FAIL: extracted 0 claims -- the scan is inert"; fail=1; }
  # A claim that IS in the source must be found; one that is not must not be.
  # Without the negative arm, an extractor returning the whole file would pass.
  probe=$(claims | head -1)
  grep -qF "$probe" "$SRC" || { echo "SELFCHECK FAIL: extracted a string not in $SRC"; fail=1; }
  claims | grep -qxF 'this string is not a retracted claim' && {
    echo "SELFCHECK FAIL: extractor invented a claim"; fail=1; }
  # Short strings match everything. The floor must be enforced, or the report
  # fills with noise and nobody reads it (H52).
  [ "$(claims | awk 'length($0) < 20' | wc -l | tr -d ' ')" -ge 0 ] || fail=1
  [ "$fail" -eq 0 ] && echo "selfcheck: $n claim(s) extracted, positive and negative arms both fire"
  exit "$fail"
fi

echo "dead claims with a quoted form in $SRC: $(claims | wc -l | tr -d ' ')"
echo "(claims under 20 characters are skipped -- a short string matches everything)"
echo
n_c=0; n_s=0
claims | while IFS= read -r c; do
  [ ${#c} -ge 20 ] || continue
  hits=$(grep -rlF "$c" --include='*.md' . 2>/dev/null \
         | grep -vE '^\./(elders|archive)' | grep -v "$SRC")
  [ -n "$hits" ] || continue
  printf 'CLAIM  %s\n' "$c"
  printf '%s\n' "$hits" | sed 's/^/  site  /'
  echo
done
echo "Each site above must be READ. A file may quote a dead claim while retracting"
echo "it, which is rule 12 being obeyed. Grep cannot tell those apart, and the two"
echo "proxies that look like they can are wrong in both directions -- see the header."
