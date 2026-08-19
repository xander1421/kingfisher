#!/bin/bash
# falsify.sh — H243's guards are two-sided. ok-1, 2026-08-19 (cycle 34 ATTACK).
#
# A census that has only ever been seen reporting "0 PID ALONE" cannot tell a
# fixed tree from a census that stopped looking. Each arm REMOVES one guard in
# an isolated copy and asserts the census goes red AND names the site; the
# control asserts it is green with the guard present. Both directions or it
# proves nothing.
#
# Scratch lives under .scratch/ (H89, §10). The live tree is never written.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D="$ROOT/.scratch/h243_falsify"
fails=0

say() { printf '  %-6s %s\n' "$1" "$2"; }
ck()  { if [ "$1" = "$2" ]; then say PASS "$3"; else say FAIL "$3 (want '$2' got '$1')"; fails=$((fails+1)); fi; }

build() {                       # build <mutation-sed-or-empty> <file>
  rm -rf "$D"; mkdir -p "$D/spikes/harness" "$D/spikes/H243_lock_liveness"
  cp "$ROOT/spikes/harness/lanelive.sh"            "$D/spikes/harness/"
  cp "$ROOT/spikes/harness/commit-msg.hook"        "$D/spikes/harness/"
  cp "$ROOT/spikes/harness/check_live_launcher.sh" "$D/spikes/harness/"
  cp "$ROOT/spikes/harness/registry.py"            "$D/spikes/harness/"
  cp "$ROOT/spikes/H243_lock_liveness/sites.py"    "$D/spikes/H243_lock_liveness/"
  ( cd "$D" && git init -q . && git config user.email t@t && git config user.name t \
      && git add -A >/dev/null 2>&1 )
  [ -n "$1" ] && { sed -i.bak "$1" "$D/$2" && rm -f "$D/$2.bak"; }
  return 0
}

count_pidonly() { python3 "$D/spikes/H243_lock_liveness/sites.py" "$D" 2>&1 | grep -c 'PID ONLY'; }
names()         { python3 "$D/spikes/H243_lock_liveness/sites.py" "$D" 2>&1 | grep 'PID ONLY'; }

echo "H243 falsifiers — each guard removed in an isolated copy"

# C0 · POSITIVE CONTROL FIRST. A suite that only ever removes guards passes
#      trivially if the census reports everything as broken.
build "" ""
ck "$(count_pidonly)" "0" "C0 control · the repaired copy reports 0 PID ALONE"

# F1 · commit-msg.hook: drop the launcher_alive guard, keep everything else.
build 's#^ *launcher_alive "$_lp" || _lp=.*#          :#' spikes/harness/commit-msg.hook
grep -q 'launcher_alive "\$_lp"' "$D/spikes/harness/commit-msg.hook" \
  && { say FAIL "F1 mutant did not apply — the anchor is stale (H217)"; fails=$((fails+1)); } \
  || say PASS "F1 mutant applied (the guard line is gone)"
ck "$(names | grep -c 'commit-msg.hook')" "1" "F1 · census names commit-msg.hook once the guard is gone"

# F2 · check_live_launcher.sh: put the bare kill -0 back.
build 's|launcher_alive "\$_lp" \&\& _locked|kill -0 "$_lp" 2>/dev/null \&\& _locked|' \
      spikes/harness/check_live_launcher.sh
grep -q 'kill -0 "\$_lp"' "$D/spikes/harness/check_live_launcher.sh" \
  && say PASS "F2 mutant applied (bare kill -0 restored)" \
  || { say FAIL "F2 mutant did not apply — the anchor is stale (H217)"; fails=$((fails+1)); }
ck "$(names | grep -c 'check_live_launcher.sh')" "1" "F2 · census names check_live_launcher.sh"

# F3 · registry.py: swap the predicate back to the pid-only helper.
build 's|alive = launcher_alive(pid)|alive = _pid_alive(int(pid or 0))|' spikes/harness/registry.py
ck "$(names | grep -c 'registry.py')" "1" "F3 · census names registry.py"

# F4 · THE CENSUS ITSELF. An empty population must REFUSE, not report a clean 0
#      -- this lane has shipped "a check whose PASS looks like its NOT-RUN" in
#      three consecutive cycles and this is the arm that would have caught it.
build "" ""
rm -rf "$D/spikes/harness" "$D/spikes/H243_lock_liveness/sites.py.none"
( cd "$D" && git rm -r -q --cached spikes/harness >/dev/null 2>&1 )
out=$(python3 "$ROOT/spikes/H243_lock_liveness/sites.py" "$D" 2>&1); rc=$?
case "$out" in
  *REFUSES*) ck "$rc" "1" "F4 · an EMPTY population refuses instead of printing 0" ;;
  *)         say FAIL "F4 · empty population did not refuse: $out"; fails=$((fails+1)) ;;
esac

rm -rf "$D"
echo
if [ "$fails" -eq 0 ]; then echo "falsify.sh: all arms two-sided, 0 failures"; else
  echo "falsify.sh: $fails FAILED"; fi
exit "$fails"
