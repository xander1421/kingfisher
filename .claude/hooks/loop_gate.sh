#!/usr/bin/env bash
# loop_gate.sh v8 — Stop hook for MISSION_LOOP continuous mode.
# v7 (ok-1, H13) locks the span-cap increment; see section 4's block.
# v8 (ok-1, H11) renames that counter: it is a SPAN CAP, not a runaway
# fuse. Measured, not renamed by taste -- section 4 carries the numbers.
# v9 (ok-1, H219) teaches section 1 the PER-LANE kill switch. See section 1b.
# Terminal signals are FILES, not prose: to end legally, the agent must
# write exactly LOOP-DONE, LOOP-HALT, or LOOP-IDLE into .loop_signal.$CALLSIGN.
# Bare .loop_signal is NO LONGER ACCEPTED -- see v5 below.
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

# 1 · Human kill switch, FLEET-WIDE (never auto-removed; human rm's it to resume)
# The per-lane spelling is section 1b, below the callsign guard, because the lane
# name has not been established or validated yet at this point in the file.
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
# v6 defect 2: LANE is interpolated into filenames and into the JSON below.
# Whitelist, because a blacklist of path and quote metacharacters is the kind of
# thing that is right until someone finds the character it forgot.
case "$LANE" in (*[!A-Za-z0-9._-]*) exit 0 ;; esac

# 1b · PER-LANE kill switch. v9, 2026-08-19 (ok-1, H219).
#
# THE DEFECT: `STOP.$CALLSIGN` retires ONE lane (H31, DONE 2026-08-17) and was
# taught to `run_loop.sh:433` and to both bring-ups. It was NOT taught to this
# hook -- section 1 read the fleet-wide `STOP` and nothing else, which was this
# file's only STOP read. H31 was verified against the launcher FILE and never
# against the hook, so the row closed with half its switch installed. §12.2, the
# site and not the class, inside a row whose whole subject is per-lane state.
#
# WHY IT COSTS A WHOLE TURN AND NOT A MOMENT, measured in
# spikes/H219_stop_asymmetry/probe.out:
#   * fleet-wide STOP  -> the hook ALLOWS the stop on attempt 0;
#   * STOP.L1, same lane -> REFUSED 20 times out of 20, span cap climbing to 20.
# The launcher's ONLY stop read is its `while` condition (`run_loop.sh:433`,
# grepped, 1 of 1), so it is consulted BETWEEN turns -- and this hook is the
# only thing that ends a turn. A lane under a per-lane stop is therefore told to
# run another cycle every time it tries to stop, and the retirement arrives when
# MAX_TURN's watchdog kills the turn (default 3600 s), logged as a wedged turn
# rather than as a retirement. The operator's documented way to retire one lane
# (`MISSION.md:303`) was an hour late and looked like a fault.
#
# ORDER IS DELIBERATE: this is BELOW the whitelist above, because $LANE is
# interpolated into a filename here exactly as it is into EXIT_MARK and BLOCKS.
# NOT A GLOB: `STOP.*` or `STOP*` would let one lane's retirement stop all five,
# which is the H31 defect restored from the other end. probe.sh arm A4 asserts
# another lane's STOP.L2 leaves L1 running, and the suite carries the same check.
[ -f "STOP.${LANE}" ] && exit 0

EXIT_MARK=".loop_exit.${LANE}"
BLOCKS=".loop_blocks.${LANE}"

# 3 · Agent terminal signal — exact content, consumed on use.
#
# v5, 2026-08-17: BARE .loop_signal IS NO LONGER ACCEPTED, and its acceptance was
# a live lane-isolation hole for three versions. Reproduced by a reviewer:
#
#   echo LOOP-HALT > .loop_signal    # exactly what MISSION_LOOP §7 instructed
#   CALLSIGN=L2 ./gate.sh   -> EXIT, writes .loop_exit.L2, consumes the signal
#   CALLSIGN=L1 ./gate.sh   -> BLOCKED, no marker, signal already gone
#
# L2 exits in L1's place and L1 can then never exit. §12.6 was satisfied in the
# naming and defeated by the compatibility branch. Worse, ATOM-3 broadcast to the
# whole fleet that isolation was "now per-callsign, and there is a test that fails
# if lane isolation regresses" -- check 5 tested only the per-lane path, and
# check 3 certified the UNSAFE path worked without ever testing its isolation.
#
# The deferral was circular: H9 kept the branch because §7 documented it, and §7
# kept documenting it because the code accepted it. Both sides are cut in the
# same edit. §7 now instructs the per-lane path only.
for SIGFILE in ".loop_signal.${LANE}"; do
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

