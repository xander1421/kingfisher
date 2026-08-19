#!/usr/bin/env bash
# test_loop_gate.sh v8 — the check MISSION_LOOP §12.3 requires for the Stop hook.
#
# v8 RATIONALE (§12.7) — ok-1, H232, 2026-08-19. DEFECT REMOVED: THIS SUITE
# TESTED THE CALLSIGN LOCK AT t=0 AND NOWHERE ELSE. The H8 block below drives 20
# simultaneous launchers and asserts ONE survivor, which is acquisition; nothing
# read the lock again, and run_loop.sh v10 had zero reads of $LOCK inside its turn
# loop, so a launcher that had LOST the lock kept producing turns forever. Live
# that day: `ok-1` on two launcher roots with one lock. The new block drives both
# directions -- a live foreign holder must retire the launcher, an ABSENT lock
# must be re-acquired rather than kill the lane -- and carries a precondition
# check, because "stopped producing turns" is otherwise passed by a launcher that
# never started (a 644 copy dies at `nohup "$0"`, measured).
#
# v7 RATIONALE (§12.7) — ok-1, H219, 2026-08-19, ATTACK cycle 30 (§12.8: the loop
# itself). DEFECT REMOVED: THIS SUITE COULD NOT SEE THAT THE PER-LANE KILL SWITCH
# WAS UNIMPLEMENTED IN THE ONE COMPONENT THAT ENDS A TURN. `STOP.$CALLSIGN` was
# taught to `run_loop.sh:433`, to both `bringup.sh` copies and to `MISSION.md:303`
# as the operator's documented way to retire ONE lane (H31) — and never to the
# hook. v6 mentioned the string only inside a LAUNCHER-span fixture, never as a
# hook input, so section 8 asserted the fleet-wide `STOP` and read as covering the
# switch. Measured pre-fix, `spikes/H219_stop_asymmetry/probe_prefix.out`: the
# hook refused `STOP.L1` under lane L1 **20 times out of 20** while fleet-wide
# `STOP` was honoured on attempt 0, so a per-lane retirement arrived only when
# `MAX_TURN`'s watchdog (3600 s) killed the turn — logged as a wedged turn, not as
# a retirement. Section 8b drives both directions and reads the ORDER out of the
# gate, and `spikes/harness/test_h219_falsify.sh` reddens each of the three.
# CLASS (§12.2): a per-lane state name taught to one reader while a second reader
# of the same state keeps the global-only spelling. Third instance — bare
# `.loop_signal` (hook v5) and one shared `.loop_blocks` are the first two, both
# in this hook's own header.
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
# v2 RATIONALE (§12.7, and this file had never carried a version at all, which is
# why the header records defects by date instead) — ok-1, H29, 2026-08-17.
# TWO DEFECTS REMOVED, both in the LAUNCHER-DRIVEN blocks, both measured before
# the repair in `spikes/H29_detach_race/probe.py` / `probe.out`:
#   1. The hostile-callsign block was INERT. Its only assertions were rc=1 and an
#      artifact absence, and `run_loop.sh` refuses in gate order -- charset,
#      roster, brief -- so with the charset whitelist neutered the brief gate
#      exited 1 instead and the block stayed green. `falsify.py F8` had been
#      printing INERT since the brief gate landed (H30) and nothing read it,
#      because nothing runs the driver automatically -- which is H29 itself.
#      CLASS: rc=1 does not say WHICH gate refused.
#   2. Four assertions were ABSENCE OF AN ASYNCHRONOUS EVENT read at the parent's
#      exit. The launcher forks and the child acts later, so the not-yet-run child
#      hands back the PASSING answer. They land green today only because
#      run_loop.sh happens to `sleep 1` after its fork: delete that line and
#      `it never reached the turn` passes over a live defect. Each block now also
#      asserts on the parent's own detach ANNOUNCEMENT, which is synchronous.
#      CLASS: an absence assertion that could be won by being early.
# Not fixed here and filed instead: removing that same `sleep 1` takes the
# 20-launcher lock check from 1 survivor to 4, so the launcher's parent->child
# lock handoff is synchronised by a timing constant whose comment gives it an
# unrelated purpose. That is a defect in `run_loop.sh`, not in this suite.
#   CORRECTED 2026-08-17 (ok-1, H61), against the sentence above: the timing
#   constant is real and what it hides is NOT a lost mutual exclusion. Deleting
#   it is an EDIT, and no load reproduced a double admission across 8 arms
#   (`spikes/H61_lock_handoff/probe_v3.out`). What the constant hides is that a
#   launcher arriving in the handoff window is refused BY ITS OWN CHILD, into
#   detach_$CALLSIGN.log, after the parent printed `detached` and exited 0 — a
#   launch failure reported as a success. And the 20-launcher block cited above
#   reads 1 survivor / 19 parent refusals with the defect present AND absent, so
#   it never covered this; the STAGGERED block at the bottom of this file does.
#
# v3 RATIONALE (§12.7) — ok-1, H61, 2026-08-17. ONE DEFECT REMOVED: this suite's
# only lock check could not distinguish the two states of the launcher's lock
# handoff, while the row that named the defect cited it as the check that would
# catch it. 75 -> 80 checks; the new block asserts WHERE a refusal is printed.
#
# v4, H178 + H191 — ok-1, 2026-08-19. THREE DEFECTS REMOVED. Written as ONE when
# the block was drafted and corrected here, because the other two were found by
# this row's own probe AFTER the header was written, and a header that
# contradicts its file is §12.5's class.
#   (a) the accounting control below, detailed at length;
#   (b) `badt` split by NAME rather than by INPUT, so an all-live-tree run
#       reported itself as MIXED — the wrong-attribution error produced by the
#       split built to prevent it. Rule now stated at the definition site:
#       a verdict is `badt` iff its INPUT is the shared working tree.
#   (c) H191, the settings.json registration loop: `for c in $cmds` splits on
#       WHITESPACE while its records are NEWLINE-delimited, so one registration
#       carrying arguments became three failures naming `python3` as missing.
#       Detail at the site; the defeated `${c%% *}` guard is the evidence.
# (a) IN FULL: A QUANTITY THAT ENTERS A VERDICT ONLY THROUGH A SUM HAS NO VERDICT
# OF ITS OWN, so an error in it is exactly cancellable by an equal and opposite
# error in the other addends. The H61 block asserted `h61_parent` (=1) and
# `h61_child` (=0) individually and then asserted `h61_surv + h61_parent +
# h61_child` = 2 — and `h61_surv`, the count of launchers that actually reached
# the turn, appeared NOWHERE ELSE. MEASURED, not reasoned: the captured red run
# `spikes/H178_suite_flake/failing_run_4.txt` reads
#     FAIL  H61: ... refused BY THE PARENT (want '1', got '2')
#     PASS    every launcher is accounted for
# on the same fixture, seven lines apart. The true state was 0 admitted and 2
# refused — NO LANE STARTED AT ALL — and the accounting control, whose comment
# says it exists so that "a launcher that is neither admitted nor refused
# invalidates both counts", passed on it because 0+2+0 = 1+1+0.
#   CLASS, for the fleet-wide grep: an asserted expression whose operands are not
#   each separately asserted. `grep -n 'check .*\$((' spikes/harness/*.sh` finds
#   exactly two sites, both here. The sibling at the 20-launcher block is SOUND
#   and is left alone: its survivor count and its refusal count are each pinned
#   by their own `check` above the sum, which is precisely what this block was
#   missing. So the repair is one added assertion, not a rewritten control.
# NOT FIXED HERE AND FILED INSTEAD (H189): *why* both launchers were refused.
# One capture in 19 observed runs. The mechanism is unresolved and the new
# assertion is what will name it next time instead of hiding it in a sum.
#
# v5, H23 — ok-1, 2026-08-19. ONE DEFECT CLASS COVERED, and the row's own F1 is
# the scope: AN INSTRUCTION THE COMPONENT DOES NOT OBEY. Not a dangling citation
# (refcheck check 4 covers those) — an interface removed or renamed while a
# surviving site still INSTRUCTS callers to use it, living where nobody looks for
# rules: a runtime's output string, a journal's "how to stop" line.
#   THE GENERAL FORM WAS MEASURED AND REJECTED, not skipped. Three candidate
# detectors over all 45 harness files, evidence in
# `spikes/H23_instruction_obeyed/`: any-path-in-a-message is 41% false positives
# (13 of 32 hits are a suite's own scratch fixtures — H14's checker-everyone-
# ignores); marker-must-appear-in-code is 28 of 30 hyphenated English and one
# `echo LOOP-FUSE > "$EXIT_MARK"` that my classifier counted as a message rather
# than a file WRITE; interpreter-plus-path has 3 sites fleet-wide and 0 finds.
#   So the six checks at the bottom of this file take the exact site the row
# names: the hook's refusal message must promise the vocabulary the hook accepts,
# both read out of the SAME file. The mutation control removes one marker from a
# copy's accept branch and the check goes red, so it is a control with its input
# named. 93 -> 99 checks.
#
# v6, H202 — ok-1, 2026-08-19, ATTACK cycle on this file's own v5. ONE DEFECT
# REMOVED AND IT IS A HOLE IN THIS SUITE, not in the hook: OF §7's THREE TERMINAL
# SIGNALS ONLY `LOOP-HALT` WAS EVER DRIVEN END TO END. `LOOP-IDLE` appeared once,
# at the bare-signal check, where the expected answer is `block` — so a hook that
# had stopped accepting it produces the same `block` and that check passes.
# `LOOP-DONE`, THE SIGNAL THAT ENDS THE MISSION, appeared nowhere except inside
# v5's own mutation string. A hook refusing either would have passed every check,
# for the whole life of the suite whose subject is the loop's exit contract.
#   CLASS: A SUITE THAT EXERCISES ONE MEMBER OF A VOCABULARY AND READS AS COVERING
#   THE VOCABULARY. This file's own history is the precedent — the 15-check version
#   passed while the hook was broken because every check set CALLSIGN.
#   FIXED AT THE CLASS: both signals are now driven (2b), and a guard requires
# EVERY marker the hook accepts to have been driven. The guard records what was
# driven AT RUNTIME via drive(), because its first draft grepped this file for
# `echo <MARKER> > .loop_signal.<lane>` and found nothing — the drives are
# parameterised, so the literal is never in the text. A text check cannot see a
# loop.
#   AND THE GUARD HAS A RUNNABLE FALSIFIER, `spikes/harness/test_h202_falsify.sh`:
# a hook carrying a FOURTH marker must turn it red and must name it. That needed
# the `KF_TEST_GATE` seam, defaulted off and asserted so two lines below its
# definition. 99 -> 107 checks.
#
# usage: bash spikes/harness/test_loop_gate.sh
# exit 0 = all pass. Non-zero = the loop contract is not enforceable as written.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# H202. A SEAM, defaulted OFF, so the coverage guard below has a runnable
# falsifier -- `test_h202_falsify.sh` points this at a hook carrying a FOURTH
# marker and requires the suite to go red naming it. Same shape and same reason as
# KF_TEST_HOOKDIR above; a check that has never been shown to fail is not a check
# (§5), and the guard's only red run so far was an accident during its own
# development. The control that keeps the seam honest is two lines below.
GATE="${KF_TEST_GATE:-$ROOT/.claude/hooks/loop_gate.sh}"
[ -f "$GATE" ] || { echo "FAIL: no hook at $GATE"; exit 1; }

