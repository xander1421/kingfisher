#!/usr/bin/env bash
# test_h219_falsify.sh v1 — ok-1, H219, 2026-08-19.
#
# THE FALSIFIER FOR test_loop_gate.sh SECTION 8b, the per-lane kill switch.
# §5: a control that cannot fail is not a control, and you state the input that
# makes it fail. Section 8b was written GREEN against a hook that already
# carried the repair, so until this file exists it has a regression record and
# no detection record — the two different claims §5 of my brief separates.
#
# THE INPUTS, three, because 8b makes three separate assertions and a mutant
# that reddens one is no evidence about the other two:
#   M1  the v9 per-lane read DELETED     — the exact pre-H219 hook. 8b's first
#       check must go RED. This is the regression this whole row exists to stop.
#   M2  the read widened to a GLOB `STOP.*` — the lazy repair. 8b's first check
#       goes green and its SECOND must go RED, because one lane's retirement
#       would then stop all five. H31's own defect restored from the other end.
#   M3  the read MOVED ABOVE the charset whitelist — behaviourally invisible
#       (a refused callsign and an allowed stop are both `exit`), so only 8b's
#       ordering check can see it. If that check cannot, it is decoration.
#
# EVERY MUTATION IS ASSERTED TO HAVE APPLIED, not merely to have changed bytes.
# H217 (ATTACKER-1): `cmp -s` and an anchor assertion agree on every successful
# edit and disagree exactly when the EDITING TOOL fails — a BSD/GNU sed split
# left a ZERO-BYTE mutant that differed from the source, compiled, and was
# scored as a finding against the module under test.
#
# ARM LABELS ARE `R<n>`, NOT the guardrail letter, AND THAT IS NOT COSMETIC.
# That letter plus a number is this repo's guardrail namespace
# (`analysis/GUARDRAILS.md`), and `refcheck.py` check 3 resolves every such token
# against it. v1's arms 1, 2 and 3 therefore read as citations of three
# guardrails that EXIST and are about something else entirely -- and a citation
# that RESOLVES TO THE WRONG THING is worse than one that does not resolve,
# because it looks like evidence (§13.2). The zero-numbered arm resolved to
# nothing at all, and AGENT-2 reported it as a live refusal of the shared gate.
#
# THIS COMMENT IS WRITTEN WITHOUT THE LITERAL TOKENS, AND THAT IS EARNED TWICE.
# `refcheck.py:414` says the same of its own comment -- "the explanation of a
# false positive becoming one" -- and my first draft of THIS block quoted the
# labels it was retiring, so the rename cleared the gate and the paragraph about
# the rename re-broke it. Read the neighbouring comment before writing yours.
#
# usage: bash spikes/harness/test_h219_falsify.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ROOT="$PWD"; SB="$ROOT/.scratch/h219_falsify"
GATE="$ROOT/.claude/hooks/loop_gate.sh"
SUITE="$ROOT/spikes/harness/test_loop_gate.sh"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }
rm -rf "$SB"; mkdir -p "$SB"

LINE='[ -f "STOP.${LANE}" ] && exit 0'
grep -qF "$LINE" "$GATE" || { echo "REFUSE: the shipped hook has no per-lane STOP read"; exit 2; }

# ---------------------------------------------------------------- M1 · deleted
grep -vF "$LINE" "$GATE" > "$SB/gate_no_perlane.sh"
ctl C1 "$([ "$(grep -cF "$LINE" "$SB/gate_no_perlane.sh")" = 0 ] && echo PASS || echo FAIL)" \
    "M1 mutation applied: the per-lane read is gone"
# AND THE MUTANT MUST STILL BE A HOOK. A file that fails to parse would redden
# the suite for a reason that has nothing to do with this row.
ctl C1b "$(bash -n "$SB/gate_no_perlane.sh" 2>/dev/null && echo PASS || echo FAIL)" \
    "M1 mutant still parses as bash"

OUT1=$(KF_TEST_GATE="$SB/gate_no_perlane.sh" bash "$SUITE" 2>&1)
printf '%s\n' "$OUT1" > "$SB/m1_run.txt"
case "$OUT1" in
  *"H219: a lane's own STOP.<lane> ends its turn (want 'exit', got 'block')"*)
     ctl R1 PASS "deleting the per-lane read turns 8b RED, naming the check" ;;
  *) ctl R1 FAIL "8b stayed green with the per-lane read DELETED — it is inert" ;;
esac

