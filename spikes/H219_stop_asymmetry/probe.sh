#!/usr/bin/env bash
# probe.sh v2 — H219 (ok-1, ATTACK cycle 30). Does the Stop hook honour the
# PER-LANE kill switch `STOP.$CALLSIGN` that H31 added to the launcher?
#
# Run:  bash spikes/H219_stop_asymmetry/probe.sh
#       KF_TEST_GATE=<a hook copy> bash spikes/H219_stop_asymmetry/probe.sh
# Exit: 0 = every arm reached its target AND the hook honours both spellings.
#       1 = an arm failed.  2 = the probe could not reach the hook (no claim).
#
# v2 FIXES THREE DEFECTS IN v1, ALL MINE, AND THE THIRD IS WHY THE SEAM EXISTS:
#
#   * v1 HAD NO SEAM, so `KF_TEST_GATE=<HEAD's hook> probe.sh` silently measured
#     the WORKING TREE hook and printed "F1/F3 FIRED ... the row dies here" —
#     the pre-fix run reporting the post-fix hook under the pre-fix label. The
#     only thing that caught it was that the banner still read v1. A probe that
#     ignores the input it is handed answers a question nobody asked (E family).
#   * A5 built its fixture with `: > 'STOP.../etc'`, which cannot be created —
#     "No such file or directory" — so the arm PASSED with no fixture present
#     and was evidence of nothing (A29). It could not have discriminated anyway:
#     a hostile callsign and an allowed stop both leave the hook at `exit`.
#     Split into A5 (artifacts, behavioural) and A6 (ORDER, read out of the
#     file); A6 is the arm that can catch a repair placed above the whitelist.
#   * C2 ran `grep -c ... || echo 0`, and grep PRINTS 0 and EXITS 1 on no match,
#     so every zero was printed twice. An instrument's own output is data.
#
# And v1's class sweep reported `bare-spelling reads: 0` for all eight per-lane
# state names because the local grep is `ugrep`, which rejected the `\{` in the
# pattern: eight clean zeros from a regex that never ran. That sweep is arm C3
# and is now python, with no shell regex dialect in the path.
#
# ISOLATION. The hook pins ROOT to the live workspace. Every arm runs a COPY in
# a mktemp -d with ROOT rewritten AND THE ANCHOR ASSERTED — an unmatched sed
# returns the input unchanged (CLAUDE.md, Editing), which would point this probe
# at the real tree and eat a running lane's terminal signal. My cycle 1 put 60
# fires into the live repo root by skipping exactly that assertion.
#
# NO `STOP` AND NO `STOP.<live lane>` IS EVER CREATED AT THE WORKSPACE ROOT:
# either retires a running lane, and five are running.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATE="${KF_TEST_GATE:-$ROOT/.claude/hooks/loop_gate.sh}"
LAUNCHER="$ROOT/run_loop.sh"
[ -f "$GATE" ] || { echo "REFUSE: no hook at $GATE"; exit 2; }
# The seam is OFF in every real run, ASSERTED rather than intended — a seam left
# silently on points every arm below at a fixture nobody ships. Same guard and
# same reason as test_loop_gate.sh's.
[ -n "${KF_TEST_GATE:-}" ] || [ "$GATE" = "$ROOT/.claude/hooks/loop_gate.sh" ] || {
  echo "REFUSE: KF_TEST_GATE is unset but GATE is not the shipped hook"; exit 2; }

T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
sed "s|^ROOT=.*|ROOT=\"$T\"|" "$GATE" > "$T/gate.sh"
grep -q "^ROOT=\"$T\"$" "$T/gate.sh" || {
  echo "REFUSE: ROOT anchor did not match; will not run the live hook"; exit 2; }
chmod +x "$T/gate.sh"
cd "$T"

pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  PASS  %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s\n' "$1"; }
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (want '$3', got '$2')"; fi; }

