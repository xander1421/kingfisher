#!/usr/bin/env sh
# peers.sh — print the live lane registry: callsign, pid, socket, addressable.
#
# Cited by prompts/ATOM-3.md, prompts/ATTACKER-1.md, WORK_QUEUE.md and
# HANDOFF.ATTACKER-1.md before it existed, which took refcheck red and blocked
# every lane's commit. A contract citing a missing artifact reads as satisfied;
# that is why refcheck refuses rather than warns, and it was right.
#
# WHAT IT IS FOR. `ListAgents` returns PEER sessions — a session's own row is
# absent — so no lane can look up its own address, and a registry built by
# self-append is a registry of guesses. This reads the two things that ARE
# observable from any lane:
#
#   * /tmp/cc-socks/<pid>.sock   a session exists and is addressable
#   * ps argv `You are <X>.`     that pid claims callsign X
#
# LIMIT, STATED. The argv scan sees only lanes launched with a callsign in
# ARGV. An interactive session carrying a callsign in its ENVIRONMENT is
# invisible: pid 2950 messaged AS ATOM-3 while `You are ATOM-3.` is pid 44527 —
# two live processes for one callsign, and the scan names the one that does not
# talk. So a row here is a LEAD, not proof of address. Proof is a message
# arriving from it, which only the receiver can observe; PEERS.md records that
# separately as OBSERVED.
#
#   ./peers.sh            # table
#   ./peers.sh --tsv      # machine-readable
set -u
cd "$(cd "$(dirname "$0")" && pwd)"

TSV=no
[ "${1:-}" = "--tsv" ] && TSV=yes

[ "$TSV" = no ] && printf '%-12s %-7s %-26s %s\n' CALLSIGN PID SOCKET ADDRESSABLE

# Lanes with a callsign in argv.
ps -eo pid=,command= 2>/dev/null | while read -r pid rest; do
  case "$rest" in
    *"You are "*)
      lane=$(printf '%s' "$rest" | grep -oE 'You are [A-Za-z0-9_-]+\.' | head -1 \
             | sed -e 's/You are //' -e 's/\.$//')
      [ -z "$lane" ] && continue
      sock="/tmp/cc-socks/${pid}.sock"
      if [ -S "$sock" ]; then addr=yes; else addr="no — no socket"; fi
      if [ "$TSV" = yes ]; then
        printf '%s\t%s\t%s\t%s\n' "$lane" "$pid" "$sock" "$addr"
      else
        printf '%-12s %-7s %-26s %s\n' "$lane" "$pid" "$sock" "$addr"
      fi ;;
  esac
done

# Sockets with no argv lane behind them. These are the invisible half: every one
# is a live session that can message you and that no scan of argv will name.
orphans=""
for s in /tmp/cc-socks/*.sock; do
  [ -S "$s" ] || continue
  p=$(basename "$s" .sock)
  ps -p "$p" -o command= 2>/dev/null | grep -q 'You are ' || orphans="$orphans $p"
done
if [ -n "$orphans" ] && [ "$TSV" = no ]; then
  printf '\nunnamed sessions (addressable, no callsign in argv):%s\n' "$orphans"
  printf 'These can message you and cannot be named from here. See PEERS.md.\n'
fi
