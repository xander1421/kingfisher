#!/bin/sh
# test_versioncheck.sh v1 — H180. Drives versioncheck.py in a throwaway tree.
#
# Check 6 is the one that matters: a file with NO version header must be
# IGNORED, not reported. Most files here have none, so a checker that flagged
# them would be red forever and get bypassed — the always-red gate H14/H52
# recorded this repo doing exactly that.
# Check 1 doubles as the anti-inertness assertion: it asserts the SANDBOX's own
# filename appears, so the suite cannot pass by reading the real harness (the
# way test_prosecite.sh v1 did).

set -u
HERE=$(cd "$(dirname "$0")" && pwd)
TOOL="$HERE/versioncheck.py"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  ok   $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL $1"; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
echo "versioncheck v1 — sandbox"

# stale: header v1, body carries a v3 block
cat > "$TMP/sandboxstale.sh" <<'F'
#!/bin/sh
# sandboxstale.sh v1 — original.
# ==== v3, H999 — later work that never touched the header ====
F
# ahead: header v5, newest block v2
cat > "$TMP/aheadfile.sh" <<'F'
#!/bin/sh
# aheadfile.sh v5 — bumped with no rationale block.
# ==== v2, H998 ====
F
# clean: header equals newest block
cat > "$TMP/cleanfile.sh" <<'F'
#!/bin/sh
# cleanfile.sh v4 — current.
# ==== v4, H997 ====
# ==== v3, H996 ====
F
# no header at all -> must be IGNORED
cat > "$TMP/nohdr.sh" <<'F'
#!/bin/sh
echo hello
F

OUT=$(python3 "$TOOL" "$TMP" 2>&1); RC=$?

[ "$RC" -eq 1 ] && ok "exit 1 when drift exists" || bad "expected exit 1, got $RC"
echo "$OUT" | grep -q 'sandboxstale.sh' && ok "stale header reported (and the SANDBOX is what was read)" \
                                        || bad "stale header NOT reported — suite may be inert"
echo "$OUT" | grep -q 'header says v1, newest block is v3' && ok "names both versions" || bad "versions not named"
echo "$OUT" | grep -q 'aheadfile.sh' && ok "header-ahead reported" || bad "header-ahead NOT reported"
echo "$OUT" | grep -q 'HEADER AHEAD OF ITS BLOCKS' && ok "header-ahead reported SEPARATELY (§12.11 family, not symptom)" \
                                                   || bad "the two drift directions were merged"
echo "$OUT" | grep -q 'cleanfile.sh' && bad "clean file wrongly reported" || ok "clean file silent"
echo "$OUT" | grep -q 'nohdr.sh'     && bad "unversioned file reported — would be red forever" \
                                     || ok "unversioned file ignored (most files have no header)"

# 8 — HEREDOC BODIES ARE DATA, NOT THIS FILE'S METADATA. v1 flagged THIS SUITE
#     at "header v1, newest block v4" because the fixtures above contain
#     `# ==== v4, H997 ====` inside `cat > f <<'F'` blocks. Excluding test files
#     would have been weakening a gate to pass it; stripping heredoc bodies is
#     the actual fix, and this check is what keeps it fixed.
cat > "$TMP/heredocfile.sh" <<'OUTER'
#!/bin/sh
# heredocfile.sh v1 — current, and its NEWEST REAL block is v1.
cat > /tmp/whatever <<'INNER'
# ==== v9, H000 — a fixture inside a heredoc, not this file's version ====
INNER
OUTER
python3 "$TOOL" "$TMP" 2>&1 | grep -q 'heredocfile.sh' \
  && bad "a version block inside a HEREDOC was read as the file's own" \
  || ok "heredoc bodies ignored (fixtures are data, not metadata)"
rm -f "$TMP/heredocfile.sh"

# 9/10 — THE TWO DEFECTS THAT MADE v1's PUBLISHED COUNT WRONG, in both directions.
#   a) a LONG `=` banner must be seen. headcheck.sh:4 has twenty-eight `=` and
#      v1's `={0,6}` missed it, so a correct file read as "header ahead".
#   b) PROSE mentioning a version must NOT count. `# v1 ran HEAD's refcheck.py`
#      is a sentence about v1, not a block declaring it.
cat > "$TMP/longbanner.sh" <<'F'
#!/bin/sh
# longbanner.sh v2 — current.
# ============================ v2, H70 — the defect removed ==================
F
python3 "$TOOL" "$TMP" 2>&1 | grep -q 'longbanner.sh' \
  && bad "a long =-banner was missed, so a correct file read as drifted" \
  || ok "long =-banner recognised as a version block"

cat > "$TMP/prosever.sh" <<'F'
#!/bin/sh
# prosever.sh v1 — current, and v1 is genuinely the newest.
# v3 ran the old comparison and was wrong about it, which is prose, not a block.
# v2 metric binding admits exactly one integer metric.
F
python3 "$TOOL" "$TMP" 2>&1 | grep -q 'prosever.sh' \
  && bad "PROSE mentioning a version was counted as a version block" \
  || ok "prose mentioning a version is not a block"
rm -f "$TMP/longbanner.sh" "$TMP/prosever.sh"

# clean tree exits 0
rm -f "$TMP/sandboxstale.sh" "$TMP/aheadfile.sh"
python3 "$TOOL" "$TMP" >/dev/null 2>&1; RC2=$?
[ "$RC2" -eq 0 ] && ok "exit 0 when every header matches" || bad "expected exit 0, got $RC2"

# refuses rather than reporting clean on a missing directory
python3 "$TOOL" "$TMP/does-not-exist" >/dev/null 2>&1; RC3=$?
[ "$RC3" -eq 3 ] && ok "refuses (exit 3) on a missing directory" || bad "expected exit 3, got $RC3"

echo ""
echo "$PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] || exit 1
