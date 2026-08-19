#!/usr/bin/env bash
# H238 probe v2 (ACCEPTANCE) — ATTACKER-1, 2026-08-19.
#
# probe.sh v1 asserts the DEFECT and therefore goes RED once it is fixed; its own
# closing note says so and calls F1/F2 "exactly the arms a repair has to invert".
# This file runs THE SAME ARMS against BOTH versions at once and reports the
# inversion, so the repair is measured and not asserted.
#
# THE BASELINE IS PINNED MECHANICALLY, never from memory: v2 is read with
# `git show HEAD:spikes/harness/stranded.sh`. If the working tree is what HEAD
# already contains, the two columns are the same file and C1 says so rather than
# printing a reassuring "no change".
#
# NO WRITES OUTSIDE THE WORKSPACE (MISSION_LOOP.md 10): everything is in .scratch/.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
NEW="$ROOT/spikes/harness/stranded.sh"
SB="$ROOT/.scratch/h238b.$$"
mkdir -p "$SB"
OLD="$SB/stranded_v2.sh"
# v2 OF THE PROBE (H243 cycle). THE DEFECT REMOVED: the baseline used to be
# `git show HEAD:`, and C1 only asserted the two files DIFFER. Once the v3 repair
# LANDED, HEAD became v3, the "before" column silently became v3 too, and A2
# printed `v2=UNATTENDED` -- a verdict v2 cannot produce. **A control that checks
# a NECESSARY condition and is read as a SUFFICIENT one**, which is the family of
# the defect this whole spike is about, in the probe that proves it. Caught
# because the arm failed loudly; it should have been caught by C1.
#
# The baseline is now RESOLVED BY ITS OWN VERSION HEADER: walk this file's
# history newest-first and take the first blob whose header says v2.
BASE_REF=""
for _c in $(git -C "$ROOT" log --format=%H -- spikes/harness/stranded.sh); do
  if git -C "$ROOT" show "$_c:spikes/harness/stranded.sh" 2>/dev/null \
       | head -3 | grep -q 'stranded\.sh v2 '; then BASE_REF=$_c; break; fi
done
[ -n "$BASE_REF" ] || {
  echo "probe2: no commit of stranded.sh carries a v2 header -- refusing to report a delta against an unidentified baseline" >&2; exit 2; }
git -C "$ROOT" show "$BASE_REF:spikes/harness/stranded.sh" > "$OLD" 2>/dev/null || {
  echo "probe2: baseline blob unreadable" >&2; exit 2; }

sha() { shasum -a 256 "$1" | awk '{print $1}'; }
OLD_SHA=$(sha "$OLD"); NEW_SHA=$(sha "$NEW")
touchtime() { date -r "$1" +%Y%m%d%H%M.%S 2>/dev/null || date -d "@$1" +%Y%m%d%H%M.%S; }
now=$(date +%s)

# ONE launcher-shaped live process, reused by every arm that needs a LIVE lock.
# `exec -a` renames argv so `ps -p ... -o command=` reads a run_loop.sh, which is
# the ONLY way v3's LIVE branch is reachable in a fixture -- and an unreachable
# branch would make every other arm here prove nothing (A15).
bash -c 'exec -a "bash ./run_loop.sh" sleep 400' &
FAKE=$!
trap 'kill "$FAKE" 2>/dev/null; rm -rf "$SB"' EXIT
spun=0
while [ "$spun" -lt 60 ]; do
  ps -p "$FAKE" -o command= 2>/dev/null | grep -q 'run_loop\.sh' && break
  spun=$((spun + 1)); sleep 0.1
done
ps -p "$FAKE" -o command= 2>/dev/null | grep -q 'run_loop\.sh' || {
  echo "probe2: could not make a launcher-shaped live pid; the LIVE arm would be inert" >&2; exit 2; }

dead=0
for c in 99991 99992 99993 65533; do kill -0 "$c" 2>/dev/null || { dead=$c; break; }; done

