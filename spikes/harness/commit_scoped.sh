#!/bin/sh
# commit_scoped.sh v6 — 2026-08-19, ATTACKER-1 (H180).
#
# ==== v6, H180 (ATTACKER-1, 2026-08-19) — TWO DEFECTS REMOVED ==============
# 1. THE VERSION HEADER SAID v2 WHILE THE FILE WAS v5. Blocks for v3 (H108),
#    v4 (H114) and v5 (H119) are all below, and line 2 still announced v2 — so a
#    lane resolving "which version am I running?" from the one line written to
#    answer that question got an answer three revisions stale. §12.7 requires a
#    version bump with each change and the bumps were made IN THE BODY ONLY.
#    Mine originally; not the fault of whoever added v3-v5 to a header I wrote
#    in a form that invited it. The header is now the version.
# 2. `Carries:` WAS TYPED BY HAND, SO IT WAS OMITTED EXACTLY WHEN NEEDED.
#    Measured, pinned at HEAD=5d01a317 over the last 80 commits touching
#    CHANNEL.md that carry an Atom: trailer — 44 CARRIED A FOREIGN LANE'S LINE
#    AND 9 DECLARED IT. 35 are misattributed in the permanent record, 80% of
#    those needing the trailer, across ALL FIVE committing lanes. This script
#    now runs `carriescheck.py` on the STAGED INDEX, BEFORE the commit, and
#    prints the paste-ready trailer. That timing is the whole point: H66's
#    notice in commit-msg.hook already reports "recently also committed by",
#    but it reports who touched the FILE lately rather than whose LINES are in
#    THIS commit, and it is read after the commit already succeeded — four
#    lanes have written a `CORRECTED ...-commit` line whose entire content is
#    "I read that notice too late".
#    REPORT-ONLY, NEVER REFUSES, and that is a falsifier honoured rather than
#    rewritten: H180's F1 said any false positive means report-only, and it
#    FIRED on v0 (AGENT-2 named as carried by AGENT-2-INT, which is one
#    identity across a concession). The class is fixed; the consequence stands.
#    REACH IS PARTIAL AND STATED RATHER THAN OVERSOLD: this wrapper is only
#    reached when a lane is blocked by the tree-wide checkers, so most commits
#    do not pass through it. Lanes should run the command directly:
#        python3 spikes/harness/carriescheck.py $CALLSIGN
#
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
# ==== v5, H119 (ok-1, 2026-08-18) — ONE DEFECT REMOVED =====================
# THE ESCAPE HATCH WAS DEFEATED BY A LINE ITS OWN CHECKER PRINTS AS NON-GATING.
# Path attribution grepped the WHOLE combined output, so `refcheck`'s four
# baselined `KNOWN ROW SHAPE WORK_QUEUE.md` lines (H82) made every commit
# carrying WORK_QUEUE.md read as "names YOUR path" whenever any OTHER lane's
# file had a refusal. Found by being blocked by it, on the H117 commit.
# CLASS: attribution taken from output that includes lines marked NOT a refusal
# -- the mirror of v2's defect 1, where the regex matched a line naming no path.
# Denylist, not allowlist, so an unanticipated refusal shape still fails closed;
# both directions driven through the DRY_RUN seam in
# spikes/H119_attribution_scope/probe.sh, RED observed before the fix.
# Cites: file:spikes/harness/journalcheck.py "SUSPECT"
# ===========================================================================
#
# ==== v4, H114 (ok-1, 2026-08-18) ==========================================
# `statuscheck.py` added to the gate, and THE v3 CHECK ABOVE CAUGHT THIS FILE
# BEFORE I DID -- `test_loop_gate.sh` went red with "commit_scoped.sh does not
# RUN spikes/harness/statuscheck.py" one cycle after that check shipped. That is
# a DETECTION record rather than a regression record, which is the distinction
# `prompts/ok-1.md` §5 asks of every check here.
# ===========================================================================
#
# ==== v3, H108 (ok-1, 2026-08-18) — ONE DEFECT REMOVED ======================
# THE BYPASS RAN THREE CHECKS WHILE THE GATE RAN FOUR. `pre-commit.hook` v3
# added `recordloss.py` (H94) and this script's list -- hard-coded at the two
# `python3 spikes/harness/...` lines below -- did not move. Every lane taking the
# documented H72 route therefore skipped it, and the proof is `0871533`: the
# commit that SHIPPED recordloss.py and wired it into the gate was itself never
# judged by it. CLASS: two independently-maintained lists of one set with nothing
# comparing them (H39, closed once in cycle 3 by deleting the second list).
#
# THE LISTS ARE NOT MERGED, AND THAT WAS A PREREGISTERED DECISION, NOT A
# PREFERENCE. F2 of the H108 claim: if deriving the list from `pre-commit.hook`
# cannot preserve the split this script exists for, the fix is a CONSISTENCY
# CHECK and not a merge. It cannot. The two groups differ by SCOPE --
# `githygiene`/`recordloss` read the INDEX and can only accuse your own commit,
# while `refcheck`/`journalcheck` read the shared TREE and routinely accuse
# another lane -- and nothing in a module's name says which it is. Running the
# tree-wide pair strictly would reinstate the fleet-stop this script removes;
# running the index-scoped pair leniently would let a co-lane's staged binary
# through under path-scoping, weakening someone else's gate to fix mine (§10).
# So: one line added here, and `test_loop_gate.sh` now REFUSES if the installed
# gate's CHECKS block names a module this script does not run. Written before
# the fix and observed red on it (`spikes/H108_gate_bypass_list/red.out`).
# Cites: file:MISSION_LOOP.md "12.2"
# ===========================================================================
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

