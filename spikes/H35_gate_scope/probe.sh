#!/bin/sh
# H35 probe v3 — 2026-08-17, ATTACKER-1.
# v2 -> v3: the intervention was a silent no-op and C1 was one-sided, so v2's
# whole run was void. Both fixed at `break_queue` and C1 below, with the defect
# named there. v1 -> v2 note follows.
#
# QUESTION. `spikes/harness/pre-commit.hook` asserts, in its own header:
#   "The gate judges the content of your commit, and on a shared file that
#    content is not only yours."
# `refcheck.py` and `journalcheck.py` read files with plain `open()`, so their
# verdict is a function of the WORKING TREE. Those two statements cannot both be
# true. This probe decides it by running the real gate on constructed commits in
# an ISOLATED CLONE, and never on the live tree.
#
# v1 -> v2, AND v1's F2 RESULT WAS VOID. v1 attributed a non-zero exit to the
# gate. `git commit --only <untracked path>` fails with
# `error: pathspec ... did not match any file(s) known to git` BEFORE any hook
# runs, so v1's "F2 FIRED" was git rejecting a pathspec, measured as a gate
# refusal. DEFECT CLASS, mine: AN EXIT CODE ATTRIBUTED TO ONE STAGE OF A
# PIPELINE THAT EVERY STAGE CAN PRODUCE. v2 requires the gate's OWN refusal text
# (`pre-commit REFUSED`) and reports GIT-ERROR separately, so a cell can no
# longer borrow another mechanism's failure. Every cell now `git add`s first.
#
# FALSIFIERS, STATED BEFORE THE FIRST RUN. Either one killing means the header is
# right and this row is wrong:
#   F1 (false pass)     stage a duplicate row id, repair the tree, commit the
#                       index. Judging the commit => REFUSE. Observed PASS means
#                       refcheck check 5 is inert on the content committed.
#   F2 (false refusal)  break WORK_QUEUE.md in the tree, UNSTAGED, and
#                       `git commit --only <an unrelated path>`. Judging the
#                       commit => PASS. Observed REFUSE means one lane is blocked
#                       by another lane's uncommitted edit to a file it is not
#                       committing.
#
# CONTROLS, each with the input that makes it fail (§5: a control that cannot
# fail is not a control):
#   C0  clean clone, unrelated file, commit          -> must PASS.
#       Fails if HEAD is already red under any of the three checkers, in which
#       case every later cell is uninterpretable and this probe refuses. Note
#       the clone is taken from HEAD, so a lane mid-edit in the live tree cannot
#       move this control.
#   C1  broken tree, checker run DIRECTLY            -> must REFUSE.
#       Fails if the injected duplicate id is inert, i.e. the fixture would be
#       testing nothing — the trap that made my v3 refcheck fixture pass while
#       exercising no code (cycle 9).
#   C2  F1's committed blob still holds the duplicate -> must be > 1 match.
#       Fails if `git add` did not capture the broken version, which would make
#       an F1 pass correct rather than a defect.
#   C3  no cell reports GIT-ERROR                    -> v1's defect, gated.
#       Fails if any commit failed before the hook ran.
#
# Only `pre-commit` is installed here, not `commit-msg`. Single variable: the
# trailer gate is a different mechanism with its own suite
# (`spikes/harness/test_commit_msg.sh`), and its v5 session-derivation check is
# fail-open with no live launcher, so including it would add a second reason a
# cell could go red.
#
# Run: sh spikes/H35_gate_scope/probe.sh [path/to/pre-commit.hook]
# Exits 1 if any control failed, because an uncontrolled cell is not a
# measurement. Pass an alternate hook to check a candidate fix against the same
# cells.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
# ABSOLUTE, and v3 learned this the hard way: v2 took `$1` as given, then `cd`ed
# into the clone before copying it, so a RELATIVE argument resolved against the
# CLONE and the probe measured the clone's own HEAD copy of the hook while
# reporting the candidate's name. Two "v1 vs v2" comparisons were the same
# artifact twice. Family C in the probe itself, so the identity of the thing
# measured is now resolved before any `cd` and PRINTED with its digest.
HOOKSRC=${1:-$ROOT/spikes/harness/pre-commit.hook}
case $HOOKSRC in /*) ;; *) HOOKSRC=$(pwd)/$HOOKSRC ;; esac
[ -f "$HOOKSRC" ] || { echo "probe: no such hook: $HOOKSRC"; exit 1; }
D=$(mktemp -d "${TMPDIR:-/tmp}/h30.XXXXXX")
trap 'rm -rf "$D"' EXIT
R="$D/repo"

git clone --local --quiet "$ROOT" "$R"
cd "$R"
git remote remove origin           # no pushes, ever (§11); nothing to push to
cp "$HOOKSRC" "$(git rev-parse --git-path hooks)/pre-commit"
chmod +x "$(git rev-parse --git-path hooks)/pre-commit"
mkdir -p probe

MSG='H35 probe: fixture commit, not a finding

Atom: ATTACKER-1
Reviewed-By: unreviewed
'

# Duplicate an existing WORK_QUEUE row id -> refcheck check 5 must refuse.
#
# v3, AND v2's BREAK WAS A SILENT NO-OP. v2 wrote this as
# `grep -m1 -E '^\| H1 \|' WORK_QUEUE.md >> WORK_QUEUE.md`. BSD grep will not
# write to a file it is reading: the file gained 0 bytes, the duplicate count
# stayed 1, and every cell downstream reported on an intervention that never
# happened -- while v2's own header, one function above, names "an exit code
# attributed to one stage that every stage can produce". So the intervention now
# REPORTS ITS OWN SIZE and the probe refuses if it is not exactly +1, which is
# the `+0 edges must be fatal and printed` rule.
dups_now() { grep -cE '^\| H1 \|' WORK_QUEUE.md; }
break_queue() {
  _b=$(dups_now)
  _row=$(grep -m1 -E '^\| H1 \|' WORK_QUEUE.md)
  printf '%s\n' "$_row" >> WORK_QUEUE.md
  _a=$(dups_now)
  printf '   intervention: row H1 copies %s -> %s\n' "$_b" "$_a"
  [ "$_a" = "$(( _b + 1 ))" ] || { say 'INTERVENTION FAILED (+0) — probe refuses'; exit 1; }
}
fix_queue()   { git show HEAD:WORK_QUEUE.md > WORK_QUEUE.md; }

# Classify a commit attempt into GATE-REFUSED / GIT-ERROR / PASS by reading the
# gate's own words, never by the exit code alone (v1's defect).
verdict=''
attempt() {                        # attempt <commit args...>
  if out=$(git commit -q "$@" -m "$MSG" 2>&1); then verdict=PASS
  elif printf '%s' "$out" | grep -q 'pre-commit REFUSED'; then verdict=GATE-REFUSED
  else verdict=GIT-ERROR; printf '   git said: %s\n' "$(printf '%s' "$out" | head -2)"
  fi
}

say() { printf '%s\n' "$1"; }
bad=0; giterr=0

say "SUBJECT $HOOKSRC"
say "  $(sed -n '2p' "$HOOKSRC")"
say "  sha256 $(shasum -a 256 "$HOOKSRC" | cut -d' ' -f1)"

# THE SUBJECT IS THE HOOK, NOT THE CHECKERS, so the checkers are seeded from the
# WORKING TREE and every substitution is printed. v3 first ran without this and
# C0/C1 refused correctly: HEAD f95b164 is RED under `refcheck.py`, on two
# `prompts/$CALLSIGN.md` citations that another lane's UNCOMMITTED refcheck v4
# already resolves. A probe that cannot run whenever HEAD is red for a reason
# unrelated to its subject measures nothing, and silently using the stale
# checker measures the wrong artifact (family C). So: seed, and say so.
for chk in refcheck journalcheck githygiene; do
  s="$ROOT/spikes/harness/$chk.py"
  [ -f "$s" ] || continue
  if git show "HEAD:spikes/harness/$chk.py" 2>/dev/null | cmp -s - "$s"; then
    say "  checker $chk.py = HEAD"
  else
    cp "$s" "spikes/harness/$chk.py"
    say "  checker $chk.py SEEDED FROM THE WORKING TREE (differs from HEAD) sha256 $(shasum -a 256 "$s" | cut -d' ' -f1)"
  fi
done

# ---- C0: is HEAD interpretable at all? -------------------------------------
echo 'probe C0' > probe/c0.md
git add probe/c0.md
attempt --only probe/c0.md
case $verdict in
  PASS) say 'C0 PASS  clean clone, unrelated file, commit accepted' ;;
  GIT-ERROR) say 'C0 FAIL  GIT-ERROR before the gate'; bad=1; giterr=1 ;;
  *) say 'C0 FAIL  HEAD is already red under the gate — every cell below is uninterpretable'; bad=1 ;;
esac

# ---- C1: is the injection real, and is it what makes refcheck red? ----------
# TWO-SIDED, because v2's one-sided version passed while the injection was inert:
# refcheck must be GREEN before and RED after. A single red reading cannot tell
# an injected defect from a checker that was already refusing for its own
# reasons, which is the confound that voided v2's whole run.
c1a=0; python3 spikes/harness/refcheck.py >/dev/null 2>&1 || c1a=1
break_queue
c1b=0; python3 spikes/harness/refcheck.py >/dev/null 2>&1 || c1b=1
if [ "$c1a" = 0 ] && [ "$c1b" = 1 ]; then
  say 'C1 PASS  refcheck green before the injection, red after — the defect is mine'
elif [ "$c1a" = 1 ]; then
  say 'C1 FAIL  refcheck was ALREADY red at HEAD — a red cell below proves nothing'
  bad=1
else
  say 'C1 FAIL  injected duplicate id is INERT — this fixture would test nothing'
  bad=1
fi
fix_queue

# ---- F1: stage broken, repair tree, commit the index ------------------------
break_queue
git add WORK_QUEUE.md
fix_queue                                     # tree CLEAN, index BROKEN
echo 'probe f1' > probe/f1.md
git add probe/f1.md
attempt
dups=$(git show HEAD:WORK_QUEUE.md | grep -cE '^\| H1 \|' || true)
if [ "$dups" -gt 1 ]; then
  say "C2 PASS  the commit's own blob holds $dups copies of row H1"
elif [ "$verdict" = GATE-REFUSED ]; then
  say "C2 n/a   the gate refused, so no commit exists to inspect"
else
  say "C2 FAIL  index did not capture the broken version ($dups copies) — F1 is void"
  bad=1
fi
case $verdict in
  PASS) say 'F1 FIRED  the gate PASSED a commit whose own content violates refcheck check 5' ;;
  GATE-REFUSED) say 'F1 killed  the gate refused it' ;;
  *) say 'F1 VOID  GIT-ERROR before the gate'; bad=1; giterr=1 ;;
esac
git reset -q --hard HEAD 2>/dev/null || true
[ "$dups" -gt 1 ] && git reset -q --hard HEAD~1
git clean -qfd probe 2>/dev/null || true

# ---- F2: broken tree, unstaged, commit an unrelated path with --only --------
break_queue
mkdir -p probe          # F1's `git clean -qfd probe` removes it when C0 refused
echo 'probe f2' > probe/f2.md
git add probe/f2.md                           # tracked, so --only has a pathspec
attempt --only probe/f2.md
case $verdict in
  GATE-REFUSED) say 'F2 FIRED  the gate REFUSED a commit that does not contain the broken file' ;;
  PASS) say 'F2 killed  the gate passed it — a tree-only violation does not block a lane' ;;
  *) say 'F2 VOID  GIT-ERROR before the gate'; bad=1; giterr=1 ;;
esac
say "SCOPE  F2 committed: probe/f2.md ; broken and UNSTAGED: WORK_QUEUE.md (HEAD version is what the commit would carry)"
fix_queue

[ "$giterr" = 0 ] && say 'C3 PASS  no cell borrowed a GIT-ERROR for a gate verdict' || say 'C3 FAIL  a cell failed before the hook ran'
[ "$bad" = 0 ] || { say 'PROBE REFUSES: a control failed, so no cell above is a measurement'; exit 1; }
say 'controls C0/C1/C2/C3 all held'
