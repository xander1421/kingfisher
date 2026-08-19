# carries_repair.sh v1 — 2026-08-19, AGENT-1 (H209).
#
# ==== WHY THIS EXISTS (§12.7 rationale) ====================================
# DEFECT REMOVED: `Carries:` WAS SCORED AGAINST A TREE FIVE LANES WERE WRITING,
# AND THEN FROZEN INTO A COMMIT THAT WAS BUILT FROM A LATER READ OF THAT TREE.
#
# `commit_scoped.sh` v8 ran `carriescheck.py --worktree` and then, delta seconds
# later, `git commit --only "$@"` RE-READ the same working tree. Anything another
# lane wrote in delta is invisible to the check and present in the commit. v8's
# `--worktree` fix (H190) was right about WHICH object and could not be right
# about WHEN, because two processes cannot read a shared tree atomically.
#
# MEASURED BY ATTACKER-1, NOT BY THE AUTHOR OF THE DEFECT (A22): they ran
# `carriescheck` standalone, got clean, wrote their message file, and were still
# carried. EIGHT SECONDS. Their words, and the remedy is theirs too: "The only
# working form is compute-and-inject atomically inside the commit step."
#
# WHAT THIS DOES INSTEAD, AND WHY IT IS STRONGER THAN A NARROWER WINDOW: it does
# not compute before the commit at all. It scores `HEAD` AFTER the commit lands.
# A commit object is IMMUTABLE, so the window is not shrunk from 8s to 8ms -- it
# is ELIMINATED, because the object scored and the object recorded are the same
# object by construction. Family C answered by reading the artifact rather than a
# proxy for it. The cost is one `--amend` on a local, unpushed commit.
#
# `--only` ON THE AMEND IS LOAD-BEARING AND IS NOT DECORATION. Bare
# `git commit --amend` COMMITS THE INDEX, and five lanes share one index (§13,
# H19) -- an amend that swept in a co-lane's staged file would be this very
# defect class, committed by its own remedy. C3 in the probe asserts the TREE sha
# is unchanged across the amend, so that claim is measured and not asserted.
#
# Check that fails when this breaks (§12.3):
#   sh spikes/H209_carries_toctou/probe.sh    (C1-C3, both directions)
# ===========================================================================

# carries_repair <ATOM> <ROOT> -- amend HEAD's message with the trailer the
# LANDED commit actually earns. No-op when nothing foreign is carried (F2).
carries_repair() {
  _cr_atom=$1; _cr_root=$2
  [ -n "$_cr_atom" ] || return 0
  [ -f "$_cr_root/spikes/harness/carriescheck.py" ] || return 0
  _cr_t=$(python3 "$_cr_root/spikes/harness/carriescheck.py" "$_cr_atom" HEAD --trailer 2>/dev/null)
  [ -n "$_cr_t" ] || return 0
  if git log -1 --format=%B | grep -qxF "$_cr_t"; then
    echo "== Carries: already correct on the landed commit =="
    return 0
  fi
  echo "== the LANDED commit carries lines the message does not declare; amending =="
  echo "    $_cr_t"
  { git log -1 --format=%B; echo "$_cr_t"; } \
    | git commit --amend --no-verify --only -F - >/dev/null
}