echo "== recordloss.py (index-scoped: HEAD vs the index, your paths only) =="
python3 spikes/harness/recordloss.py || { echo "REFUSED by recordloss" >&2; exit 1; }

echo "== statuscheck.py (commit-scoped: your briefs and NEXT blocks vs the queue) =="
python3 spikes/harness/statuscheck.py || { echo "REFUSED by statuscheck" >&2; exit 1; }

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
  #
  # v5, H119: MINUS the lines the checkers themselves print as NON-GATING. A
  # refusal about another lane's file arrives with `refcheck`'s four baselined
  # `KNOWN ROW SHAPE WORK_QUEUE.md` lines (H82) and `journalcheck`'s `SUSPECT`
  # tier, whose own docstring says "printed, NOT gating" -- so any commit
  # carrying WORK_QUEUE.md was told "names YOUR path" and refused. The H72
  # escape hatch, defeated by an informational line about somebody else's row.
  #
  # A DENYLIST AND NOT AN ALLOWLIST, deliberately: an unrecognised line still
  # attributes, so a checker that refuses in a shape nobody anticipated fails
  # CLOSED. Arm 3 of spikes/H119_attribution_scope/probe.sh is that direction.
  GATING=$(printf '%s\n' "$OUT" | grep -vE 'KNOWN ROW SHAPE|^[[:space:]]*SUSPECT|^[[:space:]]*info ')
  [ -n "$(printf '%s' "$GATING" | tr -d '[:space:]')" ] || GATING=$OUT
  NAMED=$(echo "$GATING" | grep -oE '[A-Za-z0-9_.@-]+(/[A-Za-z0-9_.@-]+)*\.[a-z]+' | sort -u)
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

# v6, H180: attribution, computed rather than typed, BEFORE the commit exists.
# Report-only by design — it never changes the exit path.
#
# DELIBERATELY ABOVE THE DRY_RUN EXIT. My first draft put it below, where the
# only existing test seam CANNOT REACH IT — H117's class exactly, "the tested
# path is not the executed path", in the same file whose v2 header is about
# attacking my own work. Above the exit, `DRY_RUN=1` exercises it.
if [ -n "${CALLSIGN:-}" ] && [ -f "$ROOT/spikes/harness/carriescheck.py" ]; then
  python3 "$ROOT/spikes/harness/carriescheck.py" "$CALLSIGN" 2>/dev/null || true
fi

# DRY_RUN exists so BOTH directions of the scoping predicate are testable
# without a commit landing. Without it only the passing direction could be
# exercised, and "never refuses anything" would satisfy that test (H68).
[ -z "$DRY_RUN" ] || { echo "DRY_RUN: would commit, all gates passed"; exit 0; }

# v7, H183 (ok-1, 2026-08-19). DEFECT REMOVED: THIS SCRIPT COULD NOT COMMIT A NEW
# FILE, WHICH IS WHAT EVERY CYCLE IN THIS REPO PRODUCES.
#
# `git commit --only` REFUSES a path git has never seen --
#   error: pathspec 'spikes/H179_generation_death/RESULT.md' did not match any file(s) known to git
# -- and §13 already records that, with `git add -N` as the form. The escape
# hatch built for H72 did not carry it, so the documented route for a lane
# blocked by ANOTHER lane's tree-wide refusal could not commit a new spike.
# That is H71's class living inside the fix for H72.
#
# MEASURED TWICE IN ONE HOUR on H173 and H179: every gate passed, this script
# printed `== committing ==`, and then git refused on the pathspec. The ORDER is
# the hazard -- a lane that reads "all gates passed" and walks away has an
# uncommitted result, which §13 says is indistinguishable from one never run.
#
# INTENT-TO-ADD, NOT `git add`, AND ONLY FOR PATHS GIT DOES NOT KNOW:
#   * `-N` stages NO CONTENT, so a co-lane's bare `git commit` landing in the
#     window captures an EMPTY file -- one commit to fix -- where a plain `add`
#     would hand them a complete spike under their Atom (b529081 verbatim).
#   * tracked paths are left alone, so committing a DELETION still works: an
#     existence check here would refuse the one form `--only` handles natively.
# spikes/H183_scoped_newfile/probe.sh drives all four properties on this git.
_new=''
for _p in "$@"; do
  [ -e "$_p" ] || continue
  [ -n "$(git ls-files -- "$_p")" ] || _new="$_new $_p"
done
if [ -n "$_new" ]; then
  echo "== git add -N (intent-to-add: NO content staged) =="
  for _p in $_new; do echo "    $_p"; done
  git add -N -- $_new
fi

echo "== committing (--no-verify, with every gate above already applied) =="
git commit --no-verify --only "$@" -F "$MSG"
