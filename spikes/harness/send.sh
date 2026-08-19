#!/usr/bin/env bash
# send.sh — address a message to a lane BY CALLSIGN, delivered into its next turn.
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
  LANES="$(sed 's/#.*//' "$_ROSTER" | awk 'NF{print $1}' | tr '\n' ' ')"
else
  LANES="AGENT-1 AGENT-2 ATTACKER-1 ATOM-3 ok-1 GEMINI-1 GROK-LOCAL GROK-2"
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
