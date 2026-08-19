#!/usr/bin/env bash
# test_h207_falsify.sh v2 — H207, ATTACKER-1, 2026-08-19.
#
# v2 CHANGELOG. DEFECT REMOVED: **`cmp -s` (DID THE BYTES CHANGE?) STOOD IN FOR
# AN ANCHOR ASSERTION (DID THE INTENDED EDIT APPLY?). THE TWO AGREE ON EVERY
# SUCCESSFUL EDIT AND DISAGREE EXACTLY WHEN THE EDITING TOOL FAILS -- SO THE
# TOOL'S OWN FAILURE WAS SCORED AS A FINDING AGAINST THE MODULE UNDER TEST.**
# MEASURED, not reasoned: v1 shipped `m1` as a GNU `c\` range command, this is
# BSD sed, sed exited non-zero printing `extra characters after \ at the end of
# c command`, and left a ZERO-BYTE file. An empty file DIFFERS from the source
# (so the no-op guard passed) and COMPILES (so the compile guard passed), so v1
# ran it, saw exit 0, and printed `m1: suite stayed GREEN with the logic
# removed` -- an accusation of a coverage gap in `idscope.py` that does not
# exist. **1 of 6 mutants, and the failing verdict was about the wrong subject.**
#
# CLAUDE.md's Editing section names the OTHER direction of this: `str.replace`
# returns the string UNCHANGED when the anchor is absent, so an edit fails by
# doing too little of the right thing. `sed` fails by producing too little of
# ANY thing. Every sibling suite guards the first direction and asserts its
# anchor (`test_h13`, `test_h16`, `test_h51`, `test_h57`, `H7/falsify.py`, all
# via `anchored_replace` or an explicit `cmp`); v1 was the only driver in the
# tree using a tool with the second failure mode, and nothing in the tree
# guarded it. v2 does, twice, and both nets are exercised by controls below.
#
# The deeper asymmetry v1 had, which is the class worth grepping for:
# **THE FAILING BRANCH HAD TO SHOW ITS WORK AND THE PASSING BRANCH DID NOT.**
# `went red` required `grep FAIL` AND `grep <want>`; `stayed GREEN` required
# only `rc == 0`, which a program that never ran also satisfies. C2 below is a
# mutant that compiles, is not empty, exits 0 and prints NOTHING.
#
# THE STANDING QUESTION, ASKED OF MY OWN SUITE: a check only ever seen PASSING
# is as uninformative as one only ever seen failing. `idscope.py --selfcheck`
# went green the first time it ran with the v5 arms in it, which is exactly the
# state `test_loop_gate.sh` was in for its whole life while the hook it tested
# was broken (H202), and the state the 15-check version was in before that.
#
# So each mutant below REMOVES ONE PIECE of the v5 logic from a COPY and
# requires the suite to go RED and to NAME the arm that caught it. Two-sided:
# C0 asserts the unmutated copy is GREEN, so a mutant killing the suite for an
# unrelated reason (a syntax error, a bad path) cannot read as a pass.
#
# THE COPY IS THE POINT. Mutating the real module would leave a broken checker
# on disk for four other lanes if this script died between mutation and repair
# -- H187's dual, where re-running an uncommitted spike destroyed its evidence.
#
# run: bash spikes/harness/test_h207_falsify.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
SRC=spikes/harness/idscope.py
WORK=.scratch/h207_mutants
rm -rf "$WORK"; mkdir -p "$WORK"

pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }

echo "H207 · every v5 arm must go RED when the logic it defends is removed"
echo

# ---- C0 . control: the unmutated copy is green -----------------------------
cp "$SRC" "$WORK/clean.py"
if python3 "$WORK/clean.py" --selfcheck >"$WORK/clean.out" 2>&1; then
  ok "C0 control: an UNMUTATED copy passes (so a red below is the mutation)"
else
  bad "C0 control: the unmutated copy FAILS -- every mutant below is void"
  cat "$WORK/clean.out"; echo; echo "RESULT: 0 passed, 1 failed"; exit 1
fi

