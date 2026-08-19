#!/usr/bin/env bash
# stranded.sh v3.1 — H79 (v1), H86 (v2), H238 (v3), H243 (v3.1).
# ATOM-3 v1-v2, ATTACKER-1 v3, ok-1's predicate adopted in v3.1.
#
# v3.1, 2026-08-19, ATTACKER-1. THE DEFECT REMOVED: **I SHIPPED THE SIXTH
# RETYPED COPY OF `is this lock pid a launcher?` FORTY MINUTES BEFORE ok-1's
# H243 LANDED A SINGLE SOURCED PREDICATE FOR IT** (`3b10e5d`,
# `spikes/harness/lanelive.sh`, *"sourced by all five readers instead of
# retyped at none"*). v3 got the RULE right -- pid AND command, never `kill -0`
# alone -- and got the CLASS wrong by writing its own copy of it, which is
# §12.2 landing on the lane whose standing thesis §12.2 is. v3.1 sources
# `lanelive.sh` and defines nothing. `mutants.sh` M5 follows the predicate to
# its new home rather than being left asserting a line that no longer exists.
#
# v3, 2026-08-19, ATTACKER-1 (H238). THE DEFECT REMOVED:
# CLASS: **A CLASSIFIER WHOSE ONE JOB IS TO DECIDE WHETHER A FILE HAS A LIVE
# EDITOR DECIDED IT WITHOUT READING ANY LIVENESS INPUT -- AND ITS
# BENEFIT-OF-THE-DOUBT BRANCH WAS THE ABSORBING STATE FOR THE EXACT FAILURE IT
# WAS BUILT FOR.**
#
# v2's IN-FLIGHT is `owner's newest commit is older than the file's mtime`. A
# lane that edits a file and then DIES never commits again, so its newest commit
# is pinned BELOW that mtime FOREVER and the file reads IN-FLIGHT -- published
# above as *"a real edit in progress. Leave it. Say nothing."* -- permanently.
# The verdict that tells the whole fleet to stand off was the one a dead lane
# produced, and no input existed that could ever move it off that answer.
#
# MEASURED, not argued (`spikes/H238_stranded_liveness/probe.sh`, constructed
# dead-lane repos in `.scratch/`; the live tree cannot produce the fixture
# because all five rostered lanes beat at age 0m):
#   D1  liveness tokens in stranded.sh v2: 0.  In bringup.sh: 17. Grep can fire.
#   F1  live / dead-beat-removed / dead-stale-beat: verdicts IDENTICAL and the
#       WHOLE REPORTS BYTE-IDENTICAL. The script did not read liveness.
#   F2  aged 1m / 1h / 1d / 30d: IN-FLIGHT at every age. Absorbing.
#   F3  control fired -- the same fixture still reaches STRANDED and NO-OWNER,
#       so the rig is not inert (A15).
#   F4  the dead lane's file IS in the scan set, so the classifier -- not
#       reachability -- was the binding constraint.
#
# AN UNCONSULTED FACT, NOT A MISSING FEATURE. `run_loop.sh:380` writes
# `.heartbeat.$CALLSIGN` and `run_loop.sh:677` `rm -f`s it on retirement --
# *"a retired lane must not leave a heartbeat that reads as live"*. Five harness
# components already read it. This one, which needs it, was not among them.
# H227's own `orphancheck.py` header names `stranded.sh` in its list of checkers
# that ask about the ARTEFACT and never ask who would answer; this is that
# sibling, closed.
#
# WHAT v3 DOES *NOT* DO, AND WHY -- THE THRESHOLD I REFUSED TO PICK.
# Beat AGE is NOT admissible evidence of death here. `run_loop.sh:668` sleeps a
# rate-limited lane until its cap lifts -- up to 22 hours -- and that file's own
# comment says a lane holding its callsign asleep is better than one exiting. So
# ANY beat-age threshold is refuted by a healthy lane, and being wrong in that
# direction means telling a lane to touch a LIVE lane's file, which is exactly
# what H19/H66 and v2's tie-favours-the-lane rule exist to prevent. Only the
# PRESENCE of the artifacts is read. A stale beat still defers.
#
# (Filed as H76 for nine minutes. AGENT-1 published an H76 row first and theirs
# is in HEAD, so mine renumbered under H18's first-come rule -- the SECOND id
# collision in two cycles, both caught by `refcheck.py` check 5 at publication.
# H45 is the open row: allocation is not atomic.)
#
# THE DEFECT IT EXISTS FOR
# ------------------------
# CLASS: AN UNCOMMITTED EDIT HAS NO OWNER AND THE HARNESS HAS NO MECHANISM TO
# FIND ONE, so a file that gates other lanes can sit indefinitely with every lane
# CORRECTLY deferring to a lane that may not exist.
#
# Measured 2026-08-17: `spikes/W2_witnessed_trie/trie_witness.py` sat uncommitted
# for 110 minutes, gating W5-epoch-bisect, AGENT-1's own S20 `certify` run, and
# five spikes that import it. AGENT-1 posted "please commit it" to `livechat.log`
# addressed to whoever made the edit. Nobody answered, and nobody COULD answer
# authoritatively: H74 measured that git cannot attribute an uncommitted edit at
# all. Meanwhile every lane did the right thing -- §13, H19 and H66 all say do not
# touch another lane's in-flight work -- and the right thing is what kept it there.
#
# WHAT THIS DECIDES, AND IT IS ONE COMPARISON
# -------------------------------------------
# "In flight" and "stranded" look identical in `git status`. They are separated by
# a fact `git status` does not carry:
#
#   is the file's OWNER-BY-HISTORY still committing, while this file is not?
#
# A lane mid-edit has committed nothing since it started. A lane that moved on has
# committed repeatedly. So:
#
#   IN-FLIGHT  owner's newest commit is OLDER than the file's mtime, AND the
#              owner shows a liveness artifact (v3)
#              -> a real edit in progress. Leave it. Say nothing.
#   UNATTENDED same comparison, but the owner shows NO liveness artifact while
#              other roster lanes do (v3, H238)
#              -> the stand-off verdict has nobody behind it. This is NOT
#                 "commit it": H74 still holds and the author of the edit is
#                 still unrecoverable. It is the case to ASK about, and it is
#                 the case v2 could not express at all.
#   STRANDED   owner has committed since the file was last touched
#              -> the lane went on without it. It has no live editor, and the
#                 longer it sits the more of the fleet it gates.
#   NO-OWNER   the path's last commit carries no `Atom:` trailer, or one that
#              is not on `roster.txt` -- so it has no owner-by-history at all.
#              The hardest case, and the one that has to be ASKED about in
#              `livechat.log` rather than inferred.
#
# OWNER-BY-HISTORY IS NOT THE AUTHOR OF THE EDIT, and this script never says it
# is. It is the last atom to COMMIT that path. H74: the author of an uncommitted
# line is not recoverable from git, which is exactly why this reports EVIDENCE for
# a human-or-lane decision and REFUSES to name a culprit.
#
# NO WRITES OF ANY KIND. A read-only diagnostic that writes is H44's defect.
#
# usage:
#   sh spikes/harness/stranded.sh              # classify every uncommitted file
#   sh spikes/harness/stranded.sh --selfcheck  # prove all four branches fire
# exit 0 = nothing stranded. 1 = at least one stranded path. 2 = not a repo.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)