# build <dir> <t_commit> <t_edit> <extra_commit:0|1> <owner_state> <third_party:0|1>
#   owner_state = live | beat-removed | beat-stale
build() {
  d=$1; tc=$2; te=$3; extra=$4; ost=$5; third=$6
  mkdir -p "$d/spikes/harness" "$d/work"
  cp "$ROOT/spikes/harness/lanelive.sh" "$d/spikes/harness/lanelive.sh" 2>/dev/null
  printf '.heartbeat.*\n.loop_lock.*\n' > "$d/.gitignore"
  printf 'AGENT-1\nATTACKER-1\nok-1\n' > "$d/roster.txt"
  ( cd "$d" || exit 1
    git init -q .; git config user.email 'probe@kingfisher.local'
    git config user.name 'H238 probe'; git config commit.gpgsign false
    printf 'committed body\n' > work/f.txt; printf 'unrelated\n' > work/other.txt
    git add roster.txt .gitignore work/f.txt work/other.txt
    GIT_AUTHOR_DATE="@$tc +0000" GIT_COMMITTER_DATE="@$tc +0000" \
      git commit -q -m "seed the fixture

Atom: AGENT-1"
    printf 'the edit that was in flight when the lane died\n' >> work/f.txt
    if [ "$extra" = "1" ]; then
      printf 'moved on\n' >> work/other.txt
      GIT_AUTHOR_DATE="@$((te + 60)) +0000" GIT_COMMITTER_DATE="@$((te + 60)) +0000" \
        git commit -q --only work/other.txt -m "the lane moved on

Atom: AGENT-1"
    fi
    touch -t "$(touchtime "$te")" work/f.txt
    case "$ost" in
      live)         printf '%s\n' "$now" > .heartbeat.AGENT-1; printf '%s\n' "$FAKE" > .loop_lock.AGENT-1 ;;
      beat-removed) : ;;                                        # run_loop.sh:677 on retirement
      beat-stale)   printf '%s\n' "$((now - 22380))" > .heartbeat.AGENT-1; printf '%s\n' "$dead" > .loop_lock.AGENT-1 ;;
    esac
    # A DIFFERENT roster lane that is demonstrably alive. Without it the fleet
    # shows no liveness apparatus at all and v3 CORRECTLY disarms -- arm A4 is
    # that case on purpose.
    [ "$third" = "1" ] && printf '%s\n' "$FAKE" > .loop_lock.ok-1
  ) >/dev/null 2>&1
}

# verdict for work/f.txt under a given stranded.sh
verdict() {  # $1 fixture dir  $2 script
  cp "$2" "$1/spikes/harness/stranded.sh"
  # v3.1 SOURCES `lanelive.sh` (H243); v2 does not and ignores the extra file.
  # Copied for BOTH columns so the arms differ by the script under test and not
  # by what its sandbox contains.
  cp "$ROOT/spikes/harness/lanelive.sh" "$1/spikes/harness/lanelive.sh" 2>/dev/null
  ( cd "$1" && sh spikes/harness/stranded.sh 2>&1 ) \
    | awk '/owner-by-history/ && /work$/ {print $1; exit}'
}
pair() {  # $1 label  $2 dir  $3 expect_old  $4 expect_new  $5 why
  o=$(verdict "$2" "$OLD"); n=$(verdict "$2" "$NEW")
  ok=true
  [ "$o" = "$3" ] || ok=false
  [ "$n" = "$4" ] || ok=false
  printf 'ARM %-22s v2=%-11s v3=%-11s expected %-11s -> %-11s  %s  %s\n' \
    "$1" "${o:-<none>}" "${n:-<none>}" "$3" "$4" "$([ "$ok" = true ] && echo PASS || echo '*** FAIL ***')" "$5"
  printf 'OBS %s {"v2": "%s", "v3": "%s", "expect_v2": "%s", "expect_v3": "%s", "pass": %s}\n' \
    "$1" "${o:-none}" "${n:-none}" "$3" "$4" "$ok"
  [ "$ok" = true ] || FAILED=$((FAILED + 1))
}
FAILED=0
tc=$((now - 3600)); te=$((now - 1800))

echo "H238 acceptance — the SAME arms as probe.sh v1, run against both versions."
OLD_V=$(head -3 "$OLD" | sed -n 's/.*stranded\.sh \(v[0-9.]*\).*/\1/p' | head -1)
NEW_V=$(head -3 "$NEW" | sed -n 's/.*stranded\.sh \(v[0-9.]*\).*/\1/p' | head -1)
echo "baseline  $OLD_V  sha256 $OLD_SHA  (commit ${BASE_REF%%??????????????????????????????????})"
echo "candidate $NEW_V  sha256 $NEW_SHA  (working tree)"
if [ "$OLD_V" != v2 ] || [ "$NEW_V" = v2 ] || [ "$OLD_SHA" = "$NEW_SHA" ]; then
  echo "C1 *** THE BASELINE IS NOT v2 (or the candidate still is). Nothing below is"
  echo "   a before/after and no delta may be published from it."
  exit 2
