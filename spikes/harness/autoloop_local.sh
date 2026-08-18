#!/usr/bin/env bash
# autoloop_local.sh — run one autoloop iteration ON THIS MACHINE.
#
# OPERATOR'S DECISION, 2026-08-18: autoloop runs locally, so the technology does
# not leave this machine. Pushing the repo to the PRIVATE remote is fine; running
# the loop on GitHub Actions is not. The compiled lock -- the only artifact Actions
# can execute -- now lives at .autoloop/autoloop.lock.yml.disabled, outside
# .github/workflows/ and gitignored, so a dispatch has nothing to run.
#
# That sentence originally cited the lock at its OLD path, which I had just moved,
# and refcheck.py refused the commit for it: "a contract citing a missing artifact
# reads as satisfied, which is why this refuses rather than warns." First time a
# mechanical gate in this repo caught a defect of mine at commit time rather than a
# reviewer catching it afterwards. H15 working.
#
# THIS ALSO DISSOLVES THE CONFLICT THE WORKFLOW COULD NOT ESCAPE. autoloop is a
# ratchet only because it persists state between runs, and the framework persisted
# by PUSHING a repo-memory branch. Run locally, state is a file on disk. The
# mechanism that made it a loop stops being the mechanism the mission forbids.
#
# usage:
#   sh spikes/harness/autoloop_local.sh <program> [--check]
#   sh spikes/harness/autoloop_local.sh fault-expression --check
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

PROG="${1:?usage: autoloop_local.sh <program-name> [--check]}"
CHECK="${2:-}"
DIR=".autoloop/programs/$PROG"
STATE=".autoloop/state/$PROG.tsv"
[ -f "$DIR/program.md" ] || { echo "no such program: $DIR/program.md"; exit 2; }
mkdir -p .autoloop/state proposed

field() { sed -n "s/^$1: *//p" "$DIR/program.md" | head -1; }
METRIC=$(field metric); DIR_=$(field metric_direction); TARGET=$(field target-metric)
: "${DIR_:=higher}"

echo "program   : $PROG"
echo "metric    : $METRIC ($DIR_ is better, target ${TARGET:-open-ended})"
prev=$(awk 'END{print $2}' "$STATE" 2>/dev/null)
echo "previous  : ${prev:-none recorded}"

# GATES BEFORE MEASUREMENT, not after. §3: gates are respected, never waited on --
# but a load-bound metric taken on a loaded machine is fiction, and S9 is the
# worked example (every timing 5.3x off). A program declaring itself
# load-insensitive may proceed; anything else must not.
# v3 (H122, ATTACKER-1, 2026-08-18). `>/dev/null` DISCARDED THE REASON, and the
# reason is the whole difference between "wait for a quiet moment" and "this can
# never pass". `quiet.sh:100` is `[ "$NCONT" -gt 0 ] && FAIL="$FAIL containers(N)"`
# -- ANY container refuses at ANY load -- and four containers belonging to another
# project have been up throughout. So the load arm varies with the fleet and the
# CONTAINER arm is a floor no lane can clear. v2 of this file recorded "quiet.sh
# REFUSES ON THIS FLEET", which read the exit code and supplied a cause; H122
# corrected it. The reason is now captured and printed.
QUIET_JSON=$(sh spikes/quiet.sh --json 2>/dev/null)
QUIET_WHY=$(printf '%s' "$QUIET_JSON" | sed -n 's/.*"refusals":"\([^"]*\)".*/\1/p')
if ! sh spikes/quiet.sh >/dev/null 2>&1; then
  if grep -qi 'load-insensitive' "$DIR/program.md"; then
    echo "gate      : quiet.sh REFUSES [${QUIET_WHY:-reason unavailable}], but this"
    echo "            program declares itself load-insensitive -- proceeding"
  else
    echo "gate      : quiet.sh REFUSES [${QUIET_WHY:-reason unavailable}] and this"
    echo "            program does not declare load-insensitivity."
    echo "            Any number produced now would be fiction. Refusing (S9)."
    exit 1
  fi
fi

