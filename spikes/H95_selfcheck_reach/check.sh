#!/bin/sh
# H95 · check.sh v1 — the harness selfcheck block must be REACHED, and every
# assertion here is made BY EXECUTION rather than by text position.
#
# WHY THIS FILE EXISTS AND WHY IT DOES NOT LOOK LIKE H78's check.sh.
# H78 wired the block in and asserted its two liveness properties POSITIONALLY:
# "the call site is below the launch loop" and "no `exit [1-9]` appears textually
# after the call site". Both were TRUE of the shipped file and neither was the
# property they name. The file had five `exit` statements ABOVE the block, two of
# them carrying all the traffic (`--check` at the census, and the full-quorum
# steady state), so the block was unreachable on every path the fleet actually
# takes and the check stayed green for eleven hours across 26 logged runs.
#
# CLASS: A CONTROL-FLOW PROPERTY ASSERTED BY TEXT POSITION INSTEAD OF BY
# EXECUTION. The repair is `trap harness_selfchecks EXIT`, which is reached from
# every termination path including ones not yet written -- and the positional
# proxies then INVERT: the function is now DEFINED near the top of the file, so
# H78's P2 reads "above the launch loop" and its P3 sees `--check`'s legitimate
# `exit 1` below the call site. A proxy that is anti-correlated with its property
# is worse than no proxy, so P2/P3's PROPERTIES ARE KEPT and re-asserted here as
# A9 (output ORDER on the launching arm) and A6 (observed exit codes). Nothing is
# dropped; two proxies are replaced by two observations.
#
# NOTHING IS LAUNCHED. Every arm runs a byte-identical COPY of bringup.sh inside
# this spike directory (mkfixture.sh), whose down-arm roster names a briefless
# callsign that bringup.sh SKIPs before the `run_loop.sh` line -- and A7 asserts
# that rather than assuming it. Fixtures live under the workspace (§10).
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
FAIL=0
MARK='=== HARNESS SELFCHECKS ==='

ck() { # ck <label> <expected rc> <actual rc>
  if [ "$2" -eq "$3" ]; then echo "  ok    $1"
  else echo "  FAIL  $1 (expected rc=$2, got rc=$3)"; FAIL=$((FAIL + 1)); fi
}

sh "$HERE/mkfixture.sh" up   >/dev/null || { echo "  FAIL  fixture up";   exit 9; }
sh "$HERE/mkfixture.sh" down >/dev/null || { echo "  FAIL  fixture down"; exit 9; }
UP="$HERE/fixture_up"; DOWN="$HERE/fixture_down"

# A1 — the subject is the shipped file. A fixture running a modified copy would
# prove nothing about what launchd executes every 600s.
cmp -s "$ROOT/bringup.sh" "$UP/bringup.sh"
ck "fixture runs a BYTE-IDENTICAL copy of the shipped bringup.sh" 0 $?

# Three arms, three termination paths. Arm names are the exits they reach:
#   up    -> `bringup: full quorum, nothing to start.`   (the steady state)
#   check -> the census exit                             (the path humans run)
#   down  -> the launch loop, then end of script          (v4's only live path)
( cd "$UP"   && ./bringup.sh          ) >"$HERE/a_up.out"    2>&1; RC_UP=$?
( cd "$UP"   && ./bringup.sh --check  ) >"$HERE/a_check.out" 2>&1; RC_CHECK=$?
( cd "$DOWN" && ./bringup.sh          ) >"$HERE/a_down.out"  2>&1; RC_DOWN=$?

for arm in up check down; do
  grep -qF "$MARK" "$HERE/a_$arm.out"
  ck "A2/3/4 the block is REACHED on the '$arm' arm" 0 $?
done

# A5 — once only. A trap is not automatically once-only: a subshell that inherits
# it would print a second section, and two sweeps per reconcile is a real cost on
# a 600s cadence.
for arm in up check down; do
  n=$(grep -cF "$MARK" "$HERE/a_$arm.out")
  [ "$n" -eq 1 ]
  ck "A5 exactly ONE sweep on the '$arm' arm (saw $n)" 0 $?
done

