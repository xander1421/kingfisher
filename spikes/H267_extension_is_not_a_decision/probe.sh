#!/usr/bin/env bash
# H267 probe -- ATTACKER-1, 2026-08-19.
#
# PREREGISTERED PREDICTIONS (written and COMMITTED before the run; the whole
# point of 12.12 is that a falsifier marked "not yet run" is how every surviving
# error survived). Each arm prints its own OBS line; the prediction is here so a
# reader can score me rather than take my summary.
#
#   D1  exclusion_is_extension_test true, denominator_computed_before_shell_set
#       true. PREDICT: both true -- the "all N green" headline's denominator does
#       not contain the excluded set, so the exclusion is invisible in the number
#       every incoming agent reads.
#   F1  break an excluded module's --selfcheck in a scratch copy.
#       PREDICT: FIRES -- aggregate rc 0 before AND after, output byte-identical,
#       while the module run directly exits non-zero.
#   F2  did the excluded set grow with no change to the excluder?
#       PREDICT: FIRES -- grew. The exclusion is an extension test, so every .sh
#       added since joins it silently; nobody decided.
#   F3  is the stated reason ("they build git sandboxes") true of its members?
#       PREDICT: FIRES -- several members carry ZERO git-sandbox tokens, run in
#       under a second, and leave git status unchanged.
#   If F1 does NOT fire the finding is withdrawn: the aggregate would already see
#   the excluded set and there is nothing here. If F2 and F3 both fail to fire,
#   the exclusion was a decision correctly stated about its members and this
#   closes as NO DEFECT.
#
# selfcheckall.py is the check that certifies every other check. It excludes
# every `*.sh` carrying `--selfcheck` with the printed reason "(they build git
# sandboxes)". This measures what that exclusion actually costs.
#
# NO WRITES OUTSIDE THE WORKSPACE (MISSION_LOOP.md 10): all arms run against a
# COPY of spikes/harness/ under $ROOT/.scratch/. F1 in particular BREAKS a module
# on purpose and must never do that to the live tree three lanes share.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
H="$ROOT/spikes/harness"
SB="$ROOT/.scratch/h267.$$"
trap 'rm -rf "$SB"' EXIT
mkdir -p "$SB"

# ---------------------------------------------------------------------------
# D1 -- decidable from the source. Is the exclusion a LIST or an EXTENSION test,
# and is the excluded set inside the denominator the tool reports?
# ---------------------------------------------------------------------------
ext_test=$(grep -c "endswith('.sh')" "$H/selfcheckall.py")
n_line=$(grep -n 'n = len(names) + len(demos)' "$H/selfcheckall.py" | cut -d: -f1)
shell_line=$(grep -n '    shell = sorted(' "$H/selfcheckall.py" | cut -d: -f1)
printf 'OBS D1 {"exclusion_is_extension_test": %s, "denominator_line": %s, "shell_set_line": %s, "denominator_computed_before_shell_set": %s}\n' \
  "$([ "$ext_test" -gt 0 ] && echo true || echo false)" "${n_line:-0}" "${shell_line:-0}" \
  "$([ -n "$n_line" ] && [ -n "$shell_line" ] && [ "$n_line" -lt "$shell_line" ] && echo true || echo false)"

# ---------------------------------------------------------------------------
# F1 -- THE DECISIVE ARM. Break one excluded module's --selfcheck in a COPY and
# ask whether the aggregate notices. Chosen module is whichever excluded module
# the RUN names first, so this does not depend on a name I typed.
# ---------------------------------------------------------------------------
# THE COPY MUST PRESERVE `spikes/harness`: selfcheckall resolves its module dir
# as <root>/spikes/harness from __file__, so a flat copy makes it crash on a
# missing path. The first draft copied to $SB/harness and every arm below read a
# TRACEBACK's exit code as a verdict -- `base_rc=1` looked exactly like a real
# red. A probe that scores a crashed process is family B, and it is the second
# time this session that only a downstream refusal caught one of mine.
mkdir -p "$SB/spikes"
cp -R "$H" "$SB/spikes/harness"
SC="$SB/spikes/harness"
run_agg() {  # $1 = output file; prints rc. REFUSES to score a crash.
  ( cd "$SC" && python3 selfcheckall.py >"$1" 2>&1; echo $? )
}
victim=$(cd "$SC" && python3 selfcheckall.py 2>&1 | grep 'NOT RUN' \
         | sed 's/.*sandboxes)://' | tr ' ' '\n' | grep '\.sh$' | head -1)
