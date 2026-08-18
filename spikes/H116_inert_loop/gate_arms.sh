#!/bin/sh
# H116 F4/F5 — is the falsifier gate EXISTENTIAL or SUBSTANTIVE, and can it fire?
# Split out of probe.sh so it does not queue behind the mutation run. Every arm
# executes a COPY of autoloop_local.sh against a program directory under this
# spike, so `.autoloop/state/` and `proposed/` are never written (§10).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
SBX="$HERE/sbx"; rm -rf "$SBX"

arm() { # arm <label> <falsifier-body>
  d="$SBX/$1"
  mkdir -p "$d/.autoloop/programs/probeprog" "$d/spikes/harness"
  cp "$ROOT/spikes/quiet.sh" "$d/spikes/quiet.sh"
  cp "$ROOT/spikes/harness/autoloop_local.sh" "$d/spikes/harness/run.sh"
  {
    printf 'metric: probe_metric\nmetric_direction: higher\ntarget-metric: 1\n\n'
    printf 'Load-insensitive by construction.\n'
    # printf '%b', NOT '%s'. The first version of this file used %s, so the
    # literal characters \n## Falsifier\n went in on ONE line, no arm had a
    # heading at all, and every arm -- including the one with a real falsifier --
    # returned rc=1. FIVE ARMS AGREEING IS WHAT A BROKEN FIXTURE LOOKS LIKE;
    # it is the third time this session (H111's missing gate, H115's removed
    # directory) that my SETUP failed in a way that reads as a verdict.
    [ -n "$2" ] && printf '%b' "$2"
  } > "$d/.autoloop/programs/probeprog/program.md"
  out=$(cd "$d" && sh spikes/harness/run.sh probeprog --check 2>&1); rc=$?
  printf '  rc=%-3d %-26s | %s\n' "$rc" "$1" \
    "$(printf '%s\n' "$out" | grep -iE '^falsifier|^REFUSE' | head -1)"
}

echo "F5 CONTROL — the gate must be able to REFUSE, or F4 proves nothing:"
arm 'no-falsifier-section' ''

echo
echo "F4 — what does it actually require?"
arm 'heading-only-EMPTY'      '\n## Falsifier\n'
arm 'heading-plus-blank-line' '\n## Falsifier\n\n'
arm 'heading-with-real-text'  '\n## Falsifier\nIf the count does not fall when a detector is removed, the metric is not measuring detection.\n'
arm 'heading-saying-none'     '\n## Falsifier\nNone. This program cannot be falsified.\n'

echo
echo '  The gate is a grep for the heading. Its header claims the falsifier'
echo "  was 'stated BEFORE the run' -- a TEMPORAL property. A run-time grep can"
echo "  only decide an EXISTENTIAL one, and above it decides even less than that:"
echo "  it decides whether a HEADING is present."

echo
echo "§10 check — the arms wrote nothing outside this spike:"
echo "  .autoloop/state entries: $(ls "$ROOT/.autoloop/state" 2>/dev/null | wc -l | tr -d ' ') (expect 0)"
echo "  proposed/autoloop-*:     $(ls "$ROOT"/proposed/autoloop-* 2>/dev/null | wc -l | tr -d ' ') (expect 0)"
rm -rf "$SBX"