# A6 — the handler must not eat `$?`, and this is a CONTROLLED PAIR rather than
# an absolute expectation. The first version of this check asserted `--check`
# exits 0 under quorum, which is what bringup.sh:45 documents; the fixture
# returned 1 on BOTH arms, and the control below is what showed the 1 predates
# the trap entirely (the fixture lane carries no brief). Asserting the absolute
# value would have published a pre-existing exit code as this row's regression.
# `$PRE` is the last commit touching bringup.sh before the trap, pinned so the
# control stays the PRE-FIX file after this row is committed.
PRE=64af5af39d81280665c1ac470d10da2d120b2a77
( cd "$ROOT" && git show "$PRE:bringup.sh" ) > "$UP/pre.sh" 2>/dev/null
cp "$UP/pre.sh" "$DOWN/pre.sh"; chmod +x "$UP/pre.sh" "$DOWN/pre.sh"
grep -q '^trap harness_selfchecks EXIT$' "$UP/pre.sh"
ck "A6 the pinned control PREDATES the trap (else it is not a control)" 1 $?
for arm in up down; do
  d="$HERE/fixture_$arm"
  for flag in '' '--check'; do
    ( cd "$d" && ./bringup.sh $flag ) >/dev/null 2>&1; rc_new=$?
    ( cd "$d" && ./pre.sh     $flag ) >/dev/null 2>&1; rc_old=$?
    [ "$rc_new" -eq "$rc_old" ]
    ck "A6 exit code UNCHANGED by the trap: arm=$arm flag='${flag:-none}' ($rc_old -> $rc_new)" 0 $?
  done
done

# A7 — safety, asserted rather than assumed: the down arm reaches the launch loop
# and must still start nothing, because its lane carries no brief.
grep -qE '^\s*launched ' "$HERE/a_down.out"
ck "A7 the down arm LAUNCHES NOTHING (no 'launched' line)" 1 $?

# A9 — v4's preregistered F3, preserved and now observed: the sweep must not be
# able to delay a lane launch. Not "the call site is below the loop" (it is not,
# any more) but "the output arrives after the launch loop's output", which is the
# execution ordering that F3 was a proxy for.
launch_ln=$(grep -nF 're-check with: ./bringup.sh --check' "$HERE/a_down.out" | head -1 | cut -d: -f1)
mark_ln=$(grep -nF "$MARK" "$HERE/a_down.out" | head -1 | cut -d: -f1)
[ -n "$launch_ln" ] && [ -n "$mark_ln" ] && [ "$mark_ln" -gt "$launch_ln" ]
ck "A9 the sweep runs AFTER the launch loop (line $mark_ln > $launch_ln), delaying no launch" 0 $?

# A8 — NEGATIVE CONTROL, and the reason to trust A2-A4. Remove the trap line and
# nothing else; the steady-state arm must go SILENT. Without this, A2-A4 pass on
# any file that prints the marker for some other reason, which is the shape of
# the defect this row is about.
NEG="$HERE/fixture_neg"
rm -rf "$NEG"; cp -R "$UP" "$NEG"
grep -v '^trap harness_selfchecks EXIT$' "$UP/bringup.sh" > "$NEG/bringup.sh"
chmod +x "$NEG/bringup.sh"
cmp -s "$UP/bringup.sh" "$NEG/bringup.sh"
ck "A8 the negative control DIFFERS from the subject (the sed found its anchor)" 1 $?
( cd "$NEG" && ./bringup.sh ) >"$HERE/a_neg.out" 2>&1
grep -qF "$MARK" "$HERE/a_neg.out"
ck "A8 with the trap removed the block is UNREACHABLE again (check can go RED)" 1 $?

rm -rf "$NEG" "$UP" "$DOWN"
rm -f "$HERE"/a_*.out          # regenerable; the committed evidence is o*/t* and RESULT.md
echo
if [ "$FAIL" -eq 0 ]; then
  echo "H95 check: 17 assertions, 0 FAILED — every exit path sweeps, exactly once,"
  echo "           exit codes intact, and the check goes red without the trap."
else
  echo "H95 check: $FAIL FAILED"
fi
exit "$FAIL"
