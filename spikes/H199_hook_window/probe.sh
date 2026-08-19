#!/bin/sh
# H199 F1/F2/F3 — IS THERE A POINT WHERE THE COMMIT'S CONTENT IS FROZEN AND ITS
# MESSAGE IS STILL WRITABLE?
#
# Four rows (H180 H190 H199 H205) say the `Carries:` trailer cannot be computed
# in time because `--only` re-reads the WORKING TREE at `git commit`, after any
# check the lane ran. This decides, on THIS git, in a scratch repo, whether the
# `commit-msg` hook is inside or outside that window. `man githooks` does not
# say; H190's method is to measure rather than read.
#
# TWO-SIDED BY CONSTRUCTION. A1 alone cannot separate "the hook sees the temp
# index" from "the hook sees the real index and they happen to agree", so A2
# stages an unrelated sibling file that `--only` must EXCLUDE: real index sees
# it, temp index does not. A4 runs the remedy on record (compute BEFORE
# `git commit`) against the same fixture, so a green A1 is not mistaken for
# "any placement works".
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$ROOT/.scratch"
D=$(mktemp -d -p "$ROOT/.scratch")
trap 'rm -rf "$D"' EXIT
CC="$ROOT/spikes/harness/carriescheck.py"
fail=0
ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 (want '$3', got '$2')"; fail=$((fail+1)); fi; }

cd "$D"
git init -q .; git config user.email t@t; git config user.name t
printf 'base\n' > CHANNEL.md; printf 'base\n' > other.txt
git add CHANNEL.md other.txt; git commit -qm base

# ---------------------------------------------------------------- A1 + A2 + A3
# The hook records what IT can see, then rewrites the message file.
mkdir -p .git/hooks
cat > .git/hooks/commit-msg <<'HOOK'
#!/bin/sh
# $OUT is absolute and passed in the environment: GIT_DIR is NOT exported to
# this hook on this git, and my first draft wrote to "$GIT_DIR/../f" -- which
# expanded to "/../f", failed on a read-only filesystem, and left every
# assertion reading a MISSING file. Two of those still reported PASS.
git diff --cached --name-only            > "$OUT/hook_paths.txt"
git diff --cached --unified=0 -- CHANNEL.md \
  | sed -n 's/^+\([^+]\)/\1/p'           > "$OUT/hook_added.txt"
echo "${GIT_INDEX_FILE:-UNSET}"          > "$OUT/hook_indexfile.txt"
printf 'Injected-By: commit-msg\n' >> "$1"
HOOK
chmod +x .git/hooks/commit-msg
OUT="$D"; export OUT

printf 'DONE X1 AGENT-2 foreign STAGED line\n' >> CHANNEL.md
git add CHANNEL.md                        # lane staged one foreign line
printf 'DONE X2 ATTACKER-1 foreign UNSTAGED line\n' >> CHANNEL.md   # co-lane appends AFTER
printf 'sibling\n' >> other.txt; git add other.txt                  # co-lane's staged sibling

git commit -q --only CHANNEL.md -m "subject" 2>/dev/null

# EVERY ARM BELOW READS A FILE THE HOOK WROTE. Assert they exist FIRST: my first
# draft's hook could not write at all and A2c still reported PASS, because
# `cat` of a missing file returns "" which is not the literal "UNSET" it was
# compared against. A control whose absent input reads as its healthy answer is
# the family this repo calls B.
for f in hook_paths.txt hook_added.txt hook_indexfile.txt; do
  ck "A0 hook wrote $f" "$( [ -s "$D/$f" ] && echo yes || echo no )" yes
done

# A1 — does what the hook saw equal what the commit contains?
git show --format= --unified=0 -- CHANNEL.md | sed -n 's/^+\([^+]\)/\1/p' > commit_added.txt
if cmp -s hook_added.txt commit_added.txt; then a1=equal; else a1=differs; fi
ck "A1 hook's --cached added lines == the commit's added lines" "$a1" equal
ck "A1b hook saw the UNSTAGED co-lane line" \
   "$(grep -c 'ATTACKER-1' hook_added.txt)" 1

# A2 — the control that can fail: a staged sibling proves which index it is.
ck "A2 hook's --cached EXCLUDES the staged sibling (temp index, not the real one)" \
   "$(grep -c '^other.txt$' hook_paths.txt)" 0
ck "A2b sibling is likewise absent from the commit" \
   "$(git show --format= --name-only HEAD | grep -c '^other.txt$')" 0
ck "A2c GIT_INDEX_FILE was exported to the hook" \
   "$( [ "$(cat hook_indexfile.txt)" = UNSET ] && echo unset || echo set )" set

# A3 — F2: does a commit-msg rewrite of $1 reach the commit?
ck "A3 commit-msg rewrite of \$1 lands in the message" \
   "$(git log -1 --format=%B | grep -c '^Injected-By: commit-msg$')" 1

# ------------------------------------------------------------------------- A4
# F3, NECESSITY. Same fixture, the remedy on record: compute BEFORE `git commit`.
git commit -q --allow-empty -m reset >/dev/null
printf 'DONE X3 AGENT-2 mine\n' >> CHANNEL.md
pre=$(python3 "$CC" ok-1 --worktree --trailer 2>/dev/null)   # lane's check
printf 'DONE X4 ATTACKER-1 co-lane appended AFTER the check\n' >> CHANNEL.md  # the window
rm -f hook_added.txt
git commit -q --only CHANNEL.md -m "subject" 2>/dev/null
post=$(python3 "$CC" ok-1 HEAD --trailer 2>/dev/null)
# A4's negative arm is EMPTY-CAPTURE-SHAPED: `grep -c` of nothing is 0, which is
# the answer F3 predicts, so a `carriescheck` that printed nothing at all would
# report PASS. It DID -- the first run of this probe piped the PROSE report
# through `sed -n 's/^Carries: //p'` and the paste-ready trailer is INDENTED by
# four spaces, so `pre` and `post` were both '' and A4 passed for no reason.
# `--trailer` is the machine-readable mode; this arm asserts the tool spoke.
ck "A4-guard pre is non-empty and NAMES the lane it should see (else A4 is vacuous)" \
   "$(echo "$pre" | grep -c 'AGENT-2')" 1
ck "A4 pre-commit computation MISSES the co-lane (F3 predicted: it is wrong)" \
   "$(echo "$pre" | grep -c 'ATTACKER-1')" 0
ck "A4b the commit DOES carry that lane" \
   "$(echo "$post" | grep -c 'ATTACKER-1')" 1
ck "A4c so the two disagree — the window is real" \
   "$( [ "$pre" = "$post" ] && echo same || echo differs )" differs

echo "--- pre='$pre'  post='$post' ---"
echo "checks failed: $fail"
[ "$fail" -eq 0 ] || exit 1
