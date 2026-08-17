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
# ASSERT THE ANCHOR MATCHED. Without this the sed can silently no-op -- the exact
# defect CLAUDE.md's Editing section warns about, where a replacement whose anchor
# is absent returns the input unchanged. A no-op here would point the copy at the
# REAL workspace and eat a running lane's terminal signal, which is precisely what
# the isolation note at the top of this file claims to prevent. Found by a fresh
# reviewer 2026-08-17: "the guard that remains".
grep -q "^ROOT=\"$T\"$" "$T/gate.sh" || {
  echo "FAIL: ROOT anchor did not match; refusing to run the live hook"; exit 1; }
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

# 3 · BARE .loop_signal MUST BE REFUSED (v5). This check previously asserted the
#     opposite and thereby CERTIFIED THE HOLE: with a shared bare signal, whichever
#     lane's hook fires first consumes it, writes its own exit marker, deletes the
#     file, and the lane that actually wrote it can then never exit. Check 5 tested
#     isolation only on the per-lane path, so the suite proved the unsafe path
#     WORKED and never asked whether it was safe. Reproduced by a fresh reviewer;
#     ATOM-3 had meanwhile told the fleet isolation was "per-callsign, and there is
#     a test that fails if lane isolation regresses". This is now that test.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-IDLE > .loop_signal
check "bare signal is REFUSED"      "$(blocked L1)"                                        "block"
check "  no marker written"         "$([ -f .loop_exit.L1 ] && echo wrote || echo none)"   "none"

# 3b · And the theft itself: a bare signal must not let ANOTHER lane exit in the
#      place of the lane that wrote it.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal
check "L2 cannot exit on a bare signal" "$(blocked L2)"                                      "block"
check "  L1 can still exit properly"    "$(echo LOOP-HALT > .loop_signal.L1; blocked L1)"    "exit"

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

# 11 · §12.6 CONCURRENCY. The fuse is `N=$(cat); N=$((N+1)); echo $N >` — an
#      unsynchronised read-modify-write. A reviewer measured 20 concurrent fires
#      for one lane landing on 5. Every check above is a single sequential
#      invocation, so a suite written FOR a two-lanes-share-state defect contained
#      no concurrency at all. This does not fix the race; it MEASURES it, so the
#      undercount is recorded rather than discovered later by someone trusting the
#      count. Marked as a known ceiling, not a pass.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
for i in $(seq 1 20); do ( CALLSIGN=L9 ./gate.sh </dev/null >/dev/null 2>&1 ) & done
wait
conc=$(cat .loop_blocks.L9 2>/dev/null || echo 0)
if [ "$conc" -eq 20 ]; then ok "fuse counts 20/20 under concurrency"
else printf '  KNOWN  fuse undercounts under concurrency: %s/20 (unsynchronised RMW, WORK_QUEUE H13)\n' "$conc"; fi

# 12 · A non-numeric counter used to be written back unchanged, so the arithmetic
#      errored, the comparison errored, and the hook fell through to block —
#      permanently, with a fuse that could never trip.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
printf '3x' > .loop_blocks.L5
blocked L5 >/dev/null
check "corrupt fuse file recovers"  "$(cat .loop_blocks.L5 2>/dev/null)" "1"

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

# --- THE REFUSAL MESSAGE IS AN INSTRUCTION, so test it as one. H16, 2026-08-17.
# v5 removed the bare .loop_signal path and edited §7 to stop pointing lanes into
# it, and left the hook's OWN refusal text still saying "into the file
# .loop_signal". A lane obeying it verbatim writes a file section 3 never reads
# and can never exit. Not a grep for the string (A30: a name grep cannot tell a
# word from a concept) -- the path is extracted from the message the hook just
# emitted, a signal is written to exactly that path, and the hook must honour it.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
refusal=$(CALLSIGN=L7 ./gate.sh </dev/null 2>/dev/null)
sigpath=$(printf '%s' "$refusal" | grep -o '\.loop_signal[^ ,"]*' | head -1)
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
if [ -z "$sigpath" ]; then
  bad "refusal message names no signal path at all"
else
  echo LOOP-HALT > "$sigpath"
  check "refusal names a path the hook obeys ($sigpath)" "$(blocked L7)" "exit"
fi

