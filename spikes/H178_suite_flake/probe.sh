#!/usr/bin/env bash
# H178 -- ok-1, 2026-08-19. A red run of test_loop_gate.sh had two meanings.
#
# Most of that suite runs in its own $T. A minority reads the SHARED WORKING TREE
# -- installed gates vs their sources, and every tracked settings.json -- and four
# other lanes edit those files as their normal mid-cycle state. Both printed the
# same sentence: "the loop contract is not enforceable as written".
#
# THE CORRECTION THIS ROW CARRIES: I recorded two sightings (cycle 15 `2 FAILED,
# 85 passed`, cycle 18 `4 FAILED, 87 passed`) as "naming no check". FALSE, and it
# was my instrument: `bad()` always prints `FAIL <name>` and I had piped the run
# through `tail -4`. The names existed and I discarded them.
#
# ALSO MEASURED HERE: the suite's TOTAL is data-dependent -- the settings.json
# block iterates over tracked files and their commands -- so a changed total is
# not the same event as a failure. 85+2=87 and 87+4=91 are different totals.
#
# The arms drive THE REAL SUITE through its KF_TEST_HOOKDIR seam, not a copy
# (H117 FA1: the tested path must be the executed path).
#
# usage: bash spikes/H178_suite_flake/probe.sh
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPIKE="$PWD"; ROOT="$(cd ../.. && pwd)"
SB="$SPIKE/sandbox"
fail=0
ctl() { [ "$2" = PASS ] || fail=1; printf '  %-4s %-4s %s\n' "$1" "$2" "$3"; }
trap 'rm -rf "$SB"' EXIT

# ---- C1 the suite is green on this tree right now, or the arms below are
#      measuring somebody's live edit instead of the seam.
OUT=$(bash "$ROOT/spikes/harness/test_loop_gate.sh" 2>&1)
printf '%s' "$OUT" | tail -1 | grep -q 'checks pass' \
  && ctl C1 PASS "baseline: $(printf '%s' "$OUT" | tail -1)" \
  || ctl C1 FAIL "baseline is already red: $(printf '%s' "$OUT" | tail -1)"

# ---- A1 all-live-tree failures are NAMED AS SUCH in the summary.
rm -rf "$SB"; mkdir -p "$SB/hooks"          # an empty hook dir: gates NOT INSTALLED
OUT=$(KF_TEST_HOOKDIR="$SB/hooks" bash "$ROOT/spikes/harness/test_loop_gate.sh" 2>&1)
TAIL=$(printf '%s' "$OUT" | tail -4)
# CORRECTED 2026-08-19, probe.sh v2, BY THIS ARM FAILING ON A LIVE FLEET. v1
# accepted only the ALL branch, and the closing note below called the MIXED
# branch unreachable because "reaching it needs a real contract check to fail,
# which this probe will not fake". It did not have to fake one: H178's own flake
# fired inside this arm and the run read `4 FAILED, 82 passed -- 3 of the
# failures are LIVE-TREE observations, 1 are contract checks`. That sentence
# NAMES THE CAUSE, which is all A1 is about, so v1 was refusing its own subject.
# A1's question is diagnosability; the count of concurrent contract failures is a
# different question and is reported below rather than folded into this verdict.
case "$TAIL" in
  *"LIVE-TREE observations"*)
     ctl A1 PASS "a red run from tree state says so: $(printf '%s' "$OUT" | grep -m1 'FAILED')" ;;
  *) ctl A1 FAIL "summary did not name the cause: $(printf '%s' "$OUT" | grep -m1 'FAILED')" ;;
esac
# THE CAPTURE THIS ROW'S OWN C1 DEMANDED: keep FULL output when a contract check
# failed alongside. Discarding the names is the exact defect H178 corrects itself
# for -- two sightings recorded as "naming no check" because they were piped
# through `tail -4`. Not an arm: an observation, written where it cannot be lost.
if printf '%s' "$TAIL" | grep -q 'are contract checks'; then
  printf '%s\n' "$OUT" > "$SPIKE/mixed_run.txt"
  printf '  obs  MIXED branch reached LIVE, contract check(s) failed concurrently: %s\n' \
    "$(printf '%s\n' "$OUT" | grep '^  FAIL' | grep -v 'NOT INSTALLED' | tr '\n' ';')"
  printf '       full output kept at spikes/H178_suite_flake/mixed_run.txt\n'
fi

