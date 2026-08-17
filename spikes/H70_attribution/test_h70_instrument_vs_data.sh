#!/usr/bin/env bash
# test_h70_instrument_vs_data.sh — H70, ATOM-3, 2026-08-17.
#
# Falsification harness for `spikes/harness/headcheck.sh` v2.
#
# §12.10: a guardrail that is written but not MECHANISED will be violated again by
# its own author, usually the same day. So this does not merely assert that v2 is
# green — a suite that only ever sees the fixed code cannot tell a working control
# from a control that cannot fail (A15). Every check below either RESTORES the v1
# defect on an ISOLATED COPY and demands red, or feeds the mechanism input that
# makes its answer decidable by hand.
#
# THE ARTIFACT IS RELOCATED, NEVER THE CALLER. `headcheck.sh` and `refcheck.py`
# both derive their root from their own path, so a test that only changes `cd`
# measures the live repo and reports that as the verdict (AGENT-1's rule 2,
# `livechat.log`; it cost allocid.sh a false PASS).
#
# §10: nothing is written outside the workspace. Scratch is `.h70.$$` beside this
# file and is removed on exit. My own first probe this span ran in `mktemp -d`,
# i.e. /tmp, which is H17's open row.
#
# usage: bash spikes/H70_attribution/test_h70_instrument_vs_data.sh
# exit 0 = every check passed. 1 = at least one failed.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HC="$ROOT/spikes/harness/headcheck.sh"
# ABSOLUTE. It was relative for one run, and the `cd "$SC/repo"` in C5 then
# resolved every `> "$SC/..."` under the new cwd: four checks reported FAIL with
# an empty `got`, which is a test failing for a reason that is not the thing
# under test. A relative scratch path in a script that cds is a control that
# cannot fire correctly.
SC="$ROOT/spikes/H70_attribution/.h70.$$"
trap 'rm -rf "$SC"' EXIT
mkdir -p "$SC" || { echo "FAIL: no scratch"; exit 1; }

pass=0; fail=0
ok()   { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi; }

echo "H70 — the instrument is a variable too"

# ---------------------------------------------------------------- C1 .. C2
# The shipped selfcheck must pass, and it must pass FOR A REASON: C2 breaks it.
"$HC" --selfcheck >"$SC/sc.out" 2>&1
check "C1  shipped --selfcheck passes" "$?" "0"

# C2 — RESTORE THE v1 DEFECT: classify() ignoring its instrument flag. This is the
# falsifier for the whole row. If --selfcheck still passes with v1's classifier
# back, then v2's checks do not test v2 and the row is worthless.
cp "$HC" "$SC/hc_v1.sh"
python3 - "$SC/hc_v1.sh" <<'PY'
import sys
p = sys.argv[1]; s = open(p).read()
old = '''  if [ "${2:-0}" = 1 ]; then
    printf 'CHECKER-UNCOMMITTED %s\\n' "$1"
  elif [ -e "$ROOT/$1" ]; then'''
new = '''  if [ -e "$ROOT/$1" ]; then'''
assert old in s, "ANCHOR ABSENT — this probe would have silently tested nothing"
open(p, 'w').write(s.replace(old, new, 1))
PY
[ $? -eq 0 ] || { echo "  FAIL C2 anchor absent (probe is inert)"; fail=$((fail+1)); }
bash "$SC/hc_v1.sh" --selfcheck >"$SC/v1.out" 2>&1
check "C2  v1 classifier restored -> --selfcheck REFUSES" "$?" "1"
if grep -q 'H70 is back' "$SC/v1.out"; then ok "C2b the refusal names H70, not a generic mismatch"
else bad "C2b refusal did not name H70: $(head -2 "$SC/v1.out" | tr '\n' ' ')"; fi

# ---------------------------------------------------------------- C3 .. C4
# The RELOCATION LIST is derived by grep from the checker invocations in the file,
# not typed (H30). C3 proves it is derived: a file with no `python3 spikes/...`
# line must yield an EMPTY list and the selfcheck must go red on it, because an
# empty list makes arm B identical to arm A and CHECKER-UNCOMMITTED unreachable.
sed 's|python3 spikes/harness/refcheck.py|python3 NOPE/refcheck.py|g' "$HC" > "$SC/hc_norelo.sh"
bash "$SC/hc_norelo.sh" --selfcheck >"$SC/norelo.out" 2>&1
check "C3  empty relocation list -> --selfcheck REFUSES" "$?" "1"
if grep -q 'relocation list is EMPTY' "$SC/norelo.out"; then ok "C3b names the unreachable branch (A15)"
else bad "C3b: $(head -2 "$SC/norelo.out" | tr '\n' ' ')"; fi