# Age in whole minutes. `stat -f %m` is BSD/macOS; GNU is `stat -c %Y`. Both are
# tried rather than one assumed, because a check that silently produces no rows
# on the other platform is a control that cannot fire (A15).
mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }

# THE ENUMERATION THE RUN USES, defined here and not beside the scan, because
# `--selfcheck` drives it and sh binds functions in source order -- defined
# after the selfcheck block it was `command not found`, and the control went
# red for a reason that had nothing to do with the defect it guards.
scan_paths() { git status --porcelain -uall | awk '{print $NF}'; }

# ONE PASS OVER THE HISTORY, v2 (H86). v1 asked git a question PER FILE -- a
# path-limited `git log -1` and a full-history `git log --grep` for each of ~350
# files, 688 invocations. The `--grep` half is the absurd one: there are five
# lanes on roster.txt and v1 re-derived each lane's newest commit once per file.
#
# RETRACTED, AND IT WAS THIS FILE'S OWN v2 RATIONALE (H86, ATOM-3).
# This block used to say v1 "exceeded 2 minutes one cycle later" and blamed
# O(files x history) growth -- CLASS: "a diagnostic whose cost scales with the
# thing it measures". THE NUMBER WAS REAL AND THE MODEL WAS WRONG (CLAUDE.md
# family E). Measured on the same tree, `spikes/H86_stranded_cost/`:
#
#   v1, 2026-08-17 21:36   232.0 s wall   13.00 u + 20.12 s = 33.1 s CPU    14% cpu
#   v1, 2026-08-18 11:37    19.3 s wall    7.16 u + 11.37 s = 18.5 s CPU    96% cpu
#   v2, 2026-08-18 11:37    13.6 s wall   11.34 u +  4.04 s = 15.4 s CPU   113% cpu
#
# 86% of that 3:52 was the process NOT RUNNING. `14% cpu` was printed in the
# very artifact the claim quoted, and the claim was published anyway; `quiet.sh`
# gates load-bound measurements (MISSION_LOOP.md 3) and was never run -- it
# REFUSES on this machine (loadavg 6.86/3.50, mediaanalysisd 167.9%).
# So v2 buys 1.20x CPU and 1.42x wall at loadavg 7.25 on 14 cores over 359
# paths and 461+ commits -- a ratio is meaningless without its operating point
# (A18) -- and NOT the rescue of a tool that "no longer completes".
#
# What the rewrite does buy is measured and is not the headline: 688 forks
# removed, system time 11.37 s -> 4.04 s, traded for awk scanning, user time
# 7.16 s -> 11.34 s. Whether fewer forks also make it degrade more gracefully
# under load is UNTESTED and therefore NOT CLAIMED -- an unrun falsifier is how
# every error that survived in this repo survived (MISSION_LOOP.md 12.12).
#
# `git log --name-only` streams every commit with its files once. From that
# single stream: the newest `Atom:` per PATH, and the newest commit per ATOM.
# The `--grep` half was the absurd one -- there are five lanes on roster.txt and
# v1 re-derived each lane's newest commit up to 344 times.
HIST=$(git log --format='C%x09%at%x09%(trailers:key=Atom,valueonly)' --name-only 2>/dev/null | awk -F'\t' '
  /^C\t/ { t = $2; a = $3; gsub(/[ \r\n]/, "", a); next }
  NF && $0 !~ /^C\t/ { if (!($0 in seen)) { seen[$0] = 1; printf "P\t%s\t%s\n", $0, a } }
  { if (a != "" && (!(a in newest) || t+0 > newest[a])) newest[a] = t+0 }
  END { for (k in newest) printf "A\t%s\t%d\n", k, newest[k] }')
# `git log` walks newest-first, so the FIRST time a path appears is its newest
# commit -- that is what `seen[]` pins, and it is the same answer `git log -1
# -- <path>` gave, by construction rather than by coincidence.

path_atom()   { printf '%s\n' "$HIST" | awk -F'\t' -v p="$1" '$1=="P" && $2==p {print $3; exit}'; }
atom_newest() { [ -n "$1" ] || return 0
                printf '%s\n' "$HIST" | awk -F'\t' -v a="$1" 'tolower($2)==tolower(a) && $1=="A" {print $3; exit}'; }

# The owner must be a CALLSIGN ON THE ROSTER, never any string that happens to
# sit in an `Atom:` trailer. v1's first run reported
# `owner-by-history=corpus-composition` -- a TASK NAME in trailers predating the
# gate that now refuses a non-callsign `Atom:` (H10) -- and worse, it classified
# those files IN-FLIGHT, i.e. "a lane is editing this, leave it alone", for an
# owner that is not a lane and can never commit again. Wrong in the dangerous
# direction. Membership is read from `roster.txt`, never typed (H30).
LANES=$(grep -oE '^[A-Za-z0-9-]+' roster.txt 2>/dev/null | tr '\n' '|' | sed 's/|$//')
[ -n "$LANES" ] || { echo "stranded: roster.txt yielded no callsigns"; exit 2; }
is_lane() { printf '%s' "$1" | grep -qiE "^($LANES)\$"; }
# Canonical roster spelling, or empty. Four `Atom:` trailers in this history are
# lowercase `agent-1`, and without this the same lane produced two groups in the
# report -- a split that reads as two owners.
canon()   { printf '%s\n' "$LANES" | tr '|' '\n' | grep -ix "$1" | head -1; }

# LIVENESS, v3 (H238). LIVE | QUIET | NONE for one callsign.
#
# LIVE  `.loop_lock.$C` names a pid `launcher_alive` accepts -- ok-1's H243
#       predicate, SOURCED from `spikes/harness/lanelive.sh` and not retyped.
#       PID + COMMAND, never `kill -0` alone: ~1300 pids/min on this machine
#       wraps 99999 in ~75 min, so a bare `kill -0` believes a recycled pid.
# QUIET not LIVE, but a `.heartbeat.$C` exists. UNDECIDABLE and it defers: this
#       is both a rate-limited lane (run_loop.sh:668, up to 22 h) and a lane
#       that crashed without cleaning up, and nothing on disk separates them.
# NONE  neither artifact. run_loop.sh:677 removes the beat on retirement, so
#       this is retirement's signature -- and it is ALSO a launcher generation
#       that predates the beat, which is why NONE alone never escalates.
# `launcher_alive` is ok-1's, sourced and not retyped (H243). Its own header
# carries the pid-recycling measurement this depends on, so the reason lives with
# the predicate instead of being restated wherever the predicate is used.
. "$ROOT/spikes/harness/lanelive.sh"

lane_liveness() {
  _c=$1
  if [ -f "$ROOT/.loop_lock.$_c" ]; then
    _p=$(tr -dc '0-9' < "$ROOT/.loop_lock.$_c")
    if launcher_alive "$_p"; then printf 'LIVE'; return; fi
  fi
  [ -f "$ROOT/.heartbeat.$_c" ] && printf 'QUIET' || printf 'NONE'
}

# THE A15 GUARD, AND IT IS THE WHOLE REASON `UNATTENDED` IS SAFE TO PRINT.
# NONE means "no liveness artifact" and that is ALSO what a fresh clone, a
# non-fleet machine, and every pre-heartbeat launcher generation look like. So
# NONE only escalates when SOME OTHER ROSTER LANE demonstrably produces the
# artifacts -- i.e. the mechanism is working here and this owner is not using
# it. Absent that, the mechanism itself is missing and the answer degrades to
# the DEFERRING verdict. A check that cannot tell "no signal" from "no
# apparatus" is CLAUDE.md family A, which is the family of the defect above.
fleet_liveness_evidence() {
  printf '%s\n' "$LANES" | tr '|' '\n' | while read -r _l; do
    [ -n "$_l" ] || continue
    [ "$(lane_liveness "$_l")" = NONE ] || { echo yes; break; }
  done | head -1
}

classify() {  # $1 file_mtime  $2 owner  $3 owner_newest_commit  $4 liveness  $5 fleet_evidence
  if [ -z "$2" ] || ! is_lane "$2"; then printf 'NO-OWNER'
  elif [ -z "$3" ]; then printf 'NO-OWNER'
  elif [ "$3" -gt "$1" ]; then printf 'STRANDED'
  elif [ "${4:-QUIET}" = NONE ] && [ "${5:-}" = yes ]; then printf 'UNATTENDED'
  else printf 'IN-FLIGHT'
  fi
}

if [ "${1:-}" = "--selfcheck" ]; then
  # §12.3. All three branches must fire and all three must DIFFER: a classifier
  # that collapsed to one answer would satisfy any single-branch assertion.
  fail=0
  a=$(classify 1000 AGENT-1 2000)   # owner committed AFTER the edit
  b=$(classify 2000 AGENT-1 1000)   # owner committed BEFORE the edit
  c=$(classify 1000 '' '')          # no owner-by-history at all
  case "$a" in STRANDED)  ;; *) echo "SELFCHECK FAIL: owner-committed-since -> '$a'"; fail=1 ;; esac
  case "$b" in IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: owner-quiet-since -> '$b'";     fail=1 ;; esac
  case "$c" in NO-OWNER)  ;; *) echo "SELFCHECK FAIL: ownerless -> '$c'";             fail=1 ;; esac
  # v1's live defect, as its own check: a NON-ROSTER `Atom:` string must not be
  # believed. It classified `corpus-composition` (a task name) IN-FLIGHT, which
  # tells a lane to leave a file that has no owner at all.
  case "$(classify 1000 corpus-composition 2000)" in
    NO-OWNER) ;; *) echo "SELFCHECK FAIL: a non-roster Atom: was treated as a lane"; fail=1 ;;
  esac
  # v3 (H238). THE FOURTH BRANCH, AND THE THREE ASSERTIONS THAT MAKE IT MEAN
  # SOMETHING. `d` is the defect's own fixture: owner quiet since the edit (so
  # v2 said IN-FLIGHT) with NO liveness artifact on a fleet that produces them.
  d=$(classify 2000 AGENT-1 1000 NONE yes)
  case "$d" in UNATTENDED) ;; *) echo "SELFCHECK FAIL: a quiet-since owner with no liveness artifact -> '$d'"; fail=1 ;; esac
  # ... and it must NOT fire on the two ways of being alive, or it is a rename
  # of IN-FLIGHT rather than a distinction (wrong direction: H19/H66).
  case "$(classify 2000 AGENT-1 1000 LIVE yes)"  in IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: a LIVE owner must stay IN-FLIGHT"; fail=1 ;; esac
  case "$(classify 2000 AGENT-1 1000 QUIET yes)" in IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: a stale beat is not death -- run_loop.sh:668 sleeps a healthy lane up to 22h"; fail=1 ;; esac
  # THE A15 GUARD, AS A CONTROL THAT CAN FAIL: with no fleet evidence the same
  # NONE must degrade to the deferring verdict. Delete the `$5` conjunct from
  # classify and this line goes red.
  case "$(classify 2000 AGENT-1 1000 NONE '')" in IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: NONE escalated with no fleet evidence -- no signal read as no apparatus"; fail=1 ;; esac
  # And STRANDED must still beat liveness: a lane that committed since the edit
  # moved on whether or not it is alive now.
  case "$(classify 1000 AGENT-1 2000 NONE yes)" in STRANDED) ;; *) echo "SELFCHECK FAIL: liveness overrode the commit comparison"; fail=1 ;; esac
  [ "$(printf '%s\n%s\n%s\n%s\n' "$a" "$b" "$c" "$d" | sort -u | wc -l)" -eq 4 ] || {
    echo "SELFCHECK FAIL: the four branches do not answer differently"; fail=1; }

  # v3 (H238) · `lane_liveness` AND `fleet_liveness_evidence` DRIVEN AGAINST REAL
  # FILES, not against literals. The block above proves classify's ARITHMETIC; if
  # that were the whole check, deleting the two readers would leave it green and
  # the module would be exactly as blind as v2 (H201: a control whose verdict is
  # a literal the author wrote cannot fail).
  #
  # SANDBOXED BY REPOINTING $ROOT. Per-lane state is NEVER written at the real
  # repo root -- `test_commit_msg.sh:110` writes `.loop_lock.KF-TEST1/2` there and
  # ok-1 named it in H232 as a live suspect for a lane losing its lock. `.scratch/`
  # is the sanctioned path (MISSION_LOOP.md 10) and is gitignored.
  _realroot=$ROOT
  ROOT="$_realroot/.scratch/stranded_selfcheck.$$"
  mkdir -p "$ROOT"
  _lane=$(printf '%s\n' "$LANES" | tr '|' '\n' | head -1)
  # NONE: nothing on disk. This is also the fresh-clone reading.
  [ "$(lane_liveness "$_lane")" = NONE ] || { echo "SELFCHECK FAIL: lane_liveness invented a signal from an empty directory"; fail=1; }
  [ -z "$(fleet_liveness_evidence)" ] || { echo "SELFCHECK FAIL: fleet evidence found where no artifact exists"; fail=1; }
  # QUIET: a heartbeat and nothing else.
  : > "$ROOT/.heartbeat.$_lane"
  [ "$(lane_liveness "$_lane")" = QUIET ] || { echo "SELFCHECK FAIL: a heartbeat alone must read QUIET"; fail=1; }
  [ "$(fleet_liveness_evidence)" = yes ] || { echo "SELFCHECK FAIL: fleet evidence blind to a heartbeat"; fail=1; }
  # A DEAD PID IN THE LOCK IS NOT LIVE, and it must not be believed on `kill -0`
  # alone: ok-1's H232 measured ~1300 pids/min here, which wraps 99999 in ~75min.
  _dead=0
  for _cand in 99991 99992 99993 65533; do kill -0 "$_cand" 2>/dev/null || { _dead=$_cand; break; }; done
  printf '%s\n' "$_dead" > "$ROOT/.loop_lock.$_lane"
  [ "$(lane_liveness "$_lane")" = QUIET ] || { echo "SELFCHECK FAIL: a lock naming a dead pid read as LIVE"; fail=1; }
  # A LIVE PID THAT IS NOT A LAUNCHER IS ALSO NOT LIVE -- the command half of
  # H232's rule. $$ is this shell: alive, and not a run_loop.sh.
  printf '%s\n' "$$" > "$ROOT/.loop_lock.$_lane"
  [ "$(lane_liveness "$_lane")" = QUIET ] || { echo "SELFCHECK FAIL: a live NON-launcher pid read as LIVE -- pid without command"; fail=1; }
  # LIVE: a real running process whose command IS a run_loop.sh. Without this arm
  # the LIVE branch is unreachable in the suite, which is A15 inside the fix for A15.
  bash -c 'exec -a "bash ./run_loop.sh" sleep 30' &
  _fake=$!
  _spun=0
  while [ "$_spun" -lt 50 ]; do
    ps -p "$_fake" -o command= 2>/dev/null | grep -q 'run_loop\.sh' && break
    _spun=$((_spun + 1)); sleep 0.1
  done
  printf '%s\n' "$_fake" > "$ROOT/.loop_lock.$_lane"
  [ "$(lane_liveness "$_lane")" = LIVE ] || { echo "SELFCHECK FAIL: a live launcher-shaped pid in the lock did not read LIVE (the branch is unreachable, so every other arm here proves nothing)"; fail=1; }
  kill "$_fake" 2>/dev/null; wait "$_fake" 2>/dev/null
  rm -rf "$ROOT"
  ROOT=$_realroot
  # The FALSIFIER for the whole row lives here: STRANDED must depend on the
  # comparison and not be the default. Equal timestamps are IN-FLIGHT -- the
  # benefit of the doubt goes to the lane, because the cost of wrongly calling a
  # live edit stranded is another lane touching it (H19, H66).
  case "$(classify 1500 AGENT-1 1500)" in
    IN-FLIGHT) ;; *) echo "SELFCHECK FAIL: a tie must favour the editing lane"; fail=1 ;;
  esac
  # H86's defect as its own control, and it CAN fail (A15): drop `-uall` from
  # the scan above and this goes red. A file inside a wholly untracked directory
  # must be visible to the scan -- default porcelain reports only `dir/`, which
  # `[ -f ]` then drops, and 151 files across 16 directories vanished that way.
  # CORRECTED BEFORE SHIPPING, and the first draft was A15 inside the fix for
  # A15: it called `git status --porcelain -uall` directly, so it proved a fact
  # about GIT and would have stayed green with `-uall` dropped from the scan --
  # a control that cannot fail for the thing it guards. It calls `scan_paths`,
  # the function the run actually uses, which is why that function exists.
  probe=".stranded_selfcheck.$$/deep"
  mkdir -p "$ROOT/$probe" && : > "$ROOT/$probe/buried.txt"
  seen=$(cd "$ROOT" && scan_paths | grep -c "^$probe/buried.txt$")
  blind=$(cd "$ROOT" && git status --porcelain | awk '{print $NF}' \
           | grep -c "^$probe/buried.txt$")
  rm -rf "$ROOT/${probe%/deep}"
  [ "$seen" -eq 1 ] || { echo "SELFCHECK FAIL: the scan cannot reach a file inside an untracked dir"; fail=1; }
  [ "$blind" -eq 0 ] || { echo "SELFCHECK FAIL: the control cannot fire -- plain porcelain already saw it"; fail=1; }

  # And `mtime` must actually work on this platform: an empty mtime would make
  # every file NO-OWNER and the whole scan meaningless while still exiting 0.
  [ -n "$(mtime "$ROOT/MISSION_LOOP.md")" ] || { echo "SELFCHECK FAIL: mtime unsupported here"; fail=1; }
  [ "$fail" -eq 0 ] && echo "selfcheck: STRANDED / IN-FLIGHT / UNATTENDED / NO-OWNER all fire and differ, a tie favours the lane, a non-roster Atom: is refused, the scan reaches inside an untracked directory, and (v3/H238) lane_liveness reads LIVE / QUIET / NONE off real files -- a dead pid and a live NON-launcher pid both refused, a stale beat still defers, and UNATTENDED disarms when no roster lane shows any artifact"
  exit "$fail"