# ------------------------------------------------------------------ M2 · glob
sed "s|^\[ -f \"STOP\.\${LANE}\" \] && exit 0|[ -n \"\$(ls STOP.* 2>/dev/null)\" ] \&\& exit 0|" \
    "$GATE" > "$SB/gate_glob.sh"
ctl C2 "$([ "$(grep -c 'ls STOP\.\*' "$SB/gate_glob.sh")" = 1 ] && echo PASS || echo FAIL)" \
    "M2 mutation applied: the read is now a glob over every lane"
ctl C2b "$(bash -n "$SB/gate_glob.sh" 2>/dev/null && echo PASS || echo FAIL)" \
    "M2 mutant still parses as bash"

OUT2=$(KF_TEST_GATE="$SB/gate_glob.sh" bash "$SUITE" 2>&1)
printf '%s\n' "$OUT2" > "$SB/m2_run.txt"
case "$OUT2" in
  *"H219: another lane's STOP.<lane> does not (want 'block', got 'exit')"*)
     ctl R2 PASS "a STOP.* glob turns 8b's SECOND check RED — one retirement cannot stop five" ;;
  *) ctl R2 FAIL "8b accepted a glob: one lane's stop would retire the whole fleet" ;;
esac
# The glob must NOT redden the first check, or A2 proves only that the mutant is
# broken in general rather than in the direction named.
case "$OUT2" in
  *"H219: a lane's own STOP.<lane> ends its turn (want"*)
     ctl R2b FAIL "the glob also reddened the OWN-lane check; R2 is not specific" ;;
  *) ctl R2b PASS "and the own-lane check stays green, so R2 is about the glob" ;;
esac

# ------------------------------------------------------- M3 · moved above the
# whitelist. Behaviourally invisible, which is the point: only the ordering
# check can see it. Built by deleting the line and re-inserting it above the
# `case`, so the mutant is the same hook with one line relocated.
awk -v line="$LINE" '
  $0 == line { next }
  /^case "\$LANE" in/ { print line }
  { print }
' "$GATE" > "$SB/gate_early.sh"
early_ps=$(grep -n '^\[ -f "STOP\.\${LANE}" \] && exit 0' "$SB/gate_early.sh" | head -1 | cut -d: -f1)
early_wl=$(grep -n 'case "\$LANE" in' "$SB/gate_early.sh" | head -1 | cut -d: -f1)
ctl C3 "$([ -n "$early_ps" ] && [ -n "$early_wl" ] && [ "$early_ps" -lt "$early_wl" ] && echo PASS || echo FAIL)" \
    "M3 mutation applied: the read moved above the whitelist (read=$early_ps whitelist=$early_wl)"
ctl C3b "$(bash -n "$SB/gate_early.sh" 2>/dev/null && echo PASS || echo FAIL)" \
    "M3 mutant still parses as bash"

OUT3=$(KF_TEST_GATE="$SB/gate_early.sh" bash "$SUITE" 2>&1)
printf '%s\n' "$OUT3" > "$SB/m3_run.txt"
case "$OUT3" in
  *"H219: the per-lane STOP read sits below the callsign whitelist (want 'below', got 'above')"*)
     ctl R3 PASS "relocating the read above the whitelist turns the ordering check RED" ;;
  *) ctl R3 FAIL "the ordering check cannot see the relocation — it is decoration" ;;
esac

# ------------------------------------------------------------------ two-sided
# Without this every R arm above would also pass on a suite red for any reason,
# including the seam pointing at a hook that does not run at all.
OUT0=$(KF_TEST_GATE="$GATE" bash "$SUITE" 2>&1)
printf '%s\n' "$OUT0" > "$SB/control_run.txt"
case "$OUT0" in
  *"checks pass") ctl R0 PASS "the SAME suite is green on the shipped hook: $(printf '%s' "$OUT0" | tail -1)" ;;
  *) ctl R0 FAIL "the suite is red on the shipped hook too, so nothing above measured anything: $(printf '%s' "$OUT0" | tail -1)" ;;
esac
# AND THE GREEN RUN MUST SHOW WORK. `rc == 0` is also what a suite that never
# ran returns; H207's own falsifier scored a program that produced nothing as a
# pass. The count is asserted non-zero rather than assumed.
n=$(printf '%s' "$OUT0" | sed -n 's/^loop_gate.sh: \([0-9]*\) checks pass$/\1/p')
ctl R0b "$([ -n "$n" ] && [ "$n" -gt 0 ] && echo PASS || echo FAIL)" \
    "and it reports having run: ${n:-no} checks"

[ "$fail" = 0 ] && echo "H219 falsifier: all arms as stated" || echo "H219 falsifier: FAILED"
exit "$fail"