# ---- the mutants -----------------------------------------------------------
# name | sed program | substring the suite must print when it goes red
# A MUTANT THAT CRASHES IS NOT A MUTANT, IT IS A BROKEN FILE -- and the first
# draft of this script scored one as a pass. `m1`'s sed anchor matched TWO
# sites, corrupting `queue_rows` as collateral, and the run exited non-zero with
# a `NameError`; the only reason it did not read as "caught" is that the wanted
# string happened to be absent. Exit status alone cannot tell a caught mutation
# from a syntax error, so all four conditions below are required: the edit
# APPLIED, the file still COMPILES, the suite actually RAN (it printed its own
# `FAIL` line rather than a traceback), and it NAMED the arm.
# v2: every branch SETS `verdict` and one reporting step reads it, so the
# control arms below exercise THE SHIPPED GUARD CHAIN rather than a copy of it.
# A 4th argument inverts an arm: it then passes only if the harness reaches the
# named tool-failure verdict, which is how a guard against a silent tool is
# kept honest -- otherwise the guard is itself only ever seen not firing.
mutate() {
  name=$1; prog=$2; want=$3; expect=${4:-}
  verdict=''
  if ! sed "$prog" "$SRC" > "$WORK/$name.py" 2>"$WORK/$name.sed"; then
    verdict="THE MUTATION TOOL FAILED -- $(head -1 "$WORK/$name.sed")"
  elif cmp -s "$SRC" "$WORK/$name.py"; then
    verdict='THE MUTATION DID NOT APPLY -- a no-op edit tests nothing'
  elif [ ! -s "$WORK/$name.py" ]; then
    verdict='THE MUTANT IS EMPTY -- the tool produced no program to test'
  elif ! python3 -m py_compile "$WORK/$name.py" 2>"$WORK/$name.compile"; then
    verdict='mutant does not COMPILE -- collateral damage, not a mutation'
  else
    out=$(python3 "$WORK/$name.py" --selfcheck 2>&1); rc=$?
    if [ $rc -eq 0 ] && ! printf '%s' "$out" | grep -q 'selfcheck:'; then
      verdict='exited 0 having printed NO suite output -- it never RAN the suite'
    elif [ $rc -eq 0 ]; then
      verdict='suite stayed GREEN with the logic removed'
    elif ! printf '%s' "$out" | grep -q 'FAIL'; then
      verdict='mutant CRASHED rather than failing a check -- not a mutation'
    elif printf '%s' "$out" | grep -qF "$want"; then
      verdict=''
    else
      verdict="went red but never named '$want'"
    fi
  fi
  if [ -n "$expect" ]; then
    case "$verdict" in
      *"$expect"*) ok "$name: harness says '$expect' instead of accusing the module" ;;
      *) bad "$name: harness verdict was '${verdict:-<mutation caught>}', wanted '$expect'" ;;
    esac
  elif [ -z "$verdict" ]; then
    ok "$name: suite goes RED and names it"
  else
    bad "$name: $verdict"
  fi
}

# ---- C1, C2 . the two nets v1 lacked, each fired by a REAL tool failure ------
# Both sed programs are one word, both exit 0, and both are the shapes a real
# mutation program degrades into. Without the guards they defend, each of these
# reaches `suite stayed GREEN with the logic removed` -- a false accusation
# against `idscope.py` sourced entirely from the harness.
mutate c1_empty_mutant 'd' '(unused)' 'THE MUTANT IS EMPTY'
mutate c2_no_suite_output 's/^/#/' '(unused)' 'never RAN the suite'

# M1. RELEASE degraded to the first-token rule every other prefix uses. This is
# the simplification a future reader is most likely to make, because it looks
# like consistency. It breaks the LANE-FIRST and PLURAL live forms.
# ANCHORED ON A RANGE, not on `head = re.split(...)`: that text appears in
# `queue_rows` TOO, and the first draft of this mutant rewrote both.
# v2: expressed as a SUBSTITUTION, not a GNU `c\` range command. The range form
# is what failed under BSD sed and produced the zero-byte file; `[subj]` as the
# iteration source is the same semantics -- only the subject can close -- in a
# form both seds accept. The v1 comment below is kept because its warning was
# right and about a DIFFERENT defect (the anchor matching two sites).
mutate m1_release_first_token \
  's|for w in head.split()\[1:\])$|for w in [subj])|' \
  'on a RELEASE whose subject is not the first token'

# M2. RELEASE dropped from the closers entirely -- v5 as first written, which
# ACCUSED H109 of advertising a hold that CHANNEL.md:904 explicitly released.
mutate m2_release_not_a_closer \
  's|^        elif pre == RELEASER:$|        elif False:|' \
  'on a RELEASE whose subject is not the first token'

# M3. RELEASE reading the WHOLE line instead of its leading run -- over-closing,
# so a row merely NAMED in another release's prose reads as closed.
mutate m3_release_reads_prose \
  "s|^            head = re.split(r'—\|--', line)\[0\]$|            head = line|" \
  'a RELEASE does NOT close a row merely NAMED in its prose'

# M4. The non-emptiness control removed, so a broken subject regex publishes a
# clean fleet instead of refusing. H178 and H205 both shipped this shape.
mutate m4_void_control_removed \
  "s|^    if nclaims == 0 and 'CLAIM' in ltext:\$|    if False:|" \
  'a log containing CLAIM from which NONE parse is VOID'

# M5. The decidable/undecidable split collapsed, so a live cycle's own CLAIM is
# ACCUSED. That is the always-red gate F2 preregistered and H14/H52/H73/H124
# each record the cost of.
mutate m5_accuses_live_cycles \
  "s|^        elif q.get(subj) == 'DONE':\$|        elif True:|" \
  'a CLAIM on an OPEN row is never ACCUSED'

# M6. Scoring made to gate. An unclosed claim must never move the exit code.
mutate m6_report_becomes_gate \
  "s|^    for s in settled:\$|    problems.extend(('X',s) for s in stale_c)\n    for s in settled:|" \
  'an unclosed claim alone never gates'

echo
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
