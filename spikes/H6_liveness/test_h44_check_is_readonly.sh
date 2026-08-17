#!/usr/bin/env bash
# test_h44_check_is_readonly.sh — H44, ATOM-3, 2026-08-17.
#
# TWO DEFECTS UNDER TEST, both in `spikes/harness/bringup.sh`, both mine.
#
# 1. `--check`, documented as "verify only, launch nothing", WROTE. `CHECK_ONLY`
#    was tested at exactly one place in the file — the launch decision — so the
#    flag was literally true and materially misleading: section 3 reinstalled
#    `.git/hooks/` (the shared enforcing gates, for every lane in this working
#    tree) and section 6 deleted loop state. A read-only flag that writes is
#    worse than no flag, because it is the one people run when being careful.
#
# 2. Section 6 SWEPT EVERY LANE'S TERMINAL SIGNAL, not the lanes it was about to
#    start. Its own comment says "a signal for a lane we are ABOUT to start" and
#    the loop said `.loop_signal.*`. `.loop_exit.$CALLSIGN` exists for the seconds
#    between the Stop hook writing it and `run_loop.sh` reading it; deleting it in
#    that window means the lane misses its own terminal signal and keeps looping
#    after being told to stop. H16 inverted — and the worse direction, because
#    H16's failure prints "terminal signal, exiting" in the log and this one is
#    silent.
#
# FALSIFIER, STATED BEFORE THE RUN: C1 runs the OLD loop verbatim and must DELETE
# the marker. If it does not, the finding is wrong and everything below is
# theatre. C4 runs the NEW loop with the guard OFF and must still clear a genuinely
# stale signal — if it does not, the "fix" is just the control switched off, which
# is the one repair this repo forbids.
#
# INTERPRETER: bash, deliberately, and `bash <<` rather than the caller's shell.
# An earlier run of C1 silently did nothing because zsh errors on an unmatched
# glob where bash leaves the literal, so the loop never executed and the probe
# reported SURVIVED. A probe run under a different interpreter than the code it
# tests measures the interpreter.
#
# run: bash spikes/H6_liveness/test_h44_check_is_readonly.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)
SUT="$ROOT/spikes/harness/bringup.sh"

pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }

SCRATCH="$ROOT/spikes/H6_liveness/.scratch.$$"
cleanup() { rm -rf "$SCRATCH"; rm -f "$ROOT/.loop_exit.KFSTALE-9"; }
trap cleanup EXIT
mkdir -p "$SCRATCH"

# The NEW loop, read out of the file under test so a revert turns these red.
NEWLOOP=$(sed -n '/^for f in \.loop_signal\.\* \.loop_exit\.\*; do/,/^done$/p' "$SUT")
[ -n "$NEWLOOP" ] || { echo "  FAIL could not extract the signal loop from $SUT"; exit 1; }
LANEPID=$(sed -n '/^lane_pid() {/,/^}/p' "$SUT")

echo "H44 · --check must not write, and a live lane's signal is not stale"
echo

# One runner for C1-C4: seed a marker, run a loop body in the scratch dir,
# report whether the marker survived. Bodies run in a subshell so `note`,
# CHECK_ONLY and lane_pid stubs cannot leak between checks.
probe() {   # probe <lane> <check_only> <body>
  ( cd "$SCRATCH" || exit 9
    rm -f .loop_signal.* .loop_exit.* 2>/dev/null
    printf 'LOOP-HALT' > ".loop_exit.$1"
    CHECK_ONLY="$2"; problems=0
    note() { :; }
    eval "$LANEPID"
    eval "$3" >/dev/null 2>&1
    [ -f ".loop_exit.$1" ] && echo kept || echo gone )
}

OLDLOOP='for f in .loop_signal.* .loop_exit.*; do
  case "$f" in *"*"*) continue ;; esac
  case "$f" in *.last) continue ;; esac
  rm -f "$f"
done'

# ---- C1 . the falsifier: the OLD loop deletes a signal regardless of whose ----
r=$(probe KFSTALE-9 no "$OLDLOOP")
[ "$r" = gone ] && ok "C1 falsifier fires - the OLD loop deletes any lane's signal" \
                || bad "C1 falsifier did NOT fire (marker $r); the defect is not reproducible and C2-C4 mean nothing"