# --- THE LAUNCHER, driven end to end. H16, 2026-08-17.
# A TERMINAL SIGNAL THAT OUTLIVES ITS SPAN. run_loop.sh cleared .loop_blocks and
# .loop_exit at turn start and not .loop_signal.$CALLSIGN, so a signal from a
# previous span was consumed at the NEXT span's first turn end and the lane
# exited having done no work. Observed live on AGENT-1: LOOP-HALT written at
# 11:30 under STOP, and the hook's STOP branch returns before it consumes a
# signal, so the file was still armed when the operator lifted STOP.
# Driven with a stub claude rather than asserted by grep, because the property is
# "a stale signal does not reach the turn", not "this line contains that word".
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
mkdir -p bin
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
# stub claude: report whether a stale terminal signal survived into the turn,
# then hand the launcher a legal exit so the test finishes in one iteration.
[ -f ".loop_signal.${CALLSIGN}" ] && echo SURVIVED > stale_reached_turn
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
cp "$ROOT/run_loop.sh" ./run_loop.sh
echo LOOP-HALT > .loop_signal.L8            # the previous span's leftover
rm -f stale_reached_turn
PATH="$T/bin:$PATH" CALLSIGN=L8 MAX_TURN=5 bash ./run_loop.sh >/dev/null 2>&1
check "launcher clears a stale signal before the turn" \
      "$([ -f stale_reached_turn ] && echo reached || echo cleared)" "cleared"
rm -f .loop_signal* .loop_exit.* .loop_blocks.* stale_reached_turn run_loop.sh loop_L8.log