# C4 — the list is non-empty and every entry exists in the live repo. Stated as
# its own check because C3 only proves the grep CAN return nothing.
relo=$(grep -oE 'python3 spikes/harness/[A-Za-z0-9_]+\.py' "$HC" | awk '{print $2}' | sort -u)
n=0; missing=0
for k in $relo; do n=$((n+1)); [ -f "$ROOT/$k" ] || missing=$((missing+1)); done
check "C4  relocation list non-empty" "$([ "$n" -gt 0 ] && echo yes || echo no)" "yes"
check "C4b every relocated checker exists" "$missing" "0"

# ---------------------------------------------------------------- C5
# THE END-TO-END CONTROL, and the one that decides the row. Build a HEAD
# materialisation, put a checker in the TREE position that resolves ONE citation
# HEAD's does not, and demand that headcheck attributes exactly that one to the
# INSTRUMENT. Uses a stub checker rather than the live refcheck.py so the control
# does not depend on whether ok-1's real edit is still uncommitted when this runs
# — a control whose input another lane can commit away is a control that stops
# being able to fail.
mkdir -p "$SC/repo/spikes/harness"
cd "$SC/repo" || exit 1
git init -q . 2>/dev/null
git config user.email t@t; git config user.name t
cat > spikes/harness/refcheck.py <<'PY'
import sys
# HEAD's checker: both citations dangle.
print("  UNRESOLVED DOC.md: `only_head_flags_this` does not exist")
print("  UNRESOLVED DOC.md: `both_flag_this` does not exist")
print("REFUSE: 2 citation(s) in the harness do not resolve.")
sys.exit(1)
PY
cp "$HC" spikes/harness/headcheck.sh
git add -A >/dev/null 2>&1; git commit -qm init >/dev/null 2>&1
# now the TREE checker — the uncommitted fix — stops flagging the first one
cat > spikes/harness/refcheck.py <<'PY'
import sys
print("  UNRESOLVED DOC.md: `both_flag_this` does not exist")
print("REFUSE: 1 citation(s) in the harness do not resolve.")
sys.exit(1)
PY
bash spikes/harness/headcheck.sh > "$SC/e2e.out" 2>&1
cd "$ROOT" || exit 1
got_instr=$(grep -c '^  CHECKER-UNCOMMITTED only_head_flags_this$' "$SC/e2e.out")
got_absent=$(grep -c '^  ABSENT both_flag_this$'                   "$SC/e2e.out")
check "C5  refusal only HEAD's checker makes -> CHECKER-UNCOMMITTED" "$got_instr" "1"
check "C5b refusal BOTH checkers make          -> ABSENT"            "$got_absent" "1"
# and the negative direction: the data-caused one must NOT be blamed on the
# instrument. Without this, a differ that returned everything would pass C5.
check "C5c the data-caused refusal is not attributed to the instrument" \
      "$(grep -c 'CHECKER-UNCOMMITTED both_flag_this' "$SC/e2e.out")" "0"

# ---------------------------------------------------------------- C6
# A CRASHED tree checker emits no UNRESOLVED lines. Arm A minus arm B would then
# be EVERYTHING, and headcheck would tell a lane its whole refusal set is already
# fixed — family B, the instrument reporting fiction, inside the fix for an
# attribution defect. Nothing may be attributed to the instrument in that case.
cd "$SC/repo" || exit 1
printf 'import sys\nraise SystemExit(open("/nonexistent").read())\n' > spikes/harness/refcheck.py
bash spikes/harness/headcheck.sh > "$SC/broken.out" 2>&1
cd "$ROOT" || exit 1
# Anchored on the CLASSIFIED-LINE form (two-space indent, then a path), not on
# the bare word: the bare word FAILED here, matching headcheck's own guidance
# paragraph "CHECKER-UNCOMMITTED is the FIX that is uncommitted", so a green
# mechanism reported red. ATTACKER-1 posted this class to `livechat.log` this
# span — a count-based assertion over a document that quotes its own vocabulary —
# and I reproduced it two hours later inside the probe for an attribution row.
check "C6  crashed tree checker -> nothing attributed to the instrument" \
      "$(grep -c '^  CHECKER-UNCOMMITTED ' "$SC/broken.out")" "0"
if grep -q 'CHECKER-BROKEN' "$SC/broken.out"; then ok "C6b the crash is REPORTED, not swallowed"
else bad "C6b crash was silent: $(head -3 "$SC/broken.out" | tr '\n' ' ')"; fi

echo
echo "$pass passed, $fail FAILED"
[ "$fail" -eq 0 ] || exit 1
