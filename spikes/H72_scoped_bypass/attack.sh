#!/bin/sh
# H72 ATTACK — three defects in commit_scoped.sh v1, my own draft, before it
# shipped. Every construct is run through BOTH the frozen v1 predicate and the
# real v2 script, because a kill needs the wrong verdict AND the right one:
# "v2 is correct here" is not evidence unless v1 was wrong here.
#
# FALSIFIER STATED BEFORE RUNNING: if the frozen v1 predicate returns the SAME
# verdict as v2 on all of C7/C8/C9, there was no defect, v2 is churn, and I
# withdraw the whole v2 rationale block.
#
# Nothing is committed: every v2 invocation passes DRY_RUN=1, which exits before
# `git commit`. Nothing is written outside the workspace (§10).
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D="$ROOT/spikes/H72_scoped_bypass"
cd "$ROOT"
FAIL=0

# ---------------------------------------------------------------------------
# The FROZEN v1 predicate, verbatim from the draft's lines 70-77. Frozen rather
# than referenced because v1 is being replaced in this same cycle; it is dead
# code kept only as the thing the kill lands on. v1 was never committed, so
# there is no blob to diff it against and I say so rather than implying one.
# ---------------------------------------------------------------------------
v1_verdict() {  # $1 = output file, $2.. = commit paths ; echoes BLOCKED|PROCEEDS
  _out=$(cat "$1"); shift
  _mine=0
  for p in "$@"; do
    if echo "$_out" | grep -qE "(REFUSE|UNRESOLVED|DUPLICATE|CONTRADICT).*$(basename "$p")"; then
      _mine=1
    fi
  done
  [ "$_mine" -eq 0 ] && echo PROCEEDS || echo BLOCKED
}

v2_verdict() {  # $1 = output file, $2 = rc, $3.. = commit paths
  _f=$1; _rc=$2; shift 2
  _o=$(DRY_RUN=1 CHECKERS_OUT_FILE="$_f" CHECKERS_RC="$_rc" \
       sh spikes/harness/commit_scoped.sh "$D/.tmsg" "$@" 2>&1) && _r=0 || _r=$?
  # A DRY_RUN that never reached the seam is a SETUP failure, not a verdict —
  # githygiene or commit-msg refused first and the predicate was never asked.
  if ! echo "$_o" | grep -q 'DRY_RUN: checker output injected'; then
    echo "SETUP-FAILED"; echo "$_o" | tail -4 | sed 's/^/      /' >&2; return
  fi
  [ "$_r" -eq 0 ] && echo PROCEEDS || echo BLOCKED
}

expect() {  # $1 = label, $2 = expected, $3 = got
  if [ "$2" = "$3" ]; then echo "  ok    $1: $3"
  else echo "  FAIL  $1: expected $2, got $3"; FAIL=$((FAIL+1)); fi
}

printf 'H72 attack: scoping predicate\n\nAtom: ATTACKER-1\nClaude-Session: local-lane-40160\nReviewed-By: unreviewed\n' > "$D/.tmsg"

# ---------------------------------------------------------------------------
# C7 — DEFECT 2. basename collision. The refusal names ANOTHER spike's
# RESULT.md; this commit carries its OWN RESULT.md, which is what every DONE
# cycle in this repo commits. 142 tracked files are named RESULT.md.
# ---------------------------------------------------------------------------
cat > "$D/.c7" <<'EOF'
  UNRESOLVED spikes/harness/test_loop_gate.sh: `spikes/H61_lock_handoff/RESULT.md` does not exist

REFUSE: 1 citation(s) in the harness do not resolve. A contract citing a missing artifact reads as satisfied,
        which is why this refuses rather than warns.
EOF
echo "== C7  another lane's RESULT.md refused; I carry MY RESULT.md =="
echo "       (v1 must be BLOCKED — the false positive; v2 must PROCEED)"
expect "C7 v1" BLOCKED  "$(v1_verdict "$D/.c7" spikes/H72_scoped_bypass/RESULT.md)"
expect "C7 v2" PROCEEDS "$(v2_verdict "$D/.c7" 1 spikes/H72_scoped_bypass/RESULT.md)"

# ---------------------------------------------------------------------------
# C8 — DEFECT 1. journalcheck's REAL refusal vocabulary, transcribed from
# journalcheck.py:309 and :316, not recalled. Per-item keyword is COLLISION,
# which v1's regex never looked for; the summary line names no path at all.
# The commit carries the very journal the refusal names.
# ---------------------------------------------------------------------------
cat > "$D/.c8" <<'EOF'
  COLLISION  HANDOFF.ATTACKER-1.md: NEXT is headed by H72, which is recorded DONE

REFUSE: 1 identifier(s) appear in both a DONE and a NEXT list (§12.5).
EOF
echo "== C8  journalcheck refuses MY OWN journal, in its real vocabulary =="
echo "       (v1 must PROCEED — the miss; v2 must be BLOCKED)"
expect "C8 v1" PROCEEDS "$(v1_verdict "$D/.c8" HANDOFF.ATTACKER-1.md)"
expect "C8 v2" BLOCKED  "$(v2_verdict "$D/.c8" 1 HANDOFF.ATTACKER-1.md)"

# ---------------------------------------------------------------------------
# C9 — DEFECT 3. A checker that CRASHED. This is githygiene.py's real failure of
# 2026-08-17 (H14), which sat in every lane's §13 path for 20+ minutes. rc!=0,
# no refusal keyword, so a text-matching predicate reads it as clean.
# ---------------------------------------------------------------------------
cat > "$D/.c9" <<'EOF'
Traceback (most recent call last):
  File "spikes/harness/refcheck.py", line 115, in <module>
    sys.exit(main())
NameError: name 're' is not defined
EOF
echo "== C9  a tree-wide checker CRASHED =="
echo "       (v1 must PROCEED — reads a crash as clean; v2 must be BLOCKED)"
expect "C9 v1" PROCEEDS "$(v1_verdict "$D/.c9" spikes/H72_scoped_bypass/attack.sh)"
expect "C9 v2" BLOCKED  "$(v2_verdict "$D/.c9" 1 spikes/H72_scoped_bypass/attack.sh)"

# ---------------------------------------------------------------------------
# C10/C11 — the OTHER direction, without which "refuse everything" passes
# C8 and C9 (H68's lesson: a fix that only ever refuses is not a fix).
# ---------------------------------------------------------------------------
echo "== C10 refusal names ONLY another lane's full path, and I carry neither =="
expect "C10 v2" PROCEEDS "$(v2_verdict "$D/.c7" 1 spikes/H72_scoped_bypass/attack.sh)"

cat > "$D/.c11" <<'EOF'
refcheck: every §N, guardrail and path citation in 50 harness files resolves
journalcheck: no identifier appears in both a DONE and a NEXT list across 5 journal(s)
EOF
echo "== C11 checkers PASS (rc=0) — must never refuse =="
expect "C11 v2" PROCEEDS "$(v2_verdict "$D/.c11" 0 HANDOFF.ATTACKER-1.md)"

rm -f "$D/.c7" "$D/.c8" "$D/.c9" "$D/.c11" "$D/.tmsg"
echo
if [ "$FAIL" -eq 0 ]; then
  echo "attack.sh: 8 assertions, 0 FAILED — v1 wrong on C7/C8/C9, v2 right on all five"
else
  echo "attack.sh: $FAIL FAILED"
fi
exit "$FAIL"
