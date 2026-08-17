#!/bin/sh
# H72 probe -- is `--no-verify` all-or-nothing?
#
# The claim under test: bypassing the TREE-WIDE document checkers (pre-commit)
# also drops the PER-COMMIT trailer gate (commit-msg), which is the check most
# likely to catch the committer's own defect. Asserted from the git docs would
# be an argument; this measures it.
#
# Runs in a THROWAWAY repo created and destroyed inside the workspace (rail
# §10), never against the shared tree, and installs this repo's real
# commit-msg.hook so the gate under test is the gate in production.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SB="$ROOT/spikes/H72_scoped_bypass/sandbox"
rm -rf "$SB"; mkdir -p "$SB"; cd "$SB"
git init -q .
git config user.email probe@local; git config user.name probe
cp "$ROOT/spikes/harness/commit-msg.hook" .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
echo x > f.txt; git add f.txt

# `if git commit ... | tail -3` tests TAIL's exit status, not git's, so the
# verdict line reported ACCEPTED while the gate was visibly refusing one line
# above it. Found by reading the output against its own verdict. rc is captured
# from the command under test, with no pipeline between them.
C1=0; git commit -q -m 'wip' > c1.out 2>&1 || C1=$?   # `set -e` would abort on the refusal we are measuring
echo "== C1: trailerless message, gate ENABLED -- must REFUSE =="
sed 's/^/    /' c1.out
if [ $C1 -eq 0 ]; then
  echo "C1 RESULT: ACCEPTED (rc=$C1)  <- control dead, the gate does not refuse"
else
  echo "C1 RESULT: REFUSED  (rc=$C1)  <- gate is live in the sandbox"
fi

C2=0; git commit -q --no-verify -m 'wip' > c2.out 2>&1 || C2=$?
echo "== C2: same trailerless message, --no-verify -- does the gate still apply? =="
sed 's/^/    /' c2.out
if [ $C2 -eq 0 ]; then
  echo "C2 RESULT: ACCEPTED (rc=$C2)  <- --no-verify DROPPED the trailer gate"
else
  echo "C2 RESULT: REFUSED  (rc=$C2)  <- --no-verify is scoped to pre-commit only"
fi

echo "== C3: what actually landed =="
git log --format='subject=%s%ntrailers=[%(trailers)]' -1 | head -5

cd "$ROOT"; rm -rf "$SB"
echo "sandbox removed: $([ -d "$SB" ] && echo NO || echo yes)"

# ---------------------------------------------------------------------------
# C4/C5 -- the scoping predicate in commit_scoped.sh, BOTH directions.
# Without C5, "never refuses anything" satisfies C4 (H68's lesson).
# DRY_RUN stops before the commit so neither direction can land anything.
# ---------------------------------------------------------------------------
cd "$ROOT"
M="$ROOT/spikes/H72_scoped_bypass/.tmsg"
printf 'H72 probe: scoping predicate under test\n\nAtom: ATTACKER-1\nClaude-Session: local-lane-40160\nReviewed-By: unreviewed\n' > "$M"

# The refusal text is CONSTRUCTED, not scavenged from whatever another lane
# happens to have left broken. It is the verbatim shape refcheck emits, and it
# names a file this commit does NOT carry (C4) and one it DOES (C5).
FAKE="$ROOT/spikes/H72_scoped_bypass/.fake_refusal"
cat > "$FAKE" <<'FAKEEOF'
  UNRESOLVED spikes/harness/test_loop_gate.sh: `spikes/H61_lock_handoff/RESULT.md` does not exist
REFUSE: 1 citation(s) in the harness do not resolve.
FAKEEOF
echo "== scoping predicate, against a CONSTRUCTED refusal naming test_loop_gate.sh =="

DRY_RUN=1 CHECKERS_OUT_FILE="$FAKE" sh spikes/harness/commit_scoped.sh "$M" \
  spikes/H72_scoped_bypass/probe.sh > c4.out 2>&1 && C4=0 || C4=$?
if [ "$C4" -eq 0 ]; then
  echo "C4 RESULT: PROCEEDS (rc=0)  <- a path NOT named by the refusal is not blocked"
else
  echo "C4 RESULT: BLOCKED  (rc=$C4) <- false positive: it blocked an unrelated path"
  tail -4 c4.out | sed 's/^/    /'
fi

DRY_RUN=1 CHECKERS_OUT_FILE="$FAKE" sh spikes/harness/commit_scoped.sh "$M" \
  spikes/harness/test_loop_gate.sh > c5.out 2>&1 && C5=0 || C5=$?
if [ "$C5" -eq 0 ]; then
  echo "C5 RESULT: PROCEEDS (rc=0)  <- CONTROL DEAD: it does not refuse even when the"
  echo "  refusal names a path the commit carries, so C4 proves nothing"
else
  echo "C5 RESULT: REFUSED  (rc=$C5) <- refuses when the refusal names YOUR path"
fi

echo "== C6: the seam must be INERT without DRY_RUN =="
# The path here is DELIBERATELY NONEXISTENT. C6 runs without DRY_RUN, so it
# reaches the real `git commit` step; the first draft passed
# `spikes/harness/test_loop_gate.sh` -- ANOTHER LANE'S FILE -- and was saved only
# by that file happening to be clean at the time. A probe must not be one dirty
# working tree away from committing someone else's work. A nonexistent path
# still reaches the injection point, which is all C6 asserts on, and git can
# commit nothing with it.
CHECKERS_OUT_FILE="$FAKE" sh spikes/harness/commit_scoped.sh "$M" \
  spikes/H72_scoped_bypass/.nonexistent-by-design > c6.out 2>&1 && C6=0 || C6=$?
if grep -q 'checker output injected' c6.out; then
  echo "C6 RESULT: SEAM ACTIVE (rc=$C6) <- the injection reached a real commit path"
else
  echo "C6 RESULT: SEAM INERT  (rc=$C6) <- injection ignored without DRY_RUN, as designed"
fi

rm -f c4.out c5.out c6.out "$FAKE" "$M"
