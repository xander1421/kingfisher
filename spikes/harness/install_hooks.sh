#!/bin/sh
# install_hooks.sh v2 — 2026-08-17. v1 ATTACKER-1 (H7); v2 AGENT-1 (H15).
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
for h in commit-msg pre-commit; do
  src="spikes/harness/$h.hook"
  dst="$(git rev-parse --git-path hooks)/$h"
  [ -f "$src" ] || { echo "install_hooks: no $src"; exit 1; }
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "installed: $dst <- $src"
done