# verdict: "exit" = the stop is ALLOWED (the turn may end), "block" = REFUSED
# (the lane is handed the loop contract and told to run another cycle).
verdict() { if CALLSIGN="$1" ./gate.sh </dev/null 2>/dev/null | grep -q '"decision":"block"'; \
            then echo block; else echo exit; fi; }
clean()   { rm -f STOP STOP.* .loop_signal.* .loop_exit.* .loop_blocks.*; }

echo "H219 · the stop switch has two spellings; until v9 each had one reader"
echo "     gate under test: $GATE"
# The banner names the artifact under test, so it must be the HIGHEST version
# and not the LAST one written. Two drafts got this wrong in a row: `sed -n 2p`
# printed `v8` while testing the v9 hook, and `grep ... | tail -1` printed `v6`,
# because this hook's rationale blocks are in the order the FILE is read, not in
# version order — v9's note sits at line 6, above v3/v5/v6's blocks. MAX, by
# number. An instrument that misidentifies its own subject is family C in three
# words, and it took two tries here to stop doing it.
echo "     hook version: v$(grep -o '^# v[0-9]*' "$T/gate.sh" | tr -dc '0-9\n' | sort -n | tail -1)"
echo

# ---------------------------------------------------------------- A · the hook
# A3 FIRST, deliberately. It is the baseline that makes A2 mean anything: a hook
# that blocked EVERYTHING would produce A2's pre-fix answer with no defect present.
clean
check "A3 no stop switch at all: the hook refuses the stop" "$(verdict L1)" "block"

# A1 is the two-sided control. If the fleet-wide STOP does not return `exit`,
# this probe never reached the branch it is about and no other arm is readable.
clean; : > STOP
check "A1 CONTROL fleet-wide STOP: the hook allows the stop" "$(verdict L1)" "exit"

# A2 IS THE ROW. Same switch, per-lane spelling, same lane. Pre-v9 this is
# `block`; that run is probe_prefix.out, produced by this same file through the
# seam above, and it is the evidence the defect was real.
clean; : > STOP.L1
check "A2 per-lane STOP.L1 also allows the stop for L1" "$(verdict L1)" "exit"

# A4 the direction that must NOT change, and the constraint on the repair: a
# `STOP*` glob would let one lane's retirement end all five, which is H31's
# defect restored from the other end.
clean; : > STOP.L2
check "A4 another lane's STOP.L2 does not stop L1" "$(verdict L1)" "block"

# A5 behavioural: a callsign the whitelist refuses leaves NO per-lane artifact.
# Stated plainly — this arm does NOT discriminate the ordering question, because
# a refused callsign and an allowed stop both leave the hook at `exit`. A6 does.
clean; : > 'STOP.L1 L2'
verdict 'L1 L2' >/dev/null
check "A5 hostile callsign leaves no span-cap file" \
      "$([ -f '.loop_blocks.L1 L2' ] && echo present || echo absent)" "absent"

# A6 ORDER, read out of the file: the per-lane STOP read must sit BELOW the
# charset whitelist, because it interpolates $LANE into a path exactly as
# EXIT_MARK and BLOCKS do. A text check, and it fails if a later edit moves it.
# Absent on a pre-v9 hook, which is a FAIL and not a skip: "the line is not there"
# is the finding, and a skip would have read as green.
wl=$(grep -n 'case "\$LANE" in' "$T/gate.sh" | head -1 | cut -d: -f1)
ps=$(grep -n '^\[ -f "STOP\.\${LANE}" \] && exit 0' "$T/gate.sh" | head -1 | cut -d: -f1)
if [ -z "$wl" ] || [ -z "$ps" ]; then
  bad "A6 ordering undecidable (whitelist line='$wl' per-lane-stop line='$ps')"
else
  check "A6 the per-lane STOP read is below the callsign whitelist" \
        "$([ "$ps" -gt "$wl" ] && echo below || echo above)" "below"
fi

