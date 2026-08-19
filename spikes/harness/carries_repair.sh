# carries_repair.sh v2 — 2026-08-19, AGENT-1 (H218; v1 was H209).
#
# ==== v2, H218 — THE OBJECT IS IMMUTABLE. `HEAD` IS NOT. =====================
# DEFECT REMOVED: v1 RE-RESOLVED `HEAD` THREE TIMES AND PINNED NOTHING, SO UNDER
# INTERLEAVE IT AMENDED THE CO-LANE'S COMMIT.
#
# v1's own rationale block, quoted so the wrong sentence stays on the record:
# *"A commit object is IMMUTABLE, so the window is not shrunk from 8s to 8ms --
# it is ELIMINATED, because the object scored and the object recorded are the
# same object by construction."* The commit object is immutable and `HEAD` is a
# SYMBOLIC REF that five lanes move. v1 resolved it inside `carriescheck … HEAD`,
# again inside `git log -1 --format=%B`, and a third time inside
# `git commit --amend`. Three reads, no pin: whatever was HEAD at the third read
# is what got rewritten.
#
# MEASURED BY ok-1 AGAINST MY FILE, NOT BY ITS AUTHOR (A22), on the SHIPPED
# function rather than a copy -- `sh spikes/H199_hook_window/probe_b.sh`, 9/9,
# two-sided so a red B2 cannot mean "the function never fired":
#     B2c  HEAD -- lane B's commit -- WAS REWRITTEN by lane A
#     B2b  lane A's own commit still lacks the trailer it was owed
#     B2e  the rewritten commit carries a trailer scored for AGENT-1 NAMING LANE B
#     B2d  ...while still declaring `Atom: ok-1`
#     B2g  tree sha unchanged -- only the MESSAGE and the sha moved
# Their verdict, and it is the standard this v2 has to meet: *"a remedy that
# trades an 8 s window for a 50 ms window is a good trade only if the CONSEQUENCE
# is unchanged, and here it is not."* Before: your own commit carries a wrong
# trailer. After: another lane's commit is silently reissued under a new sha,
# with `--no-verify` so `commit-msg.hook` never sees the rewrite, and this repo
# cites shas in prose constantly.
#
# CLASS (§12.2), grep your own tree for it: *a repair step that re-resolves a
# symbolic ref it did not pin, so under concurrency it operates on someone else's
# object.* `HEAD`, `@{-1}`, `$(ls -t … | head -1)`, `.loop_signal` without
# `$CALLSIGN` are the same shape. §12.6 states this for harness STATE; this is
# the same rule for a REF. Swept 2026-08-19 over `spikes/harness/`,
# `.claude/hooks/`, `scripts/`, `run_loop.sh`, `bringup.sh`, `.git/hooks/`:
# `ls -t` 0 hits, `@{-1}`/`@{u}`/`ORIG_HEAD` 0 hits, every `.loop_signal` /
# `.loop_lock` use already per-lane, and exactly TWO live git-ref mutations in
# the whole harness -- `commit_scoped.sh:360`, which CREATES an object and so
# cannot rewrite one, and this file. One instance, and it is mine.
#
# AND THE FIRST v2 DRAFT WAS WRONG, WHICH IS THE PART WORTH KEEPING. I wrote the
# pin, ran the probe, and C3 came back `rewritten`: **a pin taken at entry
# brackets nothing when entry is already late.** ok-1's fixture has the co-lane
# commit BEFORE `carries_repair` is called, so `HEAD` at pin time IS lane B's
# object and the pin faithfully pinned the wrong commit. Pinning answers WHEN;
# the question here is WHICH, and no amount of window-narrowing answers it. That
# is v1's own error one level up -- I had again reached for a smaller window --
# and the arm that caught it is the one that exists only because ok-1 asked for
# a two-sided A/B rather than a green post-fix run.
#
# WHAT v2 DOES INSTEAD, AND WHY IT IS NOT "A SMALLER WINDOW" AGAIN:
#   0. ASSERT THE TARGET'S IDENTITY. `HEAD`'s own `Atom:` trailer must equal the
#      atom the repair was called for. A commit declaring another lane's atom is
#      not mine to rewrite and a commit declaring none is unidentified; both
#      refuse. This holds for an interleave of ANY duration, including one that
#      completed before the function was entered, because it is a property of
#      the object rather than of the clock.
#   1. PIN once, at entry: `_cr_sha=$(git rev-parse HEAD)`. Every read after that
#      names `$_cr_sha` -- the score, the message, the tree, the parents. No
#      later read of `HEAD` decides anything.
#   2. SWAP with a COMPARE-AND-SWAP, not an amend. `git commit --amend` takes no
#      expected-value argument, so it can only ever act on whatever HEAD is when
#      git locks it; that residual read is the same defect, smaller. So v2 builds
#      the new object with `git commit-tree` and installs it with
#      `git update-ref HEAD <new> <old>`, which REFUSES unless the ref still
#      holds `<old>`. The window is not narrowed, it is closed by the ref lock:
#      there is no interval in which this function can act on an object it did
#      not pin.
#   3. REFUSE, DO NOT GUESS. When the swap is refused, it prints a paste-ready
#      `CORRECTION` naming `$_cr_sha` and rewrites nothing. H105's rule -- a
#      false accusation is worse than a miss -- applied to objects instead of
#      lanes. The commit already landed; there is nothing to fail.
#
# `--only` ON v1's AMEND WAS LOAD-BEARING (a bare `git commit --amend` commits
# the shared index, §13/H19). v2 does not need it and is strictly stronger:
# `commit-tree` is handed the PINNED commit's own tree, so the tree is unchanged
# by construction rather than by flag. C4 in the probe asserts it anyway.
#
# NOT FIXED HERE, AND IT IS THE STRUCTURALLY BETTER ANSWER: ok-1's H199 arm A
# measured 13/13 that inside the `commit-msg` hook the content is already frozen
# and the message is still writable, so the trailer can be computed at a point
# where NO object exists yet to rewrite. That is a change to a shared enforcing
# gate that refuses every lane when it breaks (H106: 2m16s fleet-wide), so it is
# its own row, not a passenger on this one (§12.1).
#
# Check that fails when this breaks (§12.3):
#   sh spikes/H218_pinned_ref/probe.sh    (C1-C6, both directions)
# ===========================================================================

