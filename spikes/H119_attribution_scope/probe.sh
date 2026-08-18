#!/usr/bin/env bash
# H119 — drive commit_scoped.sh's path attribution through its own DRY_RUN seam.
#
# Four injected checker outputs, each a real shape taken from this tree, and the
# expected verdict stated for each BEFORE the fix. The seam exists because v2's
# author wrote it: "a control that can only fire when some other lane happens to
# have left the tree broken is a coincidence, not a control."
#
# usage: bash spikes/H119_attribution_scope/probe.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
D="spikes/H119_attribution_scope/.fixtures"      # §10: under the workspace
rm -rf "$D"; mkdir -p "$D"
MSG="$D/msg"
printf 'subject\n\nAtom: ok-1\nClaude-Session: unassigned\nReviewed-By: unreviewed\n' > "$MSG"

# 1 — the live case: a REFUSAL about another lane's file, plus baselined
#     non-gating lines that name WORK_QUEUE.md, which my commit carries.
cat > "$D/mixed.out" <<'EOF'
  KNOWN ROW SHAPE WORK_QUEUE.md: `S75` has 8 fields, not 5 -- its status column is unreadable.
  KNOWN ROW SHAPE WORK_QUEUE.md: `N1` has 4 fields, not 5 -- its status column is unreadable.
  UNRESOLVED spikes/harness/autoloop_local.sh: `spikes/H116_inert_loop/gate_arms.out` does not exist

REFUSE: 1 citation(s) in the harness do not resolve.
EOF

# 2 — a REAL refusal about a path I carry. Must always refuse.
cat > "$D/mine.out" <<'EOF'
  UNRESOLVED WORK_QUEUE.md: `spikes/NOPE/x.md` does not exist

REFUSE: 1 citation(s) in the harness do not resolve.
EOF

# 3 — a refusal that marks NO line: the fail-closed direction (F2). Attribution
#     must fall back to the whole output rather than let a violation through.
cat > "$D/unmarked.out" <<'EOF'
something went wrong while reading WORK_QUEUE.md and this line carries no marker
EOF

# 4 — a crashed checker must still refuse (v2 defect 3, kept honest here).
cat > "$D/crash.out" <<'EOF'
Traceback (most recent call last):
  File "spikes/harness/refcheck.py", line 1, in <module>
EOF

run() {   # $1 fixture, $2 label, $3 expected rc
  out=$(DRY_RUN=1 CHECKERS_OUT_FILE="$D/$1" CHECKERS_RC=1 \
        sh spikes/harness/commit_scoped.sh "$MSG" WORK_QUEUE.md 2>&1)
  rc=$?
  if [ "$rc" = "$3" ]; then printf '  OK    %-46s rc=%s\n' "$2" "$rc"
  else printf '  BAD   %-46s rc=%s want %s\n' "$2" "$rc" "$3"
       printf '%s\n' "$out" | tail -3 | sed 's/^/          /'
  fi
}

echo "H119 — path attribution, driven through the DRY_RUN seam"
run mixed.out    "refusal about ANOTHER lane + baselined WORK_QUEUE" 0
run mine.out     "refusal that really names WORK_QUEUE.md"           1
run unmarked.out "refusal with NO marked line (fail closed)"         1
run crash.out    "a crashed checker still refuses"                   1
rm -rf "$D"