# THE SEAM IS OFF IN EVERY REAL RUN, asserted rather than intended. A seam that
# silently stayed on would point this whole suite at a fixture and every check
# below would be about a file nobody ships.
[ -n "${KF_TEST_GATE:-}" ] || [ "$GATE" = "$ROOT/.claude/hooks/loop_gate.sh" ] || {
  echo "FAIL: KF_TEST_GATE is unset but GATE is not the shipped hook"; exit 1; }

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

# EVERY LAUNCHER-DRIVEN CHECK BELOW NEEDS A SPAWN BRIEF, and finding that out is
# the reason this block exists. run_loop.sh v5 (H30) made an absent
# prompts/$CALLSIGN.md a refusal ABOVE the detach, so from that commit on, every
# check that drives the launcher on a scratch callsign was refused before it ran
# a turn -- and the assertions are all of the shape "the turn did not do X", so
# they stayed GREEN while testing nothing. Measured, not reasoned: the H8 checks
# added at the bottom of this file went 1 PASS / 3 FAIL against a launcher that
# was refusing every case for this reason, and the one PASS was the false one.
# A29: a probe that cannot show it reached its target has produced no evidence.
# AND THE SUITE INHERITS THE LAUNCHER'S OWN RECURSION GUARD. run_loop.sh exports
# KF_DETACHED=1 before forking, `claude -p` inherits it, and every shell an agent
# opens inherits it again -- so when this suite is run BY A LANE (which is the
# only way it is ever run) every launcher-driven check below took the
# already-detached path, while a human running the same file exercised the other
# one. Two different tests behind one name, decided by who typed the command.
# Unset here rather than per-invocation so no future check can forget it; the
# defect in the launcher itself is H34 and is fixed there too.
unset KF_DETACHED KF_LOCK_OWNER

mkdir -p prompts
for lane in L1 L2 L3 L4 L5 L6 L7 L8 L9; do
  printf '# %s — scratch lane brief for test_loop_gate.sh\n' "$lane" > "prompts/$lane.md"
done

pass=0 fail=0 treefail=0
ok()   { pass=$((pass+1)); printf '  PASS  %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
# H178 (ok-1, 2026-08-19). MOST OF THIS SUITE RUNS IN $T. A MINORITY READS THE
# SHARED WORKING TREE -- installed gates vs their sources, and every tracked
# settings.json -- and four other lanes edit those files as their NORMAL
# mid-cycle state. So a red run has two very different meanings and printed one
# sentence for both: "the loop contract is not enforceable as written", when the
# actual event may be that another lane is between an edit and a reinstall.
# NOT WEAKENED: `badt` fails the suite exactly as `bad` does -- the drift checks
# are H36's and they are the ones that matter. It is COUNTED SEPARATELY so a red
# run says which kind it is, in the summary, without reading 91 lines.
badt() { fail=$((fail+1)); treefail=$((treefail+1)); printf '  FAIL  %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (want '$3', got '$2')"; fi; }
# v4, H178. CORRECTED BY THIS ROW'S OWN PROBE, IN THE MECHANISM THIS ROW SHIPPED.
# `badt` was wired into the DRIFT checks only, and the four sibling verdicts that
# read the SAME input -- `$hookdir/pre-commit`, the INSTALLED copy -- kept plain
# `bad`. So an all-live-tree run reported itself as MIXED ("1 are contract
# checks"), which is the wrong-attribution error the tri-branch exists to
# prevent, produced by the tri-branch. Observed, not reasoned:
# `spikes/H178_suite_flake/mixed_run.txt` is that run and its lone "contract"
# failure is `no installed pre-commit to read a CHECKS list from`.
# THE RULE THE SPLIT ACTUALLY FOLLOWS, stated so the next verdict can be placed:
# a check is `badt` iff its INPUT is the shared working tree, not iff its name
# mentions drift.
checkt(){ if [ "$2" = "$3" ]; then ok "$1"; else badt "$1 (want '$3', got '$2')"; fi; }

# A launcher that DOES launch DETACHES, so the artifacts a launcher check wants to
# see are written by a child after the parent has already exited. `sleep 1` was
# the wait at two of those checks; a bounded poll is the same guarantee without
# betting the suite on one constant, and it returns the moment the artifact
# appears instead of always paying the second. Two of these checks assert the
# artifact is THERE, so a wait that is too short is a false RED -- flaky, and a
# flaky gate is a bypassed gate (H14). ok-1, H29, 2026-08-17.
wait_file() {                      # wait_file <path> [tenths of a second, 50]
  local n=${2:-50}
  while [ "$n" -gt 0 ]; do
    [ -f "$1" ] && return 0
    sleep 0.1; n=$((n - 1))
  done
  return 1
}

# H202. WHAT WAS ACTUALLY DRIVEN, recorded at RUNTIME rather than grepped out of
# this file. The first draft of the coverage guard below scanned the source for
# `echo <MARKER> > .loop_signal.<lane>` and found NOTHING -- because the drives it
# was looking for are parameterised (`echo "$M" > .loop_signal.L1`), so the literal
# is never in the text. A text check cannot see a loop. Recording the marker at the
# moment it is written is exact and cannot be defeated by refactoring the driver.
h202_driven=''
drive() {                          # drive <marker> <lane>
  echo "$1" > ".loop_signal.$2"
  case " $h202_driven " in *" $1 "*) ;; *) h202_driven="$h202_driven $1" ;; esac
}

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
drive LOOP-HALT L1
check "per-lane signal ends turn"   "$(blocked L1)"                    "exit"
check "  leaves exit marker"        "$(cat .loop_exit.L1 2>/dev/null)" "LOOP-HALT"
check "  consumes the signal"       "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "gone"

# 2b · H202, ok-1, ATTACK cycle 28 on my own cycle-27 work. THE OTHER TWO SIGNALS.
#
# MEASURED BEFORE WRITING: of §7's three terminal signals, this suite drove ONLY
# `LOOP-HALT` end to end -- 7 times. `LOOP-IDLE` appeared once, at the BARE-signal
# check below, where the expected answer is `block`, so a hook that had stopped
# accepting LOOP-IDLE altogether would produce the same `block` and that check
# would pass. And `LOOP-DONE` -- THE SIGNAL THAT ENDS THE MISSION -- appeared
# nowhere in this file except inside v5's own mutation text. For the whole life of
# the suite whose subject is the loop's exit contract, two of the three exits were
# unverified, and a hook that refused either would have passed every check.
#
# CLASS: A SUITE THAT EXERCISES ONE MEMBER OF A VOCABULARY AND READS AS COVERING
# THE VOCABULARY. Same family as this file's own history -- the 15-check version
# passed while the hook was broken because every check set CALLSIGN.
#
# Found by attacking v5's H23 block, which asserts the hook PROMISES what it
# ACCEPTS and says nothing about whether either works. The mutation control there
# drops LOOP-IDLE from the accept branch and asserts the vocabulary check goes
# red; nothing asserted that LOOP-IDLE ever ended a turn.
for M in LOOP-DONE LOOP-IDLE; do
  rm -f .loop_signal* .loop_exit.* .loop_blocks.*
  drive "$M" L1
  check "H202: a per-lane $M ends the turn"  "$(blocked L1)"                    "exit"
  check "  leaves $M as the exit marker"     "$(cat .loop_exit.L1 2>/dev/null)" "$M"
  check "  and consumes the signal"          "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "gone"
done
# THE CLASS FIX, not the site fix (§12.2). Two signals were added above; the next
# marker added to the hook would be uncovered again unless something refuses that.
# Every marker the hook ACCEPTS must be driven through it by this file.
h202_uncovered=0
for M in $(grep -E '^[[:space:]]*(LOOP-[A-Z]+\|)*LOOP-[A-Z]+\)' "$GATE" \
           | grep -oE 'LOOP-[A-Z]+' | sort -u); do
  # The DRIVE, not the mention. A marker named only in a comment or in v5's
  # mutation string is H63's fixture-reads-as-coverage defect, which this suite
  # has already paid for -- and `$h202_driven` cannot contain one, because only
  # drive() writes to it and only a real per-lane signal write calls drive().
  case " $h202_driven " in
    *" $M "*) ;;
    *) h202_uncovered=$((h202_uncovered+1))
       printf '  info  the hook accepts %s and this suite never drives it per-lane\n' "$M" ;;
  esac
