#!/usr/bin/env bash
# H230 probe — ATTACKER-1, 2026-08-19.
#
# §13's size gate reads the INDEX; commit_scoped.sh commits the WORKING TREE
# with `git commit --only`, which by design ignores the index (H19, H190).
#
# EVERY ARM RUNS IN AN ISOLATED SCRATCH REPO. Nothing here stages, commits or
# touches the live tree: four lanes share that index and breaking it to measure
# it is the failure this row is about.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
WORK="$ROOT/.scratch/h230"
GH="$ROOT/spikes/harness/githygiene.py"
pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL %s -- %s\n' "$1" "$2"; }
obs()  { printf 'OBS %s %s\n' "$1" "$2"; }

rm -rf "$WORK"; mkdir -p "$WORK"

newrepo() {                       # $1 = name -> echoes the repo path
  d="$WORK/$1"; mkdir -p "$d"; cd "$d" || exit 1
  git init -q .; git config user.email a@b; git config user.name t
  mkdir -p spikes/harness
  cp "$GH" spikes/harness/githygiene.py
  printf 'seed\n' > CHANNEL.md
  git add CHANNEL.md spikes/harness/githygiene.py
  git -c core.hooksPath=/dev/null commit -qm 'seed

Atom: T
Claude-Session: local
Reviewed-By: unreviewed'
  echo "$d"
}

big() { python3 -c "
import sys
p=sys.argv[1]
open(p,'a').write('x'*(1100*1024))" "$1"; }

# ── F1 ─ a >1 MiB file STAGED is refused ─────────────────────────────────────
d=$(newrepo f1); cd "$d" || exit 1
big CHANNEL.md
git add CHANNEL.md
out=$(python3 spikes/harness/githygiene.py 2>&1); rc=$?
obs F1 "{\"staged\":true,\"rc\":$rc,\"actionable\":$(echo "$out" | grep -qi 'ACTIONABLE' && echo true || echo false)}"
if [ "$rc" -ne 0 ] && echo "$out" | grep -qi 'exceeds'; then
  ok "F1 FIRED: a staged >1 MiB CHANNEL.md is refused (H229's direction is real)"
  f1=fired
else
  bad "F1" "expected refusal, got rc=$rc"
  f1=notfired
fi

# ── F2 ─ the SAME file, unstaged, is invisible to the same gate ──────────────
d=$(newrepo f2); cd "$d" || exit 1
big CHANNEL.md                      # working tree only; index untouched
out=$(python3 spikes/harness/githygiene.py 2>&1); rc=$?
obs F2 "{\"staged\":false,\"rc\":$rc,\"says_nothing_staged\":$(echo "$out" | grep -q 'nothing staged' && echo true || echo false)}"
# and `--only` commits it anyway: that is the path commit_scoped.sh takes
git -c core.hooksPath=/dev/null commit -q --only CHANNEL.md -m 'land it

Atom: T
Claude-Session: local
Reviewed-By: unreviewed' 2>/dev/null
landed=$(git cat-file -s "HEAD:CHANNEL.md" 2>/dev/null || echo 0)
obs F2b "{\"landed_bytes\":$landed,\"over_1MiB\":$([ "$landed" -gt 1048576 ] && echo true || echo false)}"
if [ "$rc" -eq 0 ] && [ "$landed" -gt 1048576 ]; then
  ok "F2 FIRED: gate green, and --only landed $landed bytes past the 1 MiB limit"
  f2=fired
else
  bad "F2" "rc=$rc landed=$landed"
  f2=notfired
fi

# ── F3 ─ the flip is reachable by ANOTHER party's `git add` alone ────────────
d=$(newrepo f3); cd "$d" || exit 1
big CHANNEL.md
before=$(python3 spikes/harness/githygiene.py >/dev/null 2>&1; echo $?)
git add CHANNEL.md                  # stand-in for the OTHER lane, not for me
after=$(python3 spikes/harness/githygiene.py >/dev/null 2>&1; echo $?)
obs F3 "{\"rc_before_foreign_add\":$before,\"rc_after_foreign_add\":$after}"
if [ "$before" -eq 0 ] && [ "$after" -ne 0 ]; then
  ok "F3 FIRED: my verdict flipped 0 -> $after on somebody else's git add"
  f3=fired
else
  bad "F3" "before=$before after=$after"
  f3=notfired
fi

# ── C0 ─ CONTROL: the gate is not simply always-red, and not always-green ────
d=$(newrepo c0); cd "$d" || exit 1
printf 'small\n' >> CHANNEL.md
git add CHANNEL.md
rc_small=$(python3 spikes/harness/githygiene.py >/dev/null 2>&1; echo $?)
big CHANNEL.md
git add CHANNEL.md
rc_bigst=$(python3 spikes/harness/githygiene.py >/dev/null 2>&1; echo $?)
obs C0 "{\"rc_small_staged\":$rc_small,\"rc_big_staged\":$rc_bigst}"
if [ "$rc_small" -eq 0 ] && [ "$rc_bigst" -ne 0 ]; then
  ok "C0 control: same repo, same file, small=green big=red — the gate discriminates"
else
  bad "C0 control" "small=$rc_small big=$rc_bigst — a gate with one reachable state proves nothing"
fi

# ── C1 ─ CONTROL: `--only` really does ignore the index ──────────────────────
d=$(newrepo c1); cd "$d" || exit 1
printf 'INDEXED\n' >> CHANNEL.md
git add CHANNEL.md
printf 'WORKTREE-ONLY\n' >> CHANNEL.md
git -c core.hooksPath=/dev/null commit -q --only CHANNEL.md -m 'only

Atom: T
Claude-Session: local
Reviewed-By: unreviewed'
has_wt=$(git show HEAD:CHANNEL.md | grep -c 'WORKTREE-ONLY')
obs C1 "{\"worktree_only_line_in_commit\":$has_wt}"
if [ "$has_wt" -eq 1 ]; then
  ok "C1 control: --only committed a line that was never staged"
else
  bad "C1 control" "--only did not take the worktree; the premise is wrong"
fi

cd "$ROOT" || exit 1
printf '\nRESULT: %d passed, %d failed  |  F1=%s F2=%s F3=%s\n' "$pass" "$fail" "$f1" "$f2" "$f3"
[ "$fail" -eq 0 ]