fi
echo "C1 baseline reads $OLD_V from its own header and the candidate reads $NEW_V, so the columns are a real before/after"
printf 'OBS C1 {"v2_sha256": "%s", "v3_sha256": "%s", "baseline_version": "%s", "candidate_version": "%s", "baseline_commit": "%s", "differ": true}\n' \
  "$OLD_SHA" "$NEW_SHA" "$OLD_V" "$NEW_V" "$BASE_REF"
printf 'OBS C0 {"launcher_shaped_live_pid": %d, "dead_pid_used": %d}\n' "$FAKE" "$dead"
echo

build "$SB/a1" "$tc" "$te" 0 live         1; pair A1_owner_live         "$SB/a1" IN-FLIGHT IN-FLIGHT  "a LIVE owner keeps its stand-off — the repair must not take it"
build "$SB/a2" "$tc" "$te" 0 beat-removed 1; pair A2_owner_retired      "$SB/a2" IN-FLIGHT UNATTENDED "THE DEFECT: v2's absorbing verdict, inverted"
build "$SB/a3" "$tc" "$te" 0 beat-stale   1; pair A3_beat_stale         "$SB/a3" IN-FLIGHT IN-FLIGHT  "a stale beat is NOT death (run_loop.sh:668, up to 22h) — v3 must still defer"
build "$SB/a4" "$tc" "$te" 0 beat-removed 0; pair A4_no_fleet_apparatus "$SB/a4" IN-FLIGHT IN-FLIGHT  "A15 guard: no roster lane shows any artifact, so UNATTENDED disarms"
build "$SB/a5" "$tc" "$te" 1 beat-removed 1; pair A5_control_stranded   "$SB/a5" STRANDED  STRANDED   "control: the commit comparison still wins over liveness"

# F2 re-run: was IN-FLIGHT absorbing across age, and is it still?
ages=''; oldv=''; newv=''
for a in 60 3600 86400 2592000; do
  te2=$((now - a)); tc2=$((te2 - 60))
  rm -rf "$SB/age"; build "$SB/age" "$tc2" "$te2" 0 beat-removed 1
  ages="$ages${ages:+,}$a"
  oldv="$oldv${oldv:+,}$(verdict "$SB/age" "$OLD")"
  newv="$newv${newv:+,}$(verdict "$SB/age" "$NEW")"
done
printf 'F2  ages [%s]\n    v2 [%s]\n    v3 [%s]\n' "$ages" "$oldv" "$newv"
case "$newv" in *IN-FLIGHT*) echo "    *** FAIL: v3 still absorbs at some age"; FAILED=$((FAILED + 1)) ;;
  *) echo "    PASS: v2 absorbs at every age, v3 does not" ;; esac
# The booleans are computed into variables FIRST. A `case` inside `$( )` is a
# syntax error -- the pattern's own `)` closes the substitution -- and the first
# draft of this line emitted a MALFORMED OBS while the probe still exited 0.
# certify_h238.py refused to parse it, which is the only reason it was caught.
v2abs=false; case "$oldv" in IN-FLIGHT,IN-FLIGHT,IN-FLIGHT,IN-FLIGHT) v2abs=true ;; esac
v3abs=false; case "$newv" in *IN-FLIGHT*) v3abs=true ;; esac
printf 'OBS F2 {"ages": [%s], "v2": "%s", "v3": "%s", "v2_absorbing": %s, "v3_absorbing": %s}\n' \
  "$ages" "$oldv" "$newv" "$v2abs" "$v3abs"

# NO-OWNER must remain reachable under v3, or the vocabulary lost a branch.
rm -rf "$SB/no"; build "$SB/no" "$tc" "$te" 0 beat-removed 1
mkdir -p "$SB/no/fresh"; printf 'brand new\n' > "$SB/no/fresh/new.txt"
cp "$NEW" "$SB/no/spikes/harness/stranded.sh"
vno=$( cd "$SB/no" && sh spikes/harness/stranded.sh 2>&1 | awk '/owner-by-history/ && /fresh$/ {print $1; exit}')
printf 'F3  NO-OWNER under v3: %s  %s\n' "${vno:-<none>}" "$([ "$vno" = NO-OWNER ] && echo PASS || echo '*** FAIL ***')"
printf 'OBS F3 {"noowner_under_v3": "%s"}\n' "${vno:-none}"
[ "$vno" = NO-OWNER ] || FAILED=$((FAILED + 1))

# WHO CHECKS THAT EVERY PROMISED OBS IS PARSEABLE: `certify_h238.py`, which
# refuses on its `need` list and did exactly that for the malformed F2 above.
# Not duplicated here -- a second copy of a gate is a second thing to drift.
echo
echo "probe2: $FAILED arm(s) failed"
exit "$FAILED"
