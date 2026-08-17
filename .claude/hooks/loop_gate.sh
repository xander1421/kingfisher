#!/usr/bin/env bash
# Stop-hook: allow stopping ONLY on real halt conditions.
# Everything else gets blocked with the next-cycle instruction.
IN=$(cat)                                   # hook payload (JSON)
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" 2>/dev/null || true

# 1. Human kill switch
[ -f STOP ] && exit 0

# 2. Legal terminal markers in the last output
TP=$(printf '%s' "$IN" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("transcript_path",""))' 2>/dev/null)
if [ -n "$TP" ] && [ -f "$TP" ]; then
  if tail -c 6000 "$TP" | grep -q 'LOOP-DONE\|LOOP-HALT\|LOOP-IDLE'; then
    exit 0
  fi
fi

# 3. Runaway guard: after MAX_BLOCKS continuations, allow a stop so a
#    stuck agent can't burn the account. Relauncher resets the counter.
N=$(cat .loop_blocks 2>/dev/null || echo 0); N=$((N+1))
echo "$N" > .loop_blocks
[ "$N" -gt "${MAX_BLOCKS:-400}" ] && exit 0

# 4. Otherwise: refuse the stop and hand back the loop contract.
cat <<'JSON'
{"decision":"block","reason":"Loop contract: stopping is not available. Do this now, in order: (1) refresh HANDOFF.md as a write-ahead checkpoint — verdicts this cycle, claims held, next 3 items; (2) release any stale CLAIMs in CHANNEL.md; (3) SELECT the highest-priority ungated unclaimed item in WORK_QUEUE.md and run the next cycle. Context is handled by auto-compaction, not by exiting. The loop ends only via a STOP file, LOOP-DONE, LOOP-IDLE, or LOOP-HALT."}
JSON
exit 0
