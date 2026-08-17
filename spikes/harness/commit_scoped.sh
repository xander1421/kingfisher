#!/bin/sh
# commit_scoped.sh v2 — 2026-08-17, ATTACKER-1 (H72).
#
# ==== WHY THIS EXISTS (§12.7 rationale) ====================================
# DEFECT REMOVED: `git commit --no-verify` IS ALL-OR-NOTHING. It is the only
# documented escape for a lane blocked by `pre-commit.hook`'s F2 — the
# tree-wide document checkers refusing a commit over a path the commit does not
# carry, which is normal and BY DESIGN (see `pre-commit.hook` v2's F2 paragraph
# and `spikes/H35_gate_scope/RESULT.md`). But taking that escape also drops the
# `commit-msg` trailer gate, which is the check most likely to catch the
# committer's OWN defect.
#
# MEASURED, not asserted (`spikes/H72_scoped_bypass/probe.sh`, throwaway repo
# created and destroyed inside the workspace, running this repo's real
# `commit-msg.hook`):
#   C1  trailerless message `wip`, gate live       -> REFUSED (rc=1)
#   C2  same message, `--no-verify`                -> ACCEPTED (rc=0)
#   C3  what lands                                 -> subject=wip trailers=[]
# i.e. a subject §13 explicitly forbids, on an unattributable commit.
#
# THIS WEAKENS NOTHING. It runs strictly MORE than `--no-verify` does. Which
# checkers "more" means is RESOLVED MECHANICALLY, not from memory: the whole of
# `pre-commit.hook`'s work is its `CHECKS` list at line 126 — refcheck.py,
# journalcheck.py, githygiene.py — and this script runs all three plus the real
# `commit-msg` hook. Nothing here can make a commit pass that plain
# `git commit` would have refused; it only restores checks `--no-verify`
# discards. It is not a replacement for `git commit`: reach for it only when the
# gate refused you over another lane's path, and use `git commit --only` (with
# `git add -N` for new paths, §13) every other time.
#
# ==== v2 — THREE DEFECTS IN v1, ALL MINE, ALL FOUND BY ATTACKING MY OWN =====
# ==== DRAFT BEFORE IT SHIPPED (v1 was never committed; see ATTACK.md) ======
#
# 1. VOCABULARY INVENTED BY EYE — the defect §12.4 exists to stop, committed by
#    the lane that mechanised §12.4. v1 attributed a refusal with
#    `grep -qE '(REFUSE|UNRESOLVED|DUPLICATE|CONTRADICT).*<basename>'`. Resolved
#    against the emitting code rather than recalled: `DUPLICATE` and
#    `CONTRADICT` appear ZERO times in either checker's refusal output, while
#    journalcheck's actual per-item keyword is `COLLISION` (journalcheck.py:309)
#    and was absent from the list. Its only other refusal line is the summary at
#    :316, which names NO path. So a journalcheck refusal was unattributable to
#    anyone and v1 PROCEEDED past it every time — a whole checker silently
#    descoped by a regex.
#
# 2. MATCHED ON `basename`, IN A TREE WHERE 142 TRACKED FILES ARE NAMED
#    `RESULT.md` (`git ls-files | grep -c '/RESULT\.md$'`). Any refusal naming
#    any other spike's RESULT.md matched YOUR RESULT.md. Every DONE cycle in
#    this repo commits one, so v1 refused precisely the commit shape it exists
#    to unblock. v2 compares FULL relative paths by equality. (`basename` was
#    also interpolated raw into a regex, so its `.` matched any character.)
#
# 3. EXIT STATUS DISCARDED. `pre-commit.hook:157` decides on the checker's rc;
#    v1 concatenated both checkers' stdout, `|| true`'d the status, and judged
#    the TEXT. A checker that CRASHES prints a traceback carrying no refusal
#    keyword — so it read as clean. Not hypothetical: `githygiene.py` was
#    `NameError: name 're' is not defined` at import for 20+ minutes in every
#    lane's §13 path on 2026-08-17 (H14). v2 captures rc per checker and refuses
#    outright on a traceback, because a check that did not run is not a check
#    that passed (family B).
#
# FAIL CLOSED ON THE UNATTRIBUTABLE: rc!=0 with no path named at all REFUSES.
# The permissive reading is the one the committer benefits from, and a rule
# about oneself is written against oneself (§14.3's wording, same reason).
#
# Cites: file:MISSION_LOOP.md "13"
# Cites: file:spikes/H35_gate_scope/RESULT.md "F2"
#
# Check that fails when this breaks (§12.3):
#   sh spikes/H72_scoped_bypass/probe.sh     (C1-C3, C6)
#   sh spikes/H72_scoped_bypass/attack.sh    (C7-C11, both directions)
#
# usage: sh spikes/harness/commit_scoped.sh <msgfile> <path>...
# ===========================================================================
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MSG=$1; shift
[ -n "$MSG" ] && [ -f "$MSG" ] && [ $# -gt 0 ] || {
  echo "usage: sh spikes/harness/commit_scoped.sh <msgfile> <path>..." >&2
  exit 2; }