# ---- C2 . the NEW loop LEAVES a live lane's signal alone --------------------
# A real process carrying the launch prompt, so lane_pid resolves it exactly as
# it resolves a lane. `:` is the no-op builtin - nothing is executed.
bash -c ': claude -p You are KFLIVE-9. ; sleep 25' &
livepid=$!
sleep 1
r=$(probe KFLIVE-9 no "$NEWLOOP")
[ "$r" = kept ] && ok "C2 a LIVE lane's signal survives the sweep (guard off, so this is the live-check alone)" \
                || bad "C2 a live lane's terminal signal was DELETED - the lane would miss its own stop"
kill "$livepid" 2>/dev/null; wait "$livepid" 2>/dev/null

# ---- C3 . under --check, even a genuinely stale signal is left alone --------
r=$(probe KFSTALE-9 yes "$NEWLOOP")
[ "$r" = kept ] && ok "C3 --check clears nothing, even a genuinely stale signal" \
                || bad "C3 --check DELETED a file; the flag still writes"

# ---- C4 . with the guard OFF the control still works -----------------------
# The check that stops the "fix" from being the feature switched off.
r=$(probe KFSTALE-9 no "$NEWLOOP")
[ "$r" = gone ] && ok "C4 without --check a genuinely stale signal IS still cleared (H16 stays fixed)" \
                || bad "C4 the stale-signal control no longer fires - the guard disabled the feature"

# ---- C5 · no invented flag -------------------------------------------------
# I wrote `install_hooks.sh --check` into the guard, then resolved the reference
# mechanically (§12.4) and found no such flag. A gate citing a flag that does not
# exist reads as satisfied and silently never runs.
# COMMENTS STRIPPED FIRST. This check failed on its own first run by matching the
# rationale comment that says "NOT `install_hooks.sh --check`: that flag does not
# exist" -- a checker that cannot tell a USE from a MENTION, which is A30 and is
# the same defect I had just reported in refcheck.py. Caught by the check going
# red against a fix that was already correct.
if grep -vE '^[[:space:]]*#' "$SUT" | grep -q 'install_hooks.sh --check'; then
  bad "C5 bringup.sh calls 'install_hooks.sh --check'; that flag is not parsed by install_hooks.sh"
elif grep -q 'install_hooks' "$SUT"; then
  ok "C5 the --check path does not invoke a flag install_hooks.sh does not parse"
else
  bad "C5 install_hooks is no longer referenced at all — section 3 has gone missing"
fi

# ---- C6 · end to end, the real invocation ----------------------------------
# The only check that exercises the actual command a lane or launchd would run.
before=$(find "$ROOT/.git/hooks" -type f -exec shasum {} + 2>/dev/null | shasum | cut -d' ' -f1)
printf 'LOOP-HALT' > "$ROOT/.loop_exit.KFSTALE-9"
sh "$SUT" --check >/dev/null 2>&1
after=$(find "$ROOT/.git/hooks" -type f -exec shasum {} + 2>/dev/null | shasum | cut -d' ' -f1)
[ -n "$before" ] || bad "C6 could not hash .git/hooks before the run; the comparison is vacuous"
if [ "$before" = "$after" ]; then ok "C6 a real 'bringup.sh --check' left .git/hooks byte-identical"
else bad "C6 'bringup.sh --check' REWROTE .git/hooks ($before -> $after)"; fi
if [ -f "$ROOT/.loop_exit.KFSTALE-9" ]; then ok "C6b a real 'bringup.sh --check' left a seeded signal in place"
else bad "C6b 'bringup.sh --check' deleted loop state"; fi