# ---- A2 it still FAILS. The point is diagnosability, not leniency (H36's checks
#      are the ones that matter, and never weakening a gate to pass it is a rail).
KF_TEST_HOOKDIR="$SB/hooks" bash "$ROOT/spikes/harness/test_loop_gate.sh" >/dev/null 2>&1
rc=$?
[ "$rc" != 0 ] && ctl A2 PASS "the suite still exits non-zero (rc=$rc) -- labelled, not excused" \
               || ctl A2 FAIL "the suite passed with its gates missing -- this weakened a gate"

# ---- A3 the failures really are the drift/parse ones, by name.
n=$(printf '%s' "$OUT" | grep -c 'NOT INSTALLED')
[ "$n" -ge 1 ] && ctl A3 PASS "$n gate(s) named individually, so a reader sees WHICH" \
               || ctl A3 FAIL "no gate named in the output"

# ---- C2 the seam is OFF by default: the baseline run above used the real hooks.
grep -q 'KF_TEST_HOOKDIR:-\$hookdir' "$ROOT/spikes/harness/test_loop_gate.sh" \
  && ctl C2 PASS "the seam defaults to the computed hookdir (unset in every real run)" \
  || ctl C2 FAIL "the seam is not defaulted -- a real run may not read .git/hooks"

# ---- THE SECOND SUBJECT OF THIS ROW, and the one the captured red run named.
#      probe.sh v2 (H178). The arms above are about LABELLING a red run. These are
#      about a control that stayed GREEN through one. failing_run_4.txt reads
#        FAIL  H61: ... refused BY THE PARENT (want '1', got '2')
#        PASS    every launcher is accounted for
#      seven lines apart, on one fixture. The observed triple was surv=0 parent=2
#      child=0; the intended one is 1/1/0; the accounting control sums them.
#
#      THE EXPRESSION IS EXTRACTED FROM THE SUITE, NEVER RETYPED. A copy of the
#      arithmetic would pass while the real line said something else -- H117 FA1,
#      the tested path must be the executed path.
SUITE="$ROOT/spikes/harness/test_loop_gate.sh"
EXPR=$(grep -o '\$(( h61_surv[^)]*))' "$SUITE" | head -1)

# ---- C3 the extraction found something. An empty EXPR would make A4/A5 vacuous
#      and both would report PASS -- H88's class, absence reading as agreement.
[ -n "$EXPR" ] && ctl C3 PASS "accounting expression read from the suite: $EXPR" \
                || ctl C3 FAIL "no accounting expression found -- A4/A5 below are vacuous"

evalsum() { h61_surv=$1 h61_parent=$2 h61_child=$3; eval "echo \"$EXPR\""; }

# ---- A4 the defect, replayed on the OBSERVED triple: 0 admitted, 2 refused, and
#      the sum is still the passing value. This is the run that happened.
got=$(evalsum 0 2 0)
[ "$got" = 2 ] && ctl A4 PASS "observed 0/2/0 -> sum $got: the control cannot see a fixture where NO lane started" \
               || ctl A4 FAIL "observed 0/2/0 -> sum $got, so the sum is not blind and this row's premise is wrong"

# ---- A5 two-sided: the INTENDED triple gives the same number, so the control
#      does not distinguish the states it is named for. One value, two meanings.
got2=$(evalsum 1 1 0)
[ "$got2" = "$got" ] && ctl A5 PASS "intended 1/1/0 -> sum $got2, identical: one verdict over two states" \
                     || ctl A5 FAIL "intended 1/1/0 -> $got2 vs observed $got -- they differ, premise wrong"

# ---- A6 the repair: h61_surv is now pinned by a check of its own, so the red run
#      above is REFUSED rather than absorbed. Text on the executed file, and said
#      as such: this asserts the assertion EXISTS, not that the race reproduces.
n=$(grep -c '^      "\$h61_surv" "1"' "$SUITE")
[ "$n" = 1 ] && ctl A6 PASS "h61_surv is asserted on its own (1 site); 0 admitted now FAILS" \
             || ctl A6 FAIL "h61_surv appears in no standalone check ($n sites) -- still sum-only"

# ---- C4 that new assertion CAN fail, and the input that makes it fail is READ
#      from the suite rather than asserted here: its expected value must differ
#      from the observed one. `[ 0 != 1 ]` written literally would be a control
#      that cannot fail, which is the family this whole row is about.
want=$(grep -A1 'and exactly one launcher reached the turn' "$SUITE" | tail -1 | grep -o '"[0-9]*"$' | tr -d '"')
[ -n "$want" ] && [ "$want" != "0" ] \
  && ctl C4 PASS "the added check wants '$want' and the red run measured '0' -- it fires on that run" \
  || ctl C4 FAIL "expected value unreadable or equal to the observed 0 (got '${want:-}')"