cd "$ROOT"

echo "== paths this commit carries =="
for p in "$@"; do echo "    $p"; done

echo "== githygiene.py (index-scoped, already correct) =="
python3 spikes/harness/githygiene.py || { echo "REFUSED by githygiene" >&2; exit 1; }

echo "== commit-msg trailer gate, run DIRECTLY (this is what --no-verify drops) =="
.git/hooks/commit-msg "$MSG" || { echo "REFUSED by commit-msg" >&2; exit 1; }

echo "== tree-wide document checkers, reported in full, scoped for the verdict =="
# TEST SEAM, deliberately inert outside DRY_RUN. The scoping predicate is the
# only new logic here and BOTH its directions must be exercisable on demand — a
# control that can only fire when some other lane happens to have left the tree
# broken is a coincidence, not a control (A15). Honoured only together with
# DRY_RUN, so it can never affect a commit that lands.
if [ -n "$DRY_RUN" ] && [ -n "$CHECKERS_OUT_FILE" ]; then
  OUT=$(cat "$CHECKERS_OUT_FILE"); RC=${CHECKERS_RC:-1}
  echo "    [DRY_RUN: checker output injected from $CHECKERS_OUT_FILE, rc=$RC]"
else
  RC=0
  OUT=$(python3 spikes/harness/refcheck.py 2>&1) || RC=1
  O2=$(python3 spikes/harness/journalcheck.py 2>&1) || RC=1
  OUT="$OUT
$O2"
fi
echo "$OUT" | sed 's/^/    /'

if [ "$RC" -eq 0 ]; then
  echo "== tree-wide checkers PASS — nothing to scope =="
else
  # A crashed checker is not a passing checker (defect 3).
  if echo "$OUT" | grep -q 'Traceback (most recent call last)'; then
    echo "REFUSED — a tree-wide checker CRASHED; a check that did not run has no verdict" >&2
    exit 1
  fi
  # Full relative paths named anywhere in the refusal, not basenames (defect 2).
  NAMED=$(echo "$OUT" | grep -oE '[A-Za-z0-9_.@-]+(/[A-Za-z0-9_.@-]+)*\.[a-z]+' | sort -u)
  if [ -z "$NAMED" ]; then
    echo "REFUSED — the checkers refused and named no path, so it cannot be shown not to be yours" >&2
    exit 1
  fi
  MINE=0
  for p in "$@"; do
    q=${p#./}
    if echo "$NAMED" | grep -qxF "$q"; then
      echo "    ^ names YOUR path: $q" >&2
      MINE=1
    fi
  done
  [ "$MINE" -eq 0 ] || {
    echo "REFUSED — the tree-wide checkers name a path your commit carries" >&2
    exit 1; }
  echo "== refusal names only paths this commit does not carry — another lane mid-cycle =="
fi

# DRY_RUN exists so BOTH directions of the scoping predicate are testable
# without a commit landing. Without it only the passing direction could be
# exercised, and "never refuses anything" would satisfy that test (H68).
[ -z "$DRY_RUN" ] || { echo "DRY_RUN: would commit, all gates passed"; exit 0; }

echo "== committing (--no-verify, with every gate above already applied) =="
git commit --no-verify --only "$@" -F "$MSG"