# ---- C7 . the STOP gate: bring-up must refuse into a halted fleet ----------
# Extracted and run in a scratch dir. STOP is FLEET-WIDE and constructing it for
# real would halt every lane, so the branch is exercised in isolation -- the same
# reason C1-C4 extract the signal loop instead of running the launcher.
ROOTSUT="$ROOT/bringup.sh"
STOPBLOCK=$(sed -n '/^if \[ -f STOP \]; then$/,/^fi$/p' "$ROOTSUT" | head -20)
if [ -z "$STOPBLOCK" ]; then
  bad "C7 ./bringup.sh has NO STOP gate -- it would relaunch a deliberately halted fleet every 600s"
else
  # v2 (H44 cycle 3, ATOM-3): the eval is NESTED IN ITS OWN SUBSHELL. `exit 1`
  # inside `eval` terminates the COMMAND SUBSTITUTION, so `echo "$?"` never ran
  # and r was EMPTY -- the refusing arm could not report the refusal it exists to
  # test, while the C7b arm (whose path does not exit) reported fine. One-sided,
  # in the A29 direction where the free answer is the passing one, and family A:
  # the instrument could not express its verdict. Measured before fixing: old
  # form r=[], new form r=[1], and r=[0] with the `exit 1` deleted from the
  # block -- so the new form is two-sided and can still fail.
  r=$( cd "$SCRATCH" && : > STOP; ( CHECK_ONLY=0; eval "$STOPBLOCK" ) >/dev/null 2>&1; echo "$?" )
  [ "$r" = 1 ] && ok "C7 ./bringup.sh refuses (exit 1) with STOP present" \
                || bad "C7 STOP gate did not refuse (exit '$r'); a halted fleet gets relaunched"
  r=$( cd "$SCRATCH" && ( CHECK_ONLY=1; eval "$STOPBLOCK" ) >/dev/null 2>&1; echo "$?" )
  [ "$r" = 0 ] && ok "C7b --check still REPORTS under STOP instead of exiting (a census is not a launch)" \
                || bad "C7b --check exited $r under STOP; the read-only path must still report"
  rm -f "$SCRATCH/STOP"
fi

# ---- C8 . HALTED is distinguished from DOWN --------------------------------
# The census reported a deliberately retired lane as DOWN, and DOWN reads as
# "restore me". That is what invited a relaunch into a halted fleet.
if grep -q 'HALTED' "$ROOTSUT" && grep -q 'STOP\.\$lane' "$ROOTSUT"; then
  ok "C8 the census distinguishes HALTED (fleet or per-lane STOP) from DOWN"
else
  bad "C8 the census collapses HALTED into DOWN again -- retired and dead read the same"
fi

# ---- C9 . never launch from a launcher that does not parse -----------------
# Earned: a lane edited run_loop.sh in place and three wrappers plus every
# relaunch for ten minutes died with a syntax error, into detach_*.log where
# nothing reads it, while bringup.log recorded each attempt as "launched".
if grep -vE '^[[:space:]]*#' "$ROOTSUT" | grep -q 'bash -n ./run_loop.sh'; then
  ok "C9 the launch path runs 'bash -n ./run_loop.sh' before starting anything"
else
  bad "C9 no parse gate -- a half-written launcher takes the fleet down silently"
fi
# Two-sided: the mechanism must actually detect a broken script, or C9 is a
# structural assertion about a call that cannot fail.
printf 'if true; then\n  echo "unclosed (\n' > "$SCRATCH/broken.sh"
printf 'echo ok\n' > "$SCRATCH/fine.sh"
if bash -n "$SCRATCH/fine.sh" 2>/dev/null && ! bash -n "$SCRATCH/broken.sh" 2>/dev/null; then
  ok "C9b 'bash -n' accepts a good script and rejects a broken one"
else
  bad "C9b 'bash -n' does not discriminate here; C9's gate cannot fire"
fi

# ---- C10/C11 . the headers' OWN facts, checked instead of asserted ---------
# CLASS: A PROSE HEADER ASSERTING A CHECKABLE FACT ABOUT ANOTHER ARTIFACT, WITH
# NOTHING CHECKING IT. Earned by this row's own first draft: `./bringup.sh`'s
# header said `spikes/harness/bringup.sh` was "UNTRACKED, 228 lines" and this
# file "163 lines". It had been TRACKED since 600d138, 28 minutes before that
# sentence was written, and the counts were 273 and 230 at HEAD. Measured once,
# early, then restated in FOUR documents. That is the claim decay CLAUDE.md
# names as un-mechanisable -- so mechanise the part that IS: the header's two
# load-bearing facts, and a ban on the form that rotted.

