#!/usr/bin/env bash
# H238 probe v1 — ATTACKER-1, 2026-08-19.
#
# CLAIM UNDER TEST: `spikes/harness/stranded.sh` v2 separates IN-FLIGHT from
# STRANDED with one comparison that contains NO LIVENESS INPUT, so a lane that
# edits a file and then DIES pins its own newest commit below that file's mtime
# forever and the file is IN-FLIGHT -- "a real edit in progress. Leave it. Say
# nothing." -- permanently.
#
# WHY A CONSTRUCTED REPO AND NOT THIS TREE: the fixture requires a DEAD lane.
# All five rostered lanes beat at age 0m on this machine right now, so the live
# tree cannot produce the case. That impossibility is why the hypothesis sat
# unmeasured in this lane's HANDOFF for two cycles instead of being run.
#
# THE INSTRUMENT IS THE REAL ONE. stranded.sh resolves its root as
# `dirname($0)/../..`, so it must be COPIED into each fixture to run against it.
# C0 sha256-compares the copy with the source on every arm: a probe that
# measured a divergent copy of the script would be family C.
#
# NO WRITES OUTSIDE THE WORKSPACE (MISSION_LOOP.md 10). Everything lands under
# $ROOT/.scratch/, which is the sanctioned scratch path and is gitignored.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$ROOT/spikes/harness/stranded.sh"
SB="$ROOT/.scratch/h238.$$"
trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB"

now=$(date +%s)
sha() { shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'; }
# BSD first, GNU second -- the same two-platform idiom stranded.sh itself uses
# for `stat`. A helper that silently produces nothing on the other platform is
# a control that cannot fire (A15).
touchtime() { date -r "$1" +%Y%m%d%H%M.%S 2>/dev/null || date -d "@$1" +%Y%m%d%H%M.%S; }

SRC_SHA=$(sha "$SRC")
copy_ok=1

# A pid that is definitely not running, so "dead lane" is a fact and not a
# label. Verified with kill -0 rather than assumed.
deadpid=0
for cand in 99991 99992 99993 65533 65531; do
  if ! kill -0 "$cand" 2>/dev/null; then deadpid=$cand; break; fi
done

# ---------------------------------------------------------------------------
# build_repo <dir> <t_commit> <t_edit> <extra_commit_after_edit:0|1> <liveness>
#
#   liveness = live | dead-removed | dead-stale
#
# AGENT-1 commits work/f.txt at t_commit, then work/f.txt is modified in the
# worktree and its mtime forced to t_edit. With t_edit > t_commit and no later
# commit, this IS the dead-lane shape: the lane's last act was the edit.
# ---------------------------------------------------------------------------
build_repo() {
  d=$1; tc=$2; te=$3; extra=$4; live=$5
  mkdir -p "$d/spikes/harness" "$d/work"
  cp "$SRC" "$d/spikes/harness/stranded.sh"
  [ "$(sha "$d/spikes/harness/stranded.sh")" = "$SRC_SHA" ] || copy_ok=0

  # The liveness artifacts are gitignored ON PURPOSE. The comparison must vary
  # exactly one thing; an extra untracked path would make the two arms differ
  # because the SCAN SET differs, which is not the question being asked.
  printf '.heartbeat.*\n.loop_lock.*\n' > "$d/.gitignore"
  printf 'AGENT-1\nATTACKER-1\nok-1\n' > "$d/roster.txt"

  ( cd "$d" || exit 1
    git init -q .
    git config user.email 'probe@kingfisher.local'
    git config user.name  'H238 probe'
    git config commit.gpgsign false

    printf 'committed body\n' > work/f.txt
    printf 'unrelated\n' > work/other.txt
    git add roster.txt .gitignore spikes/harness/stranded.sh work/f.txt work/other.txt
    GIT_AUTHOR_DATE="@$tc +0000" GIT_COMMITTER_DATE="@$tc +0000" \
      git commit -q -m "seed the fixture

Atom: AGENT-1"

    # The uncommitted edit. Content is made LONGER as well as different so the
    # modification does not depend on git's stat cache noticing an mtime that
    # has been moved BACKWARDS.
    printf 'the edit that was in flight when the lane died\n' >> work/f.txt

    if [ "$extra" = "1" ]; then
      # F3's STRANDED arm: the same lane commits again AFTER the edit, which is
      # the only shape the classifier can see.
      printf 'moved on\n' >> work/other.txt
      GIT_AUTHOR_DATE="@$((te + 60)) +0000" GIT_COMMITTER_DATE="@$((te + 60)) +0000" \
        git commit -q --only work/other.txt -m "the lane moved on

Atom: AGENT-1"
    fi

    touch -t "$(touchtime "$te")" work/f.txt

    case "$live" in
      live)         printf '%s\n' "$now" > .heartbeat.AGENT-1
                    printf '%s\n' "$$"   > .loop_lock.AGENT-1 ;;
      dead-removed) : ;;   # run_loop.sh:677 rm -f's the beat on retirement
      dead-stale)   printf '%s\n' "$((now - 22380))" > .heartbeat.AGENT-1
                    printf '%s\n' "$deadpid" > .loop_lock.AGENT-1 ;;
    esac
  ) >/dev/null 2>&1
}

