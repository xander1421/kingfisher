#!/usr/bin/env bash
# allocid.sh v2 — H57. Atomic id allocation, because grepping is a race.
#
# v2, 2026-08-17 (AGENT-1, H57). DEFECT REMOVED, and it is the one this file
# exists to prevent: **v1 HANDED OUT IDS THAT WERE ALREADY IN USE.**
# CLASS: *a namespace allocator whose bootstrap reads FEWER SOURCES than the
# namespace lives in.* v1 seeded the free list from `WORK_QUEUE.md`,
# `CHANNEL.md` and `livechat.log` and never looked at `spikes/` — and for the
# S/G/W/M/Q/B/N/V prefixes a number is claimed by CREATING THE DIRECTORY
# (MISSION_LOOP §13.3), so the filesystem IS the namespace. Measured before the
# repair, on 2026-08-17:
#
#   * 20 live spike directories occupied ids absent from the free list
#     (S85, G4/G6/G7/G9/G10/G12/G13/G14, W1/W2/W4/W5, M1, M2, Q1, B1, B2, N1, V1);
#   * on a fresh `.ids`, 2 of 11 prefixes COLLIDED ON THE FIRST ANSWER —
#     `allocid.sh G` returned G3 against `spikes/G3_claim_graph`, and
#     `allocid.sh V` returned V1 against `spikes/V1_feature_fuel`.
#
# v1's header argues that "adding more files to the grep cannot fix it". That is
# TRUE OF THE ALLOCATION PATH — the race is time-of-check to time-of-use — and it
# was carried over to the BOOTSTRAP, where it is false: the bootstrap races
# nothing, it establishes what is already taken, and its source set is a plain
# correctness question. A correct answer about the wrong half of the mechanism.
#
# Three changes, each with an observable consequence:
#   1. the seed reads `spikes/` (the filesystem) and every TRACKED `*.md`/`*.log`,
#      not three files;
#   2. the seed runs on EVERY invocation. The `.seeded.$p` guard meant a source
#      added later was never read, and a fresh clone bootstrapped from whatever
#      the guard was written against. Cost measured: 0.03 s;
#   3. a missing input REFUSES instead of degrading to a narrow pool (H30) —
#      no `spikes/`, or `git ls-files` returning nothing, exits 3.
#
# `git grep -E` is NOT used for the scan: **git's -E has no `\b`**, so
# `git grep -ohE '\bS[0-9]+\b'` returns ZERO matches here while the same pattern
# under plain `grep` returns 71. Same shape as the BSD-`sed` `\b` rename that
# matched nothing and exited 0 (HANDOFF C28). Cites: man:git-grep "-E" (POSIX
# extended regular expressions); measured 0 vs 71 on this tree.
#
# THE DEFECT REMOVED
# ------------------
# Five id collisions happened in this repo on 2026-08-17. H18 mechanised
# uniqueness in `refcheck.py` check 5 — and check 5 reads the WORK_QUEUE TABLE,
# which is where an id lands AFTER the work is done. Allocation happens in
# `CHANNEL.md` minutes earlier, and nothing there is atomic.
#
# MEASURED, not argued:
#   grep -oE '^CLAIM H[0-9]+ [A-Za-z0-9-]+' CHANNEL.md | awk '{print $2}' \
#     | sort | uniq -d      ->   H20 H30 H38
# Two of those three are genuine concurrent collisions (H30: AGENT-1 vs
# ATTACKER-1, renumbered to H35; H38: ok-1 vs ATTACKER-1, renumbered to H40).
#
# AND BOTH LANES RAN A CORRECT GREP. ATTACKER-1's H38 claim line names its
# method and mine names a wider one — CHANNEL + WORK_QUEUE + livechat — and we
# still collided, because the two reads were about two minutes apart and neither
# row had been published at the other's read time. **It is time-of-check to
# time-of-use, not a scope error, so adding more files to the grep cannot fix
# it.** Every previous answer to this class has been "grep more carefully".
#
# THE PRIMITIVE is the one AGENT-2 already used for the H8 launcher lock:
# `set -o noclobber` makes `> file` CREATE-OR-FAIL in one syscall, so of N
# racing shells exactly one wins. Same trick, different namespace.
#
# USAGE
#   id=$(sh spikes/harness/allocid.sh H)     # -> H43, and .ids/H43 now exists
#   sh spikes/harness/allocid.sh --selfcheck # concurrent allocations are distinct
#
# The claim line still goes in CHANNEL.md; this only decides WHICH id, and it
# decides it once. **COMMIT `.ids/` WITH YOUR CLAIM.** v1's header said the
# allocation survives a lane that never publishes "because `.ids/` is tracked";
# measured 2026-08-17, 49 of 152 id files were tracked and 103 were not — every
# `S*`, every `G*` and `H48`–`H57` existed in one lane's working tree only. The
# directory is tracked; an allocation is not, until someone commits it, and an
# uncommitted allocation is invisible to every other clone.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

