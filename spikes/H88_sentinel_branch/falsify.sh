#!/usr/bin/env bash
# H88 FALSIFIER -- does run.sh's LIVE arm actually go red when the fix is
# removed? A check nobody has broken on purpose is a check nobody has tested.
#
# F1: delete the fnote ASSIGNMENT (bringup.sh's `[ "$nfail" -lt 0 ] && fnote=`)
#     from a COPY. Expect DEFECT_PRESENT. The live file is never touched.
# F2: delete the fnote from the four PRINT SITES only, leaving the assignment.
#     Expect DEFECT_PRESENT too -- computing the state and not printing it is
#     the original defect exactly, and a check that only watches the assignment
#     would read the recomputed-and-discarded version as fixed.
# CONTROL: the untouched copy must read DEFECT_ABSENT, or F1/F2 are measuring
#     a broken copy operation rather than a removed fix.
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd ../.. && pwd)"
T=$(mktemp -d "$PWD/.falsify.XXXXXX"); trap 'rm -rf "$T"' EXIT
rc=0
verdict() { KF_H88_TARGET="$1" bash ./probe.sh 2>&1 | sed -n 's/.*verdict=\([A-Z_]*\).*/\1/p' | tail -1; }
expect() { # expect <label> <file> <want>
  local got; got=$(verdict "$2")
  if [ "$got" = "$3" ]; then printf '  %-8s PASS  %s\n' "$1" "$got"
  else printf '  %-8s FAIL  got %s, want %s\n' "$1" "${got:-<none>}" "$3"; rc=1; fi
}
cp "$ROOT/bringup.sh" "$T/control.sh"
grep -v '\[ "\$nfail" -lt 0 \] && fnote=' "$T/control.sh" > "$T/f1.sh"
sed 's/"\$age" "\$STALE_SECS" "\$fnote"/"$age" "$STALE_SECS"/; s/"\$src" "\$fnote"/"$src"/; s/"\$age" "\$fnote"/"$age"/; s/"\$age" "\$w" "\$fnote"/"$age" "$w"/' \
    "$T/control.sh" > "$T/f2.sh"
# The mutations must have BITTEN. A sed that matched nothing produces a copy of
# the control and a green run that means nothing -- CLAUDE.md's silent no-op edit.
cmp -s "$T/control.sh" "$T/f1.sh" && { echo "  MUTATE   FAIL  F1 edit was a no-op"; rc=1; }
cmp -s "$T/control.sh" "$T/f2.sh" && { echo "  MUTATE   FAIL  F2 edit was a no-op"; rc=1; }
echo "=== H88 falsifiers ==="
expect CONTROL "$T/control.sh" DEFECT_ABSENT
expect F1      "$T/f1.sh"      DEFECT_PRESENT
expect F2      "$T/f2.sh"      DEFECT_PRESENT
echo "h88_falsify=$([ $rc = 0 ] && echo PASS || echo FAIL)"
exit $rc