done
# AND THE RECORD ITSELF MUST NOT BE EMPTY. An empty $h202_driven with an empty
# accept set would leave the loop above with nothing to iterate and report 0
# uncovered -- a clean number from a check that never ran, which is the shape the
# H178 accounting control failed on.
check "H202:   and the coverage record is not empty"                           \
      "$(printf '%s' "$h202_driven" | grep -c 'LOOP-')" "1"
check "H202: every marker the hook ACCEPTS is driven end-to-end here"          \
      "$h202_uncovered" "0"

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

# 8b · H219, ok-1, 2026-08-19. THE PER-LANE KILL SWITCH, which section 8 above
#      reads as covering and does not: it drives the FLEET-WIDE file. Both
#      directions are driven because the repair must not become a glob —
#      `STOP.*` would satisfy the first check and let one lane's retirement stop
#      all five, which is H31's own defect restored from the other end.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* STOP STOP.L4b STOP.L5b
touch STOP.L4b
check "own-lane STOP ends the turn"        "$(blocked L4b)" "exit"
check "  another lane's STOP does not"     "$(blocked L5b)" "block"
rm -f STOP.L4b
# READ OUT OF THE GATE, not driven, and that is not laziness: relocating the read
# ABOVE the callsign whitelist is behaviourally INVISIBLE — a refused callsign and
# an allowed stop are both `exit` — so a behavioural check cannot see it. $LANE is
# interpolated into a filename here exactly as it is into EXIT_MARK and BLOCKS.
_wl=$(grep -n 'case "\$LANE" in' "$T/gate.sh" | head -1 | cut -d: -f1)
_st=$(grep -n 'STOP\.\${LANE}' "$T/gate.sh" | head -1 | cut -d: -f1)
check "  per-lane STOP read sits below the charset whitelist" \
      "$([ -n "$_wl" ] && [ -n "$_st" ] && [ "$_st" -gt "$_wl" ] && echo below || echo ABOVE-OR-ABSENT)" \
      "below"

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
check "  writes no fuse at all"       "$(ls .loop_blocks.* 2>/dev/null | wc -l | tr -d ' ')"      "0"

# 9b · THE PRECONDITION SECTION 9 DELETES. H20 (ok-1) filed both of its checks as
#      "unreachable without two simultaneous reverts". Measured, and only one of
#      them was: `writes no 'unknown' marker` lived above, under a section that
#      opens `rm -f .loop_signal*`, and the hook writes `.loop_exit.<LANE>` ONLY
#      after consuming a signal. So no combination of hook defects could redden
#      it -- not a check needing two reverts, a check whose own section removes
#      the thing it tests. A15: the instrument cannot produce the answer.
#
#      IT IS A NEW SECTION AND NOT A LINE ADDED TO SECTION 9, because the obvious
#      fix is wrong and the probe caught it: planting the signal in section 9
#      makes the hook exit legally under the LANE-default defect, so
#      `no callsign is not gated` STOPS FIRING on the very defect it exists for.
#      Measured on a scratch tree -- that defect alone reddens 6 checks, and with
#      the plant folded into section 9 it reddens 2. A repair that raises one
#      check's coverage by disarming five is a suite that reports better and
#      tests less.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal.unknown
_=$(nolane)
check "  writes no 'unknown' marker"  "$([ -f .loop_exit.unknown ] && echo wrote || echo none)"        "none"
check "  leaves the planted signal"   "$([ -f .loop_signal.unknown ] && echo present || echo gone)"    "present"

# 10 · An unidentified session must not consume a real lane's terminal signal.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
echo LOOP-HALT > .loop_signal.L1
check "no callsign cannot steal exit" "$(nolane)" "exit"
check "  lane signal untouched"       "$([ -f .loop_signal.L1 ] && echo present || echo gone)" "present"

# 11 · §12.6 CONCURRENCY. The fuse was `N=$(cat); N=$((N+1)); echo $N >` — an
#      unsynchronised read-modify-write. Every check above is a single sequential
#      invocation, so a suite written FOR a two-lanes-share-state defect contained
#      no concurrency at all.
#
#      THIS WAS A `KNOWN` LINE, NOT A CHECK, from the day it was written until
#      2026-08-17 (H13, ok-1). It printed the undercount and passed the suite
#      either way, so the suite's exit code could not tell a fixed fuse from a
#      broken one — a measurement standing where an assertion belongs, which is
#      the same shape as A28 (a field recorded but never read). Measured before
#      the fix on this tree: 12, 13, 14 of 20 across three runs, and 28 of 60.
#      Now REQUIRING, against loop_gate.sh v7's mkdir lock. Falsified: restore the
#      unlocked RMW on an isolated copy and this check goes red —
#      `bash spikes/harness/test_h13_falsify.sh`.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
for i in $(seq 1 20); do ( CALLSIGN=L9 ./gate.sh </dev/null >/dev/null 2>&1 ) & done
wait
conc=$(cat .loop_blocks.L9 2>/dev/null || echo 0)
check "fuse counts 20/20 under concurrency" "$conc" "20"
rm -rf .loop_blocks.L9.lock

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
  # v4, H191 -- A VALUE SPLIT ON WHITESPACE WHOSE RECORDS ARE NEWLINE-DELIMITED,
  # and the tell was sitting in the loop body the whole time. `for c in $cmds`
  # is unquoted, so it splits on IFS -- spaces -- while the python above emits
  # ONE COMMAND PER LINE. The moment a hook was registered WITH ARGUMENTS
  # (`python3 .../scratchcheck.py --hook`, ATTACKER-1, H89) that single correct
  # registration became THREE checks, three failures, and the suite reported
  # `python3` as "missing or not executable".
  #   THE DEFEATED GUARD IS THE EVIDENCE: `${c%% *}` strips the first word, so
  # its author knew commands carry arguments. The outer split had already
  # destroyed what that guard existed to handle, and it read as a no-op for
  # weeks. A guard downstream of the split that breaks it is worth more than the
  # symptom -- grep your own for `for x in $(...)` over anything line-shaped.
  #   `command -v` REPLACES `[ -x ]` AND THIS DOES NOT WEAKEN THE GATE: an
  # interpreter found on PATH does resolve, which is the question being asked,
  # and `[ -x python3 ]` was answering a different one. The `$` refusal is
  # deliberately still tested against the WHOLE command line, so an env var in an
  # ARGUMENT is refused exactly as before -- an unresolvable reference is
  # unresolvable wherever it sits (§12.4).
  #   AND THE FIRST DRAFT OF THIS FIX WAS `printf ... | while read`, WHICH IS THE
  # SAME FAMILY AGAIN: a pipeline runs its right side in a SUBSHELL, so every
  # ok/badt inside would have incremented a copy of pass/fail/treefail and the
  # parent would have printed the old totals. A check that cannot report its
  # verdict. Caught before it ran, by the arm below asserting the count MOVES.
  while IFS= read -r c; do
    [ -n "$c" ] || continue
    case "$c" in
      *'$'*) check "reg $sj resolves without env" "env-var-in-path" "literal-path" ;;
      *) if command -v "${c%% *}" >/dev/null 2>&1; then ok "reg $sj resolves to an executable"
         else badt "reg $sj resolves to an executable (missing or not executable: ${c%% *} in: $c)"; fi ;;
    esac
  done <<< "$cmds"
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
#
# TWO GUARDS ADDED 2026-08-17 (AGENT-1, H30), AND THIS CHECK WAS MEASURED INERT
# WITHOUT THEM. `cleared` is the ABSENCE of a marker, so a launcher that never
# reaches its turn scores identically to one that cleared the signal correctly --
# A29, a probe that cannot show it reached its target has produced no evidence.
# It went inert within minutes of two unrelated launcher changes:
#   * the spawn-brief requirement (H30, defect 8) refuses before the turn, and
#     the scratch tree had no prompts/ at all, so the launcher exited 1 and the
#     stub never ran. `test_h16_falsify.sh` reported `INERT` with the H16 defect
#     restored -- caught by running the falsifier, not by reading the suite.
#   * the self-detach (defect 7) makes the parent exit 0 after ~1s while the turn
#     runs asynchronously, so both this marker and the exit code became a race
#     against the child. KF_DETACHED=1 is the launcher's own recursion guard and
#     is set here so the body runs in the FOREGROUND: the property under test is
#     the loop body, not the detacher. The hostile-callsign block below
#     deliberately does NOT set it, because there the refusal must beat the
#     detach and rc=0 from a detached parent is exactly the defect to catch.
rm -f .loop_signal* .loop_exit.* .loop_blocks.*
mkdir -p bin
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
# stub claude: report whether a stale terminal signal survived into the turn,
# then hand the launcher a legal exit so the test finishes in one iteration.
echo ran > turn_ran
[ -f ".loop_signal.${CALLSIGN}" ] && echo SURVIVED > stale_reached_turn
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
cp "$ROOT/run_loop.sh" ./run_loop.sh
mkdir -p prompts && printf '# L8 — scratch lane brief for the launcher checks\n' > prompts/L8.md
echo LOOP-HALT > .loop_signal.L8            # the previous span's leftover
rm -f stale_reached_turn turn_ran
PATH="$T/bin:$PATH" KF_DETACHED=1 CALLSIGN=L8 MAX_TURN=5 bash ./run_loop.sh >/dev/null 2>&1
check "  launcher's turn actually ran (else 'cleared' means nothing)" \
      "$([ -f turn_ran ] && echo ran || echo never)" "ran"
check "launcher clears a stale signal before the turn" \
      "$([ -f stale_reached_turn ] && echo reached || echo cleared)" "cleared"

