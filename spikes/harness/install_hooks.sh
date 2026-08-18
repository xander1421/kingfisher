#!/bin/sh
# install_hooks.sh v3 — 2026-08-18. v1 ATTACKER-1 (H7); v2 AGENT-1 (H15);
# v3 AGENT-2 (H106).
#
# v3 REMOVES A DEFECT THAT REFUSED A LIVE COMMIT. v2's `cp "$src" "$dst"` opens
# the destination with O_TRUNC and streams into it, so a lane running `git
# commit` during the write executes a PREFIX of the gate:
#
#   .git/hooks/pre-commit: line 252: unexpected EOF while looking for matching '"'
#
# observed 2026-08-18 against `06efe7e`, with `bash -n` on the same file clean
# one command later and both installed gates byte-identical to their sources.
# **A gate that refuses a commit and is provably sound a second later has
# refused for a reason no lane can diagnose**, and the fleet's instruction is to
# run this installer after any pull while five lanes commit continuously.
#
# CLASS: a shared executable replaced by an in-place truncating write, so any
# process executing it during the window runs a partial file. MEASURED before
# repair (`spikes/H106_hook_install_race/`): one writer and one executor over
# this repo's own `pre-commit.hook`, 6 s per arm, **52 parse failures in 2,264
# executions for `cp` and 0 in 1,167 for rename(2)**.
#
# v3 writes a sibling temp and rename(2)s it into place: rename is atomic within
# a filesystem, so an executor sees the whole old file or the whole new one and
# never a prefix. The temp is a SIBLING and not `$TMPDIR` on purpose -- rename
# across filesystems is not atomic and would reintroduce the defect quietly.
#
# `sh spikes/harness/install_hooks.sh --selfcheck` asserts the destination's
# INODE CHANGES on reinstall, which is what distinguishes replace-by-rename from
# truncate-in-place deterministically. It fails if v2's `cp` ever comes back.
#
# v2 installs BOTH gates instead of one. v1 installed `commit-msg` only, so when
# `pre-commit.hook` landed for H15 it was tracked, reviewed, drift-checked -- and
# installed nowhere, which is the EXACT defect v1's own header is about, one
# artifact later. A list, not a second cp, so gate three does not repeat it.
#
# THE ONLY ENFORCING GATE IN THIS REPO LIVES IN A DIRECTORY GIT DOES NOT TRACK.
# `spikes/harness/commit-msg.hook` is tracked and reviewable; `.git/hooks/` is
# not, and never can be. So on 2026-08-17 the state was:
#
#   * a clone, a worktree, or a re-init gets NO commit gate and is told nothing
#     -- MISSION_LOOP §13.1's "a check that REPORTS but does not GATE is prose
#     with extra steps" arriving at its own gate, which is simply ABSENT;
#   * nothing referenced `commit-msg.hook` from anywhere in the tree, so the
#     tracked file was reachable only by having watched someone install it;
#   * nothing compared the installed copy to the source, so editing the source
#     changed the reviewed artifact and not the enforced one -- the C family,
#     "the artifact is not what you think", at the enforcement layer.
#
# Idempotent. `git rev-parse --git-path` rather than `$root/.git/hooks`, because
# in a worktree `.git` is a FILE and that path does not exist -- resolved
# mechanically per §12.4 instead of assumed.
#
# Checked by spikes/harness/test_loop_gate.sh, which fails if the installed hook
# is missing, not executable, or has drifted from the tracked source.
set -e
cd "$(git rev-parse --show-toplevel)"

# Replace ATOMICALLY. The temp is a sibling of the destination so rename(2)
# stays within one filesystem; chmod happens on the temp, before it is visible
# under the live name, so no executor ever sees a non-executable gate either.
install_atomic() {
  _src="$1"; _dst="$2"
  _tmp="$_dst.tmp.$$"
  cp "$_src" "$_tmp"
  chmod +x "$_tmp"
  mv -f "$_tmp" "$_dst"
}

if [ "$1" = "--selfcheck" ]; then
  # H106's defect is invisible to a content comparison -- v2 and v3 install
  # byte-identical files. What separates them is WHETHER THE DESTINATION IS THE
  # SAME FILE afterwards: truncate-in-place keeps the inode, replace-by-rename
  # does not. So the inode is the observable, and this check goes red the moment
  # anyone reinstates `cp "$src" "$dst"`.
  t=$(mktemp -d) || exit 1
  trap 'rm -rf "$t"' EXIT
  printf '#!/bin/sh\nexit 0\n' > "$t/src"
  install_atomic "$t/src" "$t/dst"
  before=$(ls -i "$t/dst" | awk '{print $1}')
  install_atomic "$t/src" "$t/dst"
  after=$(ls -i "$t/dst" | awk '{print $1}')
  fail=0
  [ "$before" != "$after" ] || { echo "  FAIL  destination inode unchanged -- the install is a truncate-in-place, which is H106"; fail=1; }
  [ -x "$t/dst" ] || { echo "  FAIL  installed file is not executable"; fail=1; }
  # POSITIVE CONTROL: the inode test must be able to say SAME, or it is a check
  # that cannot fail (A15). A deliberate truncate-in-place must be caught.
  cp "$t/src" "$t/dst"
  ctl_before=$(ls -i "$t/dst" | awk '{print $1}')
  cp "$t/src" "$t/dst"
  ctl_after=$(ls -i "$t/dst" | awk '{print $1}')
  [ "$ctl_before" = "$ctl_after" ] || { echo "  FAIL  control: a deliberate cp changed the inode, so the observable does not separate the two installs"; fail=1; }
  [ "$fail" = 0 ] && echo "install_hooks selfcheck: replace-by-rename changes the inode, cp does not, installed file is executable"
  exit "$fail"
fi

# v4 (H115, ATTACKER-1, 2026-08-18) adds `pre-push`, and adds it to the LIST
# rather than beside it -- which is the extension point v2's header wrote down
# after v1 installed one gate and left the next one tracked, reviewed and
# installed nowhere. THE DEFECT IT CLOSES IS NOT IN THIS FILE: `.git/hooks/` held
# two gates, both refusing at COMMIT time, while §11's rail is crossed at PUSH
# time -- and `git remote -v` began resolving on 2026-08-18, so the rail stopped
# being safe by accident. See `spikes/H115_push_rail/`.
for h in commit-msg pre-commit pre-push; do
  src="spikes/harness/$h.hook"
  dst="$(git rev-parse --git-path hooks)/$h"
  [ -f "$src" ] || { echo "install_hooks: no $src"; exit 1; }
  mkdir -p "$(dirname "$dst")"
  install_atomic "$src" "$dst"
  echo "installed: $dst <- $src"
done