# THE FALSIFIER MUST EXIST BEFORE THE RUN. This is the whole basis of the accept
# rule below: a falsifier written after the number moved is a story fitted to a
# result, and rule 2 would launder it into an accepted retraction.
# v2 (H116, ATTACKER-1, 2026-08-18). THE GATE DECIDED WHETHER A HEADING EXISTED
# AND PRINTED A CLAIM ABOUT *WHEN* THE FALSIFIER WAS WRITTEN. Measured, four arms
# on copies (`spikes/H116_inert_loop/gate_arms.v1.out`, with the same arms
# against v2 beside it in `gate_arms.v2.out`): an EMPTY `## Falsifier`
# section passed, a heading followed by a blank line passed, and a section whose
# body reads "None. This program cannot be falsified." passed -- each printing
# `falsifier : stated before the run`. The control fires (no section REFUSES), so
# the gate works; it just answers a smaller question than it reports.
#
# TEMPORAL PROPERTIES CANNOT BE DECIDED AT RUN TIME, so this does two things
# instead of overclaiming one: it requires the section to have a BODY, and it
# records the commit that last touched program.md beside the number, which is
# what actually lets a later reader check the falsifier predates the metric.
grep -qi '^## Falsifier' "$DIR/program.md" || {
  echo "REFUSE: program states no falsifier. Rule 2 cannot be applied to a program"
  echo "        whose falsifier could be written after seeing the metric."; exit 1; }
FBODY=$(awk 'tolower($0) ~ /^## falsifier/ {f=1; next} /^## / {f=0} f' "$DIR/program.md" \
        | grep -v '^[[:space:]]*$' | head -5)
[ -n "$FBODY" ] || {
  echo "REFUSE: program has a '## Falsifier' HEADING and no falsifier under it."
  echo "        An empty section satisfies a grep and states nothing."; exit 1; }
FCOMMIT=$(git log -1 --format=%h -- "$DIR/program.md" 2>/dev/null)
echo "falsifier : present with a body; program.md last committed at ${FCOMMIT:-UNCOMMITTED}"
echo "            (CEILING: this checks that text EXISTS, not that it says"
echo "            anything -- no run-time check can read English, and none can"
echo "            date a claim. The text is reproduced in the summary and the"
echo "            commit is recorded so a human can date it.)"
printf '            > %s\n' "$FBODY"

[ "$CHECK" = "--check" ] && { echo; echo "--check: gates pass, nothing run."; exit 0; }

echo; echo "=== measure ==="
# v2 (H116). TWO DEFECTS HERE, AND THE LOOP HAD NEVER REACHED EITHER BECAUSE
# quiet.sh REFUSES ON THIS FLEET IN 0-OF-6 SAMPLES WITH 5 LANES LIVE.
#
# (a) THE EXTRACTOR COULD NOT MATCH ITS OWN INSTRUMENT. It grepped stdout for
#     `detected[_ ]classes?[: ]+[0-9]+`; `mutate.py` prints
#     `  {class:15s} {d:3d}/{t:3d} detected` -- the word at the END of the line --
#     and emits no such string anywhere. So `cur` was always empty and the run
#     exited 1 on its only runnable program. `.autoloop/state/` was empty and no
#     `proposed/autoloop-*.md` existed, which is what that looks like from
#     outside. Scraping a regex out of another program's PROSE is the same defect
#     `eval_graph_ai.py` was repaired for hours earlier; the artifact exists
#     (`mutation.json`) and is machine-readable.
#
# (b) THE METRIC WAS DECLARED AND THE INSTRUMENT WAS HARDCODED. `METRIC` came
#     from program.md while the measurement ran `mutate.py` regardless -- so a
#     program declaring anything else got a number labelled with its own metric
#     name and computed from a different one. `kingfisher_mission` declares NO
#     metric at all. Now: a metric this runner cannot source REFUSES, by name,
#     rather than being silently mislabelled (H111's class).
ART=spikes/M1_9_mutation/mutation.json
started=$(date +%s)
raw=$(python3 spikes/M1_9_mutation/mutate.py 2>&1 | tail -30)
case "$METRIC" in
  detected_mutation_classes) ;;
  *) echo "REFUSE: this runner can source 'detected_mutation_classes' and nothing"
     echo "        else. The program declares '${METRIC:-<none>}'. A number under"
     echo "        the wrong label is worse than no number."; exit 1 ;;
esac
[ -f "$ART" ] || { echo "REFUSE: the instrument produced no $ART."; printf '%s\n' "$raw" | tail -8; exit 1; }
# C-FAMILY: the artifact must be the one THIS run wrote. A stale file left by an
# earlier run reads exactly like a fresh measurement.
mt=$(stat -f %m "$ART" 2>/dev/null || stat -c %Y "$ART" 2>/dev/null)
[ -n "$mt" ] && [ "$mt" -ge "$started" ] || {
  echo "REFUSE: $ART is not newer than this run (mtime=$mt, started=$started)."
  echo "        Reading it would report a previous run's number as this one's."
  printf '%s\n' "$raw" | tail -8; exit 1; }