IDS="${KF_IDS:-.ids}"

seed_from_tree() {
  # Every id already spoken for, from every place one can be spoken for.
  # Reading the append-only logs here is not the H28 mistake: H28 forbids
  # resolving a STATUS against a log, and this resolves EXISTENCE, which a log
  # can only ever under-report in the safe direction. The three sources below
  # are ORed and de-duplicated; each one alone under-reports.
  p="$1"
  # (1) THE FILESYSTEM. `spikes/S85_verify_vs_reexec` claims S85 whether or not
  #     any document says so, and v1 could not see it (§13.3).
  ls spikes 2>/dev/null | grep -oE "^$p[0-9]+"
  # (2) every tracked .md/.log — 71 S-ids against the three logs' 37.
  git ls-files -z -- '*.md' '*.log' 2>/dev/null \
    | xargs -0 grep -ohE "\b$p[0-9]+\b" 2>/dev/null
  # (3) the three shared logs even when a lane has not committed them yet.
  grep -ohE "\b$p[0-9]+\b" WORK_QUEUE.md CHANNEL.md livechat.log 2>/dev/null
}

refuse_if_input_missing() {
  # H30: a missing INPUT must not silently degrade a mechanism to a narrower
  # one that still reports success. Here the degraded form allocates a USED id,
  # so it refuses. Fail-closed on the sources, because the alternative failure
  # is the collision this file exists to end.
  [ -d spikes ] || {
    echo "allocid: no spikes/ directory under $(pwd) -- refusing to allocate" \
         "from a partial namespace (H57)" >&2; exit 3; }
  git ls-files >/dev/null 2>&1 || {
    echo "allocid: \`git ls-files\` failed under $(pwd) -- refusing to allocate" \
         "from a partial namespace (H57)" >&2; exit 3; }
}

alloc() {
  p="$1"
  refuse_if_input_missing
  mkdir -p "$IDS"
  # Seeded on EVERY invocation, not once: the `.seeded.$p` guard froze the free
  # list against whatever sources existed the first time, which is how a live
  # `spikes/` directory stayed invisible after the scan was widened. Seeding
  # only ever REMOVES ids from the pool, so it cannot race the allocation below.
  seed_from_tree "$p" | sort -u | while read -r i; do : > "$IDS/$i" 2>/dev/null; done
  n=1
  # noclobber is the whole mechanism. `set -C` then `> f` fails if f exists, and
  # the test-and-create is one open(2) with O_EXCL -- not a `[ -f ]` followed by
  # a write, which is the same read-modify-write shape H13 measured losing 35%
  # of its increments.
  while [ "$n" -lt 10000 ]; do
    if ( set -C; : > "$IDS/$p$n" ) 2>/dev/null; then
      printf '%s%s\n' "$p" "$n"
      return 0
    fi
    n=$((n + 1))
  done
  echo "allocid: no free id under prefix $p below 10000" >&2
  return 1
}