# --- A LANE WITH NO SPAWN BRIEF. H30, 2026-08-17, AGENT-1.
# `prompts/$CALLSIGN.md` was read as `$([ -f "$BRIEF_FILE" ] && ... && cat ...)`
# inside the prompt, so an absent brief expanded to the empty string and the lane
# launched looking exactly like a briefed one. Of three live lanes at 13:25 only
# ATTACKER-1 had a brief; the only written form of the callsign-allocation rule
# (H8) is §0 of a brief, so it reached one lane in three.
# CLASS: a missing INPUT silently degrades a mechanism to a no-op while it still
# reports success. THE POSITIVE CONTROL IS THE POINT -- L8 above launches with a
# brief and reaches its turn, so this check cannot be green because the launcher
# refuses everything.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* turn_ran stale_reached_turn
PATH="$T/bin:$PATH" CALLSIGN=L10 MAX_TURN=5 bash ./run_loop.sh >nobrief.out 2>&1
check "launcher refuses a callsign with no spawn brief"        "$?" "1"
check "  and the CALLER sees it, not detach_L10.log"           \
      "$(grep -c 'no spawn brief' nobrief.out)" "1"
check "  refusal names the file to write"                      \
      "$(grep -c 'prompts/L10.md' nobrief.out)" "2"
check "  it never reached the turn"                            \
      "$([ -f turn_ran ] && echo ran || echo none)" "none"
check "  and never detached an unbriefed lane"                 \
      "$([ -f detach_L10.log ] && echo detached || echo none)" "none"
# The two checks above this one are absence-of-an-async-event, and MEASURED under
# the brief gate's own defect (spikes/H29_detach_race/probe.out): `it never
# reached the turn` goes RED with run_loop.sh's post-fork `sleep 1` in place and
# GREEN without it, over the same live defect. The child's artifacts are its own;
# the announcement is the PARENT's, printed before it exits, so this check's
# verdict does not depend on how fast the child gets scheduled. ok-1, H29.
check "  and announced no detach (synchronous, unlike the child's artifacts)"   \
      "$(grep -c 'detached (survives caller teardown)' nobrief.out)" "0"
rm -f nobrief.out detach_L10.log loop_L10.log
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
# H178 SEAM. The live-tree accounting added to the summary is a BRANCH, and a
# branch nothing drives is prose. `KF_TEST_HOOKDIR` points this block at a
# directory the probe controls, so spikes/H178_suite_flake/probe.sh can drive
# THIS suite -- not a copy of it -- into the all-live-tree state and read the
# summary it prints. Unset in every real run, including the ones above and below.
hookdir="${KF_TEST_HOOKDIR:-$hookdir}"
# Both gates, by list. AGENT-1/H15 added `pre-commit`; checking only the one
# gate that existed when this check was written is how an installer ships with a
# hook it does not install.
# H36 (ATOM-3, 2026-08-17) — INSTANCE 3 OF H35's CLASS, AND ONLY THE WORD WAS
# WRONG. This block compared `$ROOT/spikes/harness/$g.hook` — the WORKING TREE —
# and reported "gate matches its TRACKED source". Tracked means committed. The
# live instance the row recorded was two commands: `cmp` against the tree EQUAL
# while `git show HEAD:...| cmp` DIFFER, so an uncommitted source edit plus a
# reinstall read as NO DRIFT while the enforced gate existed in no commit.
#
# THE COMPARISON IS KEPT, because it is the right one and the falsifier decided
# it rather than my preference: `install_hooks.sh:35` is `cp "$src" "$dst"` with
# `src` the TREE path, so "does the installed gate match what installing would
# put there" is a tree question. Had the installer read HEAD, the comparison
# would have been the defect and the message fine — the opposite fix.
#
# THE HEAD LINE IS INFORMATIONAL AND MUST STAY THAT WAY. The row is explicit
# that a bare HEAD comparison turns the suite red for every harness author with
# an uncommitted hook edit installed, which is a legitimate mid-cycle state and
# would make this an always-red gate — H52's class, and H14's "a flaky gate is a
# bypassed gate" applies to an always-red one exactly as thoroughly.
# H115 adds pre-push. The list is the whole mechanism -- a gate absent from it
# is drift-checked nowhere, which is exactly what happened to pre-commit between
# v1 and v2 of the installer.
for g in commit-msg pre-commit pre-push; do
  src="$ROOT/spikes/harness/$g.hook"
  if [ ! -f "$src" ]; then
    bad "$g.hook source is missing from spikes/harness"
  elif [ ! -x "$hookdir/$g" ]; then
    badt "$g gate matches its working-tree source (NOT INSTALLED — sh spikes/harness/install_hooks.sh)"
  elif ! cmp -s "$src" "$hookdir/$g"; then
    badt "$g gate matches its working-tree source (DRIFTED from spikes/harness/$g.hook)"
  else
    ok "$g gate matches its working-tree source (what install_hooks.sh would copy)"
  fi
  # H124, ATOM-3. THE DRIFT CHECK ABOVE CANNOT SEE A BROKEN GATE: `cmp -s`
  # compares an installed copy to its source, and IDENTICAL BROKEN BYTES COMPARE
  # EQUAL. Earned the same hour -- a stray `"` in pre-commit.hook was installed
  # in front of five lanes for 2m16s while this suite reported 88 checks pass.
  # git reads a non-zero exit from pre-commit as REFUSE, so an unparseable gate
  # does not leak commits through, it refuses EVERY commit from EVERY lane.
  # CLASS: a check that verifies an artifact is the RIGHT one but never that it
  # is a VALID one. `install_hooks.sh` v5 now refuses to install one; this is
  # the detection half, because .git/hooks can also be edited by hand.
  if [ -x "$hookdir/$g" ]; then
    if sh -n "$hookdir/$g" 2>/dev/null; then
      ok "  $g installed gate PARSES"
    else
      badt "  $g installed gate DOES NOT PARSE -- it refuses every commit from
        every lane: $(sh -n "$hookdir/$g" 2>&1 | head -1)"
    fi
  fi
  # Informational, never a verdict: is the ENFORCED gate in any commit? A reader
  # checking compliance, and every clean clone, gets the committed copy.
  if [ -x "$hookdir/$g" ]; then
    if git -C "$ROOT" show "HEAD:spikes/harness/$g.hook" 2>/dev/null | cmp -s - "$hookdir/$g"; then
      printf '  info  %s installed gate is byte-identical to HEAD (in a commit)\n' "$g"
    else
      printf '  info  %s installed gate DIFFERS from HEAD — the enforcing gate exists in no commit%s\n' \
        "$g" "$(git -C "$ROOT" diff --quiet HEAD -- "spikes/harness/$g.hook" 2>/dev/null || printf ' (its source is uncommitted)')"
    fi
  fi
done

# --- WHAT THE INSTALLED GATE ACTUALLY RUNS. ok-1, H94.
# The drift block above proves the installed gate is the reviewed gate. It says
# nothing about whether the checks that gate NAMES can run, and `pre-commit.hook`
# is fail-open by design on an absent checker -- "a broken clone, not a
# violation". So a renamed or moved module silently converts a gate into a
# SKIP line, and the hook still exits 0. That is H30's class (a missing input
# degrades a mechanism to a no-op while it still reports success) sitting in the
# only enforcing gate this repo has, and nothing in this suite looked at it.
# Read out of the INSTALLED copy, not the source: the enforced list is the one
# that matters, and the two can differ for exactly as long as a reinstall is
# forgotten.
installed_pc="$hookdir/pre-commit"
if [ -r "$installed_pc" ]; then
  pc_checks=$(sed -n "/^CHECKS='/,/'\$/p" "$installed_pc" | sed "s/^CHECKS='//; s/'\$//")
  n_missing=0; n_checks=0
  for c in $pc_checks; do
    # Only path-shaped tokens: if the CHECKS block's terminating quote ever moves,
    # the sed range runs on into the body and the loop would otherwise report
    # every word of the hook as a missing check.
    case "$c" in */*.py) ;; *) continue ;; esac
    n_checks=$((n_checks+1))
    [ -f "$ROOT/$c" ] || { n_missing=$((n_missing+1)); printf '  info  gate names a check that is not there: %s\n' "$c"; }
  done
  checkt "every check the installed pre-commit names EXISTS (else it SKIPs, green)" \
        "$n_missing" "0"
  [ "$n_checks" -ge 4 ] && ok "the installed pre-commit runs $n_checks checks" \
    || badt "the installed pre-commit runs $n_checks checks (want >= 4)"
  # H94 by name: the record-loss gate is the one whose absence is invisible --
  # it fires only on a commit that REMOVES a completed record, so an inert copy
  # looks exactly like a fleet that never lost one.
  case "$pc_checks" in
    *recordloss.py*) ok "the record-loss gate (H94) is wired into pre-commit" ;;
    *) badt "the record-loss gate (H94) is NOT wired into pre-commit" ;;
  esac
  # H108. THE BYPASS PATH MUST RUN WHAT THE GATE RUNS. `commit_scoped.sh` is the
  # §13 escape hatch for H72 -- another lane's tree state refusing your commit --
  # and it reaches the same commit through `--no-verify`, so every check it does
  # NOT run is a check that any lane can miss by taking the documented route.
  # It named three modules while the gate ran four, and the commit that shipped
  # the fourth went through it unjudged (0871533). Two independently-maintained
  # lists of one set, which is H39's class; this is the thing that compares them.
  cs="$ROOT/spikes/harness/commit_scoped.sh"
  if [ -r "$cs" ]; then
    n_absent=0
    for c in $pc_checks; do
      case "$c" in */*.py) ;; *) continue ;; esac
      # The RUN, not the mention: a module named only in a comment is H63's
      # fixture-reads-as-coverage defect, which this suite has already paid for.
      grep -q "python3 $c" "$cs" || { n_absent=$((n_absent+1))
        printf '  info  commit_scoped.sh does not RUN %s\n' "$c"; }
    done
    check "the §13 bypass runs every check the gate runs (H108)" "$n_absent" "0"
  else
    badt "no commit_scoped.sh to compare the gate's CHECKS list against (H108)"
  fi
