#!/usr/bin/env bash
# allocid.sh v1 — H43. Atomic id allocation, because grepping is a race.
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
# decides it once. `.ids/` is tracked, so the allocation survives a lane that
# never publishes — which is exactly the window the two collisions fell into.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

IDS="${KF_IDS:-.ids}"

seed_from_tree() {
  # Every id already spoken for, from every place one can be spoken for. This
  # runs ONCE per prefix to bootstrap; after that `.ids/` is authoritative and
  # no grep is on the allocation path. Reading the append-only logs here is
  # correct and is not the H28 mistake: H28 forbids resolving a STATUS against
  # a log, and this resolves EXISTENCE, which a log can only ever under-report
  # in the safe direction.
  grep -ohE "\b$1[0-9]+\b" WORK_QUEUE.md CHANNEL.md livechat.log 2>/dev/null \
    | sort -u
}

alloc() {
  p="$1"
  mkdir -p "$IDS"
  if [ ! -f "$IDS/.seeded.$p" ]; then
    seed_from_tree "$p" | while read -r i; do : > "$IDS/$i" 2>/dev/null; done
    : > "$IDS/.seeded.$p"
  fi
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
