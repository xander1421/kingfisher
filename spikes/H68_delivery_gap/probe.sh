#!/usr/bin/env bash
# H68 — probe.sh v1. ATTACKER-1, 2026-08-17, cycle 18.
# Run: sh spikes/H68_delivery_gap/probe.sh     (exit 1 if any check fails)
#
# THE QUESTION
# ------------
# H56 made `bringup.sh` refuse a lane that is up and PRODUCING NOTHING. One hour
# later the same census still said `quorum: 5/5` over a fleet that is up and
# running SUPERSEDED CODE. Same class -- a signal about the SUPERVISOR and not the
# WORK -- at a second site in the file H56 fixed. §12.2 against its own author,
# inside one cycle. So: is there any route from "launcher fix committed" to
# "launcher fix running", and does anything say when there is not?
#
# THREE MEASURED FACTS (each reproduced by this probe against the live tree)
#   P1  NO EXECUTABLE CALLED `check_live_launcher.sh`. Every reference was prose.
#   P2  `bringup.sh` had no notion of staleness and `MISSING` is its only launch
#       list, so a live-but-stale lane is neither MISSING nor HALTED and no path
#       in the scheduled monitor can replace one.
#   P3  `HUMAN_NEEDED.md`'s relaunch ask was closed "RESOLVED BY EVENTS" against
#       "the newest commit touching run_loop.sh" -- a reference that MOVES on every
#       launcher edit, so RESOLVED could only ever be instantaneously true.
#
# FALSIFIERS POSTED TO CHANNEL.md BEFORE THIS FILE EXISTED
#   F1  if any `bringup.sh` path can replace a LIVE lane, P2 is wrong.
#   F2  if any executable invokes the staleness check, P1 is wrong.
#   F3  SCOPE BOUND. If the inert generation is functionally equivalent to HEAD,
#       this is bookkeeping. **F3 BIT: the CLAIM said "superseded four versions
#       ago" and exactly ONE commit is inert** -- `90decab`, this lane's own v9.
#       The magnitude is withdrawn; the gap is not, because the one thing that
#       cannot reach the fleet is the counter that would have surfaced the
#       86-minute outage. Counted here, never asserted.
#
# CONTROLS
#   C1  the staleness report must NOT gate `bringup --check`. Only a human can
#       relaunch a live lane, so the condition has a PERMANENT non-zero floor and
#       H52 recorded that such a gate is read as background noise. This is what
#       separates it from H56's STALLED branch, which the lane itself clears.
#       FAILS IF: --check exits non-zero while the only fault is stale launchers.
#   C2  and --check must still refuse what it DOES gate, or C1 is satisfied by a
#       census that never refuses anything.
#       FAILS IF: a STALLED lane no longer produces a non-zero exit.
#   C3  FALSIFIER OF THE FIX: delete the RUNNING CODE block from a copy and the
#       section must vanish. +0 edits is fatal and checked.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT" || exit 1
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then printf 'ok    %s\n' "$1"; pass=$((pass+1));
       else printf 'FAIL  %s\n        got  %s\n        want %s\n' "$1" "$2" "$3"; fail=$((fail+1)); fi; }

echo "== P1/F2 — does any EXECUTABLE invoke the staleness check?"
# Prose references do not run. Restricted to executables, and bringup.sh is
# excluded from the "before" count precisely because this row is what adds it.
callers=$(grep -rln 'check_live_launcher' --include='*.sh' --include='*.py' --include='*.plist' . 2>/dev/null \
          | grep -v '^./elders/' | grep -v 'check_live_launcher.sh' | sort | tr '\n' ' ')
printf '   executables referencing it: %s\n' "${callers:-NONE}"
ck "P1 bringup.sh now invokes it (it was the only scheduled monitor and did not)" \
   "$(printf '%s' "$callers" | grep -c './bringup.sh')" "1"

