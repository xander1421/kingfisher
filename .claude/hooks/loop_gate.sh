#!/usr/bin/env bash
# loop_gate.sh v4 — Stop hook for MISSION_LOOP continuous mode.
# Terminal signals are FILES, not prose: to end legally, the agent must
# write exactly LOOP-DONE, LOOP-HALT, or LOOP-IDLE into .loop_signal
# (or, preferred with more than one lane, .loop_signal.$CALLSIGN).
# Mentioning those words in conversation has no effect.
#
# ROOT is pinned. CLAUDE_PROJECT_DIR was unset and the session project dir is
# spikes/S51_multicore, so the $(pwd) fallback would have looked for STOP and
# .loop_signal in the wrong directory even once the hook was registered.
#
# v3, 2026-08-17: v2 consumed the signal to .loop_signal.last, which no other
# process read, so run_loop.sh could not see a legal exit and fell back to
# grepping its own log for the marker words -- reintroducing at the launcher
# exactly the prose-matching defect this hook was written to remove. The signal
# now lands in .loop_exit.$CALLSIGN, which only run_loop.sh clears. State is
# per-lane because two lanes sharing one .loop_signal let one consume the
# other's exit, and one .loop_blocks gave them a shared fuse.
ROOT="/Users/victorianikolenko/kingfisher"
cd "$ROOT" 2>/dev/null || true
cat >/dev/null   # consume hook payload; no transcript parsing since v2

# 1 · Human kill switch (never auto-removed; human rm's it to resume)
[ -f STOP ] && exit 0

# 2 · FAIL CLOSED ON LANE IDENTITY.  v4, 2026-08-17.
#
# v3 wrote LANE="${CALLSIGN:-unknown}", and that default is the whole bug. Every
# session without a callsign -- a human at a terminal, a reviewer reading the
# repo, a subagent -- became lane "unknown", so:
#   * interactive sessions were gated and told to run cycles they are not part of;
#   * all of them shared .loop_signal.unknown / .loop_blocks.unknown, so a human
#     reading the repo incremented THE FLEET'S runaway fuse (observed: 3);
#   * .loop_exit.unknown was written and nothing ever cleared it, because
#     run_loop.sh only clears .loop_exit.$CALLSIGN for a real lane;
#   * §12.6 "harness state is per-lane, never global" was satisfied in the naming
#     and defeated in practice -- per-lane names collapsing to one name.
#
# H1 was marked DONE on that. It was not. The v3 test only ever ran with
# CALLSIGN set, so it exercised the happy path and could not see this; the
# unset case is now checked in spikes/harness/test_loop_gate.sh.
#
# A lane is a process launched by run_loop.sh, which exports CALLSIGN. Nothing
# else on disk distinguishes one, so identity must come from the launch. No
# callsign means not a lane, and the loop contract does not apply.
if [ -z "${CALLSIGN:-}" ]; then
  exit 0
fi
LANE="$CALLSIGN"
EXIT_MARK=".loop_exit.${LANE}"
BLOCKS=".loop_blocks.${LANE}"

# 3 · Agent terminal signal — exact content, consumed on use.
#     Per-lane path first; bare .loop_signal still accepted because MISSION_LOOP
#     §7 documents it and live agents were started against that contract.
for SIGFILE in ".loop_signal.${LANE}" ".loop_signal"; do
  [ -f "$SIGFILE" ] || continue
  SIG=$(tr -d '[:space:]' < "$SIGFILE")
  case "$SIG" in
    LOOP-DONE|LOOP-HALT|LOOP-IDLE)
      printf '%s\n' "$SIG" > "$EXIT_MARK"
      mv -f "$SIGFILE" "${SIGFILE}.last"
      exit 0
      ;;
    *)
      rm -f "$SIGFILE"   # malformed signal: ignore it and block
      ;;
  esac
done

# 4 · Runaway fuse: cap blocked stops per TURN, not per session.
#     The comment said "per session" and was wrong: run_loop.sh clears
#     .loop_blocks.$CALLSIGN at every turn start, so 400 blocked stops would
#     have to occur inside ONE turn for this to blow. As written it cannot fire
#     for the runaway it exists to stop. Left per-turn and relabelled rather
#     than moved to per-session, because changing the semantics under two live
#     lanes is a cutover change; opened as H11.
N=$(cat "$BLOCKS" 2>/dev/null || echo 0); N=$((N+1))
echo "$N" > "$BLOCKS"
if [ "$N" -gt "${MAX_BLOCKS:-400}" ]; then
  echo LOOP-FUSE > "$EXIT_MARK"
  exit 0
fi

# 5 · Otherwise: refuse the stop, hand back the loop contract
cat <<'JSON'
{"decision":"block","reason":"Loop contract: stopping is unavailable. A legal exit requires writing exactly one of LOOP-DONE / LOOP-HALT / LOOP-IDLE into the file .loop_signal, and only under MISSION_LOOP section 7 conditions. Otherwise, in order: (1) refresh HANDOFF.md as the write-ahead checkpoint; (2) release stale CLAIMs in CHANNEL.md; (3) SELECT the highest-priority ungated unclaimed WORK_QUEUE item and run the next cycle. Quoting marker words in prose does nothing."}
JSON
exit 0