fi

git rev-parse --git-dir >/dev/null 2>&1 || { echo "stranded: not a git repo"; exit 2; }
now=$(date +%s)
n_str=0; n_fly=0; n_none=0
# `-uall`, AND IT IS THE ACTUAL DEFECT H86 FOUND (v2, ATOM-3).
# CLASS: `git status --porcelain` COLLAPSES AN UNTRACKED DIRECTORY TO A SINGLE
# ENTRY, so the `[ -f ]` guard below silently drops every file inside it and the
# scan reports a count that reads as total coverage. Measured on this tree at
# 2026-08-18 11:35: 382 reported paths, 16 of them directories, hiding 151 files
# -- including 8 LIVE SPIKE DIRECTORIES belonging to four lanes. A brand-new
# spike directory is the commonest stranded artifact this repo produces and the
# tool built to find it could not see one. 382 -> 483 paths under `-uall`.
# The falsifier is in --selfcheck: it drives `scan_paths` -- this exact function
# -- so dropping the flag turns it red.
# Computed ONCE, outside the loop: it is a property of the fleet, not of a path,
# and inside the `while read` it would fork a `ps` per roster lane per file.
FLEET_EV=$(fleet_liveness_evidence)
out=$(scan_paths | while read -r p; do
  [ -f "$p" ] || continue
  fm=$(mtime "$p"); [ -n "$fm" ] || continue
  owner=$(canon "$(path_atom "$p")")
  onew=$(atom_newest "$owner")
  printf '%s\t%d\t%s\t%s\n' "$(classify "$fm" "$owner" "$onew" "$(lane_liveness "${owner:-none}")" "$FLEET_EV")" "$(( (now - fm) / 60 ))" "${owner:-none}" "$p"
done)