# verdict for work/f.txt, or NONE if the scan never surfaced it
verdict() { grep -oE '(STRANDED|IN-FLIGHT|NO-OWNER)[[:space:]]+[0-9]+m' "$1" \
              | head -1 >/dev/null 2>&1
            awk '/owner-by-history/ && /work$/ {print $1; exit}' "$1"; }
run_arm() { ( cd "$1" && sh spikes/harness/stranded.sh > "$1/../$2.out" 2>&1; echo $? ); }

# ===========================================================================
# D1 -- decidable from the design, before any run: does the script read ANY
# liveness signal? The control is the same grep over a file that DOES.
# ===========================================================================
LIVE_TOKENS='heartbeat|loop_lock|kill -0|peers\.sh|fleetcensus|pgrep|ps -'
n_stranded=$(grep -cE "$LIVE_TOKENS" "$SRC")
n_bringup=$(grep -cE "$LIVE_TOKENS" "$ROOT/spikes/harness/bringup.sh")
printf 'OBS D1 {"liveness_tokens_in_stranded_sh": %d, "liveness_tokens_in_bringup_sh": %d, "grep_can_fire": %s}\n' \
  "$n_stranded" "$n_bringup" "$([ "$n_bringup" -gt 0 ] && echo true || echo false)"

# ===========================================================================
# F1 -- hold every input fixed, vary ONLY owner liveness.
# ===========================================================================
tc=$((now - 3600)); te=$((now - 1800))
build_repo "$SB/live"         "$tc" "$te" 0 live
build_repo "$SB/dead_removed" "$tc" "$te" 0 dead-removed
build_repo "$SB/dead_stale"   "$tc" "$te" 0 dead-stale
rc_live=$(run_arm "$SB/live" live)
rc_dr=$(run_arm "$SB/dead_removed" dead_removed)
rc_ds=$(run_arm "$SB/dead_stale" dead_stale)
v_live=$(verdict "$SB/live.out"); v_dr=$(verdict "$SB/dead_removed.out"); v_ds=$(verdict "$SB/dead_stale.out")

# Byte-comparison of the whole reports, not only the target line.
same_lr=$(cmp -s "$SB/live.out" "$SB/dead_removed.out" && echo true || echo false)
same_ls=$(cmp -s "$SB/live.out" "$SB/dead_stale.out"   && echo true || echo false)
ident=$([ "$v_live" = "$v_dr" ] && [ "$v_live" = "$v_ds" ] && echo true || echo false)
printf 'OBS F1 {"verdict_live": "%s", "verdict_dead_removed": "%s", "verdict_dead_stale": "%s", "verdicts_identical": %s, "report_bytes_identical_live_vs_dead_removed": %s, "report_bytes_identical_live_vs_dead_stale": %s, "rc_live": %s, "rc_dead_removed": %s, "rc_dead_stale": %s, "dead_pid_used": %d}\n' \
  "$v_live" "$v_dr" "$v_ds" "$ident" "$same_lr" "$same_ls" "$rc_live" "$rc_dr" "$rc_ds" "$deadpid"

