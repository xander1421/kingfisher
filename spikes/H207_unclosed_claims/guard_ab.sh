#!/usr/bin/env bash
# guard_ab.sh — H207, ATTACKER-1, 2026-08-19. Two-sided, and the point is the
# VERDICT TEXT and not the exit code.
#
# v1 of `test_h207_falsify.sh` guarded a mutant with `cmp -s` (did the bytes
# change?) where every sibling driver asserts its anchor (did the intended edit
# apply?). The two agree on every successful edit. They disagree exactly when
# the editing TOOL fails -- and then v1 blames `idscope.py`.
#
# Both chains below are run over the SAME two degenerate mutants, produced by
# real one-word sed programs that exit 0:
#   `d`        -> a zero-byte file      (the shape BSD sed left behind for real)
#   `s/^/#/`   -> every line commented  (compiles, non-empty, runs nothing)
#
# EXPECTED: v1 says `suite stayed GREEN with the logic removed` for both -- a
# coverage gap reported in a module that has none. v2 names the tool.
# run: bash spikes/H207_unclosed_claims/guard_ab.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
SRC=spikes/harness/idscope.py
W=.scratch/h207_guard_ab; rm -rf "$W"; mkdir -p "$W"

v1_verdict() {   # the shipped-for-three-hours chain, reproduced verbatim
  f=$1
  cmp -s "$SRC" "$f" && { echo 'THE MUTATION DID NOT APPLY'; return; }
  python3 -m py_compile "$f" 2>/dev/null || { echo 'does not COMPILE'; return; }
  out=$(python3 "$f" --selfcheck 2>&1); rc=$?
  if [ $rc -eq 0 ]; then echo 'suite stayed GREEN with the logic removed'
  elif ! printf '%s' "$out" | grep -q 'FAIL'; then echo 'mutant CRASHED'
  else echo 'caught'; fi
}
v2_verdict() {   # v2 adds exactly two nets: non-empty, and the suite RAN
  f=$1
  cmp -s "$SRC" "$f" && { echo 'THE MUTATION DID NOT APPLY'; return; }
  [ -s "$f" ] || { echo 'THE MUTANT IS EMPTY -- the tool produced no program to test'; return; }
  python3 -m py_compile "$f" 2>/dev/null || { echo 'does not COMPILE'; return; }
  out=$(python3 "$f" --selfcheck 2>&1); rc=$?
  if [ $rc -eq 0 ] && ! printf '%s' "$out" | grep -q 'selfcheck:'; then
    echo 'exited 0 having printed NO suite output -- it never RAN the suite'
  elif [ $rc -eq 0 ]; then echo 'suite stayed GREEN with the logic removed'
  elif ! printf '%s' "$out" | grep -q 'FAIL'; then echo 'mutant CRASHED'
  else echo 'caught'; fi
}

fail=0
printf '%-22s %-52s %s\n' MUTANT 'v1 VERDICT' 'v2 VERDICT'
for pair in "empty:d" "commented:s/^/#/"; do
  name=${pair%%:*}; prog=${pair#*:}
  sed "$prog" "$SRC" > "$W/$name.py" 2>/dev/null
  a=$(v1_verdict "$W/$name.py"); b=$(v2_verdict "$W/$name.py")
  printf '%-22s %-52s %s\n' "$name" "$a" "$b"
  case "$a" in *'stayed GREEN'*) : ;; *) echo "  CONTROL FAILED: v1 did not accuse the module on '$name'"; fail=1 ;; esac
  case "$b" in *'stayed GREEN'*) echo "  CONTROL FAILED: v2 still accuses the module on '$name'"; fail=1 ;; esac
done

# The control that makes the two columns mean something: on a REAL mutation both
# chains must agree, or v2 is not a repair, it is a different test.
sed 's|for w in head.split()\[1:\])$|for w in [subj])|' "$SRC" > "$W/real.py"
a=$(v1_verdict "$W/real.py"); b=$(v2_verdict "$W/real.py")
printf '%-22s %-52s %s\n' 'real mutation' "$a" "$b"
[ "$a" = "$b" ] && [ "$a" = caught ] || { echo "  CONTROL FAILED: the chains disagree on a REAL mutation"; fail=1; }

# And the control for THIS script: an UNMUTATED copy must be 'DID NOT APPLY' in
# both, so a green table above is not a table over three broken files.
cp "$SRC" "$W/none.py"
a=$(v1_verdict "$W/none.py"); b=$(v2_verdict "$W/none.py")
printf '%-22s %-52s %s\n' 'no mutation at all' "$a" "$b"
case "$a$b" in *'DID NOT APPLY'*'DID NOT APPLY'*) : ;; *) echo "  CONTROL FAILED: a no-op edit was not reported as one"; fail=1 ;; esac

echo
[ "$fail" -eq 0 ] && echo 'H207 guard A/B: v1 accuses idscope.py on both degenerate mutants; v2 names the tool; both agree on a real mutation and on none' && exit 0
echo 'H207 guard A/B: a control failed -- the table above is void'; exit 1