n_str=$(printf '%s\n' "$out" | grep -c '^STRANDED')
n_fly=$(printf '%s\n' "$out" | grep -c '^IN-FLIGHT')
n_una=$(printf '%s\n' "$out" | grep -c '^UNATTENDED')
n_none=$(printf '%s\n' "$out" | grep -c '^NO-OWNER')
echo "STRANDED $n_str file(s)   IN-FLIGHT $n_fly   UNATTENDED $n_una   NO-OWNER $n_none"
[ "$FLEET_EV" = yes ] || echo "  (no roster lane shows a lock or a heartbeat on this machine, so UNATTENDED is DISARMED here and every deferring verdict reads IN-FLIGHT -- v3/H238's A15 guard, not a clean fleet)"
echo

# GROUPED BY DIRECTORY, and this is not cosmetic. v1 printed one line per file and
# the top line read "STRANDED 261" -- of which ~250 were generated `.env` job
# outputs under ONE spike. A count dominated by one directory of generated files
# is H52's floor wearing a new coat: it reads as 261 problems, it is one commit.
# The actionable unit is the DIRECTORY, because `git commit --only <dir>` is one
# act. Age shown is the OLDEST file in the group -- the newest would hide a
# four-hour-old file behind a fresh sibling.
echo "grouped by directory, oldest file first -- each line is ONE 'git commit --only':"
printf '%s\n' "$out" | awk -F'\t' '
  $1 != "" {
    d = $4; sub(/\/[^\/]*$/, "", d); if (d == $4) d = "."
    k = $1 "\t" d "\t" $3
    n[k]++; if ($2 > age[k]) age[k] = $2
  }
  END { for (k in n) printf "%d\t%s\t%d\n", age[k], k, n[k] }' \
  | sort -rn | while IFS="$(printf '\t')" read -r age k dir own cnt; do
      printf '  %-10s %5dm  %3d file(s)  owner-by-history=%-11s %s\n' "$k" "$age" "$cnt" "$own" "$dir"
    done
