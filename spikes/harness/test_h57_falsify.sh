#!/usr/bin/env bash
# test_h57_falsify.sh — H57. Does `allocid.sh --selfcheck` go RED when the defect
# returns? A passing suite cannot answer that for itself (H7), and my own C24
# entry records a fix that made a live check INERT within five minutes with only
# the falsifier saying so.
#
# THE DEFECT: allocid.sh v1 seeded its free list from three documents and never
# from `spikes/`, where MISSION_LOOP §13.3 says a spike number is claimed — by
# creating the directory. Measured before the repair: 20 live spike directories
# absent from the pool, and `allocid.sh G` answering G3 against
# `spikes/G3_claim_graph`.
#
# THREE FALSIFIERS, because the v2 change has three parts and a green suite over
# any one of them is a check that cannot fail:
#   1. delete the filesystem line from the seed  -> the fixture check must go RED
#   2. delete the tracked-documents line         -> allocation must lose ids the
#                                                   three shared logs do not name
#   3. restore the `.seeded.$p` guard            -> a source added after the first
#                                                   run must become invisible
#
# NO STALE COPY IS COMMITTED. Each broken variant is derived here at run time
# from the live source and deleted, because a checked-in copy of a shared
# instrument is exactly A24 — a second artifact that drifts from its origin.
# Every patch ASSERTS ITS ANCHOR MATCHED first: a `sed` whose anchor is absent
# leaves the file unchanged and the run then reports the fixed behaviour under
# the defect's name (BSD `sed` has no `\b`, HANDOFF C28).
#
# usage: bash spikes/harness/test_h57_falsify.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/spikes/harness/allocid.sh"
[ -f "$SRC" ] || { echo "FAIL: no allocid.sh at $SRC"; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail=0

# A tree the broken variants can be run against: id Z7 exists ONLY as a spikes/
# directory, Z1..Z6 only in the shared logs, and Z8 only in a tracked .md that
# is not one of the three the v1 seed read.
build_tree() {
  t="$1"
  rm -rf "$t"; mkdir -p "$t/spikes/harness" "$t/spikes/Z7_on_disk_only"
  for i in 1 2 3 4 5 6; do echo "Z$i"; done > "$t/WORK_QUEUE.md"
  : > "$t/CHANNEL.md"; : > "$t/livechat.log"
  mkdir -p "$t/analysis"; echo 'Z8 is claimed in this document only' > "$t/analysis/NOTES.md"
  ( cd "$t" && git init -q . >/dev/null 2>&1 && git add -A >/dev/null 2>&1 )
}

# --- control: the LIVE source on that tree must answer neither Z7 nor Z8 -------
build_tree "$WORK/live"
cp "$SRC" "$WORK/live/spikes/harness/allocid.sh"
got=$(KF_IDS="$WORK/live/.ids" sh "$WORK/live/spikes/harness/allocid.sh" Z 2>&1)
if [ "$got" = "Z9" ]; then
  echo "  OK   live allocid.sh answers Z9 -- it sees the directory AND the .md"
else
  echo "  BAD  live allocid.sh answered '$got', expected Z9. The fixture does not"
  echo "       reproduce the environment the falsifiers below assume"
  fail=1
fi

# --- falsifier 1: remove the filesystem line ----------------------------------
build_tree "$WORK/f1"
sed 's|^  ls spikes 2>/dev/null | grep -oE.*$|  :|' "$SRC" > /dev/null 2>&1 || true
awk '!/ls spikes 2>\/dev\/null \| grep -oE/' "$SRC" > "$WORK/f1/spikes/harness/allocid.sh"
if cmp -s "$SRC" "$WORK/f1/spikes/harness/allocid.sh"; then
  echo "  BAD  falsifier 1's edit matched NOTHING -- the anchor is gone, so the"
  echo "       result below would be the fixed code reported under the defect's name"
  fail=1
else
  got=$(KF_IDS="$WORK/f1/.ids" sh "$WORK/f1/spikes/harness/allocid.sh" Z 2>&1)
  if [ "$got" = "Z7" ]; then
    echo "  OK   falsifier 1: without the filesystem line it answers Z7, and"
    echo "       spikes/Z7_on_disk_only holds Z7 -- the defect is reachable"
  else
    echo "  BAD  falsifier 1: expected Z7 with the filesystem line removed, got '$got'."
    echo "       The fixture cannot express the defect, so the live check proves nothing"
    fail=1
  fi
fi

# --- falsifier 2: remove the tracked-documents line ---------------------------
build_tree "$WORK/f2"
awk '!/git ls-files -z -- /' "$SRC" | awk '!/xargs -0 grep -ohE/' \
  > "$WORK/f2/spikes/harness/allocid.sh"
if cmp -s "$SRC" "$WORK/f2/spikes/harness/allocid.sh"; then
  echo "  BAD  falsifier 2's edit matched NOTHING"
  fail=1
else
  got=$(KF_IDS="$WORK/f2/.ids" sh "$WORK/f2/spikes/harness/allocid.sh" Z 2>&1)
  if [ "$got" = "Z8" ]; then
    echo "  OK   falsifier 2: without the tracked-document scan it answers Z8,"
    echo "       which analysis/NOTES.md claims -- the second source is load-bearing"
  else
    echo "  BAD  falsifier 2: expected Z8, got '$got'"
    fail=1
  fi
fi

# --- falsifier 3: restore the .seeded guard -----------------------------------
# The guard froze the pool against whatever sources existed at first run. Driven
# the way it actually bit: allocate once, THEN add a spike directory, and a
# guarded allocator never sees it.
build_tree "$WORK/f3"
python3 - "$SRC" "$WORK/f3/spikes/harness/allocid.sh" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
anchor = '  seed_from_tree "$p" | sort -u | while read -r i; do : > "$IDS/$i" 2>/dev/null; done'
guarded = ('  if [ ! -f "$IDS/.seeded.$p" ]; then\n'
           '    seed_from_tree "$p" | sort -u | while read -r i; do : > "$IDS/$i" 2>/dev/null; done\n'
           '    : > "$IDS/.seeded.$p"\n'
           '  fi')
if anchor not in s:
    sys.exit('ANCHOR-MISSING')
open(dst, 'w').write(s.replace(anchor, guarded))
PY
if [ $? -ne 0 ] || cmp -s "$SRC" "$WORK/f3/spikes/harness/allocid.sh"; then
  echo "  BAD  falsifier 3's edit matched NOTHING -- anchor absent"
  fail=1
else
  first=$(KF_IDS="$WORK/f3/.ids" sh "$WORK/f3/spikes/harness/allocid.sh" Z 2>&1)
  mkdir -p "$WORK/f3/spikes/Z10_added_after_first_run"
  second=$(KF_IDS="$WORK/f3/.ids" sh "$WORK/f3/spikes/harness/allocid.sh" Z 2>&1)
  if [ "$second" = "Z10" ]; then
    echo "  OK   falsifier 3: with the guard restored, a directory created after"
    echo "       the first allocation is invisible and Z10 is handed out ($first then $second)"
  else
    echo "  BAD  falsifier 3: expected Z10 from the guarded copy, got '$second'"
    fail=1
  fi
  # and the LIVE source must not do that.
  build_tree "$WORK/f3b"
  cp "$SRC" "$WORK/f3b/spikes/harness/allocid.sh"
  KF_IDS="$WORK/f3b/.ids" sh "$WORK/f3b/spikes/harness/allocid.sh" Z >/dev/null 2>&1
  mkdir -p "$WORK/f3b/spikes/Z10_added_after_first_run"
  live2=$(KF_IDS="$WORK/f3b/.ids" sh "$WORK/f3b/spikes/harness/allocid.sh" Z 2>&1)
  if [ "$live2" = "Z10" ]; then
    echo "  BAD  the LIVE source also answered Z10 -- re-seeding is not happening"
    fail=1
  else
    echo "  OK   live source re-seeds and skips Z10 (answered $live2)"
  fi
fi

# --- falsifier 4: the refusal path, and the FIRST draft of this check was wrong
# H30: a missing input must refuse, not allocate from a partial namespace.
#
# The first version ran the LIVE script with cwd set to an empty directory and
# expected exit 3. It got Z2, because `allocid.sh` opens with
# `cd "$(dirname "$0")/../.."` — it resolves its root from its OWN PATH and
# ignores the caller's cwd entirely. So the test was measuring the real repo,
# which of course has `spikes/`. **A refusal test must relocate the SCRIPT, not
# the caller.** Both halves are driven separately below, because they refuse for
# different reasons and a single "it exited 3" cannot tell which fired.
mkdir -p "$WORK/nospikes/a/b"
cp "$SRC" "$WORK/nospikes/a/b/allocid.sh"
out=$( KF_IDS="$WORK/nospikes/.ids" sh "$WORK/nospikes/a/b/allocid.sh" Z 2>&1 ); rc=$?
if [ "$rc" = 3 ] && echo "$out" | grep -q 'no spikes/'; then
  echo "  OK   refusal 4a: a tree with no spikes/ exits 3 rather than allocating"
else
  echo "  BAD  refusal 4a: rc=$rc, output '$out'"
  fail=1
fi

mkdir -p "$WORK/nogit/spikes/harness"
cp "$SRC" "$WORK/nogit/spikes/harness/allocid.sh"
out=$( KF_IDS="$WORK/nogit/.ids" sh "$WORK/nogit/spikes/harness/allocid.sh" Z 2>&1 ); rc=$?
if [ "$rc" = 3 ] && echo "$out" | grep -q 'git ls-files'; then
  echo "  OK   refusal 4b: spikes/ present but no git repo exits 3 -- the"
  echo "       document half of the namespace is unreadable, so it refuses"
else
  echo "  BAD  refusal 4b: rc=$rc, output '$out'"
  fail=1
fi

[ "$fail" = 0 ] && echo "test_h57_falsify: every part of the v2 change is load-bearing"
exit "$fail"
