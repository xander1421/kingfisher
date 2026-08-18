#!/bin/sh
# H116 probe — is the local autoloop reachable, and what is behind its first gate?
#
# NOTHING IS ACCEPTED AND NOTHING IS PUBLISHED. Every full run below executes a
# COPY of autoloop_local.sh whose program directory and state file live under
# this spike (§10), so `proposed/` and `.autoloop/state/` are never written by
# the probe. Asserted at the end, not assumed.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT" || exit 9

echo "=== F2 — is the first gate refusing TRANSIENTLY or PERMANENTLY? ==="
echo "One reading is not a rate. Sampling quiet.sh; each sample is a full run."
q=0; n=6
i=1
while [ "$i" -le "$n" ]; do
  sh spikes/quiet.sh >/dev/null 2>&1
  rc=$?
  [ "$rc" -eq 0 ] && q=$((q+1))
  printf '  sample %d: rc=%d%s\n' "$i" "$rc" "$([ "$rc" -eq 0 ] && echo ' (quiet)' || echo ' (REFUSES)')"
  i=$((i+1))
done
echo "  quiet in $q of $n samples"
echo "  live lanes on this host: $(ls .loop_lock.* 2>/dev/null | wc -l | tr -d ' ')"

echo
echo "=== F3 — the extractor, against the instrument's REAL output ==="
echo "Not against my reading of the regex. mutate.py is run once and captured."
raw=$(python3 spikes/M1_9_mutation/mutate.py 2>&1 | tail -30)
printf '%s\n' "$raw" > "$HERE/mutate.tail.out"
echo "  captured $(printf '%s\n' "$raw" | wc -l | tr -d ' ') lines to mutate.tail.out"
# the EXACT pipeline from autoloop_local.sh:36 (v1)
cur=$(printf '%s\n' "$raw" | grep -oE 'detected[_ ]classes?[: ]+[0-9]+' | grep -oE '[0-9]+$' | tail -1)
echo "  extractor yields: '${cur:-<EMPTY>}'"
if [ -z "$cur" ]; then
  echo "  => the script's own guard fires: 'could not extract' and exit 1."
  echo "     The loop cannot complete an iteration on its only runnable program."
else
  echo "  => F3 FIRED: the extractor works and my reading was wrong."
fi
echo "  lines in the real output that contain the word 'detected':"
printf '%s\n' "$raw" | grep -n 'detected' | head -4 | sed 's/^/      /'
echo "  a line matching 'detected_classes: N' anywhere in it: \
$(printf '%s\n' "$raw" | grep -cE 'detected[_ ]classes?[: ]+[0-9]+')"

echo
echo "=== the metric label vs the number under it ==="
for p in fault-expression kingfisher_mission; do
  m=$(sed -n 's/^metric: *//p' ".autoloop/programs/$p/program.md" | head -1)
  printf '  %-20s declares metric=%-28s instrument run: mutate.py (hardcoded)\n' \
    "$p" "'${m:-<none>}'"
done

echo
echo "=== F4/F5 — the falsifier gate: existential or substantive? ==="
# A copy of the script and of the program dir, so the real state file and
# proposed/ are untouched.
SBX="$HERE/sbx"; rm -rf "$SBX"; mkdir -p "$SBX"
for arm in 'F5-control-no-falsifier' 'F4-empty-falsifier' 'F4-real-falsifier'; do
  d="$SBX/$arm/.autoloop/programs/probeprog"
  mkdir -p "$d" "$SBX/$arm/spikes"
  cp -R "$ROOT/spikes/quiet.sh" "$SBX/$arm/spikes/quiet.sh"
  cp "$ROOT/spikes/harness/autoloop_local.sh" "$SBX/$arm/run.sh"
  printf 'metric: probe_metric\nmetric_direction: higher\ntarget-metric: 1\n\nLoad-insensitive by construction.\n' > "$d/program.md"
  case "$arm" in
    F4-empty-falsifier)  printf '\n## Falsifier\n' >> "$d/program.md" ;;
    F4-real-falsifier)   printf '\n## Falsifier\nIf the count does not fall when a detector is removed, the metric is not measuring detection.\n' >> "$d/program.md" ;;
  esac
  # `cd` in the script resolves ../.. from its own location, so run.sh sits where
  # spikes/harness/ would be two levels down from the arm root.
  mkdir -p "$SBX/$arm/spikes/harness"; mv "$SBX/$arm/run.sh" "$SBX/$arm/spikes/harness/run.sh"
  out=$(cd "$SBX/$arm" && sh spikes/harness/run.sh probeprog --check 2>&1); rc=$?
  gate=$(printf '%s\n' "$out" | grep -E 'falsifier|REFUSE' | head -1)
  printf '  %-24s rc=%d  %s\n' "$arm" "$rc" "${gate:-<no falsifier line>}"
done

echo
echo "=== §10 — did the probe write anything outside this spike? ==="
echo "  .autoloop/state entries: $(ls "$ROOT/.autoloop/state" 2>/dev/null | wc -l | tr -d ' ') (expect 0)"
echo "  proposed/autoloop-*:     $(ls "$ROOT"/proposed/autoloop-* 2>/dev/null | wc -l | tr -d ' ') (expect 0)"
rm -rf "$SBX"