# carries_repair <ATOM> <ROOT> -- amend the message of the commit that was HEAD
# WHEN THIS FUNCTION WAS ENTERED with the trailer that commit actually earns.
# No-op when nothing foreign is carried; refuses when HEAD has moved under it.
carries_repair() {
  _cr_atom=$1; _cr_root=$2
  [ -n "$_cr_atom" ] || return 0
  [ -f "$_cr_root/spikes/harness/carriescheck.py" ] || return 0

  # ---- PIN. Nothing below re-reads HEAD to decide anything. ----------------
  _cr_sha=$(git rev-parse -q --verify HEAD 2>/dev/null) || return 0
  [ -n "$_cr_sha" ] || return 0

  # ---- ASSERT THE TARGET'S IDENTITY, because the pin alone cannot. ---------
  # A pin taken at entry brackets nothing if the co-lane committed BEFORE entry
  # -- then HEAD already IS their object and the pin faithfully pins the wrong
  # commit. The only property that survives any interleave is the one the object
  # carries about itself: a commit declaring another lane's `Atom:` is not mine
  # to rewrite, and a commit declaring no atom at all is unidentified. Refuse
  # both. (ATOM-3's class, same day: a harness that hardcodes the NAME of a
  # target whose identity it never asserts.)
  _cr_head_atom=$(git show -s --format='%(trailers:key=Atom,valueonly=true)' \
                    "$_cr_sha" | head -1 | tr -d '\r')
  if [ "$_cr_head_atom" != "$_cr_atom" ]; then
    echo "== REFUSED: HEAD is not this lane's commit, so there is nothing here to repair. =="
    echo "   HEAD $_cr_sha declares Atom: ${_cr_head_atom:-<none>}; this repair is for $_cr_atom."
    echo "   Nothing was rewritten. If your own commit was owed a trailer, it is the one"
    echo "   below HEAD -- post a CORRECTION to CHANNEL.md rather than reissuing a co-lane sha."
    return 0
  fi

  _cr_t=$(python3 "$_cr_root/spikes/harness/carriescheck.py" \
            "$_cr_atom" "$_cr_sha" --trailer 2>/dev/null)
  [ -n "$_cr_t" ] || return 0
  if git show -s --format=%B "$_cr_sha" | grep -qxF "$_cr_t"; then
    echo "== Carries: already correct on the landed commit =="
    return 0
  fi

  # ---- build the replacement from the PINNED object only -------------------
  _cr_parents=$(git rev-list --parents -n 1 "$_cr_sha" | cut -d' ' -f2- \
                | sed 's/[^ ]*/-p &/g')
  # The author env must reach `commit-tree`, which is the LAST stage of the
  # pipeline -- a `VAR=… git show …` prefix would have set it on the FIRST.
  # Command substitution is a subshell, so these exports do not leak to callers.
  _cr_new=$(
    GIT_AUTHOR_NAME=$(git show -s --format=%an "$_cr_sha")
    GIT_AUTHOR_EMAIL=$(git show -s --format=%ae "$_cr_sha")
    GIT_AUTHOR_DATE=$(git show -s --format=%aI "$_cr_sha")
    export GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_AUTHOR_DATE
    git show -s --format=%B "$_cr_sha" \
      | git interpret-trailers --trailer "$_cr_t" \
      | git commit-tree $_cr_parents -F - "$_cr_sha^{tree}"
  ) || return 0
  [ -n "$_cr_new" ] || return 0

  # ---- COMPARE-AND-SWAP. Refuses unless HEAD is still the object we scored. -
  if git update-ref -m "carries_repair: Carries: for $_cr_sha" \
       HEAD "$_cr_new" "$_cr_sha" 2>/dev/null; then
    echo "== the LANDED commit carries lines the message does not declare; amended =="
    echo "    $_cr_t"
  else
    echo "== REFUSED: HEAD moved under this repair -- a co-lane committed while it ran. =="
    echo "   Nothing was rewritten. $_cr_sha is owed the trailer below; post it as a"
    echo "   CORRECTION to CHANNEL.md rather than reissuing another lane's sha:"
    echo "   CORRECTION $_cr_sha $_cr_atom -- $_cr_t"
  fi
}
