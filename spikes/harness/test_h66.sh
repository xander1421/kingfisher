#!/bin/sh
# test_h66.sh — the runnable check §12.3 requires for `commit-msg.hook` v7.
#
# Every case below is a way v6 was wrong or a way v7 could be. Driven against
# THROWAWAY repos created and destroyed inside the workspace (§10), running the
# real hook source, never the live tree.
#
#   sh spikes/harness/test_h66.sh
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HOOK="$ROOT/spikes/harness/commit-msg.hook"
fails=0

ck() { # name, condition-already-evaluated ($2 = 0 for pass), detail
  if [ "$2" -eq 0 ]; then echo "PASS  $1"; else echo "FAIL  $1  $3"; fails=$((fails+1)); fi
}

mk() { # -> a fresh repo on stdout, with the hook installed
  d=$(mktemp -d "$ROOT/.h66test.XXXXXX")
  git -C "$d" init -q
  git -C "$d" config user.email t@t
  git -C "$d" config user.name t
  cp "$HOOK" "$d/.git/hooks/commit-msg"
  chmod +x "$d/.git/hooks/commit-msg"
  echo "$d"
}

msg() { # atom, extra-lines -> a legal message file path
  printf 'S1: a finding was recorded here\n\n%s\nAtom: %s\nClaude-Session: unassigned\nReviewed-By: unreviewed\n' \
    "$2" "$1" > "$D/.msg"
  echo "$D/.msg"
}

# ---------------------------------------------------------------- POSITIVE
# A gate that refuses everything passes every negative case below. This is the
# shape githygiene.py was in at permanent exit 1 (H14), so it comes first.
D=$(mk)
echo "a finding" > "$D/RESULT.md"
git -C "$D" add RESULT.md
rc=0; git -C "$D" commit -q -F "$(msg AGENT-1)" >/dev/null 2>&1 || rc=$?
ck "an ordinary commit with legal trailers is ACCEPTED" "$rc" "rc=$rc"
rm -rf "$D"

# ------------------------------------------------- SITE 2: HANDOFF.md, v6's hole
# v6: `HANDOFF.md` does not match `HANDOFF.*.md`, so it fell through
# `*) continue` and NO owner was inferred -- the one journal the gate could not
# protect was the one whose filename carries no callsign.
D=$(mk)
echo "seed" > "$D/RESULT.md"; git -C "$D" add RESULT.md
git -C "$D" commit -q -F "$(msg AGENT-1)" >/dev/null 2>&1
echo "agent-1 journal" > "$D/HANDOFF.md"
git -C "$D" add HANDOFF.md
rc=0; out=$(git -C "$D" commit -F "$(msg ATOM-3)" 2>&1) || rc=$?
case "$rc$out" in
  0*) ck "SITE 2 — ATOM-3 committing HANDOFF.md is REFUSED" 1 "accepted (this is v6's defect)" ;;
  *) echo "$out" | grep -q "another lane's files" \
       && ck "SITE 2 — ATOM-3 committing HANDOFF.md is REFUSED" 0 \
       || ck "SITE 2 — ATOM-3 committing HANDOFF.md is REFUSED" 1 "refused for another reason" ;;
esac

# ... and its OWNER must still be able to commit it, or the fix is a brick.
git -C "$D" reset -q
echo "agent-1 journal" > "$D/HANDOFF.md"; git -C "$D" add HANDOFF.md
rc=0; git -C "$D" commit -q -F "$(msg AGENT-1)" >/dev/null 2>&1 || rc=$?
ck "SITE 2 — AGENT-1 committing its OWN HANDOFF.md is ACCEPTED" "$rc" "rc=$rc"

# ... and `Carries:` is still the honest cross-lane escape.
echo "repaired by a peer" >> "$D/HANDOFF.md"; git -C "$D" add HANDOFF.md
rc=0; git -C "$D" commit -q -F "$(msg ATOM-3 'Carries: AGENT-1')" >/dev/null 2>&1 || rc=$?
ck "SITE 2 — 'Carries: AGENT-1' still lets a peer commit it" "$rc" "rc=$rc"
rm -rf "$D"

# ------------------------------------------- SITE 1: the shared-source REPORT
# A path another atom committed recently must be REPORTED and must NOT change
# the verdict. Both halves matter: reporting nothing is useless, and refusing
# would make every shared-file commit red, which is bypassed as thoroughly as a
# flaky gate (H14, H52).
D=$(mk)
echo "row" > "$D/WORK_QUEUE.md"; git -C "$D" add WORK_QUEUE.md
git -C "$D" commit -q -F "$(msg ATOM-3)" >/dev/null 2>&1
echo "my row" >> "$D/WORK_QUEUE.md"; git -C "$D" add WORK_QUEUE.md
rc=0; out=$(git -C "$D" commit -F "$(msg AGENT-1)" 2>&1) || rc=$?
ck "SITE 1 — a shared path is REPORTED" \
   "$(echo "$out" | grep -q 'shared-source paths' && echo 0 || echo 1)" \
   "no NOTE emitted"
ck "SITE 1 — ... and the commit is still ACCEPTED (report, never refuse)" "$rc" "rc=$rc"
ck "SITE 1 — ... and the NOTE names the other atom" \
   "$(echo "$out" | grep -q 'ATOM-3' && echo 0 || echo 1)" "atom not named"

# THE NULL. A path only ever committed by ME must produce NO note, or the report
# fires on every commit and carries no information.
echo "mine" > "$D/mine.md"; git -C "$D" add mine.md
git -C "$D" commit -q -F "$(msg AGENT-1)" >/dev/null 2>&1
echo "mine again" >> "$D/mine.md"; git -C "$D" add mine.md
out=$(git -C "$D" commit -F "$(msg AGENT-1)" 2>&1) || true
ck "SITE 1 NULL — a path only this atom has touched produces NO note" \
   "$(echo "$out" | grep -q 'shared-source paths' && echo 1 || echo 0)" \
   "reported a path with no other atom"
rm -rf "$D"

echo
if [ "$fails" -ne 0 ]; then echo "test_h66: $fails FAILED"; exit 1; fi
echo "test_h66: all checks pass"