else
  badt "no installed pre-commit to read a CHECKS list from (sh spikes/harness/install_hooks.sh)"
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
  # STABLE NAME, outcome in the parenthetical. A check that RENAMES ITSELF when
  # it fails cannot be tracked from a green run to a red one, so its coverage is
  # unmeasurable — falsify.py reported seven of these as never-reddened when they
  # redden every time under F3, just under a different name. Measuring coverage
  # is what exposed it; nobody would find this by reading.
  if [ -z "$out" ]; then
    ok "hostile callsign handled: $label (refused)"
  elif printf '%s' "$out" | python3 -c 'import json,sys; json.load(sys.stdin)' 2>/dev/null; then
    ok "hostile callsign handled: $label (gated, valid JSON)"
  else
    bad "hostile callsign handled: $label (UNPARSEABLE decision)"
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
# THE BRIEF IS HERE SO THE CHARSET GATE IS WHAT REFUSES, and finding that out is
# H29's first result. MEASURED, not reasoned (spikes/H29_detach_race/probe.out):
# with the charset whitelist NEUTERED this block stayed ALL GREEN, because
# run_loop.sh refuses in gate order -- charset, roster, brief -- and there is no
# `prompts/L"6.md`, so the brief gate exited 1 for a reason this block is not
# about. `falsify.py F8` has been printing `INERT` since the brief gate landed
# (H30) and nobody read it, because nothing runs the driver automatically --
# which is this row.
#
# CLASS: **rc=1 does not say WHICH gate refused, so a check asserting only the
# exit code goes inert the moment an EARLIER gate refuses for an unrelated
# reason.** Grep for launcher checks whose only assertion is `"$rc" "1"`. The
# no-brief block below was already immune, for the reason worth copying: it
# asserts the refusal TEXT as well as the code.
printf '# scratch brief: leaves the CHARSET gate as the only refusal left\n' > 'prompts/L"6.md'
out=$(PATH="$T/bin:$PATH" CALLSIGN='L"6' MAX_TURN=5 bash ./rl.sh 2>&1)
rc=$?
check "  launcher refuses what the hook will not gate" "$rc" "1"
check "  and refuses for THAT reason, not an earlier gate's"                  \
      "$(printf '%s' "$out" | grep -c 'CALLSIGN must contain only')" "1"
# ABSENCE OF AN ASYNCHRONOUS EVENT IS NOT OBSERVABLE AT THE PARENT'S EXIT. The
# launcher forks, the parent returns, and the child reaches `claude` some time
# later -- so `[ -f launcher_reached_claude ]` read here is a race whose PASSING
# answer is the free one. It lands green today only because run_loop.sh happens
# to `sleep 1` after its fork, a line with no test-facing purpose sitting inside
# the component under test: with that line deleted, the sibling check `it never
# reached the turn` below PASSES OVER A LIVE DEFECT (measured, same probe).
# So the load-bearing assertion is the second one: the parent ANNOUNCES its
# detach on its own stdout before exiting, which is synchronous by construction
# and cannot be won by being early.
check "  launcher never reached claude"                                      \
      "$([ -f launcher_reached_claude ] && echo spawned || echo none)" "none"
check "  and announced no detach (the PARENT prints it, so this cannot race)"  \
      "$(printf '%s' "$out" | grep -c 'detached (survives caller teardown)')" "0"
rm -f ./rl.sh launcher_reached_claude 'loop_L"6.log' 'prompts/L"6.md' \
      .loop_exit.* .loop_blocks.* .loop_lock.*
check "  hostile callsigns left no state" \
      "$(ls .loop_exit.* .loop_blocks.* 2>/dev/null | wc -l | tr -d ' ')" "0"
rm -f pwned

# --- CALLSIGN ALLOCATION: A SECOND LAUNCHER ON A HELD CALLSIGN. AGENT-2, H8.
# A callsign names the lane's .loop_signal / .loop_exit / .loop_blocks and signs
# every CHANNEL line, so two launchers on one callsign share a terminal signal
# and sign each other's work. §12 answers this in prose and prompts/ATTACKER-1.md
# §0 tells a lane to look for a holder with `ps -eo command= | grep 'You are X\.'`
# -- an instruction that cannot be carried out, because `ps` shows every launcher
# as `bash ./run_loop.sh` with the callsign nowhere in argv, and the `claude -p`
# child that does carry it exists only while a turn is in flight.
#
# Driven end to end against a copy of the real launcher, per the section above:
# the property is "the second launcher refuses", not "this file contains that
# word". Three cases, because the branch has three outcomes and the middle one is
# the whole reason the check is not `kill -0`.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* .loop_lock.*
mkdir -p bin fake
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo reached > launcher_reached_claude
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"     # let the launcher finish in one pass
STUB
chmod +x bin/claude
# A process whose command matches a launcher, without being one. Started from a
# file actually named run_loop.sh so `ps -o command=` reports what a real
# launcher reports -- constructing the case rather than trusting the predicate.
# The trailing `exit 0` is load-bearing: bash EXECs the last simple command of a
# script, so a fixture ending in `sleep 30` becomes a process whose `ps command=`
# reads `sleep 30` and matches nothing. It cost this check one red run, and the
# assertion below is here so it cannot cost a future one a GREEN one -- a fixture
# that stopped resembling its target would otherwise make the refusal untestable
# while reading as covered (A29).
printf '#!/usr/bin/env bash\nsleep 30\nexit 0\n' > fake/run_loop.sh
bash fake/run_loop.sh & holder=$!
check "fixture holder is indistinguishable from a launcher to ps"            \
      "$(ps -p "$holder" -o command= 2>/dev/null | grep -c 'run_loop\.sh')" "1"
cp "$ROOT/run_loop.sh" ./run_loop.sh
rm -f launcher_reached_claude

echo "$holder" > .loop_lock.L9
out=$(PATH="$T/bin:$PATH" CALLSIGN=L9 MAX_TURN=5 bash ./run_loop.sh 2>&1); rc=$?
check "second launcher on a HELD callsign refuses"  "$rc" "1"
check "  names the holding pid"                                              \
      "$(printf '%s' "$out" | grep -q "HELD by live launcher pid ${holder}" && echo named || echo silent)" "named"
check "  and never reached claude"                                           \
      "$([ -f launcher_reached_claude ] && echo spawned || echo none)" "none"
check "  holder's lock is left intact"             "$(cat .loop_lock.L9)" "$holder"

# A DEAD holder must be reclaimed, not respected. There is no release path in the
# launcher on purpose -- a trap covers a clean exit and misses SIGKILL, the
# watchdog's own pkill and a power cut -- so this branch is the only thing
# standing between a crashed lane and a callsign nobody can ever launch again.
sleep 0.2 & dead=$!; wait "$dead" 2>/dev/null
echo "$dead" > .loop_lock.L9
rm -f launcher_reached_claude
PATH="$T/bin:$PATH" CALLSIGN=L9 MAX_TURN=5 bash ./run_loop.sh >/dev/null 2>&1
wait_file launcher_reached_claude                # was `sleep 1` — H29
check "dead holder's lock is reclaimed"                                      \
      "$([ -f launcher_reached_claude ] && echo launched || echo refused)" "launched"
check "  lock no longer names the dead pid"                                  \
      "$([ "$(cat .loop_lock.L9 2>/dev/null)" = "$dead" ] && echo stale || echo replaced)" "replaced"

# PID REUSE. `kill -0` alone reports HELD for any live process that inherited the
# pid, and pid reuse is not theoretical here: this fleet burned ~1300 pids/minute
# with three lanes running, so a 99999-pid space wraps in about 75 minutes. A
# false HELD refuses a legitimate lane, and a dead lane has no next cycle. Delete
# the command half of the liveness test and this check -- and only this one --
# goes red.
sleep 30 & impostor=$!
echo "$impostor" > .loop_lock.L9
rm -f launcher_reached_claude
PATH="$T/bin:$PATH" CALLSIGN=L9 MAX_TURN=5 bash ./run_loop.sh >/dev/null 2>&1
wait_file launcher_reached_claude                # was `sleep 1` — H29
check "a reused pid that is not a launcher does not hold a callsign"         \
      "$([ -f launcher_reached_claude ] && echo launched || echo refused)" "launched"
kill "$holder" "$impostor" 2>/dev/null
# The launcher DETACHES, so anything it spawned outlives this test unless it is
# reaped here. That is not a hypothetical tidiness point: a launcher spawned from
# a probe under CALLSIGN=ok-1 was found alive in the repo root at 13:26 today,
# running real turns with no brief and no queue row, which is the incident H8 was
# closed on.
for lk in .loop_lock.*; do
  [ -f "$lk" ] || continue
  lkpid=$(cat "$lk" 2>/dev/null)
  case "$lkpid" in ''|*[!0-9]*) continue ;; esac
  ps -p "$lkpid" -o command= 2>/dev/null | grep -q 'run_loop\.sh' && kill "$lkpid" 2>/dev/null
done

# --- CALLSIGN ALLOCATION, PART 2: THE LOCK AFTER t=0. ok-1, H232, 2026-08-19.
# The block above proves a second launcher is refused AT LAUNCH, and that was the
# whole of the mutual exclusion: v10 had ZERO reads of $LOCK inside its turn loop
# (lines 433-635, extracted mechanically in spikes/H232_two_lanes_one_lock/
# probe.sh, because reading a line range by eye is what §12.4 forbids). So a
# launcher that had LOST the lock kept producing turns forever while
# `cat .loop_lock.<CS>` -- the one command every spawn brief tells a lane to
# trust -- named the other one. Observed live the day this was written: `ok-1` on
# TWO launcher roots (3619, 56520) with one lock, four other callsigns on one
# each, and the duplicate had to be retired by hand because a run_loop.sh edit
# reaches a lane only at relaunch (H21).
# BOTH DIRECTIONS ARE DRIVEN. A retire-on-mismatch that fires on an ABSENT lock
# would let any third party -- bringup's stale-state clear, a stray rm, a probe --
# kill a healthy lane, which is the same file outliving/undercutting its span that
# H16 and H196 are about, pointed the other way.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* .loop_lock.* turns_L10.log
mkdir -p bin prompts fake
cp "$ROOT/run_loop.sh" ./run_loop.sh
chmod +x ./run_loop.sh          # `nohup "$0"` EXECs the copy; 644 dies at exec
printf '# scratch\n' > prompts/L10.md
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo turn >> turns_L10.log
exit 0
STUB
chmod +x bin/claude
: > turns_L10.log
PATH="$T/bin:$PATH" CALLSIGN=L10 MAX_TURN=10 BACKOFF_STEP=1 bash ./run_loop.sh >/dev/null 2>&1
n=200; while [ "$n" -gt 0 ] && [ "$(wc -l < turns_L10.log)" -lt 2 ]; do sleep 0.1; n=$((n-1)); done
# PRECONDITION, and it is not decoration: with a 644 copy this launcher produces
# no turns, and then "stopped producing turns" passes over a launcher that never
# started -- an absence assertion won by being early, which is v2's own class.
check "L10 launcher is producing turns before the lock is touched"           \
      "$([ "$(wc -l < turns_L10.log)" -ge 2 ] && echo yes || echo no)" "yes"
