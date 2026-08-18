#!/bin/sh
# test_h58_entry_point.sh v1 — H58, ATOM-3, 2026-08-18.
#
# THE DEFECT IT GUARDS
# ====================
# CLASS: **TWO ARTIFACTS COMPETE TO DEFINE ONE ENTRY POINT, AND THE ONE THAT IS
# NOT IN CHARGE DOES NOT SAY SO.**
#
# `launchctl list` shows `com.kingfisher.bringup` LOADED, naming the ROOT
# `bringup.sh` (StartInterval 600). `spikes/harness/net.kingfisher.fleet.plist`
# names `spikes/harness/bringup.sh` at 300 instead. Four files in this repo
# record that the second is PROPOSED and never installed -- and the plist itself
# recorded it in ZERO places while carrying a plain `INSTALL —` block, so a human
# following that file's own instructions loads a SECOND fleet agent beside the
# live one. A caveat that lives everywhere except the artifact it is about is not
# a caveat (LEDGER standing rule 12).
#
# WHY A CHECK AND NOT JUST THE EDIT: the edit is prose, and prose is what failed
# here. This fails if the marker is ever removed, or if a THIRD plist appears, or
# if the proposed plist ever stops naming which agent supersedes it.
#
# WHAT IT DELIBERATELY DOES NOT DO: decide which script should be the entry
# point, or touch ~/Library/LaunchAgents. §10 -- that is outside the workspace
# and changing it is a human action.
#
#   sh spikes/harness/test_h58_entry_point.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
fail=0
ok()   { printf '  PASS  %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }

LIVE_PLIST=com.kingfisher.bringup.plist
PROPOSED=spikes/harness/net.kingfisher.fleet.plist

# C1 · every fleet plist in the tree is accounted for. A THIRD one appearing is
# the whole defect recurring, so the count is asserted rather than the names.
found=$(grep -rl 'ProgramArguments' --include='*.plist' . 2>/dev/null \
        | grep -v '^./elders/' | grep -v '^./archive/' | sort)
n=$(printf '%s\n' "$found" | grep -c .)
if [ "$n" -eq 2 ]; then
  ok "exactly 2 fleet plists in the tree"
else
  bad "expected 2 fleet plists, found $n:
$found"
fi

# C2 · the PROPOSED one declares itself superseded AND names its successor.
# Naming matters: "proposed" alone still leaves a reader hunting for what is
# actually running, which is the hunt that produced this row.
if [ -f "$PROPOSED" ]; then
  grep -q 'PROPOSED, NEVER INSTALLED, AND SUPERSEDED' "$PROPOSED" \
    && ok "proposed plist declares itself superseded" \
    || bad "$PROPOSED no longer declares itself superseded -- it did not for its
        first day, and four OTHER files carried the caveat instead"
  grep -q 'com.kingfisher.bringup' "$PROPOSED" \
    && ok "  and names the agent that supersedes it" \
    || bad "$PROPOSED does not name com.kingfisher.bringup, so a reader cannot
        tell what IS running without leaving the file"
else
  bad "$PROPOSED is gone; if that was deliberate, delete this check with it"
fi

# C3 · the two plists must not name the same script. If they ever do, one of
# them is redundant rather than superseded and this check is the wrong shape --
# it fails loudly instead of silently continuing to guard nothing.
p_live=$(grep -o '[^<>]*bringup\.sh' "$LIVE_PLIST" 2>/dev/null | head -1)
p_prop=$(grep -o '[^<>]*bringup\.sh' "$PROPOSED" 2>/dev/null | tail -1)
if [ -n "$p_live" ] && [ -n "$p_prop" ] && [ "$p_live" != "$p_prop" ]; then
  ok "the two plists name different scripts (that is WHY one is superseded)"
else
  bad "expected two different script paths, got live='$p_live' proposed='$p_prop'"
fi

# C4 · THE CONTROL THAT CAN FAIL, and it is the one the plist's own VERIFY step
# could not do: count, do not match. `launchctl list | grep kingfisher` prints a
# line for ONE agent and for TWO, so it cannot detect the single mistake the
# INSTALL block makes. Counting can.
#
# A SKIP IS NOT A PASS (H6). If launchctl is unavailable this reports SKIP and
# says what went unchecked, rather than exiting 0 and reading as verified.
if command -v launchctl >/dev/null 2>&1; then
  loaded=$(launchctl list 2>/dev/null | grep -c 'kingfisher')
  if [ "$loaded" -eq 1 ]; then
    ok "exactly 1 kingfisher LaunchAgent is loaded"
  elif [ "$loaded" -eq 0 ]; then
    printf '  SKIP  no kingfisher LaunchAgent loaded -- reboot survival is OFF.\n'
    printf '        NOT a pass: C4 checked nothing about the live entry point.\n'
  else
    bad "$loaded kingfisher LaunchAgents are loaded. Two agents, two intervals,
        two scripts -- this is exactly what the superseded INSTALL block does.
        Unload one:  launchctl unload ~/Library/LaunchAgents/net.kingfisher.fleet.plist"
  fi
else
  printf '  SKIP  launchctl absent (not macOS). C4 unchecked, NOT passed.\n'
fi

[ "$fail" -eq 0 ] && printf 'test_h58_entry_point: one entry point, and the loser says so\n'
exit "$fail"
