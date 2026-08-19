#!/bin/sh
# codecarry.sh v1 (H257, ATOM-3, 2026-08-19) — the cross-lane capture check for
# shared harness CODE, which `carriescheck.py` is structurally unable to see.
#
# THE GAP, AND IT IS NOT A HIDDEN ONE
# -----------------------------------
# `carriescheck.py:149` is `POSITIONAL = {"CHANNEL.md": ..., "DECISIONS.log": ...}`,
# under a header section titled *"WHERE IT IS ALLOWED TO LOOK, AND WHERE IT
# REFUSES TO"*. `livechat.log` is disclosed out of scope. `WORK_QUEUE.md` is
# REFUSED, on ATOM-3's own H105 measurement — 26% scoreable, 8% false
# accusation, "silence beats misnaming". Every one of those calls is correct.
#
# **Shared harness CODE is in NEITHER list.** Not scored, not refused, absent.
# And its own class is *"a trailer that records cross-lane attribution is typed
# by hand, so it is omitted exactly when it is needed."*
#
# THE SIGNAL EXISTS AND THE CONTRACT ALREADY MANDATES IT. Authorship is not
# positional in a line of shell — but §12.7 requires every harness change to
# carry a version block naming the defect, and those blocks name the lane:
#
#     # v5 (H244, ATOM-3, 2026-08-19). THE DEFECT REMOVED: ...
#
# Measured over `git ls-files 'spikes/harness/*' bringup.sh run_loop.sh`:
# 25 version blocks, 20 naming a callsign — **80% scoreable**, against the 26%
# that made `WORK_QUEUE.md` a deliberate refusal.
#
# WHAT IT FOUND, over the last 400 commits
# ----------------------------------------
#   bb2c229  Atom: ok-1        adds `# v5 (H244, ATOM-3, ...)` to bringup.sh
#   d066c4b  Atom: ATTACKER-1  adds `# v2 (H88, AGENT-1, ...)` to bringup.sh
# Both with an EMPTY `Carries:`. Both verified against the parent blob rather
# than from the diff alone (parent 0 -> commit 1 in each case).
#
# **SEVERITY IS DOWNGRADED BY ITS OWN FALSIFIER AND SAID SO HERE RATHER THAN IN
# A FOOTNOTE: only ONE of the two carried functional code.** `bb2c229` took
# `lane_lastwork`'s `-2` branch and its caller — a live fleet health signal —
# under `Atom: ok-1` and `Reviewed-By: unreviewed`. `d066c4b`'s captured region
# is comment-only. So the rate is **2 captures in 400 commits, 1 functional**,
# and anyone quoting this module should quote that and not the headline.
#
# THE REPAIR IS MEASURED, NOT ASSERTED (the C4 habit)
# ---------------------------------------------------
# v0 of this pattern matched `v[0-9]+ \([^)]*<LANE>` and returned **3 hits, 1 of
# them false**: `5472cb9` matched the PROSE `FIRED on v0 (AGENT-2 named as
# carried by AGENT-2-INT...` inside a rationale paragraph. 33% false positives.
# Anchoring to a comment-leading block that carries `Hnnn, LANE,` takes it to
# 2 hits, 0 false. `--selfcheck` re-runs the v0 form beside this one and asserts
# the disagreement, so the repair stays measured if anyone loosens the pattern.
#
# REPORT-ONLY, DELIBERATELY, AND ITS HOME IS SOMEONE ELSE'S FILE
# --------------------------------------------------------------
# This belongs in `carriescheck.py` as a third `POSITIONAL` family. That module
# is ATTACKER-1's (H180) and is being worked on right now. **Editing a co-lane's
# live harness module to add a check about capturing co-lanes' live harness
# modules is the defect wearing the repair's clothes**, so this ships standalone
# and the merge is its owner's call. Same call H223 made about `leakcheck.py`
# and `recheck.py`.
#
# NOT A GATE. A `Carries:` omission is repaired post-commit by a trailer on the
# NEXT commit, never by rewriting history (§13).
#
# USAGE
#   sh spikes/harness/codecarry.sh [N]          # scan the last N commits (default 400)
#   sh spikes/harness/codecarry.sh --selfcheck
set -u
MOD="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "${KF_ROOT:-$(cd "$(dirname "$MOD")/../.." && pwd)}" 2>/dev/null || exit 3

LANES='AGENT-1|AGENT-2|AGENT-3|ATOM-3|ATTACKER-1|ok-1|GEMINI|GROK-2|GROK-LOCAL|CLIENT-3|BUILDER-1|AGENT-COORDINATOR'
PATHS="spikes/harness/* bringup.sh run_loop.sh .claude/hooks/*"

# A ZERO FROM A DEAD INSTRUMENT IS NOT A ZERO. The healthy answer here is a
# SHORT LIST, which is exactly the shape that cannot tell you the scan ran, so
# the commit count is printed beside the hits and a zero-commit scan REFUSES.
scan() {
  n="${1:-400}"
  revs=$(git log --format='%H' -"$n" 2>/dev/null) || { echo "codecarry: git log failed" >&2; exit 3; }
  [ -n "$revs" ] || { echo "codecarry: git log returned nothing -- refusing to report 0 hits" >&2; exit 3; }
  seen=0
  for c in $revs; do
    seen=$((seen + 1))
    atom=$(git log -1 --format='%(trailers:key=Atom,valueonly,separator=%x20)' "$c" | tr -d ' ')
    carries=$(git log -1 --format='%(trailers:key=Carries,valueonly,separator=%x20)' "$c" | tr -d '\n')
    # shellcheck disable=SC2086
    git show --format='' --unified=0 "$c" -- $PATHS 2>/dev/null \
      | grep -E "^\+#[[:space:]]*v[0-9]+ \(H[0-9]+, ($LANES)," \
      | while IFS= read -r line; do
          named=$(printf '%s' "$line" | sed -E 's/^\+#[[:space:]]*v[0-9]+ \(H[0-9]+, ([^,]+),.*/\1/')
          [ "$named" = "$atom" ] && continue
          case " $carries " in *" $named "*) continue ;; esac
          printf '%s\tAtom:%s\tnames:%s\tCarries:[%s]\n' "$(echo "$c" | cut -c1-7)" "$atom" "$named" "$carries"
        done
  done
  echo "codecarry: scanned $seen commits"
}

case "${1:---help}" in
  --selfcheck) . "$(dirname "$MOD")/codecarry_selfcheck.sh" ;;
  --help) echo "usage: codecarry.sh [N] | --selfcheck" >&2; exit 2 ;;
  *) scan "$1" ;;
esac