# 4 · SPAN CAP: bound the number of blocked stops inside ONE `claude -p`.
#     Called a "runaway fuse" from v1 to v7 and that name is withdrawn (v8,
#     ok-1, H11, 2026-08-17). MISSION_LOOP §7 already describes what it really
#     is -- "LOOP-FUSE ... means a session span ended, not that work finished"
#     -- and the two descriptions had been sitting in the tree disagreeing.
#
#     WHAT IT COUNTS, measured in `spikes/H11_fuse_scope/probe.out`, three arms:
#       * inside one span the counter climbs 1,2,3,4,5 and LOOP-FUSE is written
#         past MAX_BLOCKS -- the mechanism works where it is driven;
#       * across spans it does NOT accumulate. run_loop.sh:387 clears it at every
#         span start, so three spans of two turn ends each read 2, 2, 2 -- not 6;
#       * IN A CRASH LOOP IT NEVER MOVES AT ALL. The counter is ABSENT at every
#         observation across three spans in which `claude` exits instantly, while
#         .loop_fails reaches 3.
#
#     That last arm is the row. A blocked stop exists only when the agent RAN and
#     tried to end a turn, so a span in which claude never starts increments
#     nothing -- and that is the only runaway this fleet has actually recorded:
#     18 consecutive instant-exit spans on "You've hit your session limit" (H56,
#     14:29-15:56, five lanes). This counter was blind to all 86 minutes of it.
#
#     NOT FIXED BY MAKING IT PERSIST, and that is the whole decision: per-span is
#     the correct scope for a per-span bound, and the cross-span counter already
#     exists as a DIFFERENT mechanism -- `.loop_fails.$CALLSIGN`, written by
#     run_loop.sh v9 (defect 12) and read by bringup.sh, which refuses quorum on
#     it. Two counters, two scopes, and the defect was one of them wearing the
#     other's name. Pinned by test_loop_gate.sh so the scope cannot drift back.
# A non-numeric counter used to be written back unchanged, so bash arithmetic
# errored, the -gt comparison errored, and the hook fell through to block --
# permanently, with a fuse that could never trip. `printf '3x' > .loop_blocks.L5`
# reproduced it. Anything not all-digits is treated as absent.
#
# v7, 2026-08-17 (ok-1, H13). THE INCREMENT WAS AN UNSYNCHRONISED READ-MODIFY-
# WRITE and lost most of what it counted. Measured on this tree before the fix:
# 20 concurrent fires for one lane landed on 12, 13 and 14 across three runs, and
# 60 fires landed on 28 -- so the fuse blows LATE, at roughly twice its nominal
# MAX_BLOCKS, which is the direction that lets a runaway run on. `mkdir` is the
# portable atomic test-and-set; macOS ships no flock(1). The lock is around the
# RMW only, so the file stays a plain decimal count and checks 6, 7 and 12 --
# per-lane counting, the 400-seeded fuse release, and corrupt-file recovery --
# test exactly what they tested before.
#
# FAIL OPEN, deliberately, and this is the part that matters more than the
# counting. A shared gate that can wedge every lane is a worse defect than the
# one being fixed (H9, H11): after ~1s of spinning we clear the lock and proceed
# UNLOCKED, degrading to the v6 behaviour rather than refusing to return. The
# only way a holder keeps this for a second is that it died inside two shell
# commands, so removing it is the correct reading of that state, not a guess.
LOCK="${BLOCKS}.lock"
held=no
i=0
while [ "$i" -lt 50 ]; do
  if mkdir "$LOCK" 2>/dev/null; then held=yes; break; fi
  i=$((i+1)); sleep 0.02
done
[ "$held" = no ] && rm -rf "$LOCK"
N=$(cat "$BLOCKS" 2>/dev/null || echo 0)
case "$N" in (''|*[!0-9]*) N=0 ;; esac
N=$((N+1))
echo "$N" > "$BLOCKS"
[ "$held" = yes ] && rmdir "$LOCK" 2>/dev/null
if [ "$N" -gt "${MAX_BLOCKS:-400}" ]; then
  echo LOOP-FUSE > "$EXIT_MARK"
  exit 0
fi

# 5 · Otherwise: refuse the stop, hand back the loop contract
#
# v6, 2026-08-17 (H16): THIS MESSAGE NAMED A PATH THIS HOOK NO LONGER ACCEPTS.
# It said "into the file .loop_signal" -- the bare name v5 removed one section
# above, in the same file, in the same edit that stopped §7 instructing lanes
# into it. A lane obeying the refusal verbatim writes .loop_signal, section 3
# never looks at it, and the lane cannot exit at all. H9 was recorded DONE with
# this live: the deferral was called circular and cut on the §7 side only, which
# is §12.2 -- the site, not the class -- inside the fix for a class defect.
# The path is now interpolated from $LANE, so it cannot drift from the path
# section 3 reads. test_loop_gate.sh extracts the path out of this string,
# writes a signal to exactly it, and requires the hook to honour it: an
# instruction the hook gives must be an instruction the hook obeys.
printf '{"decision":"block","reason":"Loop contract: stopping is unavailable. A legal exit requires writing exactly one of LOOP-DONE / LOOP-HALT / LOOP-IDLE into the file .loop_signal.%s , and only under MISSION_LOOP section 7 conditions. Otherwise, in order: (1) refresh HANDOFF.md as the write-ahead checkpoint; (2) release stale CLAIMs in CHANNEL.md; (3) SELECT the highest-priority ungated unclaimed WORK_QUEUE item and run the next cycle. Quoting marker words in prose does nothing."}\n' "$LANE"
exit 0
