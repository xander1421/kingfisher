#!/usr/bin/env bash
# loop_gate.sh v2 — Stop hook for MISSION_LOOP continuous mode.
# Terminal signals are FILES, not prose: to end legally, the agent must
# write exactly LOOP-DONE, LOOP-HALT, or LOOP-IDLE into .loop_signal.
# Mentioning those words in conversation has no effect.
# ROOT is pinned. CLAUDE_PROJECT_DIR was unset and the session project dir is
# spikes/S51_multicore, so the $(pwd) fallback would have looked for STOP and
# .loop_signal in the wrong directory even once the hook was registered.
ROOT="/Users/victorianikolenko/kingfisher"
cd "$ROOT" 2>/dev/null || true
cat >/dev/null   # consume hook payload; no transcript parsing in v2

# 1 · Human kill switch (never auto-removed; human rm's it to resume)
[ -f STOP ] && exit 0

# 2 · Agent terminal signal — exact content, consumed on use
if [ -f .loop_signal ]; then
  SIG=$(tr -d '[:space:]' < .loop_signal)
  case "$SIG" in
    LOOP-DONE|LOOP-HALT|LOOP-IDLE)
      mv -f .loop_signal .loop_signal.last
      exit 0
      ;;
    *)
      rm -f .loop_signal   # malformed signal: ignore it and block
      ;;
  esac
fi

# 3 · Runaway fuse: cap blocked stops per session; relauncher resets
N=$(cat .loop_blocks 2>/dev/null || echo 0); N=$((N+1))
echo "$N" > .loop_blocks
if [ "$N" -gt "${MAX_BLOCKS:-400}" ]; then
  echo LOOP-FUSE > .loop_signal.last
  exit 0
fi

# 4 · Otherwise: refuse the stop, hand back the loop contract
cat <<'JSON'
{"decision":"block","reason":"Loop contract: stopping is unavailable. A legal exit requires writing exactly one of LOOP-DONE / LOOP-HALT / LOOP-IDLE into the file .loop_signal, and only under MISSION_LOOP section 7 conditions. Otherwise, in order: (1) refresh HANDOFF.md as the write-ahead checkpoint; (2) release stale CLAIMs in CHANNEL.md; (3) SELECT the highest-priority ungated unclaimed WORK_QUEUE item and run the next cycle. Quoting marker words in prose does nothing."}
JSON
exit 0
