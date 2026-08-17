#!/usr/bin/env bash
# test_loop_gate.sh — the check MISSION_LOOP §12.3 requires for the Stop hook.
#
# Written 2026-08-17 because the loop machinery had NO test of any kind while it
# was the only thing standing between the fleet and a silent stall. Two defects
# had already shipped undetected: the hook was registered in a directory the
# session never used (inert for a whole session), and the launcher decided the
# loop was over by grepping its own log for the marker words that the hook's own
# refusal message quotes.
#
# ISOLATION IS THE POINT. The hook pins ROOT to the real workspace and mutates
# .loop_signal / .loop_blocks / .loop_exit. Running the live hook to test it
# would consume a running lane's terminal signal and kill it. So this copies the
# hook, rewrites ROOT to a scratch dir, and exercises the copy. A test that can
# stop production is not a test.
#
# usage: bash spikes/harness/test_loop_gate.sh
# exit 0 = all pass. Non-zero = the loop contract is not enforceable as written.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="$ROOT/.claude/hooks/loop_gate.sh"
[ -f "$GATE" ] || { echo "FAIL: no hook at $GATE"; exit 1; }

T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
sed "s|^ROOT=.*|ROOT=\"$T\"|" "$GATE" > "$T/gate.sh"
chmod +x "$T/gate.sh"
cd "$T"

pass=0 fail=0
ok()   { pass=$((pass+1)); printf '  PASS  %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (want '$3', got '$2')"; fi; }

# blocked() prints "block" when the hook refuses the stop, "exit" when it allows it.
blocked() { if CALLSIGN="$1" ./gate.sh </dev/null 2>/dev/null | grep -q '"decision":"block"'; \
            then echo block; else echo exit; fi; }

echo "loop_gate.sh contract:"

# 1 · With no signal the loop must NOT be endable. This is the whole point of the
#     hook; if it ever returns exit here, every lane stops after one turn.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* STOP
check "no signal refuses the stop" "$(blocked L1)" "block"

# 2 · A valid per-lane signal must end the turn AND leave a marker run_loop.sh can
#     read. v2 consumed it to .loop_signal.last, which nothing read — that is why
#     the launcher resorted to grepping prose.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal.L1
check "per-lane signal ends turn"   "$(blocked L1)"                    "exit"
check "  leaves exit marker"        "$(cat .loop_exit.L1 2>/dev/null)" "LOOP-HALT"
check "  consumes the signal"       "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "gone"

# 3 · Bare .loop_signal must keep working: MISSION_LOOP §7 documents that path and
#     live agents were started against it. Backward compatibility is load-bearing,
#     not politeness.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-IDLE > .loop_signal
check "bare signal still honoured"  "$(blocked L1)"                    "exit"
check "  marker records the kind"   "$(cat .loop_exit.L1 2>/dev/null)" "LOOP-IDLE"

# 4 · Prose must never end a loop. The v1 hook grepped the transcript and fired on
#     a mere mention; anything not an exact marker is malformed and must be dropped.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo "done for now, writing LOOP-HALT next turn" > .loop_signal.L1
check "malformed signal refuses"    "$(blocked L1)" "block"
check "  malformed is removed"      "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "gone"

# 5 · §12.6 — lane isolation. L2 must not be able to exit on L1's signal.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal.L1
check "other lane cannot consume"   "$(blocked L2)" "block"
check "  victim's signal intact"    "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "present"
check "  no marker leaked to L2"    "$([ -f .loop_exit.L2 ] && echo leaked || echo none)"   "none"

# 6 · §12.6 — separate fuses. A shared counter trips at half the intended count per
#     lane and each lane's reset clears the other's.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
blocked L1 >/dev/null; blocked L1 >/dev/null; blocked L2 >/dev/null
check "fuses count per lane"        "$(cat .loop_blocks.L1 2>/dev/null)/$(cat .loop_blocks.L2 2>/dev/null)" "2/1"

# 7 · The runaway fuse must release the loop rather than block forever, and say why.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo 400 > .loop_blocks.L3
out=$(MAX_BLOCKS=400 CALLSIGN=L3 ./gate.sh </dev/null 2>/dev/null)
check "fuse releases the loop"      "$([ -z "$out" ] && echo exit || echo block)" "exit"
check "  fuse marker written"       "$(cat .loop_exit.L3 2>/dev/null)" "LOOP-FUSE"

# 8 · The human kill switch outranks everything, including a blocking state.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
touch STOP
check "STOP outranks the contract"  "$(blocked L4)" "exit"
rm -f STOP

# 9 · §12.6 FAIL CLOSED ON IDENTITY — the case v3 shipped broken and that THIS
#     TEST COULD NOT SEE, because every check above sets CALLSIGN. v3 defaulted
#     an absent callsign to lane "unknown", so a human at a terminal was gated
#     and told to run cycles, and every callsign-less session shared one fuse and
#     one exit marker with the fleet (observed live: .loop_blocks.unknown = 3,
#     incremented by a reviewer merely reading the repo). A lane is a process
#     run_loop.sh exported CALLSIGN into; nothing else on disk distinguishes one.
#     No callsign therefore means not a lane. Happy-path-only coverage is how a
#     15-check suite passed over this.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
nolane() { if env -u CALLSIGN ./gate.sh </dev/null 2>/dev/null | grep -q '"decision":"block"'; \
           then echo block; else echo exit; fi; }
check "no callsign is not gated"      "$(nolane)" "exit"
check "  writes no 'unknown' fuse"    "$([ -f .loop_blocks.unknown ] && echo wrote || echo none)" "none"
check "  writes no 'unknown' marker"  "$([ -f .loop_exit.unknown ] && echo wrote || echo none)"   "none"
check "  writes no fuse at all"       "$(ls .loop_blocks.* 2>/dev/null | wc -l | tr -d ' ')"      "0"

# 10 · An unidentified session must not consume a real lane's terminal signal.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal.L1
check "no callsign cannot steal exit" "$(nolane)" "exit"
check "  lane signal untouched"       "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "present"

# --- REGISTRATION, not just the script. Added 2026-08-17, ATTACK cycle 8.
# All 22 checks above invoke loop_gate.sh directly, so the suite went green while
# the repo-root registration pointed at "$CLAUDE_PROJECT_DIR/.claude/hooks/..."
# with CLAUDE_PROJECT_DIR unset -- an unresolvable path. Same class as §14.4's
# earned lesson: a suite that exercises the component and not its WIRING passes
# over the defect that stops the component from ever being called. §12.4 wants
# references resolved mechanically, and an env var in a hook path cannot be.
for sj in $(cd "$ROOT" && git ls-files '*.claude/settings.json'); do
  cmds=$(python3 - "$ROOT/$sj" <<'PYEOF'
import json, re, sys
print('\n'.join(re.findall(r'"command"\s*:\s*"([^"]+)"', open(sys.argv[1]).read())))
PYEOF
)
  for c in $cmds; do
    case "$c" in
      *'$'*) check "reg $sj resolves without env" "env-var-in-path" "literal-path" ;;
      *) if [ -x "${c%% *}" ]; then ok "reg $sj -> $(basename "${c%% *}") exists"
         else bad "reg $sj points at a missing or non-executable file: $c"; fi ;;
    esac
  done
done

echo
if [ "$fail" -eq 0 ]; then
  echo "loop_gate.sh: ${pass} checks pass"
  exit 0
fi
echo "loop_gate.sh: ${fail} FAILED, ${pass} passed — the loop contract is not enforceable as written"
exit 1
