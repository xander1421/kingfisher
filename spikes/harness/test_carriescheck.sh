#!/bin/sh
# test_carriescheck.sh v1 — H180. Drives carriescheck.py in a throwaway git repo.
#
# The cases that matter are the ones that would make it USELESS rather than
# merely wrong, and each has a name here:
#   * check 4 -- WORK_QUEUE.md must be IGNORED. If it were scanned, ATOM-3's
#     H105 measurement says ~8% of the names would be WRONG, and a gate that
#     falsely accuses a peer is worse than no gate.
#   * check 5/6 -- the two identity classes must stay SILENT. CLIENT-3 IS ATOM-3
#     (MISSION_LOOP §14.1) and AGENT-2-INT was signing AGENT-2 before conceding
#     (CHANNEL.md:708). Naming either is a false accusation.
#   * check 7 -- own-lines-only must pass SILENTLY, or the tool is noise and
#     gets ignored, which is the always-red-gate failure H14/H52 recorded.

set -u
HERE=$(cd "$(dirname "$0")" && pwd)
TOOL="$HERE/carriescheck.py"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ok   $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL $1"; }

# §10 (H89): scratch lives INSIDE the workspace. A bare `mktemp -d` resolves to
# $TMPDIR, which on macOS is /var/folders/... — outside. `.scratch/` is gitignored.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$ROOT/.scratch"
TMP=$(mktemp -d "$ROOT/.scratch/carries.XXXXXX"); trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 1
git init -q .; git config user.email t@t; git config user.name t

stage() { git add "$1" >/dev/null 2>&1; }

echo "carriescheck v1 — sandbox"

# 1/2 — a foreign CHANNEL line is named, and the trailer is paste-ready
printf 'CLAIM H1 ATOM-3 something they wrote\n' > CHANNEL.md
stage CHANNEL.md
OUT=$(python3 "$TOOL" ATTACKER-1 2>&1)
echo "$OUT" | grep -q 'ATOM-3'          && ok "foreign CHANNEL line names its author" || bad "foreign CHANNEL line NOT named"
echo "$OUT" | grep -q 'Carries: ATOM-3' && ok "prints a paste-ready trailer"          || bad "no paste-ready trailer"
# ANTI-INERTNESS: the tool must echo the SANDBOX's own line text, not merely a
# callsign that also exists in the real repo. test_prosecite.sh v1 was inert for
# exactly this reason -- 7 of 9 checks passed against the real tree because the
# fixture's number happened to exist there too.
echo "$OUT" | grep -q 'something they wrote' && ok "reads the SANDBOX index, not the real repo" \
                                             || bad "sandbox not being read — checks may be inert"

# 3 — DECISIONS.log is positional too
printf '2026-08-19 ok-1 decided a thing\n' > DECISIONS.log
stage DECISIONS.log
python3 "$TOOL" ATTACKER-1 2>&1 | grep -q 'ok-1' && ok "DECISIONS.log author detected" || bad "DECISIONS.log author missed"

# 4 — WORK_QUEUE.md must be IGNORED (H105: 8% false accusation rate)
rm -f CHANNEL.md DECISIONS.log; git rm -q --cached CHANNEL.md DECISIONS.log >/dev/null 2>&1
printf '| H9 | row mentioning ATOM-3 and AGENT-1 as participants | OPEN |\n' > WORK_QUEUE.md
stage WORK_QUEUE.md
python3 "$TOOL" ATTACKER-1 2>&1 | grep -qE 'ATOM-3|AGENT-1' \
  && bad "WORK_QUEUE.md was scanned — H105 measured 8% of those names WRONG" \
  || ok "WORK_QUEUE.md ignored (participants are not authors)"

# 5 — CLIENT-3 is ATOM-3 (§14.1): carrying it under ATOM-3 must be SILENT
rm -f WORK_QUEUE.md; git rm -q --cached WORK_QUEUE.md >/dev/null 2>&1
printf 'DONE H2 CLIENT-3 a line under the retired name\n' > CHANNEL.md
stage CHANNEL.md
python3 "$TOOL" ATOM-3 2>&1 | grep -q 'CLIENT-3' \
  && bad "CLIENT-3 named as carried by ATOM-3 — same identity per §14.1" \
  || ok "CLIENT-3/ATOM-3 treated as one identity"

# 6 — AGENT-2-INT was signing AGENT-2 before conceding (CHANNEL.md:708)
printf 'NOTE AGENT-2 a line from before the concession\n' > CHANNEL.md
stage CHANNEL.md
python3 "$TOOL" AGENT-2-INT 2>&1 | grep -q 'Carries:' \
  && bad "accused across the AGENT-2 concession, which is not mechanically resolvable" \
  || ok "AGENT-2/AGENT-2-INT concession not accused across"

# 7 — own lines only must pass SILENTLY
printf 'DONE H3 ATTACKER-1 my own line\n' > CHANNEL.md
stage CHANNEL.md
OUT=$(python3 "$TOOL" ATTACKER-1 2>&1)
echo "$OUT" | grep -q 'Carries:' && bad "own-lines-only produced a trailer — the tool is noise" \
                                 || ok "own lines only: silent"

# 8 — prose mentioning a peer mid-line is NOT authorship
printf 'DONE H4 ATTACKER-1 and ATOM-3 should read this, AGENT-1 too\n' > CHANNEL.md
stage CHANNEL.md
python3 "$TOOL" ATTACKER-1 2>&1 | grep -q 'Carries:' \
  && bad "a peer NAMED in prose was read as its author" \
  || ok "mid-line mentions are not authorship (position only)"

# 9 — refuses rather than guessing when it has no atom
printf 'CLAIM H5 ATOM-3 x\n' > CHANNEL.md; stage CHANNEL.md
( CALLSIGN= python3 "$TOOL" >/dev/null 2>&1 ); RC=$?
[ "$RC" -eq 3 ] && ok "refuses (exit 3) with no atom rather than guessing" || bad "expected exit 3, got $RC"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
