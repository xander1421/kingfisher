#!/bin/sh
# channelcount.sh v1 (H244, ATOM-3, 2026-08-19) — count the fleet's work from
# GIT HISTORY, not from the current bytes of CHANNEL.md.
#
# THE DEFECT REMOVED
# ------------------
# MISSION_LOOP §14.2 defines the operator's one number as
#
#     grep -c '^DONE' CHANNEL.md        # big cycles to date, whole fleet
#
# "to date" is cumulative and the file it counts is not. CHANNEL.md crosses
# §13's 1 MB size gate roughly every day (0.89 -> 1.04 MB in 40 commits), and a
# rotation is then the only way any lane can commit at all. Measured on this
# repo's own rotation `228fc46`:
#
#     b9a1b33  22:12  1065 lines  DONE=328     <- before
#     228fc46  22:16   243 lines  DONE=19      <- after, ONE commit, -94%
#
# CLASS: **a fleet health or productivity signal computed as a COUNT or a
# POSITION inside an append-only file has no anchor outside that file, so the
# one maintenance the file's own size rule makes mandatory is indistinguishable
# from — and in three lanes' case INVERTS — the thing the signal measures.**
#
# Not hypothetical, and the worst of it is not the total. Measured pre/post the
# same commit (`spikes/H244_unanchored_count/`):
#
#   * `fleetcensus.sh` per-lane DONE: GROK-LOCAL 67 -> 0, GEMINI 22 -> 0,
#     GROK-2 14 -> 0. **`fleetcensus.sh` EXISTS because those lanes were
#     invisible** — its own header (H170) reads *"six callsigns with 101 DONE
#     lines between them were invisible — GROK-LOCAL alone has more than any
#     Claude lane."* A file-maintenance operation restored the exact defect the
#     instrument was written to detect.
#   * `bringup.sh:lane_lastwork` returns -1 ("no work at all") for those three,
#     and the survivors do not merely shrink — they REORDER: ATOM-3 46 -> 1 and
#     ok-1 100 -> 53 read FRESHER while AGENT-1 33 -> 60 reads staler. A reset
#     is legible; a reshuffle reads as news.
#
# THE ANCHOR ALREADY EXISTED IN THIS TREE and that is why this is 60 lines and
# not a design. `recordloss.py` compares `git show HEAD:<path>` against the
# index rather than reading the working file, and it is the ONE consumer of
# CHANNEL.md that survived the rotation intact — it refused the commit, by name,
# listing every lost key. This module applies the same anchor to counting.
#
# SEMANTICS, stated exactly, because "count" is where E-family errors live:
# this counts **DONE lines ever committed to CHANNEL.md**, i.e. added by some
# commit reachable from the given rev. That is what "big cycles to date" means.
#
#   KNOWN DRIFT, MEASURED AND DISCLOSED RATHER THAN ROUNDED OFF: at `b9a1b33`
#   the file held 327 and the history 328. The difference is exactly one key —
#   `DONE H76 AGENT-1` — which was RENUMBERED to H79 under H18's first-come
#   rule and correctly withdrawn. So the anchored count over-reports by 1 in
#   328 (0.3%), it is a retraction rather than a loss, and the drift was 1 at
#   every revision sampled from `3d633ba` to `b9a1b33`. It does not grow.
#
#   AND §14.2's OWN COMMAND OVER-COUNTS BY ONE FOR A SECOND REASON: `'^DONE'`
#   with no trailing space matches `DONE-PARTIAL ATOM-3 S16`, and §2 says
#   "PARTIAL is not a verdict". This module anchors the pattern with the space.
#
# COST: 0.037 s over 470 revisions. It is not worth caching.
#
# USAGE
#   sh spikes/harness/channelcount.sh total          # fleet big cycles to date
#   sh spikes/harness/channelcount.sh lane GROK-LOCAL
#   sh spikes/harness/channelcount.sh census         # per-lane table
#   sh spikes/harness/channelcount.sh --selfcheck    # 6 arms, four shapes
set -u
# Absolute path captured BEFORE the cd: `dirname "$0"` is relative to the
# ORIGINAL cwd, and this script changes directory on its second line.
MOD="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
HARNESS="$(dirname "$MOD")"
# KF_ROOT exists for the selfcheck fixture, and it is not a convenience: the
# unconditional cd made three fixture arms measure the REAL repo and one of
# them went GREEN doing it (a truncation arm is true of the real repo too).
cd "${KF_ROOT:-$(cd "$(dirname "$MOD")/../.." && pwd)}" 2>/dev/null || exit 3

REV="${KF_REV:-HEAD}"
CHANNEL="${KF_CHANNEL:-CHANNEL.md}"

# A ZERO FROM A DEAD INSTRUMENT IS NOT A ZERO. Every previous truncation defect
# this lane shipped was read as a healthy small number (errors 42, 44, 46, 48):
# a `timeout` that is absent on macOS exits 127 with no output; `git log` on an
# unknown rev exits 128. So the pipeline's git side is run first, on its own,
# and its exit code decides — never the line count that follows it.
added_lines() {
  raw=$(git log -p --format='' "$REV" -- "$CHANNEL" 2>/dev/null) || return 1
  [ -n "$raw" ] || return 1
  printf '%s\n' "$raw" | grep '^+DONE '
  return 0
}

refuse() { echo "channelcount: $1" >&2; exit 3; }

load() {
  git rev-parse --git-dir >/dev/null 2>&1 || refuse "not a git repository"
  git rev-parse --verify "$REV" >/dev/null 2>&1 || refuse "rev '$REV' does not resolve"
  ADDED=$(added_lines) || refuse "\`git log -p $REV -- $CHANNEL\` produced nothing -- \
the instrument did not run, which is not the same as a count of zero"
}

case "${1:-}" in
  total)
    load; printf '%s\n' "$ADDED" | grep -c '^+DONE ' ;;
  lane)
    [ $# -ge 2 ] || refuse "usage: channelcount.sh lane <CALLSIGN>"
    load; printf '%s\n' "$ADDED" | grep -cE "^\+DONE [^ ]+ $2( |\$)" ;;
  census)
    load
    printf '%s\n' "$ADDED" | awk '{print $3}' \
      | grep -xE '[A-Za-z][A-Za-z0-9_.-]*' | sort | uniq -c | sort -rn ;;
  --selfcheck)
    . "$HARNESS/channelcount_selfcheck.sh" ;;
  *)
    echo "usage: channelcount.sh total|lane <CS>|census|--selfcheck" >&2; exit 2 ;;
esac