_l10=$(cat .loop_lock.L10 2>/dev/null)
printf '#!/usr/bin/env bash\nsleep 30\nexit 0\n' > fake/run_loop.sh
bash fake/run_loop.sh & thief=$!
echo "$thief" > .loop_lock.L10
_t1=$(wc -l < turns_L10.log); sleep 6; _t2=$(wc -l < turns_L10.log)
check "a launcher that has LOST the lock stops producing turns"              \
      "$([ "$_t2" -eq "$_t1" ] && echo stopped || echo running)" "stopped"
check "  and names the pid that holds the callsign now"                      \
      "$([ "$(grep -c "$thief" loop_L10.log 2>/dev/null)" -ge 1 ] && echo named || echo silent)" "named"
kill "$thief" "$_l10" 2>/dev/null; pkill -f 'You are L10\.' 2>/dev/null
# THE OTHER DIRECTION: an ABSENT lock is re-acquired, never fatal.
rm -f .loop_lock.L11 turns_L11.log
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo turn >> turns_L11.log
exit 0
STUB
chmod +x bin/claude
printf '# scratch\n' > prompts/L11.md
: > turns_L11.log
PATH="$T/bin:$PATH" CALLSIGN=L11 MAX_TURN=10 BACKOFF_STEP=1 bash ./run_loop.sh >/dev/null 2>&1
n=200; while [ "$n" -gt 0 ] && [ "$(wc -l < turns_L11.log)" -lt 2 ]; do sleep 0.1; n=$((n-1)); done
rm -f .loop_lock.L11                     # the third-party delete
_u1=$(wc -l < turns_L11.log); sleep 6; _u2=$(wc -l < turns_L11.log)
check "a lane whose lock was DELETED keeps running"                          \
      "$([ "$_u2" -gt "$_u1" ] && echo running || echo stopped)" "running"
check "  and takes its own lock back"                                        \
      "$(_p=$(cat .loop_lock.L11 2>/dev/null); [ -n "$_p" ] && ps -p "$_p" -o command= 2>/dev/null | grep -c 'run_loop\.sh' || echo 0)" "1"
_l11=$(cat .loop_lock.L11 2>/dev/null); kill "$_l11" 2>/dev/null
pkill -f 'You are L11\.' 2>/dev/null
rm -f turns_L10.log turns_L11.log .loop_lock.L10 .loop_lock.L11

# --- ADMISSION: THE ROSTER GATE. ok-1, H63, ATTACK cycle (§2, §12.8), 2026-08-17.
# `roster.txt` is the fleet's sanction list, and run_loop.sh says why in its own
# comment: *"a brief that the lane wrote for itself is not sanction to run.
# roster.txt is the sanction."* It is the answer to H32 (the launcher gates entry
# and nothing audits what is inside) and the subject of H38's two-roster
# divergence -- i.e. it decides which lanes may run at all.
#
# MEASURED BEFORE THIS BLOCK EXISTED (`spikes/H63_roster_attack/attack.out`): the
# ENTIRE gate could be deleted from run_loop.sh and this suite stayed 66/66 green,
# and `grep -qx` could be loosened to `grep -q` -- which admits `ok` against a
# roster listing `ok-1` -- with the same 66/66. `grep -n roster` in this file
# returned three lines and all three were a scratch roster written FOR the
# simultaneity block below. The gate with the widest blast radius in the launcher
# had no check of any kind.
rm -f .loop_signal* .loop_exit.* .loop_blocks.* .loop_lock.* launcher_reached_claude
cp "$ROOT/run_loop.sh" ./run_loop.sh
mkdir -p bin prompts
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo reached > launcher_reached_claude
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"     # let the launcher finish in one pass
STUB
chmod +x bin/claude
printf '# scratch roster for the admission checks\nR-IN\nok-1\n' > roster.txt
for l in R-IN R-OUT ok; do printf '# scratch\n' > "prompts/$l.md"; done
# A BRIEF EXISTS FOR EVERY ARM HERE. The brief gate sits BELOW the roster gate,
# and H62 is the cycle that measured what a later gate refusing first does to a
# check: it goes green for a reason the block is not about. Every refusal below is
# therefore attributable to the roster gate and nothing else.
out=$(PATH="$T/bin:$PATH" CALLSIGN=R-OUT MAX_TURN=5 bash ./run_loop.sh 2>&1); rc=$?
check "unrostered callsign is refused"                       "$rc" "1"
check "  refusal names the roster, not just a code"                           \
      "$(printf '%s' "$out" | grep -c 'is not in roster.txt')" "1"
check "  and the unrostered lane never reached claude"                        \
      "$([ -f launcher_reached_claude ] && echo spawned || echo none)" "none"
check "  and announced no detach (unrostered)"                                \
      "$(printf '%s' "$out" | grep -c 'detached (survives caller teardown)')" "0"
# THE POSITIVE CONTROL, and without it this whole block is satisfied by a launcher
# that refuses everything -- which is the state the H8 checks were measured in
# (1 PASS / 3 FAIL, and the one PASS was the false one). KF_DETACHED=1 so the loop
# body runs in the FOREGROUND and "it launched" is a fact rather than a race (H62).
rm -f launcher_reached_claude
PATH="$T/bin:$PATH" KF_DETACHED=1 CALLSIGN=R-IN MAX_TURN=5 bash ./run_loop.sh >/dev/null 2>&1
check "  a ROSTERED callsign is admitted (else the gate just says no)"        \
      "$([ -f launcher_reached_claude ] && echo launched || echo refused)" "launched"
# `grep -qx`, not `grep -q`. Measured: with the x dropped, `ok` is admitted by a
# roster listing `ok-1` -- and this fleet has a live callsign that is a prefix of
# nothing and a suffix of nothing by luck, not by rule.
rm -f launcher_reached_claude .loop_lock.* .loop_exit.*
out=$(PATH="$T/bin:$PATH" CALLSIGN=ok MAX_TURN=5 bash ./run_loop.sh 2>&1); rc=$?
check "a callsign that is a SUBSTRING of a rostered one is refused" "$rc" "1"
check "  and it never reached claude either"                                  \
      "$([ -f launcher_reached_claude ] && echo spawned || echo none)" "none"
# ROSTER ABSENT IS FAIL-OPEN. Pinned by OBSERVATION, not endorsed: with no
# roster.txt the launcher warns and admits ANY callsign, so the admission
# mechanism degrades to a no-op on a missing input while still reporting success
# -- H30's class at the gate that decides who may run. Whether a missing sanction
# list should mean "no lanes" or "all lanes" is the OPERATOR's call, not an
# agent's (A22: the agent is the beneficiary), so it is filed in HUMAN_NEEDED.md
# and this check exists to make the current answer deliberate: change the
# behaviour and you must change this check and say why.
rm -f launcher_reached_claude .loop_lock.* .loop_exit.*
mv roster.txt roster.txt.aside
outn=$(PATH="$T/bin:$PATH" KF_DETACHED=1 CALLSIGN=R-OUT MAX_TURN=5 bash ./run_loop.sh 2>&1)
check "roster ABSENT admits any callsign (FAIL-OPEN — measured, not chosen)"  \
      "$([ -f launcher_reached_claude ] && echo launched || echo refused)" "launched"
check "  and says so out loud"                                                \
      "$(printf '%s' "$outn" | grep -c 'WARNING roster.txt absent')" "1"
for lk in .loop_lock.*; do
  [ -f "$lk" ] || continue
  lkpid=$(cat "$lk" 2>/dev/null)
  case "$lkpid" in ''|*[!0-9]*) continue ;; esac
  ps -p "$lkpid" -o command= 2>/dev/null | grep -q 'run_loop\.sh' && kill "$lkpid" 2>/dev/null
done
rm -f roster.txt.aside prompts/R-IN.md prompts/R-OUT.md prompts/ok.md \
      launcher_reached_claude loop_R-IN.log loop_R-OUT.log loop_ok.log \
      detach_R-OUT.log detach_ok.log .loop_lock.* .loop_exit.* .loop_blocks.*

# SIMULTANEITY, because "atomic by construction" is a claim this repo has been
# wrong about before. AGENT-2, the ATTACK cycle on its own H8 lock. The checks
# above construct a lock that ALREADY EXISTS; none of them constructs two
# launchers arriving at the same instant, and check 11 above measures the runaway
# fuse losing 10 of 20 concurrent fires (H13) -- a suite written FOR a
# shared-state defect that contained no concurrency until that check.
#
# FALSIFIER, STATED BEFORE THE RUN: if N simultaneous launchers on one callsign
# ever yield two processes reaching a turn, the lock is decoration. It did not
# fire -- 20 launchers, 1 survivor, 19 refused as HELD, 0 unaccounted.
#
# N=20 deliberately matches H13's concurrency measurement so the two numbers are
# comparable: same fleet, same machine, one mechanism holds and one does not.
cp "$ROOT/run_loop.sh" ./run_loop.sh
mkdir -p bin
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster for this check only\nRACE-1\n' > roster.txt
printf '# scratch\n' > prompts/RACE-1.md
: > reached_claude; : > race.log
for _i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
  ( PATH="$T/bin:$PATH" CALLSIGN=RACE-1 MAX_TURN=5 bash ./run_loop.sh >>race.log 2>&1 ) &
