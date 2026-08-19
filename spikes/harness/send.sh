#!/usr/bin/env bash
# send.sh — address a message to a lane BY CALLSIGN, delivered into its next turn.
#
# v2, 2026-08-19 (AGENT-1, H184). DEFECT REMOVED: **THIS SCRIPT REFUSED EVERY
# CALLSIGN IN THE FLEET FOR ~2 HOURS AND ITS OWN STATUS COMMAND REPORTED HEALTHY.**
# `f6f923d` (16:28) dropped the space between the sed EXPRESSION and its FILENAME:
#     sed 's/#.*//'"$_ROSTER"        <- one argument, not two
# so sed read `s/#.*///Users/.../roster.txt` as its script, refused with "bad flag
# in substitute command", printed nothing, and LANES became EMPTY. Every consumer
# reads "not in LANES" as "not a declared lane", so `send.sh AGENT-2 ...` answered
# `'AGENT-2' is not a declared lane ()` -- with the empty parens printing the whole
# evidence and nobody reading it -- and `--list` walked an empty loop and printed
# `(nothing pending)`. MEASURED AT THE FIX: 62 lines pending for AGENT-1, 62 for
# AGENT-2, 81 for ATTACKER-1, all reported as nothing.
#
# CLASS, which is the part worth carrying: **a missing input degraded the mechanism
# to a narrower one that still reported success.** H30's rule, already written into
# `allocid.sh`'s own `refuse_if_input_missing`, and not applied here. The roster
# EXISTING is not the roster being READ, and the difference was invisible because
# the failure direction was quiet. v2 refuses on an empty lane list rather than
# treating it as a roster that sanctions nobody. Check: `sh spikes/harness/test_send.sh`.
#
# The commit that broke it is titled "a quorum check that can never read green stops
# being read". It shipped a `--list` that can never read anything BUT green.
#
# WHY THIS EXISTS. Lanes had no addressable channel. What existed:
#   * livechat.log — append-only prose, broadcast, and a lane only sees it if it
#     happens to re-read the file. No addressing, no delivery guarantee.
#   * CHANNEL.md — claims, not conversation.
#   * SendMessage between sessions — but peer names are session-derived
#     (`kingfisher-d3`, `kingfisher-60`, two of which collide), so THERE IS NO
#     CALLSIGN -> ADDRESS MAPPING. You cannot reach AGENT-1 by asking for AGENT-1.
#
# The one path that certainly reaches a lane is its launch prompt, because
# run_loop.sh builds that prompt every turn. So an inbox delivered through the
# prompt is a channel with a delivery guarantee, and archived on delivery so it is
# read once rather than every turn forever.
#
# This is NOT publishing. Everything stays in the workspace; §11 is untouched.
#
# usage:
#   sh spikes/harness/send.sh AGENT-1 "one-line message"
#   sh spikes/harness/send.sh ok-1 < message.md
#   echo "..." | sh spikes/harness/send.sh ATTACKER-1
#   sh spikes/harness/send.sh --all "goes to every declared lane"
#   sh spikes/harness/send.sh --list          # what is undelivered, per lane
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

# H38, third copy. rostercheck.py found this after ../../roster.txt and
# bringup.sh were reconciled: a hard-coded lane set is not one site, it is a
# class, and fixing two of three leaves the same contradiction one file over.
# Read the sanction file; the literal survives only as a no-roster fallback.
_ROSTER="$(cd "$(dirname "$0")/../.." && pwd)/roster.txt"
if [ -f "$_ROSTER" ]; then
  # H184: the space after the sed EXPRESSION is load-bearing. Without it the shell
  # concatenates expression and filename into ONE argument -- sed then reads
  # `s/#.*///Users/.../roster.txt` as its script, refuses with "bad flag in
  # substitute command", writes nothing to stdout, and LANES becomes EMPTY.
  LANES="$(sed 's/#.*//' "$_ROSTER" | awk 'NF{print $1}' | tr '\n' ' ')"
else
  LANES="AGENT-1 AGENT-2 ATTACKER-1 ATOM-3 ok-1"
fi

# H184, AND THIS IS THE CLASS RATHER THAN THE TYPO. An empty LANES must REFUSE.
# Every consumer below treats "not in LANES" as "not a declared lane", so an empty
# list is indistinguishable from a roster that sanctions nobody: `send.sh X` refuses
# every callsign, and `--list` walks an empty loop and prints "(nothing pending)" --
# a FALSE GREEN over a dead channel, which is the one reading nobody investigates.
# Same rule allocid.sh already states for its own inputs (H30): a missing input must
# not silently degrade a mechanism to a narrower one that still reports success.
# The roster existing is not the same as the roster being READ.
if [ -z "$(printf '%s' "$LANES" | tr -d '[:space:]')" ]; then
  echo "send.sh: lane list is EMPTY after reading $_ROSTER -- refusing rather than" >&2
  echo "         reporting every callsign undeclared and every inbox quiet (H184)." >&2
  exit 3
fi
mkdir -p inbox inbox/archive

if [ "${1:-}" = "--list" ]; then
  echo "UNDELIVERED"
  n=0
  for l in $LANES; do
    if [ -s "inbox/$l.md" ]; then
      printf '  %-12s %s lines pending\n' "$l" "$(wc -l < "inbox/$l.md" | tr -d ' ')"
      n=$((n+1))
    fi
  done
  [ "$n" -eq 0 ] && echo "  (nothing pending)"
  echo "DELIVERED"
  ls -1 inbox/archive 2>/dev/null | tail -8 | sed 's/^/  /'
  exit 0
fi

TARGETS="${1:?usage: send.sh <CALLSIGN|--all> [message]   (or pipe on stdin)}"
shift || true
[ "$TARGETS" = "--all" ] && TARGETS="$LANES"

# The sender is whoever ran this. A message whose sender is unknown cannot be
# replied to, and an unattributable claim is the defect CHANNEL.md exists to
# prevent -- two lanes signing AGENT-2 cost a spike rename.
FROM="${CALLSIGN:-$(whoami)@interactive}"

if [ $# -gt 0 ]; then BODY="$*"; else BODY="$(cat)"; fi
[ -n "$BODY" ] || { echo "send.sh: empty message, nothing sent"; exit 1; }

for l in $TARGETS; do
  case " $LANES " in
    *" $l "*) ;;
    *) echo "send.sh: '$l' is not a declared lane ($LANES)"; exit 1 ;;
  esac
  # Refuse a lane with no brief: it cannot be running, so the message would sit
  # undelivered forever and look sent. bringup.sh --check reports that state.
  [ -f "prompts/$l.md" ] || { echo "send.sh: no prompts/$l.md; '$l' is not a lane that runs"; exit 1; }
  {
    printf '\n──── message to %s, from %s ────\n' "$l" "$FROM"
    printf '%s\n' "$BODY"
  } >> "inbox/$l.md"
  printf 'queued for %s (%s lines pending)\n' "$l" "$(wc -l < "inbox/$l.md" | tr -d ' ')"
done
