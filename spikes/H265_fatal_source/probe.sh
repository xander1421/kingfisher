#!/bin/bash
# probe.sh — H265, "a fallback that cannot run". ok-1, 2026-08-19.
#
# Every arm runs in .scratch/ (H89, §10). The live tree, the live index and the
# installed hooks are never touched: a test that can stop production is not a
# test, and the subject here IS the commit path.
set -u
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
D="$ROOT/.scratch/h265"
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1";
       else fail=$((fail+1)); printf '  FAIL  %s: got [%s] want [%s]\n' "$1" "$2" "$3"; fi; }

rm -rf "$D"; mkdir -p "$D"

echo "== A0 · THE SEMANTICS, measured rather than recalled (§13.2) =="
: > "$D/present.sh"
ck "sh: a failed \`.\` with \`|| true\` never reaches the next command" \
   "$(cd "$D" && sh -c '. ./absent.sh 2>/dev/null || true; echo REACHED' 2>/dev/null)" ""
ck "bash: the same line DOES reach it -- so this is shell-specific, not universal" \
   "$(cd "$D" && bash -c '. ./absent.sh 2>/dev/null || true; echo REACHED' 2>/dev/null)" "REACHED"
ck "sh: the guarded form reaches it" \
   "$(cd "$D" && sh -c '[ -r ./absent.sh ] && . ./absent.sh; echo REACHED' 2>/dev/null)" "REACHED"
ck "F5 CONTROL · the guarded form still SOURCES a file that is present" \
   "$(cd "$D" && printf 'V=sourced\n' > present.sh && sh -c '[ -r ./present.sh ] && . ./present.sh; echo "${V:-unset}"' 2>/dev/null)" "sourced"

echo "== A1 · F1: H243's refusal must be REACHABLE when the module is absent =="
mkdir -p "$D/a1"; cp "$ROOT/bringup.sh" "$D/a1/bringup.sh"
out=$( cd "$D/a1" && sh bringup.sh --check 2>&1 ); rc=$?
ck "A1 the sandbox census still exits non-zero"      "$rc" "1"
ck "A1 and it now SAYS WHY -- before the fix this was 0 bytes (probe.before.out)" \
   "$(printf '%s' "$out" | grep -ci 'lanelive\.sh')" "1"

echo "== A2 · F3: the commit path must stay FAIL-OPEN with the module absent (H9/H11) =="
# A REAL git repo with a REAL commit-msg hook, built here. Never the live one:
# the subject IS the commit path, and a test that can stop production is not a test.
mkdir -p "$D/a2"; ( cd "$D/a2" && git init -q . && git config user.email t@t && git config user.name t )
mkdir -p "$D/a2/spikes/harness"
cp "$ROOT/spikes/harness/commit-msg.hook" "$D/a2/.git/hooks/commit-msg"
chmod +x "$D/a2/.git/hooks/commit-msg"
msg="$D/a2/m.txt"
printf 'S1: a finding\n\nAtom: ok-1\nClaude-Session: unassigned-in-lane\nReviewed-By: unreviewed\n' > "$msg"
# lanelive.sh DELIBERATELY ABSENT. Before the fix this refused every commit and
# printed nothing about why; the hook's contract is fail-open (H9/H11), because a
# shared gate that can wedge every lane is worse than the defect it guards.
printf 'one\n' > "$D/a2/f1.md"
out2=$( cd "$D/a2" && git add f1.md >/dev/null 2>&1 && CALLSIGN=ok-1 git commit -F "$msg" 2>&1 ); rc2=$?
ck "A2 the commit LANDS with the module absent"      "$rc2" "0"
# AN ARM REMOVED RATHER THAN ADJUSTED, and the reason is the finding: I asserted
# that no `lane:` session is minted here, and it IS -- because with no lock file
# the hook falls to its argv test, which greps the HOST's process table and finds
# the real `ok-1` launcher running on this machine. That is the hook behaving
# correctly (the argv test is the stricter of its two paths, cycle 34), and it is
# a test whose answer depends on whether this host happens to be running a lane.
# Production state leaking into a fixture is not a stricter test, it is a flaky
# one. The property it was reaching for is already covered, deliberately and with
# a constructed fixture, by `test_commit_msg.sh`'s H243 arm: a lock naming a live
# NON-launcher must not mint a session.

echo "== A3 · CONTROL: with the module PRESENT the hook still works =="
cp "$ROOT/spikes/harness/lanelive.sh" "$D/a2/spikes/harness/lanelive.sh"
printf 'two\n' > "$D/a2/f2.md"
out3=$( cd "$D/a2" && git add f2.md >/dev/null 2>&1 && CALLSIGN=ok-1 git commit -F "$msg" 2>&1 ); rc3=$?
ck "A3 the commit lands with lanelive.sh present too" "$rc3" "0"
ck "A3 CONTROL the arms differ in INPUT, not only in label" \
   "$([ -r "$D/a2/spikes/harness/lanelive.sh" ] && echo present || echo absent)" "present"

printf '\n%s pass, %s fail\n' "$pass" "$fail"
rm -rf "$D"
[ "$fail" -eq 0 ]