# C10: both copies are tracked, and neither header may claim otherwise. Fails if
# a copy is ever untracked (the state the header used to assert) or if the word
# UNTRACKED comes back to describe the sibling.
# SCOPED TO THE FILE-MAP, and this was measured the hard way: C10 and C12 both
# fired on their FIRST run against the CORRECTION BLOCK that quotes the wrong
# text -- a pattern matching the prose that quotes the thing it looks for.
# ATTACKER-1 recorded that class under H48 after hitting it twice in one row; a
# correction that names what it withdrew is required by §5, so a gate that
# refuses on the quotation makes the two rules contradict. `factmap` stops at
# the first correction block AND at the first non-comment line, so it reads only
# the part a reader takes as current fact.
factmap() { awk '!/^#/{exit} /^# CORRECTED/{exit} {print}' "$1"; }
c10=0
for f in bringup.sh spikes/harness/bringup.sh; do
  git ls-files --error-unmatch "$ROOT/$f" >/dev/null 2>&1 || {
    c10=1; bad "C10 $f is NOT tracked -- a header that calls it tracked is now false"; }
  # The delimiter must exist, or `factmap` silently widens to the whole header
  # and C12 starts reading prose it was never scoped to. Fail loud, not open.
  grep -q '^# CORRECTED' "$ROOT/$f" || {
    c10=1; bad "C10 $f has no '# CORRECTED' delimiter; factmap's scope is unbounded"; }
done
factmap "$ROOTSUT" | grep -q 'UNTRACKED' && {
  c10=1; bad "C10 ./bringup.sh's file-map calls the sibling UNTRACKED again; git says otherwise"; }
[ "$c10" = 0 ] && ok "C10 both copies tracked, and no file-map claims the sibling is not"

# C11: the header names the path the LOADED LaunchAgent actually runs. Read out
# of launchd and the installed plist, never from the repo's copy of it -- the
# repo copy is what a lane can edit and the installed one is what runs, which is
# the whole H44 distinction. SKIPS rather than passes when launchd has no such
# job: a check that cannot observe its subject must not report a verdict (A15).
AGENT="$HOME/Library/LaunchAgents/com.kingfisher.bringup.plist"
if launchctl list 2>/dev/null | grep -q 'com\.kingfisher\.bringup' && [ -f "$AGENT" ]; then
  # From the <string> ELEMENT, not a loose path grep: the first version matched
  # `INVOKED VIA /bin/bash, NOT /bin/sh, AND THAT IS LOAD-BEARING. bringup.sh`
  # out of a COMMENT and reported launchd running it. A plist comment is not a
  # ProgramArguments entry, and a check that cannot tell them apart is reading
  # prose about the instrument instead of the instrument.
  loaded=$(sed -n 's|.*<string>\(/[^<]*bringup\.sh\)</string>.*|\1|p' "$AGENT" | head -1)
  if [ "$loaded" = "$ROOT/bringup.sh" ]; then
    ok "C11 the loaded LaunchAgent names ./bringup.sh, as both headers state"
  else
    bad "C11 launchd runs '$loaded', NOT $ROOT/bringup.sh -- both headers are wrong"
  fi
else
  printf '  SKIP C11 com.kingfisher.bringup is not loaded here; nothing to observe\n'
fi

# C12: no line-count assertion about a repo file may return to either header.
# The form itself is the defect -- it is stale on the next edit and tells the
# reader nothing `wc -l` would not. Two-sided by construction: it fires on the
# exact string that was there.
if { factmap "$ROOTSUT"; factmap "$SUT"; } | grep -qE '[0-9]{2,4} lines'; then
  bad "C12 a line-count claim is back in a bringup.sh header; it goes stale on the next edit"
else
  ok "C12 neither bringup.sh header asserts a line count"
fi

echo
echo "-------------------------------------------------------------"
printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
