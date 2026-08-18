#!/bin/sh
# test_h75_routing.sh v1 — H75, ATOM-3, 2026-08-18.
#
# THE DEFECT IT GUARDS
# ====================
# CLASS: **A CHECK NOBODY IS ROUTED TO IS PROSE WITH EXTRA STEPS** (H15) -- and
# `pre-commit.hook` v3 was worse than un-routed, it was MIS-routed: both refusal
# sites said `Bypass: git commit --no-verify` and named
# `spikes/harness/commit_scoped.sh` at neither, while that wrapper sat in the
# same directory. H72 measured what the advertised escape costs: `--no-verify`
# drops the `commit-msg` trailer gate too, landing `subject=wip trailers=[]`.
#
# WHY THIS DRIVES A REAL REFUSAL INSTEAD OF GREPPING THE SOURCE
# =============================================================
# A grep for the string would pass on a hook that contains the text in a comment
# and never prints it, and it would pass on a `_route` helper that no refusal
# path calls. That is this repo's most-repeated defect -- a check that asserts
# the presence of a fix rather than its EFFECT -- so this builds a throwaway repo
# inside the workspace (§10), makes the gate refuse for real, and reads stdout.
#
# BOTH refusal sites are exercised, because H75's whole defect was two sites
# saying the same wrong thing and a fix reaching one of them would look green.
#
#   sh spikes/harness/test_h75_routing.sh
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
cd "$ROOT"
fail=0
ok()  { printf '  PASS  %s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; fail=1; }

TMP=$(mktemp -d "$ROOT/spikes/.h75routing.XXXXXX") || exit 2
trap 'rm -rf "$TMP"' EXIT INT TERM

git init -q "$TMP" 2>/dev/null
(cd "$TMP" && git config user.email x@y && git config user.name x) >/dev/null 2>&1
mkdir -p "$TMP/spikes/harness" "$TMP/.git/hooks"
cp spikes/harness/pre-commit.hook "$TMP/.git/hooks/pre-commit"
chmod +x "$TMP/.git/hooks/pre-commit"
# The hook resolves CHECKS relative to the repo root. A refcheck.py that always
# refuses is the shortest way to reach refusal site 2 deterministically -- the
# point here is the ROUTING TEXT, not which checker fired.
cp spikes/harness/refcheck.py "$TMP/spikes/harness/" 2>/dev/null
printf 'import sys\nprint("synthetic refusal")\nsys.exit(1)\n' \
  > "$TMP/spikes/harness/refcheck.py"
: > "$TMP/spikes/harness/journalcheck.py"
: > "$TMP/spikes/harness/githygiene.py"
printf 'seed\n' > "$TMP/seed.txt"
(cd "$TMP" && git add -A && git commit -qm base --no-verify) >/dev/null 2>&1

# --- SITE 2: a checker refuses.
printf 'x\n' >> "$TMP/seed.txt"
out2=$(cd "$TMP" && git add seed.txt && git commit -m t 2>&1)
case "$out2" in
  *'pre-commit REFUSED'*) ok "site 2 (checker refusal) fires" ;;
  *) bad "site 2 did not refuse; this test proves nothing about it:
$out2" ;;
esac
case "$out2" in
  *commit_scoped.sh*) ok "  and routes to commit_scoped.sh" ;;
  *) bad "site 2 refusal does NOT name commit_scoped.sh -- H75's exact defect" ;;
esac
case "$out2" in
  *'strictly MORE than'*|*'also drops the TRAILER gate'*)
     ok "  and says WHY, so the safer route is not just an alternative" ;;
  *) bad "site 2 names the wrapper without saying --no-verify is lossier; a lane
        picks the shorter command when told nothing" ;;
esac

# --- SITE 1: staged content differs from the worktree (the H35 unsoundness
#     guard). A different code path, and v3 had the same wrong text here.
printf 'staged\n' > "$TMP/seed.txt"
(cd "$TMP" && git add seed.txt) >/dev/null 2>&1
printf 'worktree-differs\n' > "$TMP/seed.txt"
out1=$(cd "$TMP" && git commit -m t 2>&1)
case "$out1" in
  *'not the content on disk'*) ok "site 1 (unsoundness guard) fires" ;;
  *) bad "site 1 did not fire; the routing there is unproven:
$out1" ;;
esac
case "$out1" in
  *commit_scoped.sh*) ok "  and routes to commit_scoped.sh" ;;
  *) bad "site 1 refusal does NOT name commit_scoped.sh -- a fix that reached
        one refusal site and not the other would look green without this" ;;
esac

# --- The wrapper must exist, or every refusal above advertises a missing tool.
# H23's class: a surviving site instructing callers to use an interface that is
# not there. A gate citing a missing artifact reads as satisfied.
[ -f spikes/harness/commit_scoped.sh ] \
  && ok "the routed-to wrapper actually exists" \
  || bad "pre-commit routes to spikes/harness/commit_scoped.sh and it is ABSENT"

[ "$fail" -eq 0 ] && printf 'test_h75_routing: both refusal sites route to the scoped wrapper, and say why\n'
exit "$fail"