# ---- A8 THE SUMMARY'S TOTALS EQUAL THE LINES PRINTED. This is the mechanical
#      detector for "a check that cannot report its verdict": any block whose
#      ok/badt run inside a SUBSHELL still PRINTS its lines while the parent's
#      counters never move. H191's first fix was `printf ... | while read`, which
#      is exactly that, and this arm is what would have caught it. General over
#      the whole suite, not specific to that block.
B=$(bash "$SUITE" 2>&1)
lp=$(printf '%s\n' "$B" | grep -c '^  PASS ')
lf=$(printf '%s\n' "$B" | grep -c '^  FAIL ')
sum=$(printf '%s\n' "$B" | grep -E 'checks pass|FAILED,' | tail -1)
case "$sum" in
  *"checks pass") sp=$(printf '%s' "$sum" | sed 's/.*: *\([0-9]*\) checks pass/\1/'); sf=0 ;;
  *) sf=$(printf '%s' "$sum" | sed 's/.*: *\([0-9]*\) FAILED.*/\1/')
     sp=$(printf '%s' "$sum" | sed 's/.*FAILED, *\([0-9]*\) passed.*/\1/') ;;
esac
[ "$lp" = "$sp" ] && [ "$lf" = "$sf" ] \
  && ctl A8 PASS "totals match the lines: $sp pass / $sf fail printed and counted" \
  || ctl A8 FAIL "counters lost: printed $lp pass / $lf fail, summary says $sp / $sf -- a block is incrementing in a subshell"

# ---- A9 H191: ONE VERDICT PER REGISTERED COMMAND, not per whitespace token.
#      `for c in $cmds` split a command line with arguments into three, so the
#      single correct registration `python3 .../scratchcheck.py --hook` produced
#      three failures naming `python3` as missing. Counted against the source of
#      truth -- the "command" entries in the tracked settings.json files.
regs=$(printf '%s\n' "$B" | grep -c '^  \(PASS\|FAIL\)  reg ')
want=$(cd "$ROOT" && git ls-files '*.claude/settings.json' | while IFS= read -r f; do
         grep -o '"command"[[:space:]]*:' "$f"; done | grep -c .)
[ "$regs" = "$want" ] && [ "$want" -gt 0 ] \
  && ctl A9 PASS "$regs registration verdict(s) for $want registered command(s) -- no whitespace split" \
  || ctl A9 FAIL "$regs verdicts for $want commands (want equal, both non-zero)"

# ---- A7 the reclassification holds. Every verdict derived from the INSTALLED
#      hook copy is a live-tree observation, so an all-tree run must not report a
#      contract failure. Asserted on the run A1 already made, not a fresh one.
if printf '%s' "$TAIL" | grep -q 'are contract checks'; then
  ctl A7 FAIL "an all-live-tree run still reports contract failures: $(printf '%s' "$TAIL" | grep -m1 FAILED)"
else
  ctl A7 PASS "empty hookdir -> ALL failures classed live-tree: $(printf '%s' "$OUT" | grep -m1 FAILED)"
fi

echo
echo "  WITHDRAWN in v2, and then the withdrawal was itself corrected. v1 said the"
echo "  MIXED branch had no arm because reaching it 'needs a real contract check to"
echo "  fail, which this probe will not fake'. It DID appear -- and my first reading,"
echo "  that the H61 flake had fired inside the probe, WAS WRONG. The lone"
echo "  'contract' failure was 'no installed pre-commit to read a CHECKS list from',"
echo "  which A1's own empty hookdir CAUSES, deterministically. It was labelled a"
echo "  contract failure only because badt covered the drift checks and not the four"
echo "  siblings reading the same installed hook. That is the wrong-attribution error"
echo "  the tri-branch exists to prevent, produced by the tri-branch, and the fix is"
echo "  in test_loop_gate.sh v4: badt iff the INPUT is the shared tree."
echo "  STILL NOT EXERCISED: the H61 race is not reproduced on demand. A6 asserts"
echo "  the new assertion EXISTS; only a red run shows it firing. That is H189."
[ "$fail" = 0 ] && echo "H178 probe: all arms as stated" || echo "H178 probe: FAILED"
exit "$fail"
