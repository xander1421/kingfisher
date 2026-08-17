#!/usr/bin/env bash
# check_live_launcher.sh v1 — A24 applied to a RUNNING PROCESS.
#
# THE DEFECT IT EXISTS FOR (H21, found 2026-08-17 by ATTACK cycle 18):
# `run_loop.sh` was fixed at 11:52 and 12:00. Every live launcher started at
# 11:49. They were still executing the OLD code, and nothing anywhere said so.
#
# MEASURED, not argued -- /tmp probe, a bash script editing itself mid-run:
#   * the loop body kept the PRE-EDIT text for every remaining iteration;
#   * and bash resumed reading AFTER the loop at a stale byte offset, dying with
#     `unexpected EOF while looking for matching '"'`.
# Bash parses a top-level `while ... done` once and runs it from memory, so a
# long-running launcher never sees an edit, and the code after its loop can be
# read as garbage.
#
# THE ASYMMETRY THAT MAKES "FIXED" AMBIGUOUS, and it is why this check is only
# about the launcher:
#   * `loop_gate.sh` is a FRESH PROCESS per turn end -- a hook fix is live at the
#     next stop, no relaunch needed. (Verified: the refusal text now names
#     .loop_signal.$CALLSIGN, which was edited at 11:52 into lanes spawned 11:49.)
#   * `run_loop.sh` is a LONG-RUNNING process -- a launcher fix is live only at
#     the next relaunch. H16 and the v4 callsign whitelist are both in this state
#     right now.
#
# A24 says a digest pins which artifact, not what is in it. This is the same
# sentence about processes: the file on disk is not the code that is running, and
# `git log` cannot tell you which lanes have the fix.
#
# REFUSES, per the harness rule that a gate refuses rather than warns.
# usage: bash spikes/harness/check_live_launcher.sh [--selfcheck]
# exit 0 = every live launcher is at or newer than run_loop.sh.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LAUNCHER="$ROOT/run_loop.sh"

# macOS `ps` prints lstart as "Mon Aug 17 11:49:21 2026". Parsed rather than
# regex-sliced so a format change fails loudly instead of comparing nonsense.
start_epoch() { date -j -f "%a %b %d %T %Y" "$1" +%s 2>/dev/null; }