done
wait
sleep 2
check "20 simultaneous launchers on one callsign leave ONE survivor"          \
      "$(sort -u reached_claude | grep -c .)" "1"
check "  the other 19 are refused as HELD"                                    \
      "$(grep -c 'is HELD by live launcher' race.log)" "19"
# A survivor count of 1 with 19 refusals is not the same evidence as a survivor
# count of 1 alone: the first run of this probe returned 0 AND 0, because the
# roster gate (run_loop.sh v7) refused every launcher before the lock was
# reached. 0 survivors reads like a pass on the falsifier as stated, and it was a
# probe that never arrived (A29). The two counts must sum to 20 or nothing here
# is evidence.
check "  every launcher is accounted for"                                     \
      "$(( $(sort -u reached_claude | grep -c .) + $(grep -c 'is HELD by live launcher' race.log) ))" "20"
for lkpid in $(cat .loop_lock.RACE-1 2>/dev/null); do kill "$lkpid" 2>/dev/null; done
rm -f roster.txt prompts/RACE-1.md reached_claude race.log
rm -rf fake run_loop.sh launcher_reached_claude loop_L9.log loop_RACE-1.log .loop_lock.* .loop_exit.* .loop_blocks.*

# STAGGERED ARRIVAL — THE WINDOW THE BLOCK ABOVE CANNOT SEE. ok-1, H61.
#
# The simultaneity block is 20 launchers at ONE instant, and that is the one
# arrival time the old `sleep 1` did cover: all 20 hit the lock while the first
# parent is still inside its sleep, so 19 are correctly refused. Measured across
# 8 arms in `spikes/H61_lock_handoff/probe_v3.out`, 20-at-once reads
# `1 survivor / 19 parent refusals` with the defect present AND with it fixed —
# i.e. THIS SUITE'S ONLY LOCK CHECK WAS BLIND TO THE DEFECT, which is why the row
# was filed claiming "the check that fails when it breaks already exists". It did
# not. A second arrival time is a different check, not a variant of this one.
#
# The window is between the PARENT's exit and the CHILD's reclaim: the lock names
# a dead pid, the liveness test correctly calls it stale, and a launcher arriving
# there is admitted by the parent and refused later BY ITS OWN CHILD — into
# detach_$CALLSIGN.log, after the parent printed `detached` and exited 0.
#
# FALSIFIER, STATED BEFORE THE RUN and run: revert run_loop.sh's condition wait
# to `sleep 1` and this block must go RED. It does — `refused_by_parent` reads 0
# and `refused_by_child` reads 1. Evidence: `spikes/H61_lock_handoff/RESULT.md`.
#
# WHAT THIS BLOCK DOES NOT ASSERT, deliberately: a double admission. There isn't
# one — the child's own lock check still catches the second lane. The defect is
# WHERE the refusal is printed, so that is what is asserted. Asserting the
# survivor count alone would be green under the defect (it is: 1 either way).
awk '{ if ($0 ~ /^LOCK="\.loop_lock\.\$\{CALLSIGN\}"$/)
         print "[ -n \"${KF_DETACHED:-}\" ] && sleep 3   # H61: a slow child";
       print }' "$ROOT/run_loop.sh" > run_loop.sh
chmod +x run_loop.sh              # `nohup "$0"` re-execs BY PATH: a 644 copy
                                  # detaches a child that dies at exec, which is
                                  # how this block first ran (0 survivors, 0
                                  # refusals) — caught by the accounting check.
                                  # AND THE NAME IS LOAD-BEARING: the lock's
                                  # liveness test is `ps -o command= | grep -q
                                  # 'run_loop\.sh'`, so a copy under any other
                                  # name is not recognised as a launcher, every
                                  # held lock reads stale, and this block
                                  # measured 2 survivors — a double admission it
                                  # had manufactured itself.
# An injection that missed its anchor leaves a block testing an unmodified
# launcher and reporting a pass — H62 class 1, and `edits.anchored_replace` exists
# because a str.replace no-op shipped that way. So the injection is asserted.
check "H61: the slow-child injection reached the launcher copy"               \
      "$(grep -c 'H61: a slow child' run_loop.sh)" "1"
mkdir -p bin prompts
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo "$$" >> reached_claude
sleep 8                       # hold the turn: lane A is ALIVE when B arrives.
echo LOOP-HALT > ".loop_exit.${CALLSIGN}"
STUB
chmod +x bin/claude
printf '# scratch roster for this check only\nRACE-2\n' > roster.txt
printf '# scratch\n' > prompts/RACE-2.md
: > reached_claude; : > race.log
( PATH="$T/bin:$PATH" CALLSIGN=RACE-2 MAX_TURN=60 bash ./run_loop.sh >>race.log 2>&1 ) &
sleep 1.5          # after a 1 s parent sleep, before a 3 s child's reclaim
( PATH="$T/bin:$PATH" CALLSIGN=RACE-2 MAX_TURN=60 bash ./run_loop.sh >>race.log 2>&1 ) &
wait
sleep 4
h61_surv=$(sort -u reached_claude | grep -c .)
h61_parent=$(grep -c 'is HELD by live launcher' race.log)
h61_child=$(grep -c 'is HELD by live launcher' detach_RACE-2.log 2>/dev/null)
h61_child=${h61_child:-0}         # `grep -c` exits 1 on zero matches, so `|| echo
                                  # 0` appends a SECOND 0 and the arithmetic below
                                  # dies on "0\n0". Absent file -> empty -> 0.
check "H61: a launcher arriving in the handoff window is refused BY THE PARENT"  \
      "$h61_parent" "1"
check "  and not in the detach log the caller never reads"                       \
      "$h61_child" "0"
# The bounded wait's own report, in the direction it must NOT fire: a healthy
# handoff completes well inside 10 s, so this going non-zero means the wait was
# shortened or the child stopped reclaiming.
check "  and the parent does not warn about an unclaimed lock"                   \
      "$(grep -c 'has not claimed' race.log)" "0"
# v4, H178. THE SUM BELOW IS NOT A VERDICT ON `h61_surv` AND WAS THE ONLY PLACE
# IT APPEARED. 0 admitted + 2 refused sums to the same 2 as 1 admitted + 1
# refused, and the red run in spikes/H178_suite_flake/failing_run_4.txt is that
# exact state passing this control seven lines under the check it contradicts.
# Pinned on its own, in the direction that matters: the fixture is worthless if
# no lane ever started, and that is a different report from "refused twice".
check "  and exactly one launcher reached the turn"                              \
      "$h61_surv" "1"
# Same accounting rule as the block above, for the same reason: 1 survivor is not
# evidence on its own, and here the two refusal counts are the finding, so a
# launcher that is neither admitted nor refused invalidates both of them.
check "  every launcher is accounted for"                                        \
      "$(( h61_surv + h61_parent + h61_child ))" "2"
for lkpid in $(cat .loop_lock.RACE-2 2>/dev/null); do kill "$lkpid" 2>/dev/null; done
rm -f roster.txt prompts/RACE-2.md reached_claude race.log run_loop.sh \
      detach_RACE-2.log loop_RACE-2.log .loop_lock.* .loop_exit.* .loop_blocks.*

# WHAT THE SPAN CAP COUNTS, AND WHAT IT CANNOT SEE. ok-1, H11.
#
# Section 7 above drives the hook directly and proves the cap FIRES. It says
# nothing about scope, and scope is the row: `run_loop.sh:387` clears
# .loop_blocks.$CALLSIGN at every span start, so the count bounds ONE `claude -p`
# and not a lane's life. That is the right scope -- MISSION_LOOP §7 defines
# LOOP-FUSE as "a session span ended" -- but nothing pinned it, so a future
# "fix" that made the counter persist would silently convert a span bound into a
# lifetime bound and no check would notice.
#
# The second arm is the finding: a blocked stop exists only when the agent RAN
# and tried to end a turn, so a span in which `claude` exits instantly increments
# NOTHING. That is the only runaway this fleet has recorded -- 18 consecutive
# instant-exit spans on "You've hit your session limit" (H56). The counter that
# does see it is a different file, .loop_fails.$CALLSIGN, and this block asserts
# both halves so neither can be quietly re-attributed to the other.
#
# Measured first, in `spikes/H11_fuse_scope/probe.out`: 2,2,2 across three spans
# for the running arm, ABSENT at every observation for the crash-loop arm.
# ITS OWN STUB DIRECTORY, AND THAT IS NOT TIDINESS. Every launcher block above
# writes `$T/bin/claude` and starts launchers that DETACH; those survive the
# block that started them, and each new span re-resolves `claude` on the PATH
# they inherited. So a lane from an earlier block runs THIS block's stub. It is
# not a hypothesis: with a shared `bin/`, the crash-loop arm below read
# `ABSENT,ABSENT,ABSENT` while `.loop_fails.FUSE-1` read 2 — three stub runs, two
# of them this block's — reproducibly, twice. A stale lane cannot forge the
# per-lane files, so the contamination shows up as an extra line from a lane that
# is not mine, which is why every line is TAGGED with the callsign that wrote it
# and the checks read only their own. Filed as a queue row for the general case;
# fixed here for this block. ok-1, H11.
cp "$ROOT/run_loop.sh" ./run_loop.sh; chmod +x run_loop.sh
mkdir -p bin11 prompts
printf '# scratch roster for this check only\nFUSE-1\n' > roster.txt
printf '# scratch\n' > prompts/FUSE-1.md
mine() { grep -c "^FUSE-1 $1\$" seen.log; }
cat > bin11/claude <<'STUB'
#!/usr/bin/env bash
# an agent that RUNS and ends two turns, which is what invokes the Stop hook
n=$(( $(cat spans 2>/dev/null || echo 0) + 1 )); echo "$n" > spans
bash ./gate.sh </dev/null >/dev/null 2>&1
bash ./gate.sh </dev/null >/dev/null 2>&1
echo "${CALLSIGN} $(cat ".loop_blocks.${CALLSIGN}" 2>/dev/null || echo ABSENT)" >> seen.log
[ "$n" -ge 2 ] && touch "STOP.${CALLSIGN}"
exit 0
STUB
chmod +x bin11/claude
: > seen.log; rm -f spans .loop_fails.FUSE-1
PATH="$T/bin11:$PATH" KF_DETACHED=1 CALLSIGN=FUSE-1 MAX_TURN=30 BACKOFF_STEP=1 \
  bash ./run_loop.sh >/dev/null 2>&1