# ------------------------------------------------- B · what a refused stop COSTS
# The cost of a refused stop is not zero: the hook increments the span cap on
# every refusal and hands back the loop contract. Modelled faithfully — an agent
# obeying the contract retries — and BOUNDED, so this cannot hang.
turn_ends_within() {          # turn_ends_within <lane> <tries>
  local n=0
  while [ "$n" -lt "$2" ]; do
    [ "$(verdict "$1")" = exit ] && { echo "$n"; return 0; }
    n=$((n+1))
  done
  echo no
}
clean; : > STOP
check "B1 under fleet-wide STOP the turn ends on the first attempt" "$(turn_ends_within L1 20)" "0"
clean; : > STOP.L1
check "B2 under per-lane STOP the turn ends on the first attempt"   "$(turn_ends_within L1 20)" "0"
echo "  MEASURED  B2 span cap after that attempt: $(cat .loop_blocks.L1 2>/dev/null || echo absent)"

# ------------------------------------ C · where the switch is read, mechanically
echo
echo "C1 · every STOP read in the launcher (this decides WHEN a stop is delivered)"
grep -n -- '-f STOP\|-f "STOP' "$LAUNCHER" | sed 's/^/    /'
c_total=$(grep -c -- '-f STOP\|-f "STOP' "$LAUNCHER")
c_while=$(grep -n -- '-f STOP\|-f "STOP' "$LAUNCHER" | grep -c 'while ')
echo "    launcher STOP reads: $c_total total, $c_while inside a \`while\` condition"
check "C1 the launcher consults the switch only BETWEEN turns" "$c_total" "$c_while"

echo
echo "C2 · every harness file that reads the stop switch, and which spellings"
python3 - "$ROOT" "$GATE" <<'PY'
import re, sys, pathlib
root, gate = pathlib.Path(sys.argv[1]), sys.argv[2]
files = [gate, 'run_loop.sh', 'bringup.sh', 'peers.sh',
         'spikes/harness/bringup.sh', 'spikes/harness/quiet.sh']
def rel(p):
    try:    return str(p.relative_to(root))
    except ValueError: return str(p)
for f in files:
    p = pathlib.Path(f) if pathlib.Path(f).is_absolute() else root / f
    if not p.exists():
        continue
    lines = [l for l in p.read_text().splitlines() if not l.lstrip().startswith('#')]
    bare = sum(1 for l in lines if re.search(r'-f\s+"?STOP"?(\s|\]|$)', l))
    per  = sum(1 for l in lines if re.search(r'STOP\.(\$|\{|\w)', l))
    if bare or per:
        flag = '   <-- reads the switch, knows only one spelling' if bare and not per else ''
        print(f'    {rel(p):<38} fleet-wide={bare} per-lane={per}{flag}')

print()
print("C3 · THE CLASS SWEEP: a per-lane state name still read at a BARE spelling")
names = ['loop_signal','loop_exit','loop_blocks','heartbeat','loop_fails',
         'loop_lock','loop_turn_gen','loop_launcher']
readers = [gate, 'run_loop.sh', 'bringup.sh', 'peers.sh',
           'spikes/harness/bringup.sh', 'scripts/autoloop.py']
tot = 0
for n in names:
    hits = []
    for f in readers:
        p = pathlib.Path(f) if pathlib.Path(f).is_absolute() else root / f
        if not p.exists():
            continue
        for i, l in enumerate(p.read_text().splitlines(), 1):
            if l.lstrip().startswith('#'):
                continue
            for m in re.finditer(r'\.' + n, l):
                if l[m.end():m.end()+1] != '.':
                    hits.append((f'{p.name}:{i}', l.strip()[:64]))
    tot += len(hits)
    print(f'    .{n:<15} bare sites: {len(hits)}')
    for where, text in sorted(set(hits))[:3]:
        # PRINTED, not just counted: the one hit on this tree is a MESSAGE
        # STRING, and a bare count would have read as a live second site.
        print(f'        {where}  {text}')
print(f'    -> {tot} bare site(s) across 8 per-lane state names.')
PY

echo
echo "probe: $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
