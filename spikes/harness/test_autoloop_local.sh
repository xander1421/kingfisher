#!/bin/sh
# test_autoloop_local.sh v1 — H116. The §12.3 runnable check for
# `autoloop_local.sh`, which by its author's own answer had never run in anger.
#
# EVERY ARM RUNS THE REAL SCRIPT, byte-identical, inside an arm directory under
# this spike (§10). The script does `cd "$(dirname $0)/../.."`, so a copy placed
# at `<arm>/spikes/harness/` reads that arm's `.autoloop/`, its `spikes/quiet.sh`
# and its `spikes/M1_9_mutation/mutate.py` — which is how the instrument can be a
# STUB here. The real one takes over eight minutes and spawns `fuelrun` at 100%
# CPU; a suite nobody can afford to run is a suite nobody runs.
#
# WHAT THIS SUITE DOES NOT CONSTRUCT, said out loud because that is the question
# that matters: no arm exercises a FLOAT metric. v2 moved the accept comparison
# from `[ -gt ]` to awk because this fleet's headline metrics are floats, but the
# v2 metric binding admits exactly one integer metric, so a float cannot reach
# the comparison today. The awk form is kept — it is the same size and correct on
# the edge case — and its untested surface is named here rather than implied.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
SRC="$ROOT/spikes/harness/autoloop_local.sh"
D="$ROOT/spikes/H116_inert_loop/.arms"
FAIL=0

ck() { # ck <label> <expected rc> <actual rc>
  if [ "$2" -eq "$3" ]; then echo "  ok    $1"
  else echo "  FAIL  $1 (expected rc=$2, got rc=$3)"; FAIL=$((FAIL + 1)); fi
}

# arm <name> <metric> <falsifier-body-or-empty> <stub: fresh|stale|nojson>
arm() {
  a="$D/$1"; rm -rf "$a"
  mkdir -p "$a/spikes/harness" "$a/spikes/M1_9_mutation" \
           "$a/.autoloop/programs/p" "$a/proposed"
  cp "$SRC" "$a/spikes/harness/run.sh"
  # quiet.sh: a stub that PASSES, so the arms test this script and not the load
  # of the machine running the suite. The real gate's behaviour is H116's F2 and
  # is measured separately (0 of 6 samples quiet, 5 lanes live).
  printf '#!/bin/sh\nexit 0\n' > "$a/spikes/quiet.sh"
  # A fixture with two mutation classes detected and one not: the metric is
  # "classes detected by at least one program", so the expected answer is 2.
  cat > "$a/fixture.json" <<'JSON'
{"m1": {"by_class": {"evaluated": [3, 10]}},
 "m2": {"by_class": {"evaluated": [1, 10]}},
 "m3": {"by_class": {"evaluated": [0, 10]}},
 "_tree": "fixture"}
JSON
  case "$4" in
    fresh)  printf '#!/usr/bin/env python3\nimport shutil,sys\nshutil.copy("fixture.json","spikes/M1_9_mutation/mutation.json")\nprint("stub instrument ran")\n' > "$a/spikes/M1_9_mutation/mutate.py" ;;
    stale)  # the instrument runs and does NOT rewrite the artifact: a previous
            # run's number sitting there reads exactly like a fresh measurement.
            cp "$a/fixture.json" "$a/spikes/M1_9_mutation/mutation.json"
            touch -t 202001010000 "$a/spikes/M1_9_mutation/mutation.json"
            printf '#!/usr/bin/env python3\nprint("stub instrument ran, wrote nothing")\n' > "$a/spikes/M1_9_mutation/mutate.py" ;;
    nojson) printf '#!/usr/bin/env python3\nprint("stub instrument ran, produced no artifact")\n' > "$a/spikes/M1_9_mutation/mutate.py" ;;
  esac
  { printf 'metric: %s\nmetric_direction: higher\ntarget-metric: 3\n\n' "$2"
    printf 'Load-insensitive by construction.\n'
    [ -n "$3" ] && printf '\n## Falsifier\n%b\n' "$3"
  } > "$a/.autoloop/programs/p/program.md"
  ( cd "$a" && sh spikes/harness/run.sh p >out.txt 2>&1 )
  return $?
}

REAL='If the count does not fall when a detector is removed, it is not measuring detection.'

# A1 — THE CONTROL, first: a well-formed program must COMPLETE. Without it every
# refusal below is satisfied by a script that refuses unconditionally.
arm ok detected_mutation_classes "$REAL" fresh
ck "A1 a well-formed program COMPLETES a full iteration" 0 $?
grep -q 'current   : 2' "$D/ok/out.txt"
ck "A1 and the metric is computed from the ARTIFACT (2 of 3 classes detected)" 0 $?
[ -f "$D/ok/.autoloop/state/p.tsv" ]
ck "A1 and state is written, which had never happened before H116" 0 $?
[ -f "$D/ok/proposed/autoloop-p.md" ]
ck "A1 and the human-facing summary lands in proposed/" 0 $?
grep -q 'Falsifier stated in program.md' "$D/ok/proposed/autoloop-p.md"
ck "A1 and the summary REPRODUCES the falsifier text for a human to date" 0 $?

# A2 — the H116 finding: a heading with no body used to pass and print
# "stated before the run".
arm empty_falsifier detected_mutation_classes '' fresh
ck "A2 no ## Falsifier section at all REFUSES (the gate can fire)" 1 $?
arm heading_only detected_mutation_classes '\n' fresh
ck "A2 a ## Falsifier HEADING with an empty body REFUSES" 1 $?
grep -q 'HEADING and no falsifier under it' "$D/heading_only/out.txt"
ck "A2 and it names what is wrong rather than the generic refusal" 0 $?

# A3 — the metric label must describe the number under it (H111's class).
arm wrong_metric filtered_mrr "$REAL" fresh
ck "A3 a metric this runner cannot source REFUSES instead of mislabelling" 1 $?
grep -q "declares 'filtered_mrr'" "$D/wrong_metric/out.txt"
ck "A3 and it names the metric it was asked for" 0 $?

# A4 — C family: the artifact must be the one THIS run wrote.
arm stale_artifact detected_mutation_classes "$REAL" stale
ck "A4 an artifact older than the run REFUSES (a stale number reads as fresh)" 1 $?
arm no_artifact detected_mutation_classes "$REAL" nojson
ck "A4 no artifact at all REFUSES" 1 $?

# A5 — §10: no arm may write outside its own directory.
outside=$(find "$ROOT/.autoloop/state" -type f 2>/dev/null | wc -l | tr -d ' ')
ck "A5 the suite wrote nothing into the real .autoloop/state ($outside file(s))" 0 "$outside"
n=$(ls "$ROOT"/proposed/autoloop-* 2>/dev/null | wc -l | tr -d ' ')
ck "A5 and nothing into the real proposed/ ($n file(s))" 0 "$n"

rm -rf "$D"
echo
if [ "$FAIL" -eq 0 ]; then
  echo "test_autoloop_local: 14 assertions, 0 FAILED — one full iteration completes,"
  echo "                     the metric comes from the artifact, and four refusals"
  echo "                     fire for four different reasons."
else
  echo "test_autoloop_local: $FAIL FAILED"
fi
exit "$FAIL"