# THE REFERENCE INSTANT a process's start time is compared against (v2, H59).
# A FUNCTION, and the body and --selfcheck both call it, deliberately: if this
# is reverted to the working-tree mtime the selfcheck goes red, which is the
# only structure that makes the selfcheck a test of the CODE rather than of a
# fixture. Prints "<epoch> <description>"; description is carried into every
# message so the verdict always says what it was measured against.
launcher_ref() {   # launcher_ref <repo-dir> <launcher-path>
  _d=$1; _f=$2 _c=
  _c=$(cd "$_d" && git log -1 --format=%ct -- "$(basename "$_f")" 2>/dev/null)
  if [ -n "$_c" ]; then
    printf '%s newest commit touching %s (%s)\n' "$_c" "$(basename "$_f")" \
      "$(cd "$_d" && git log -1 --format=%h -- "$(basename "$_f")")"
  else
    # No git, or the launcher was never committed. Fall back to mtime and SAY
    # SO: the fallback IS v1's weaker comparison, and a fallback that reads
    # identically to the fixed path is how a silent regression survives.
    printf '%s working-tree mtime (NO COMMIT FOUND -- this is v1s weaker comparison)\n' \
      "$(stat -f %m "$_f")"
  fi
}

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3: the check ships a check. Both directions, because a comparison that
  # only ever sees one side is the happy-path coverage that let H1's 15-check
  # suite pass over a live defect.
  now=$(date +%s)
  fail=0
  stale_case=$(( now - 600 )); fresh_case=$(( now + 600 ))
  [ "$stale_case" -lt "$now" ] || { echo "SELFCHECK FAIL: stale not detected"; fail=1; }
  [ "$fresh_case" -ge "$now" ] || { echo "SELFCHECK FAIL: fresh misreported"; fail=1; }
  e=$(start_epoch "$(date '+%a %b %d %T %Y')")
  [ -n "$e" ] || { echo "SELFCHECK FAIL: cannot parse this platform's lstart"; fail=1; }

  # v2 (H59). THE CHECK THAT FAILS WHEN v1's DEFECT COMES BACK. Everything above
  # this line passed while the checker was condemning 25 healthy processes,
  # because it only ever tested arithmetic on numbers it made up itself -- which
  # is the shape §12.3 exists to forbid. These two run on a REAL FILE.
  #
  # Scratch inside the workspace (§10), and NEVER on the shared run_loop.sh: a
  # live lane's launcher has not finished reading its own tail (H21), so
  # touching it to test a checker would be the defect under test, committed.
  sc="$ROOT/spikes/harness/.selfcheck.$$"
  mkdir -p "$sc" 2>/dev/null
  ( cd "$sc" && git init -q . 2>/dev/null && printf 'echo v1\n' > run_loop.sh &&
    git add run_loop.sh 2>/dev/null &&
    git -c user.email=selfcheck@local -c user.name=selfcheck commit -qm seed 2>/dev/null ) || {
      echo "SELFCHECK FAIL: could not build the fixture"; rm -rf "$sc"; exit 1; }

  h_before=$(shasum -a 256 "$sc/run_loop.sh" | cut -d' ' -f1)
  commit_t=$(cd "$sc" && git log -1 --format=%ct -- run_loop.sh)
  # Pure mtime bump, identical bytes. The stamp is SET, not slept for: with
  # `sleep 1; touch` the gap was exactly one second, so no integer start time
  # exists strictly between the commit and the touch and the v1 arm could not
  # fire -- a fixture too small to hold the case it was built to demonstrate.
  # That failure is the reason this comment is here; it fired on the first run.
  touch -t "$(date -r $(( commit_t + 10 )) +%Y%m%d%H%M.%S)" "$sc/run_loop.sh"
  h_after=$(shasum -a 256 "$sc/run_loop.sh" | cut -d' ' -f1)
  mtime_t=$(stat -f %m "$sc/run_loop.sh")

  # A. the fixture must actually be the case under test, or B and C prove
  #    nothing. A29: a control asserted against a setup that did not happen
  #    reports the free answer.
  if [ "$h_before" != "$h_after" ] || [ "$mtime_t" -le "$commit_t" ]; then
    echo "SELFCHECK FAIL: fixture did not reproduce a pure mtime bump"; fail=1
  else
    # THE REFERENCE IS TAKEN FROM launcher_ref, THE FUNCTION THE BODY USES.
    # Revert that function to `stat -f %m` and B goes red -- which is what makes
    # this a test of the code and not of arithmetic on numbers I chose.
    r=$(launcher_ref "$sc" "$sc/run_loop.sh"); r_t=${r%% *}
    proc_t=$(( commit_t + 1 ))   # started AFTER the real change, BEFORE the touch

    # B. the defect: v1's reference condemns this process, v2's must not.
    [ "$proc_t" -lt "$mtime_t" ] || \
      { echo "SELFCHECK FAIL: v1 arm cannot fire -- the fixture has no gap to condemn"; fail=1; }
    [ "$proc_t" -ge "$r_t" ] || \
      { echo "SELFCHECK FAIL: a pure mtime bump still condemns a live process (launcher_ref reverted?)"; fail=1; }

    # C. and the check must still catch what it EXISTS for: a process that
    #    started before the last real change IS running pre-fix code. Without
    #    this, "never condemns anything" would pass B, and switching the control
    #    off is the one repair this repo forbids.
    [ "$(( commit_t - 1 ))" -lt "$r_t" ] || \
      { echo "SELFCHECK FAIL: a genuinely stale process is no longer detected"; fail=1; }
  fi
  rm -rf "$sc"

  [ "$fail" -eq 0 ] && echo "selfcheck: lstart parsing, and a pure mtime bump no longer condemns a live process"
  exit "$fail"
fi

[ -f "$LAUNCHER" ] || { echo "REFUSE: no launcher at $LAUNCHER"; exit 1; }

