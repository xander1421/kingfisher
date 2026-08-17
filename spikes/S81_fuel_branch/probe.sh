#!/bin/sh
# S81 — does `fuel_used` stay constant when CONTROL FLOW branches on a
# nondeterministic value?  ATTACKER-1, 2026-08-17.
#
# THE FALSIFIER WAS WRITTEN IN out/LEDGER.md AND MARKED NOT YET RUN. The row
# reads:
#
#   ~~Fuel is deterministic even when output is not~~ | superseded | S57.
#   test_gnd_conv.metta calls (flip): three different result hashes across three
#   platforms, fuel_used = 1012 on all three. The meter is separable from the
#   result. Held 30/30 runs, 18 distinct outputs. **But nothing in that program
#   branches on the random value**, so control flow is fixed and fuel *cannot*
#   vary -- this is the trivial case. `(if (flip) (long) 0)` is untested and the
#   billing design needs it.
#
# CLAUDE.md: "Every error that survived here is one whose falsifier was written
# and marked 'not yet run'." This runs it.
#
# PREDICTION, recorded before the run: if the meter is separable from the result
# in general, fuel is one value across runs while the hash varies. If it is
# confined to non-branching programs, fuel takes TWO values that track the
# branch, and `fuel_used` cannot serve as a replication oracle or a billing
# quantity for any program whose control flow touches a nondeterministic op.
#
# usage: sh spikes/S81_fuel_branch/probe.sh [runs]      (default 20)
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BIN="$ROOT/spikes/S30_speed_duel/bin/fuelrun.v2.host"
N="${1:-20}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

# PROVENANCE (family C). This is a PREBUILT binary; a Cargo feature was measured
# moving fuel_used 107 -> 580 on identical source (spikes/V1_feature_fuel), so a
# fuel number is meaningless without saying which artifact produced it. Every
# comparison below is WITHIN this one binary -- run against run -- so a stale
# binary cannot manufacture the effect; it could only change the magnitudes.
[ -x "$BIN" ] || { echo "no fuelrun at $BIN"; exit 1; }
echo "binary   $BIN"
echo "sha256   $(shasum -a 256 "$BIN" | cut -d' ' -f1)"
echo "host     $(uname -m) $(uname -s)"
echo

LONG='(+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))'
fuel() { "$BIN" "$1" 2000000 2>&1 | awk '/^fuel_used/{print $2}'; }
hash8() { "$BIN" "$1" 2000000 2>&1 | awk '/^raw_hash/{print substr($2,1,8)}'; }
spread() { sort -n | uniq -c | awk '{printf "%s(x%s) ", $2, $1} END{print ""}'; }

# --- C0 · IS THE MECHANISM UNDER TEST EVEN ACTIVE?
# `!(flip)` on its own returns the atom `(flip)` UNREDUCED, identical hash every
# run: the RNG ops are registered by `import! &self random`, so without that line
# a "flip" program measures the ABSENCE of flip. A whole afternoon of runs could
# have been spent concluding flip is deterministic. Assert the mechanism is on.
printf '!(flip)\n' > "$T/bare.metta"
printf '!(import! &self random)\n!(flip)\n' > "$T/live.metta"
bare=$(for i in $(seq 1 5); do hash8 "$T/bare.metta"; done | sort -u | wc -l | tr -d ' ')
live=$(for i in $(seq 1 "$N"); do hash8 "$T/live.metta"; done | sort -u | wc -l | tr -d ' ')
echo "C0  flip WITHOUT the import: $bare distinct hash(es) in 5   -> inert, as expected"
echo "C0  flip WITH    the import: $live distinct hash(es) in $N   -> $([ "$live" -ge 2 ] && echo 'ACTIVE' || echo 'NOT ACTIVE -- result below is void')"
[ "$live" -ge 2 ] || { echo "REFUSING: the nondeterminism under test did not occur."; exit 1; }

# --- C1 · CAN THE INSTRUMENT EXPRESS THE VERDICT? (A15)
# If both branches cost the same fuel, constant fuel in the treatment would
# prove nothing at all -- the experiment would be unable to produce the answer
# whichever way it came out. Decidable before the run, so it is decided here.
printf '!(import! &self random)\n!(if True %s 0)\n' "$LONG" > "$T/bt.metta"
printf '!(import! &self random)\n!(if False %s 0)\n' "$LONG" > "$T/bf.metta"
ft=$(fuel "$T/bt.metta"); ff=$(fuel "$T/bf.metta")
echo "C1  forced True branch  fuel = $ft"
echo "C1  forced False branch fuel = $ff"
echo "C1  separation          = $((ft - ff)) fuel  -> $([ "$ft" -ne "$ff" ] && echo 'the meter CAN see the branch' || echo 'BLIND -- result below is void')"
[ "$ft" -ne "$ff" ] || { echo "REFUSING: a fuel difference this test cannot see."; exit 1; }

# --- C2 · BASELINE. A program with no nondeterminism must be constant in both,
# or the run-to-run variation below is the harness and not the subject.
printf '!(import! &self random)\n!(if True %s 0)\n' "$LONG" > "$T/base.metta"
echo "C2  fixed program, $N runs: fuel $(for i in $(seq 1 "$N"); do fuel "$T/base.metta"; done | spread)"

# --- TREATMENT
printf '!(import! &self random)\n!(if (flip) %s 0)\n' "$LONG" > "$T/br.metta"
echo
echo "TREATMENT  !(if (flip) LONG 0), $N runs"
echo "  fuel   $(for i in $(seq 1 "$N"); do fuel "$T/br.metta"; done | spread)"
echo "  hash   $(for i in $(seq 1 "$N"); do hash8 "$T/br.metta"; done | sort | uniq -c | awk '{printf "%s(x%s) ", $2, $1} END{print ""}')"
echo
# The two treatment values must equal the two forced-branch values plus the cost
# of evaluating (flip) itself. That is an arithmetic identity the data either
# satisfies or does not, and it is the difference between "fuel varies" and
# "fuel varies FOR THE REASON CLAIMED" -- CLAUDE.md's correct-numbers-wrong-
# attribution, checked rather than asserted.
fl=$(fuel "$T/live.metta"); imp=$(printf '!(import! &self random)\n' > "$T/i.metta"; fuel "$T/i.metta")
echo "ATTRIBUTION  bare import = $imp,  import+flip = $fl,  so (flip) costs $((fl - imp))"
echo "             forced branches $ft / $ff  + $((fl - imp))  =  $((ft + fl - imp)) / $((ff + fl - imp))"
echo "             -> compare against the two treatment fuel values above."
