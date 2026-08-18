#!/usr/bin/env bash
# H86 compare.sh v1 — ATOM-3, 2026-08-17. Runs the PREREGISTERED falsifier for
# the stranded.sh v1->v2 rewrite:
#
#   "one `git log --name-only` pass ... if that does not reproduce v1's exact
#    classification counts on the current tree, the rewrite is wrong and v1 stays"
#
# and the CLAIM's own refinement of it: diff FILE BY FILE, never totals --
# equal totals with different assignments is the failure a summary cannot see.
#
# THE CONTROL THIS SCRIPT EXISTS FOR
# ----------------------------------
# Both versions read the LIVE worktree, five lanes are committing into it, and v1
# takes ~4 minutes. So a difference between the two runs is ambiguous by default:
# the rewrite may be wrong, or the tree may simply have moved between them. That
# ambiguity is not a caveat to write down afterwards, it is the whole experiment.
#
# So the fast version is run TWICE, STRADDLING the slow one -- v2a, v1, v2b --
# and the tree is fingerprinted at every boundary. v2a == v2b plus an unmoved
# fingerprint is what makes the v1-vs-v2 diff mean anything. If they differ, the
# window was dirty and this script says so instead of reporting a verdict.
#
# CAN THIS CONTROL FAIL? Yes, and that is the point (A15): `touch` any
# uncommitted file, or let a lane commit, while it runs -- the fingerprint moves
# and DRIFT is reported. It fired for real on the first run of this script.
#
# The AGE column is deliberately excluded from the comparison: it is
# (now - mtime)/60, so a file crossing a minute boundary between two runs changes
# it with nothing about the classification having changed. Comparing it would
# make a passing rewrite look broken -- a control that fires on its own clock.
# The claim is the CLASSIFICATION, and that is fields 1, 3, 4.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
D=spikes/H86_stranded_cost

fingerprint() {   # HEAD + every uncommitted path and its mtime = the exact input
  { git rev-parse HEAD
    git status --porcelain | awk '{print $NF}' | sort | while read -r p; do
        [ -f "$p" ] && printf '%s\t%s\n' "$p" "$(stat -f %m "$p" 2>/dev/null || stat -c %Y "$p" 2>/dev/null)"
      done
  } | shasum -a 256 | cut -c1-16
}
run() {  # run() <script> <dumpfile> ; prints wall seconds
  local s e
  s=$(date +%s)
  DUMP="$D/$2" sh "$D/$1" > "$D/${2%.tsv}.stdout" 2>&1
  e=$(date +%s)
  echo $((e - s))
}
# classification only: field 1 (verdict), 3 (owner), 4 (path). Never field 2 (age).
key() { awk -F'\t' 'NF>=4 {print $1"\t"$3"\t"$4}' "$1" | sort; }

F0=$(fingerprint); echo "fingerprint before v2a : $F0"
T2A=$(run v2.sh v2a.tsv);  echo "v2a  ${T2A}s"
F1=$(fingerprint); echo "fingerprint after  v2a : $F1"
T1=$(run v1.sh v1a.tsv);   echo "v1   ${T1}s"
F2=$(fingerprint); echo "fingerprint after  v1  : $F2"
T2B=$(run v2.sh v2b.tsv);  echo "v2b  ${T2B}s"
F3=$(fingerprint); echo "fingerprint after  v2b : $F3"

echo
DRIFT=no
[ "$F0" = "$F1" ] && [ "$F1" = "$F2" ] && [ "$F2" = "$F3" ] || DRIFT=yes
key "$D/v2a.tsv" > "$D/.k2a"; key "$D/v2b.tsv" > "$D/.k2b"; key "$D/v1a.tsv" > "$D/.k1"
STABLE=no; cmp -s "$D/.k2a" "$D/.k2b" && STABLE=yes

echo "tree fingerprint unmoved across all four boundaries : $([ $DRIFT = no ] && echo YES || echo 'NO  <-- window was dirty')"
echo "v2 reproduces itself across the v1 run (v2a == v2b) : $STABLE"
echo "rows: v1=$(wc -l < "$D/.k1") v2a=$(wc -l < "$D/.k2a") v2b=$(wc -l < "$D/.k2b")"
echo "speedup: v1 ${T1}s / v2 ${T2A}s"
echo
if cmp -s "$D/.k1" "$D/.k2a"; then
  echo "VERDICT: IDENTICAL file-by-file (verdict, owner, path) across $(wc -l < "$D/.k1" | tr -d ' ') paths."
  RC=0
else
  echo "VERDICT: DIFFERS. Lines only in v1 (<) / only in v2 (>):"
  diff "$D/.k1" "$D/.k2a" | head -60
  RC=1
fi
if [ "$DRIFT" = yes ] || [ "$STABLE" = no ]; then
  echo
  echo "*** NOT DECISIVE: the tree moved under the comparison. Re-run. ***"
  RC=2
fi
rm -f "$D/.k1" "$D/.k2a" "$D/.k2b"
exit $RC