# Two spans, each ending two turns. Accumulating would read 2 then 4.
check "the span cap counts two turn ends per span and does NOT accumulate"     \
      "$(mine 2)/$(mine 4)" "2/0"
rm -f STOP.FUSE-1 spans seen.log .loop_blocks.* .loop_exit.* .loop_fails.*

cat > bin11/claude <<'STUB'
#!/usr/bin/env bash
# THE RUNAWAY THAT ACTUALLY HAPPENED: claude exits instantly, the agent never
# runs, no turn ever ends, and so the Stop hook is never invoked.
n=$(( $(cat spans 2>/dev/null || echo 0) + 1 )); echo "$n" > spans
echo "${CALLSIGN} $(cat ".loop_blocks.${CALLSIGN}" 2>/dev/null || echo ABSENT)" >> seen.log
[ "$n" -ge 2 ] && touch "STOP.${CALLSIGN}"
# NOT A VENDOR QUOTA STRING, and the wording is load-bearing (ok-1, H232 cycle,
# 2026-08-19). This fixture used to print "You've hit your session limit" because
# that is the sentence the real runaway printed. run_loop.sh then LEARNED to parse
# it: the quota branch matches "hit your (weekly|usage|session|daily) limit",
# finds no reset time in this stub's output, falls back to 1800 s and SLEEPS.
# MEASURED: this suite hung with `sleep 1800` under its own launcher, twice per
# run, and `spikes/harness/bringup.sh:195` runs this suite synchronously -- so the
# fleet's preflight hung with it. The crash loop is this block's subject; the quota
# path is a different subject and has NO check at all, because any fixture that
# reaches it sleeps for at least 60 s (the parser's floor). Filed, not built here.
# CLASS: a fixture that simulates a failure by printing a REAL vendor string
# becomes an input to whatever later branch learns to parse that string.
echo "stub: instant exit, no vendor message"
exit 1
STUB
chmod +x bin11/claude
: > seen.log; rm -f spans .loop_fails.FUSE-1
PATH="$T/bin11:$PATH" KF_DETACHED=1 CALLSIGN=FUSE-1 MAX_TURN=30 BACKOFF_STEP=1 \
  bash ./run_loop.sh >/dev/null 2>&1
check "  and a crash loop increments it NOT AT ALL"                            \
      "$(mine ABSENT)/$(grep -c '^FUSE-1 [0-9]' seen.log)" "2/0"
# The other half of the same fact: the counter that DOES see a crash loop is a
# different file. Without this the check above is satisfied by a launcher that
# has stopped counting anything, and by one that never ran a second span.
check "  while .loop_fails counts every one of those spans"                    \
      "$(cat .loop_fails.FUSE-1 2>/dev/null)" "2"
rm -f STOP.FUSE-1 spans seen.log run_loop.sh roster.txt prompts/FUSE-1.md \
      loop_FUSE-1.log .loop_blocks.* .loop_exit.* .loop_fails.* .loop_lock.*
rm -rf bin11

# --- H23. AN INSTRUCTION THE COMPONENT DOES NOT OBEY. ok-1, 2026-08-19.
#
# The row's class is NOT a dangling citation (refcheck check 4 covers those). It
# is an interface removed or renamed in code while a SURVIVING SITE STILL
# INSTRUCTS CALLERS TO USE IT -- something that exists and is WRONG, living where
# nobody looks for rules: a runtime's own output string, a journal's "how to stop"
# line. Four sites in one sweep; three fixed by AGENT-1 under H16.
#
# THE ROW STATES THE HARD PART AND IT IS TRUE: a string test cannot separate this
# class in general, because rationale blocks legitimately NAME what was removed.
# Three general detectors were measured on all 45 harness files BEFORE this block
# was written, and all three are reported in spikes/H23_instruction_obeyed/:
#   (i)   any repo path inside an emitted string must exist -- 13 of 32 hits are
#         a suite's own scratch fixtures. 41% false positives; H14's named failure
#         mode, a checker everyone learns to ignore.
#   (ii)  a marker named in a message must appear in non-message code -- 30 hits,
#         28 of them hyphenated English (LIVE-TREE, SELF-REVIEW, FALSE-POSITIVE)
#         or document names. And one "orphan" was `echo LOOP-FUSE > "$EXIT_MARK"`,
#         a FILE WRITE my own classifier had counted as a message: the instrument
#         could not tell its two inputs apart, which is this session's own class.
#   (iii) `<interpreter> <repo path>` inside a message, which IS an instruction by
#         grammar -- 3 sites fleet-wide, 0 unresolved. Real but nearly empty.
# So this block takes the row's OWN F1 instead, which is exact and has no false
# positives by construction: THE HOOK'S REFUSAL MESSAGE IS AN INSTRUCTION, AND
# THE HOOK MUST OBEY IT. Both sets are read out of the SAME file, so they cannot
# drift apart without this going red.
gate_vocab() {                     # $1 = a hook; echoes "equal", "differ:..." or "empty:..."
  _acc=$(grep -E '^[[:space:]]*(LOOP-[A-Z]+\|)*LOOP-[A-Z]+\)' "$1" \
         | grep -oE 'LOOP-[A-Z]+' | sort -u | tr '\n' ' ')
  _msg=$(grep '"decision":"block"' "$1" | grep -oE 'LOOP-[A-Z]+' | sort -u | tr '\n' ' ')
  # AN EMPTY EXTRACTION MUST NOT READ AS AGREEMENT. Two empty sets are equal, and
  # that is exactly how a check reports green after the thing it greps for is
  # renamed -- the e3b0c442 shape, an empty capture hashed as data.
  if [ -z "$_acc" ] || [ -z "$_msg" ]; then echo "empty:[$_acc][$_msg]"; return; fi
  if [ "$_acc" = "$_msg" ]; then echo equal; else echo "differ:[$_acc][$_msg]"; fi
}
check "H23: the hook's refusal message names exactly the markers it ACCEPTS"    \
      "$(gate_vocab "$GATE")" "equal"
check "  and the vocabulary is the three §7 signals, not an empty grep"         \
      "$(grep -E '^[[:space:]]*(LOOP-[A-Z]+\|)*LOOP-[A-Z]+\)' "$GATE" | grep -oE 'LOOP-[A-Z]+' | sort -u | grep -c .)" "3"
# THE CONTROL, WITH ITS INPUT NAMED (§5: a control that cannot fail is not a
# control). Remove ONE marker from the accept branch of a COPY and the check above
# must go red. The mutation is asserted, because a sed whose anchor is absent
# returns the input unchanged and would leave this arm testing the unmutated hook.
sed 's/LOOP-DONE|LOOP-HALT|LOOP-IDLE)/LOOP-DONE|LOOP-HALT)/' "$GATE" > mutated_gate.sh
check "  the mutation reached the accept branch"                                \
      "$(grep -c 'LOOP-DONE|LOOP-HALT)' mutated_gate.sh)" "1"
case "$(gate_vocab mutated_gate.sh)" in
  differ:*) ok "  and a hook that stops accepting LOOP-IDLE while still promising it FAILS" ;;
  *)        bad "  a hook that stops accepting LOOP-IDLE while still promising it PASSES -- the check is inert" ;;
esac
# The message also names the FILE a lane must write and three artifacts it must
# refresh. §12.4 wants those resolved mechanically, and they are NOT backticked,
# so refcheck check 4 -- which matches backticked paths only -- does not see them.
h23_sig=$(grep '"decision":"block"' "$GATE" | grep -oE '\.loop_[a-z]+' | sort -u)
check "  the signal file the message names is the one the hook READS"           \
      "$(grep -c "SIGFILE in \"${h23_sig}\." "$GATE")" "1"
h23_missing=0
for a in $(grep '"decision":"block"' "$GATE" | grep -oE '[A-Za-z_][A-Za-z_.]*\.md' | sort -u); do
  [ -f "$ROOT/$a" ] || { h23_missing=$((h23_missing+1)); printf '  info  the hook instructs every lane to refresh %s, which is absent\n' "$a"; }
done
check "  every artifact the message instructs a lane to update EXISTS"          \
      "$h23_missing" "0"
rm -f mutated_gate.sh

echo
if [ "$fail" -eq 0 ]; then
  echo "loop_gate.sh: ${pass} checks pass"
  exit 0
fi
# H178: the count is DATA-DEPENDENT -- the settings.json block iterates over
# tracked files and their commands -- so a changed TOTAL is not the same event as
# a failure, and two sightings of "N FAILED" were read as one thing.
if [ "$treefail" -gt 0 ] && [ "$treefail" -eq "$fail" ]; then
  echo "loop_gate.sh: ${fail} FAILED, ${pass} passed — ALL of them are LIVE-TREE observations"
  echo "  (installed gates vs their sources, tracked settings.json). Another lane"
  echo "  between an edit and a reinstall produces exactly this. The contract checks,"
  echo "  which run in \$T, all passed. Re-run before reading it as a regression."
elif [ "$treefail" -gt 0 ]; then
  echo "loop_gate.sh: ${fail} FAILED, ${pass} passed — ${treefail} of the failures are LIVE-TREE observations, $((fail - treefail)) are contract checks"
else
  echo "loop_gate.sh: ${fail} FAILED, ${pass} passed — the loop contract is not enforceable as written"
fi
exit 1