# v2 (H59, ATOM-3, 2026-08-17) — THE DEFECT REMOVED.
#
# v1: `mtime=$(stat -f %m "$LAUNCHER")`, and the verdict it printed was
# `running PRE-FIX code`. Those are two different facts. mtime moves for a
# `touch`, a checkout, a no-op save, or a lane mid-edit on an UNCOMMITTED
# change -- none of which is a fix -- so the entire fleet flips to STALE within
# one second of anyone opening the file.
#
# MEASURED 2026-08-17 16:08, and the verdict was contradicted by an independent
# observable rather than by argument:
#   * v1 printed `REFUSE: 25 of 25 live launcher processes predate run_loop.sh`;
#   * the newest COMMIT touching run_loop.sh was cc1da90 at 14:09:34 (H48, the
#     mid-turn heartbeat beater) and the OLDEST live launcher started 14:29:16,
#     twenty minutes AFTER it;
#   * so the committed fix was running, and it was directly visible: BEAT_EVERY
#     is 30 and all five `.heartbeat.*` read under 30s old. Pre-H48 the beat was
#     written once per turn and lanes read 2255s stale. The one fix the checker
#     said was not running was the one leaving fingerprints every 30 seconds.
#   * the mtime that condemned all 25 was 16:04:09, from an UNCOMMITTED edit a
#     live lane was still writing.
# F1 stated before the run and it did not kill this: a `touch` on a copy moved
# the mtime with a byte-identical sha256, which is the whole thesis in one line.
# F2 likewise: run_loop.sh took 11 commits today, so on a fleet that edits its
# own launcher hourly the green branch is not reachable in practice.
#
# TWO CLASSES, both already named in this repo, which is why this is a fix and
# not a preference:
#   * H35 — a checker that reads the WORKING TREE while its verdict is
#     attributed to the COMMIT. Fourth site; H36 is still open on the third.
#   * H52 — a checker with a permanent non-zero floor is read as background
#     noise. H14 says a flaky gate is a bypassed gate; an always-red gate is
#     bypassed exactly as thoroughly, and this one had been red for hours.
#
# THE FIX IS TO COMPARE AGAINST THE COMMIT, NOT THE FILE. The question the
# caller is asking is "is the fix I committed running?", and git already records
# when content last changed. NO SIDECAR AND NO WRITE OF ANY KIND: a read-only
# diagnostic that writes is H44's defect, fixed two hours ago in bringup.sh.
# An uncommitted edit is now REPORTED, not counted -- no running process can
# have it, which is expected and not a fleet-wide stall.
ref=$(launcher_ref "$ROOT" "$LAUNCHER")
mtime=${ref%% *}
refwhat=${ref#* }
if ! (cd "$ROOT" && git diff --quiet HEAD -- run_loop.sh 2>/dev/null); then
  printf 'EDIT IN FLIGHT: run_loop.sh differs from HEAD (mtime %s). No running\n' \
    "$(date -r "$(stat -f %m "$LAUNCHER")" '+%H:%M:%S')"
  printf '                process can carry an uncommitted change, and that is\n'
  printf '                expected, not a stall. Judged against %s.\n\n' "$refwhat"
fi
stale=0 seen=0

while IFS= read -r line; do
  pid=${line%% *}
  rest=${line#* }
  st=$(start_epoch "$rest")
  [ -n "$st" ] || { echo "REFUSE: cannot parse start time for pid $pid ('$rest')"; exit 1; }
  seen=$((seen + 1))
  if [ "$st" -lt "$mtime" ]; then
    stale=$((stale + 1))
    printf 'STALE  pid %-7s started %s, predates %s (%s) -- running PRE-FIX code\n' \
      "$pid" "$(date -r "$st" '+%H:%M:%S')" "$(date -r "$mtime" '+%H:%M:%S')" "$refwhat"
  fi
done < <(ps -eo pid,lstart,command | grep '[r]un_loop.sh' | awk '{print $1, $2, $3, $4, $5, $6}')

if [ "$seen" -eq 0 ]; then
  echo "no live launcher: nothing to be stale (this is not a pass, it is an absence)"
  exit 0
fi
if [ "$stale" -gt 0 ]; then
  echo "REFUSE: $stale of $seen live launcher processes predate the $refwhat."
  echo "        Their fixes are COMMITTED and NOT running. Relaunch is the only cure;"
  echo "        editing the file again changes nothing for them, and can corrupt"
  echo "        the tail they have not read yet."
  exit 1
fi
echo "all $seen live launcher processes are at or newer than the $refwhat"
exit 0
