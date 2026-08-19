#!/bin/sh
# H214 — every out-of-band `git diff --cached` check in commit_scoped.sh scored
# the SHARED index, which is another lane's staging area, not this commit.
#
# TWO-SIDED AND TWO-DIRECTIONAL. The row I filed charged A15, "a control that
# cannot fire". The measurement is worse: it CAN fire, about the WRONG FILES.
# So this asserts both directions with the REAL `commit-msg.hook`, never a stub:
#   FALSE NEGATIVE  the H19 ownership gate is INERT on the only commit path used
#   FALSE POSITIVE  a co-lane STAGING a file makes that gate refuse YOUR commit
#
# It also runs the arm that retracted the row's own diagnosis: under a real
# `git commit --only`, git builds a TEMPORARY index and exports it as
# GIT_INDEX_FILE, so `--cached` is exactly the working-tree content of your
# paths. The hook was right; the call site was wrong. That is the branch the
# row's own F1 preregistered as "this row is mis-aimed".
#
# §10: everything is built under this spike directory, nothing outside it.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HOOK="$ROOT/spikes/harness/commit-msg.hook"
D="$ROOT/spikes/H214_index_scope/.sandbox"   # ABSOLUTE: this probe cd's into it
pass=0; fail=0
ck() { # ck <name> <cond-as-string-result> ; expects "$2" = yes|no
  if [ "$2" = yes ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1"
  else fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; fi
}

newrepo() {
  rm -rf "$D"; mkdir -p "$D"; cd "$D" || exit 2
  git init -q .; git config user.email a@b.c; git config user.name t
  mkdir -p .git/hooks; cp "$HOOK" .git/hooks/commit-msg; chmod +x .git/hooks/commit-msg
  echo base > mine.txt
  printf '# HANDOFF — write-ahead checkpoint (other lane)\n' > HANDOFF.OTHER-9.md
  git add -A; git commit -q --no-verify -m "base
Atom: AGENT-1
Claude-Session: local
Reviewed-By: unreviewed"
  cd "$ROOT" || exit 2
}

msgfile() {  # writes $D/m.txt; $D is ABSOLUTE because callers have cd'd into it
  printf 'subject line for the probe\n\nAtom: AGENT-1\nClaude-Session: local\nReviewed-By: unreviewed\n' \
    > "$D/m.txt" || { echo "FIXTURE VOID: cannot write $D/m.txt" >&2; exit 2; }
}

# THE FIX, extracted verbatim in shape from commit_scoped.sh v10 so this probe
# tests the mechanism rather than a paraphrase of it.
with_scoped_index() { # $1 = msgfile, rest = paths
  _m=$1; shift
  _ix="$PWD/.probe_index.$$"
  GIT_INDEX_FILE="$_ix" git read-tree HEAD
  GIT_INDEX_FILE="$_ix" git add -A -- "$@"
  GIT_INDEX_FILE="$_ix" .git/hooks/commit-msg "$_m" 2>&1
  _rc=$?
  rm -f "$_ix"
  return $_rc
}

echo "H214 — the index four checks read is not the commit they gate"
echo

# ---- A1: git's OWN invocation. The arm that retracts the row's diagnosis. ----
newrepo; cd "$D" || exit 2
echo "MINE" >> mine.txt
echo "COLANE" >> HANDOFF.OTHER-9.md
git add HANDOFF.OTHER-9.md          # a co-lane's add sits in the SHARED index
cat > .git/hooks/commit-msg <<'H'
#!/bin/sh
git diff --cached --name-only > .seen
exit 0
H
chmod +x .git/hooks/commit-msg
msgfile
git commit -q --only mine.txt -F m.txt 2>/dev/null
[ -f .seen ] || { echo "FIXTURE VOID: the hook never ran — A1b would pass on an empty file" >&2; exit 2; }
seen=$(tr '\n' ' ' < .seen)
case "$seen" in *mine.txt*) r=yes ;; *) r=no ;; esac
ck "A1a a REAL 'git commit --only' shows the hook YOUR path ($seen)" "$r"
case "$seen" in *HANDOFF.OTHER-9*) r=no ;; *) r=yes ;; esac
ck "A1b ...and NOT the co-lane's staged path — so the HOOK was never wrong" "$r"

# ---- A2/A3: the direct call, before and after the scoped index ----
cp "$HOOK" .git/hooks/commit-msg; chmod +x .git/hooks/commit-msg
cat > .git/hooks/commit-msg <<'H'
#!/bin/sh
git diff --cached --name-only > .seen
exit 0
H
chmod +x .git/hooks/commit-msg
echo MORE >> mine.txt
.git/hooks/commit-msg m.txt
seen=$(tr '\n' ' ' < .seen)
case "$seen" in *mine.txt*) r=no ;; *) r=yes ;; esac
ck "A2 the DIRECT call (commit_scoped v9) does NOT show your path ($seen)" "$r"
with_scoped_index m.txt mine.txt >/dev/null 2>&1
seen=$(tr '\n' ' ' < .seen)
case "$seen" in *mine.txt*) r=yes ;; *) r=no ;; esac
ck "A3 the SCOPED index (v10) shows exactly your path ($seen)" "$r"
cd "$ROOT" || exit 2

# ---- A4: FALSE NEGATIVE — the ownership REFUSAL is inert on the used path ----
newrepo; cd "$D" || exit 2
echo "AGENT-1 EDITING ANOTHER LANE'S JOURNAL" >> HANDOFF.OTHER-9.md
msgfile
if .git/hooks/commit-msg m.txt >/dev/null 2>&1; then r=yes; else r=no; fi
ck "A4a v9: committing another lane's journal is NOT refused — the H19 gate is INERT" "$r"
if with_scoped_index m.txt HANDOFF.OTHER-9.md >/dev/null 2>&1; then r=no; else r=yes; fi
ck "A4b v10: the same commit IS refused — the gate fires again" "$r"
cd "$ROOT" || exit 2

# ---- A5: FALSE POSITIVE — a co-lane's `git add` refuses YOUR commit ----
newrepo; cd "$D" || exit 2
echo "COLANE WRITE" >> HANDOFF.OTHER-9.md
git add HANDOFF.OTHER-9.md              # THEIR add, in the SHARED index
echo "MY UNRELATED EDIT" >> mine.txt
msgfile
if .git/hooks/commit-msg m.txt >/dev/null 2>&1; then r=no; else r=yes; fi
ck "A5a v9: a co-lane STAGING their journal REFUSES your unrelated commit" "$r"
if with_scoped_index m.txt mine.txt >/dev/null 2>&1; then r=yes; else r=no; fi
ck "A5b v10: your unrelated commit passes — one lane can no longer block another" "$r"
staged=$(git diff --cached --name-only | tr '\n' ' ')
case "$staged" in *HANDOFF.OTHER-9*) r=yes ;; *) r=no ;; esac
ck "A6 the SHARED index is left exactly as found ($staged)" "$r"
cd "$ROOT" || exit 2

rm -rf "$D"
echo
echo "H214 probe: $pass pass, $fail fail"
[ "$fail" -eq 0 ] || exit 1