# ===========================================================================
# F2 -- is IN-FLIGHT absorbing? Age the WHOLE scenario: the lane's last commit
# moves back with the edit, because a dead lane's commit cannot stay recent.
# ===========================================================================
ages=''; verds=''; all_fly=true
for a in 60 3600 86400 2592000; do
  te2=$((now - a)); tc2=$((te2 - 60))
  rm -rf "$SB/age"
  build_repo "$SB/age" "$tc2" "$te2" 0 dead-removed
  rc_age=$(run_arm "$SB/age" age)
  v=$(verdict "$SB/age.out")
  [ "$v" = "IN-FLIGHT" ] || all_fly=false
  ages="$ages${ages:+, }$a"; verds="$verds${verds:+, }\"$v:rc$rc_age\""
done
printf 'OBS F2 {"age_seconds": [%s], "verdicts": [%s], "all_in_flight": %s}\n' "$ages" "$verds" "$all_fly"

# ===========================================================================
# F3 -- THE CONTROL THAT MUST FAIL. The same fixture must be able to produce
# the other two answers, or a green IN-FLIGHT is an inert rig (A15).
# ===========================================================================
rm -rf "$SB/strand"
build_repo "$SB/strand" "$tc" "$te" 1 dead-removed
rc_strand=$(run_arm "$SB/strand" strand)
v_strand=$(verdict "$SB/strand.out")
# NO-OWNER: an untracked path has no owner-by-history at all.
rm -rf "$SB/noown"
build_repo "$SB/noown" "$tc" "$te" 0 dead-removed
mkdir -p "$SB/noown/fresh"; printf 'brand new spike\n' > "$SB/noown/fresh/new.txt"
run_arm "$SB/noown" noown >/dev/null
v_noown=$(awk '/owner-by-history/ && /fresh$/ {print $1; exit}' "$SB/noown.out")
printf 'OBS F3 {"stranded_arm_verdict": "%s", "stranded_arm_rc": %s, "noowner_arm_verdict": "%s", "three_answers_reachable": %s}\n' \
  "$v_strand" "$rc_strand" "$v_noown" \
  "$([ "$v_strand" = STRANDED ] && [ "$v_noown" = NO-OWNER ] && [ "$v_live" = IN-FLIGHT ] && echo true || echo false)"

# ===========================================================================
# F4 -- the dead lane's file must be reachable by the scan at all, or the
# classifier is not the binding constraint.
# ===========================================================================
seen=$(cd "$SB/dead_removed" && git status --porcelain -uall | awk '{print $NF}' | grep -c '^work/f.txt$')
printf 'OBS F4 {"dead_lane_file_in_scan_set": %d}\n' "$seen"
printf 'OBS C0 {"copy_sha256_equals_source_on_every_arm": %s, "source_sha256": "%s"}\n' \
  "$([ "$copy_ok" = 1 ] && echo true || echo false)" "$SRC_SHA"

# ===========================================================================
# The probe exits 0 when it RAN, not when the finding holds -- certify_h238.py
# reads the OBS lines and decides. A probe that folded its own verdict into its
# exit code would let a broken arm read as a refutation.
#
# NOTE ON DIRECTION: F1 and F2 assert the CURRENT behaviour, so this file goes
# RED WHEN THE DEFECT IS FIXED. That is deliberate -- it is the acceptance test
# for the repair, and F1/F2 are exactly the arms a repair has to invert.
# ===========================================================================
[ -n "$v_live" ] && [ -n "$v_strand" ] && [ -n "$v_noown" ] || {
  echo "PROBE INCOMPLETE: an arm produced no verdict; the fixture, not the finding, is what failed" >&2
  exit 2; }
exit 0
