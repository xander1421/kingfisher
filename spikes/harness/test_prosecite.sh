#!/bin/sh
# test_prosecite.sh v1 — H168. Drives prosecite.py in a throwaway tree.
#
# The suite constructs the cases the tool must get RIGHT and, deliberately, the
# case that would make it UNABLE TO FIRE. ATTACKER-1's brief: "your instinct on
# any check should be: what case does this suite not construct?" — the answer
# for a self-referential scanner is check 3. If RESULT.md were included in its
# own artifact set every prose number would match itself, the tool would report
# a permanent clean bill of health, and nothing would ever look wrong.

set -u
HERE=$(cd "$(dirname "$0")" && pwd)
TOOL="$HERE/prosecite.py"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ok   $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL $1"; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/spikes/A_backed" "$TMP/spikes/B_ghost" "$TMP/spikes/C_crossspike" \
         "$TMP/spikes/D_notmetric" "$TMP/spikes/E_trailingzero" "$TMP/spikes/F_txtonly"

# A: number is in its own result.json -> clean
printf 'MRR was 0.3611 on test.\n'       > "$TMP/spikes/A_backed/RESULT.md"
printf '{"mrr": 0.3611}\n'               > "$TMP/spikes/A_backed/result.json"
# B: number exists nowhere -> must be reported
# 0.8642097 is deliberately NOT G92's real 0.9246: a fixture that also exists in
# the real repo would pass whether or not the sandbox is being scanned.
printf 'Valid MRR 0.8642097 for _hypernym.\n' > "$TMP/spikes/B_ghost/RESULT.md"
printf '{"routing": "rotate"}\n'         > "$TMP/spikes/B_ghost/result.json"
# C: number lives in ANOTHER spike's artifact -> legitimate citation, clean
printf 'Beats the 0.3611 baseline.\n'    > "$TMP/spikes/C_crossspike/RESULT.md"
printf '{}\n'                            > "$TMP/spikes/C_crossspike/result.json"
# D: <3 decimals and a date are not metric-shaped -> ignored
printf 'v1.2 on 2026-08-19, ratio 1.09 over 42 runs.\n' > "$TMP/spikes/D_notmetric/RESULT.md"
printf '{}\n'                            > "$TMP/spikes/D_notmetric/result.json"
# E: 0.3550 in prose vs 0.355 in artifact -> same number, clean
printf 'Scored 0.3550 exactly.\n'        > "$TMP/spikes/E_trailingzero/RESULT.md"
printf '{"v": 0.355}\n'                  > "$TMP/spikes/E_trailingzero/result.json"
# F: artifact is RUN.txt, not json -> clean. This is the case whose absence made
#    the first measurement in prosecite.py's own header wrong.
printf 'Elapsed 27.469880104064940 s.\n' > "$TMP/spikes/F_txtonly/RESULT.md"
printf 'elapsed=27.469880104064940\n'    > "$TMP/spikes/F_txtonly/RUN.txt"

OUT=$(cd "$TMP" && python3 "$TOOL" 2>&1); RC=$?

echo "prosecite v1 — sandbox"
[ "$RC" -eq 1 ] && ok "exit 1 when ghosts exist" || bad "expected exit 1, got $RC"
echo "$OUT" | grep -q '0.8642097'             && ok "B_ghost ghost reported (number absent from real repo)" || bad "B_ghost ghost NOT reported"
echo "$OUT" | grep -q 'A_backed'              && bad "A_backed wrongly reported"   || ok  "A_backed clean (own artifact)"
echo "$OUT" | grep -q 'C_crossspike'          && bad "C_crossspike wrongly reported" || ok "C_crossspike clean (cites another spike)"
echo "$OUT" | grep -q 'D_notmetric'           && bad "D_notmetric wrongly reported" || ok "D_notmetric clean (<3dp, dates, versions)"
echo "$OUT" | grep -q 'E_trailingzero'        && bad "E_trailingzero wrongly reported" || ok "E_trailingzero clean (0.3550 == 0.355)"
echo "$OUT" | grep -q 'F_txtonly'             && bad "F_txtonly wrongly reported"  || ok "F_txtonly clean (.txt is an artifact, not just .json)"

# --- check 3: THE TOOL MUST NOT BE ABLE TO SATISFY ITSELF --------------------
# If RESULT.md were in the artifact set, B_ghost's 0.9246 would match its own
# prose and the scan would go permanently green. Assert the exclusion holds by
# giving a spike NOTHING but a RESULT.md.
mkdir -p "$TMP/spikes/G_selfonly"
printf 'A number that exists only here: 0.7654321\n' > "$TMP/spikes/G_selfonly/RESULT.md"
OUT2=$(cd "$TMP" && python3 "$TOOL" 2>&1)
echo "$OUT2" | grep -q '0.7654321' \
  && ok "self-reference excluded — a number present only in its own RESULT.md still fires" \
  || bad "RESULT.md counts as its own artifact: THE CHECK CAN NEVER FIRE"

# --- refusal, not degradation, on no inputs (H30's class) --------------------
EMPTY=$(mktemp -d); mkdir -p "$EMPTY/spikes"
(cd "$EMPTY" && python3 "$TOOL" >/dev/null 2>&1); RC2=$?
rm -rf "$EMPTY"
[ "$RC2" -eq 3 ] && ok "refuses (exit 3) on an empty tree rather than reporting clean" \
                 || bad "expected exit 3 on empty tree, got $RC2"

# --- clean tree exits 0 ------------------------------------------------------
rm -rf "$TMP/spikes/B_ghost" "$TMP/spikes/G_selfonly"
(cd "$TMP" && python3 "$TOOL" >/dev/null 2>&1); RC3=$?
[ "$RC3" -eq 0 ] && ok "exit 0 when every number is backed" || bad "expected exit 0, got $RC3"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