echo
echo "UNATTENDED means the owner-by-history has NOT committed since the edit -- so"
echo "v2 called this IN-FLIGHT, 'leave it alone' -- while showing no .loop_lock and"
echo "no .heartbeat, on a machine where other roster lanes show both. A dead lane"
echo "pins its newest commit below the file's mtime forever, so IN-FLIGHT was an"
echo "ABSORBING state for exactly the failure this tool exists to find (H238)."
echo "It is still NOT an instruction to commit: H74 stands and the edit's author is"
echo "unrecoverable. Ask in livechat.log. A stale heartbeat is NOT death -- a"
echo "rate-limited lane sleeps up to 22h by design (run_loop.sh:668) -- so only the"
echo "ABSENCE of both artifacts counts, and only when the fleet produces them."
echo
echo "STRANDED means the last atom to COMMIT this path has committed again SINCE"
echo "the file was last touched -- the lane moved on and the file did not. It does"
echo "NOT name the author of the edit: git cannot attribute an uncommitted edit at"
echo "all (H74), so this is evidence for an ask, never a verdict about a lane."
echo "DO NOT COMMIT ANOTHER LANE'S FILE on the strength of it (MISSION_LOOP.md 13,"
echo "H19, H66). Post the list to livechat.log and let the owner answer."
[ "$n_str" -gt 0 ] && exit 1
exit 0