cur=$(python3 - "$ART" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
muts = {k: v for k, v in d.items() if k != '_tree'}
print(sum(1 for v in muts.values()
          if sum(a for a, _ in v['by_class'].values()) > 0))
PYEOF
)
[ -n "$cur" ] || { echo "could not compute $METRIC from $ART."; exit 1; }
echo "current   : $cur  ($METRIC, computed from $ART, not scraped from stdout)"

# ACCEPT RULE, tuned. Stock autoloop accepts only an improvement, and that rule
# would have rejected every correction that gives this project its value --
# G15 0.501->0.067, shaping 54x->4.1-5.6x, G17's 0.441 shown to be 74% chance
# structure, S9's throughput /5.3. A loop that only ratchets upward accumulates
# unfalsified claims, and unfalsified is not true.
verdict=REJECT; why=""
if [ -z "${prev:-}" ]; then verdict=BASELINE; why="first observation; nothing to compare"
# v2 (H116): `-gt` is an INTEGER comparison and this fleet's headline metrics are
# floats (`filtered_mrr` 0.2648). A float here did not compare wrong, it made the
# shell error out -- so the comparison goes through awk, which handles both.
elif [ "$DIR_" = higher ] && awk -v a="$cur" -v b="$prev" 'BEGIN{exit !(a>b)}'; then verdict=ACCEPT; why="metric rose $prev -> $cur"
elif [ "$DIR_" = lower ]  && awk -v a="$cur" -v b="$prev" 'BEGIN{exit !(a<b)}'; then verdict=ACCEPT; why="metric fell $prev -> $cur (lower is better)"
elif [ "$cur" = "$prev" ]; then verdict=REJECT; why="metric unchanged at $cur"
else
  verdict=REJECT
  why="metric moved the wrong way ($prev -> $cur). If a falsifier stated BEFORE this run fired and caused it, a human records this as a RETRACTION and accepts it; this script will not make that call for you."
fi
echo "verdict   : $verdict — $why"

# CROSS-VENDOR REVIEW — the point of running Claude and Gemini as partners.
#
# This project's central blind spot is stated in its own words: replication catches
# DISAGREEMENT, never a SHARED BUG. Two devices running the same code agree on the
# same wrong answer, so a second TARGET buys nothing and only a second
# IMPLEMENTATION does. It is why `operator` is pinned to 1, why the MORK licence
# blocks the only differential engine, and why every G-number rests on one miner.
#
# The same defect had been running in the FLEET and nobody had named it. Five
# lanes, all Claude: correlated priors, correlated blind spots. The day's record is
# that no atom's own suite caught its own defect and every real catch came from
# another lane looking -- but those lanes are the same model, so "another lane
# looking" was a weaker check than it appeared.
#
# A different vendor is the first genuinely UNCORRELATED reviewer this fleet has
# had. That makes `Reviewed-By` mean something instead of being ceremony: an
# accepted iteration should carry a reviewer from the OTHER vendor, so the
# proposer and the checker do not share a failure mode.
if [ -n "${AUTOLOOP_PARTNER:-}" ]; then
  echo "partner   : $AUTOLOOP_PARTNER — cross-vendor review requested"
  echo "            an accepted iteration must carry Reviewed-By naming the other"
  echo "            vendor; same-vendor review is a second target, not a second"
  echo "            implementation."
else
  echo "partner   : NONE SET. This iteration is single-vendor, so its review is"
  echo "            correlated with its proposer. Set AUTOLOOP_PARTNER=gemini (or"
  echo "            =claude) to record who checked it. Not fatal; recorded."
fi

printf '%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$cur" "$verdict" >> "$STATE"

# The human-facing artefact goes to proposed/, like every external-facing thing
# here. §11 unchanged: filing is a human action.
{
  printf '# autoloop (local) — %s\n\n' "$PROG"
  printf 'Ran on this machine. Not GitHub Actions: operator decision 2026-08-18,\n'
  printf 'the technology does not leave the machine.\n\n'
  printf '| when | %s | verdict |\n|---|---|---|\n' "$METRIC"
  awk -F'\t' '{printf "| %s | %s | %s |\n", $1, $2, $3}' "$STATE"
  printf '\n**This run:** %s\n\n' "$why"
  printf '**Falsifier stated in program.md** (last committed `%s` -- date it\n' "${FCOMMIT:-UNCOMMITTED}"
  printf 'against the row above; this script cannot):\n\n%s\n\n' "$FBODY"
  printf 'D6 is NOT established by this script. Before any number here is quoted:\n'
  printf 'runnable code, pinned seed, controls that can fail, and\n'
  printf '`python3 spikes/harness/kfcheck.py` certification. A metric with no\n'
  printf 'generator behind it is an unaudited claim with a number attached.\n'
} > "proposed/autoloop-$PROG.md"
echo "summary   : proposed/autoloop-$PROG.md"