selfcheck() {
  # THE ASSERTION THAT MATTERS IS CONCURRENCY, and it is the assertion the
  # existing uniqueness check does not make: check 5 compares rows that already
  # exist. Twenty shells allocate at once and must receive twenty DISTINCT ids.
  # A sequential test passes on the broken version too -- that is exactly how
  # test_loop_gate.sh's 15-check suite passed over a live defect.
  t="$(mktemp -d)"
  trap 'rm -rf "$t"' RETURN 2>/dev/null || true
  ( KF_IDS="$t/ids" ; export KF_IDS
    : > "$t/out"
    for _ in $(seq 1 20); do
      ( KF_IDS="$t/ids" sh "$0" Z >> "$t/out" ) &
    done
    wait )
  got=$(wc -l < "$t/out" | tr -d ' ')
  uniq_n=$(sort -u "$t/out" | wc -l | tr -d ' ')
  fail=0
  if [ "$got" = 20 ]; then echo "  OK   20 concurrent allocations returned 20 ids"
  else echo "  BAD  20 concurrent allocations returned $got ids"; fail=1; fi
  if [ "$uniq_n" = "$got" ]; then echo "  OK   every id distinct ($uniq_n/$got)"
  else echo "  BAD  ids collided: $uniq_n distinct of $got"; fail=1; fi
  # NEGATIVE CONTROL: the grep-then-write method this replaces, driven the same
  # way, must LOSE ids -- otherwise the concurrency above proves nothing about
  # the defect and only that this machine is slow enough to serialise anyway.
  : > "$t/racy"
  mkdir -p "$t/racy_ids"
  for _ in $(seq 1 20); do
    ( n=$(ls "$t/racy_ids" 2>/dev/null | wc -l | tr -d ' ')
      n=$((n + 1)); : > "$t/racy_ids/Z$n"; echo "Z$n" >> "$t/racy" ) &
  done
  wait
  # THE ID THAT EXISTS ONLY ON DISK (H57). A spike number is claimed by CREATING
  # THE DIRECTORY (§13.3), so an allocator that reads only documents cannot see
  # it. Fixture: a scratch repo whose logs name Z1..Z6 and whose `spikes/` holds
  # `Z7_on_disk_only`. A correct allocator must not answer Z7.
  r="$t/fixture"
  mkdir -p "$r/spikes/harness" "$r/spikes/Z7_on_disk_only"
  cp "$0" "$r/spikes/harness/allocid.sh"
  for i in 1 2 3 4 5 6; do echo "Z$i"; done > "$r/WORK_QUEUE.md"
  : > "$r/CHANNEL.md"; : > "$r/livechat.log"
  ( cd "$r" && git init -q . >/dev/null 2>&1 && git add -A >/dev/null 2>&1 )
  fx=$(KF_IDS="$r/.ids" sh "$r/spikes/harness/allocid.sh" Z 2>&1)
  if [ "$fx" = "Z7" ]; then
    echo "  BAD  allocated Z7, and spikes/Z7_on_disk_only holds it -- the"
    echo "       filesystem is not on the seed path"
    fail=1
  else
    echo "  OK   an id held only by a spikes/ directory is not allocated (got $fx)"
  fi
  # NEGATIVE CONTROL for that fixture: the v1 seed -- three documents, no
  # filesystem -- driven over the same tree must ANSWER Z7, or the fixture
  # cannot tell a fixed allocator from a broken one and the OK above is empty.
  v1n=1
  while [ "$v1n" -lt 100 ]; do
    grep -qE "\bZ$v1n\b" "$r/WORK_QUEUE.md" "$r/CHANNEL.md" "$r/livechat.log" \
      2>/dev/null || break
    v1n=$((v1n + 1))
  done
  if [ "Z$v1n" = "Z7" ]; then
    echo "  OK   negative control: the v1 three-document seed answers Z7 here"
  else
    echo "  BAD  negative control: v1's seed answered Z$v1n, not Z7 -- the fixture"
    echo "       does not reproduce the defect, so the check above proves nothing"
    fail=1
  fi
  r_uniq=$(sort -u "$t/racy" | wc -l | tr -d ' ')
  if [ "$r_uniq" -lt 20 ]; then
    echo "  OK   negative control: grep-then-write collided ($r_uniq distinct of 20)"
  else
    echo "  BAD  negative control did NOT collide -- this box serialises, so the"
    echo "       positive result above is not evidence that noclobber is why"
    fail=1
  fi
  rm -rf "$t"
  [ "$fail" = 0 ] && echo "selfcheck: allocation is atomic; the method it replaces is not"
  return "$fail"
}

case "${1:-}" in
  --selfcheck) selfcheck ;;
  '') echo "usage: allocid.sh <PREFIX>|--selfcheck   e.g. allocid.sh H" >&2; exit 2 ;;
  *) alloc "$1" ;;
esac