# --- THE COMMIT GATE IS WIRED IN AN UNTRACKED DIRECTORY. ATTACKER-1, H7.
# Same class as the settings.json block above (a wiring reference nothing
# resolves), one layer down. `.git/hooks/` is not tracked and cannot be, so the
# only ENFORCING gate in the repo is absent from every clone and worktree, and
# `spikes/harness/commit-msg.hook` had no installer and no reference anywhere in
# the tree. Editing the source changed the reviewed artifact and not the
# enforced one. Install with `sh spikes/harness/install_hooks.sh`.
hookdir=$(cd "$ROOT" && git rev-parse --git-path hooks 2>/dev/null)
case "$hookdir" in /*) ;; *) hookdir="$ROOT/$hookdir" ;; esac
src="$ROOT/spikes/harness/commit-msg.hook"
if [ ! -f "$src" ]; then
  bad "commit-msg.hook source is missing from spikes/harness"
elif [ ! -x "$hookdir/commit-msg" ]; then
  bad "commit gate NOT INSTALLED at $hookdir/commit-msg (sh spikes/harness/install_hooks.sh)"
elif ! cmp -s "$src" "$hookdir/commit-msg"; then
  bad "installed commit gate has DRIFTED from its tracked source"
else
  ok "commit gate installed and identical to its tracked source"
fi

# --- THE COMMIT GATE MUST REFUSE ANOTHER LANE'S FILES. ATTACKER-1, H19.
# Three lanes share one git index and `git commit` takes the index, not your
# adds, so a correctly-scoped `git add` by one lane lands in the next lane's
# commit under ITS Atom: trailer. Observed: b529081, `Atom: AGENT-1`, carrying
# HANDOFF.ATTACKER-1.md and 840 lines of a second lane's cycle.
# Driven against a throwaway repo, because the property is "the hook refuses
# this staged set", and a grep for the rule would pass over a hook that had it
# written down and unreachable.
grepo="$T/gaterepo"; rm -rf "$grepo"; mkdir -p "$grepo"
( cd "$grepo" && git init -q && git config user.email t@t && git config user.name t )
cp "$ROOT/spikes/harness/commit-msg.hook" "$grepo/hook.sh"; chmod +x "$grepo/hook.sh"
gatemsg() { printf 'subject line\n\nAtom: MINE-1\nClaude-Session: x\nReviewed-By: unreviewed\n%s\n' "$1" > "$grepo/msg"; }
gaterun() { ( cd "$grepo" && sh ./hook.sh msg >/dev/null 2>&1 ) && echo accept || echo refuse; }

( cd "$grepo" && : > HANDOFF.OTHER-9.md && git add HANDOFF.OTHER-9.md )
gatemsg ''
check "commit gate refuses another lane's journal"  "$(gaterun)" "refuse"
# Declared deliberately, so it must pass -- otherwise the only way to repair
# another lane's file is --no-verify, which bypasses the trailer gates too.
gatemsg 'Carries: OTHER-9'
check "  ... unless Carries: names it"              "$(gaterun)" "accept"
# POSITIVE CONTROL. A gate that refuses everything is not a gate; this is the
# input that separates "it checks ownership" from "it always says no".
( cd "$grepo" && git rm -q --cached HANDOFF.OTHER-9.md && : > HANDOFF.MINE-1.md \
  && git add HANDOFF.MINE-1.md )
gatemsg ''
check "  ... and accepts the atom's OWN journal"    "$(gaterun)" "accept"
rm -rf "$grepo"

# --- A CALLSIGN IS AN UNTRUSTED STRING. ATTACKER-1, H7, 2026-08-17.
# The hook interpolates $LANE into .loop_exit.$LANE, .loop_blocks.$LANE and --
# since H16 rewrote section 5 at 11:52 -- into the refusal JSON itself. Nothing
# validated its shape. MEASURED against the pre-fix hook: CALLSIGN='L"6' emits
#   {"decision":"block","reason":"...file .loop_signal.L"6 , and only..."}
# which is JSONDecodeError at char 178, so the harness cannot read the block
# decision and the refusal is lost -- the lane stops for the reason the whole
# hook exists to prevent. Reachable only after H16; the fix for the refusal
# message opened an injection INTO the refusal message.
#
# ALSO RECORDED, because a negative result that is not printed gets re-asserted:
# CALLSIGN='/../escaped' does NOT write outside the directory. ATTACKER-1 stated
# that it did, then ran it: `.loop_exit.` + `/../escaped` needs the directory
# `.loop_exit.` to exist, it does not, the redirect fails, 0 files escaped. The
# whitelist still excludes it, but on the JSON evidence, not the traversal.
#
# The property, not the remedy: whatever the hook DECIDES for a hostile
# callsign, its output must be readable. A check that asserted `exit 0` would
# have to be rewritten by anyone who chose to escape the string instead.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* pwned
for cs in 'L"6' 'L\6' 'L 6' '../L6' '$(touch pwned)' 'L`6' 'L
6'; do
  out=$(CALLSIGN="$cs" ./gate.sh </dev/null 2>/dev/null)
  label=$(printf '%s' "$cs" | tr -d '\n')
  if [ -z "$out" ]; then
    ok "hostile callsign refused: $label"
  elif printf '%s' "$out" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
    ok "hostile callsign still emits valid JSON: $label"
  else
    bad "hostile callsign emits an UNPARSEABLE decision: $label"
  fi
done
check "  no callsign was executed"  "$([ -f pwned ] && echo ran || echo none)" "none"
# The hook refuses a malformed callsign SILENTLY -- it exits 0, which is correct
# for a non-lane and catastrophic for a real one: the lane spawns and runs with
# no loop contract at all, unsupervised, looking normal. So the launcher must
# refuse the same shapes LOUDLY, at the one place a human is watching. Both ends
# of the whitelist, or the fix is worse than the defect.
#
# THE STUB IS NOT OPTIONAL. Written first without it, and when its falsifier
# disarmed the guard the launcher fell through to `command -v claude`, found the
# REAL one, and spawned a live agent on the callsign L"6 -- a test that starts
# production, minutes after this file's own header says a test that can stop
# production is not a test. Killed by hand; nothing reached CHANNEL. So the stub
# shadows claude on PATH and the check ALSO asserts the launcher never got that
# far, which is the property that makes the test safe rather than merely lucky.
mkdir -p bin
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo reached > launcher_reached_claude
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"     # let the launcher finish in one pass
STUB
chmod +x bin/claude
cp "$ROOT/run_loop.sh" ./rl.sh
rm -f launcher_reached_claude
PATH="$T/bin:$PATH" CALLSIGN='L"6' MAX_TURN=5 bash ./rl.sh >/dev/null 2>&1
rc=$?
check "  launcher refuses what the hook will not gate" "$rc" "1"
check "  launcher never reached claude"                                      \
      "$([ -f launcher_reached_claude ] && echo spawned || echo none)" "none"
rm -f ./rl.sh launcher_reached_claude 'loop_L"6.log' .loop_exit.* .loop_blocks.*
check "  hostile callsigns left no state" \
      "$(ls .loop_exit.* .loop_blocks.* 2>/dev/null | wc -l | tr -d ' ')" "0"
rm -f pwned

echo
if [ "$fail" -eq 0 ]; then
  echo "loop_gate.sh: ${pass} checks pass"
  exit 0
fi
echo "loop_gate.sh: ${fail} FAILED, ${pass} passed — the loop contract is not enforceable as written"
exit 1