[ -n "$victim" ] || { echo "probe: no excluded module found in the copy -- the fixture, not the finding, failed" >&2; exit 2; }
base_rc=$(run_agg "$SB/base.out")
grep -q 'Traceback' "$SB/base.out" && { echo "probe: the aggregate CRASHED in the copy; refusing to score a traceback as a verdict" >&2; exit 2; }
# The break is unmissable: --selfcheck exits 1 and says so.
# Prepended, not appended: an appended guard sits after the module's own
# `--selfcheck` block and would never run, so the break itself would be inert.
{ printf '#!/usr/bin/env bash\n# H267: deliberately broken in a scratch copy\nif [ "${1:-}" = "--selfcheck" ]; then echo "H267 BROKEN ON PURPOSE"; exit 1; fi\n'
  cat "$SC/$victim"; } > "$SB/victim.tmp"
mv "$SB/victim.tmp" "$SC/$victim"
direct_rc=$( cd "$SC" && sh "./$victim" --selfcheck >/dev/null 2>&1; echo $? )
[ "$direct_rc" -ne 0 ] || { echo "probe: the break did not take -- the module still passes --selfcheck, so F1 would prove nothing" >&2; exit 2; }
brk_rc=$(run_agg "$SB/broken.out")
same=$(cmp -s "$SB/base.out" "$SB/broken.out" && echo true || echo false)
printf 'OBS F1 {"victim": "%s", "aggregate_rc_before": %s, "aggregate_rc_after_breaking_it": %s, "module_rc_run_directly": %s, "aggregate_output_byte_identical": %s}\n' \
  "$victim" "$base_rc" "$brk_rc" "$direct_rc" "$same"

# ---------------------------------------------------------------------------
# F2 -- did the excluded set grow without a decision? Resolve from history: the
# set is every *.sh in harness carrying --selfcheck, so recompute it at HEAD and
# at the last commit that TOUCHED selfcheckall.py.
# ---------------------------------------------------------------------------
last_touch=$(git -C "$ROOT" log -1 --format=%H -- spikes/harness/selfcheckall.py)
count_at() {  # $1 = commit
  git -C "$ROOT" ls-tree -r --name-only "$1" -- spikes/harness \
    | grep '\.sh$' | while read -r p; do
        git -C "$ROOT" show "$1:$p" 2>/dev/null | grep -q -- '--selfcheck' && echo "$p"
      done | wc -l | tr -d ' '
}
n_then=$(count_at "$last_touch")
n_now=$(count_at HEAD)
printf 'OBS F2 {"last_commit_touching_selfcheckall": "%s", "excluded_count_at_that_commit": %s, "excluded_count_at_HEAD": %s, "grew_with_no_change_to_the_excluder": %s}\n' \
  "${last_touch}" "$n_then" "$n_now" \
  "$([ "$n_now" -gt "$n_then" ] && echo true || echo false)"

# ---------------------------------------------------------------------------
# F3 -- is the STATED REASON true of its members? Run every excluded module that
# contains no git-sandbox token, timed, and snapshot the tree around each.
#
# THE SNAPSHOT IS NOISY ON PURPOSE AND SAYS SO: four other lanes are live in this
# working tree, so a path appearing between two snapshots is not necessarily this
# module's doing. It is reported, never attributed.
# ---------------------------------------------------------------------------
rows=''
for m in $(cd "$ROOT" && python3 spikes/harness/selfcheckall.py 2>&1 | grep 'NOT RUN' \
           | sed 's/.*sandboxes)://' | tr ' ' '\n' | grep '\.sh$'); do
  tok=$(grep -cE 'git init|git clone|mktemp -d|\.scratch' "$H/$m")
  [ "$tok" -eq 0 ] || continue
  before=$(cd "$ROOT" && git status --porcelain -uall | shasum -a 256 | awk '{print $1}')
  t0=$(python3 -c 'import time;print(time.time())')
  rc=$( cd "$ROOT" && sh "spikes/harness/$m" --selfcheck >/dev/null 2>&1; echo $? )
  t1=$(python3 -c 'import time;print(time.time())')
  after=$(cd "$ROOT" && git status --porcelain -uall | shasum -a 256 | awk '{print $1}')
  el=$(python3 -c "print(round($t1-$t0,2))")
  rows="$rows${rows:+,}{\"module\": \"$m\", \"git_sandbox_tokens\": 0, \"rc\": $rc, \"seconds\": $el, \"tree_status_unchanged\": $([ "$before" = "$after" ] && echo true || echo false)}"
done
printf 'OBS F3 {"zero_token_modules": [%s]}\n' "$rows"
exit 0