echo
echo "== P2/F1 — can any bringup path replace a LIVE lane?"
# MISSING is the launch list. Show that it is fed only by the DOWN branch.
feeds=$(grep -c 'MISSING+=(' bringup.sh)
downfeed=$(grep -B4 'MISSING+=(' bringup.sh | grep -c 'DOWN')
ck "F1 DOES NOT FIRE: MISSING has exactly one feeder" "$feeds" "1"
ck "F1 DOES NOT FIRE: and that feeder is the DOWN branch" "$downfeed" "1"
ck "F1 DOES NOT FIRE: STALLED is not added to MISSING (H56 kept it out on purpose)" \
   "$(grep -A12 'nfail" -ge 2' bringup.sh | grep -c 'MISSING+=(')" "0"
ck "F1 DOES NOT FIRE: HALTED is not added either" \
   "$(grep -A6 'HALTED IS NOT DOWN' bringup.sh | grep -c 'MISSING+=(')" "0"

echo
echo "== P3 — the ask was closed against a reference that moves"
# TWICE, ONE LINE APART, AND THE SECOND TIME AFTER I HAD WRITTEN THE COMMENT
# BELOW. This asserted `== 1` and went red at 2 the moment my own REOPENED block
# quoted the phrase it counts. Both assertions in this section were counts where
# the property is presence, and I fixed one and left its neighbour -- §12.2's own
# defect, inside the probe of a row about §12.2. Named rather than quietly
# corrected: when you fix an over-specified assertion, fix its siblings in the
# same block, because they were written by the same hand in the same minute.
ck "P3 HUMAN_NEEDED still carries a RESOLVED BY EVENTS block for the relaunch ask" \
   "$([ "$(grep -c 'RESOLVED BY EVENTS' HUMAN_NEEDED.md)" -ge 1 ] && echo yes || echo no)" "yes"
ck "P3 and the ask is REOPENED beside it rather than the block being edited (§9)" \
   "$(grep -c 'REOPENED — .RESOLVED BY EVENTS. cannot hold for a moving reference' HUMAN_NEEDED.md)" "1"
# PRESENCE, not a COUNT. This asserted `== 1` on its first run and went red at 2,
# because a peer had already inserted my own H67 correction into that file and it
# quotes the same phrase. The PROPERTY is "it resolved against the moving
# reference"; the number of times the phrase appears is not the property, and a
# check that asserts a count where the property is presence goes red on an
# unrelated edit -- MISSION_LOOP §7's own lesson ("a citation to a number that
# changes is stale by construction") pointed at an assertion instead of a doc.
ck "P3 and it resolved against the moving reference, not a pinned commit" \
   "$([ "$(grep -c 'newest commit touching' HUMAN_NEEDED.md)" -ge 1 ] && echo yes || echo no)" "yes"
bash spikes/harness/check_live_launcher.sh >/dev/null 2>&1; clcrc=$?
printf '   check_live_launcher.sh exit code RIGHT NOW: %s\n' "$clcrc"
ck "P3 the 'resolved' verdict is false again, which is the point" "$clcrc" "1"

echo
echo "== F3 — how much is actually inert? COUNTED, not asserted"
oldest=$(bash spikes/harness/check_live_launcher.sh 2>&1 | grep '^STALE' \
         | sed -E 's/.*started ([0-9:]+),.*/\1/' | sort | head -1)
inert=$(git log --format='%h %ad' --date=format:'%H:%M:%S' -- run_loop.sh \
        | awk -v t="${oldest:-00:00:00}" '$2>t' | wc -l | tr -d ' ')
printf '   oldest live launcher start %s; commits to run_loop.sh after it: %s\n' "${oldest:-?}" "$inert"
git log --format='   INERT %h %s' -- run_loop.sh | head -"${inert:-0}"
ck "F3 BIT AND THE CLAIM IS CORRECTED: exactly 1 commit inert, not four versions" "$inert" "1"

echo
echo "== the report is wired into the only scheduled monitor"
out=$(./bringup.sh --check 2>&1); rc=$?
ck "RUNNING CODE section present"        "$(printf '%s\n' "$out" | grep -c '=== RUNNING CODE ===')" "1"
ck "  it carries the checker's verdict"  "$(printf '%s\n' "$out" | grep -c 'REFUSE: .* live launcher processes predate')" "1"
ck "  and names the remedy as a human action" \
   "$(printf '%s\n' "$out" | grep -c 'human action')" "1"
ck "C1 NOT GATED: --check exits 0 with 5 stale launchers" "$rc" "0"

echo
echo "== C2 — but --check must still refuse what it DOES gate"
T=$(mktemp -d "$ROOT/spikes/H68_delivery_gap/.scratch.XXXXXX") || exit 1
trap 'rm -rf "$T"' EXIT
cp bringup.sh "$T/bringup.sh"; chmod +x "$T/bringup.sh"
mkdir -p "$T/prompts" "$T/spikes/harness"
printf '# L68 scratch brief\n' > "$T/prompts/L68.md"
printf 'L68\n' > "$T/roster.txt"
sleep 300 & holder=$!
echo "$holder" > "$T/.loop_lock.L68"
date +%s > "$T/.heartbeat.L68"
echo 3 > "$T/.loop_fails.L68"
( cd "$T" && bash ./bringup.sh --check >c2.out 2>&1 ); c2rc=$?
ck "C2 a STALLED lane still makes --check exit non-zero" "$c2rc" "1"
ck "C2 and the absent checker is reported as UNKNOWN, not clear" \
   "$(grep -c 'staleness unknown' "$T/c2.out")" "1"

echo
echo "== C3 — falsifier: delete the RUNNING CODE block, the section must vanish"
python3 - "$ROOT/bringup.sh" > "$T/bu_noblock.sh" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
out = re.sub(r'\necho\necho "=== RUNNING CODE ==="\n.*?\nfi\n', '\n', src, count=1, flags=re.S)
assert out != src, 'C3 anchor absent — the falsifier would have reported +0 edits as a pass'
sys.stdout.write(out)
PY
ck "C3 the revert exists and parses" \
   "$([ -s "$T/bu_noblock.sh" ] && bash -n "$T/bu_noblock.sh" 2>/dev/null && echo usable || echo broken)" "usable"
ck "C3 the revert actually changed the file (+0 edits is fatal)" \
   "$(cmp -s bringup.sh "$T/bu_noblock.sh" && echo unchanged || echo changed)" "changed"
cp "$T/bu_noblock.sh" "$T/bringup.sh"; chmod +x "$T/bringup.sh"
echo 0 > "$T/.loop_fails.L68"
( cd "$T" && bash ./bringup.sh --check >c3.out 2>&1 ) || true
ck "C3 FIRES: without the block there is no RUNNING CODE section" \
   "$(grep -c 'RUNNING CODE' "$T/c3.out")" "0"

kill "$holder" 2>/dev/null
printf '\n%s passed, %s FAILED\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
