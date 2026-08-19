#!/usr/bin/env bash
# test_send.sh — H184. Fails when send.sh cannot read its own roster.
#
# THE ASSERTION THAT MATTERS IS THE NEGATIVE CONTROL. "send.sh accepts a declared
# lane" passes against the broken version too if the fixture happens to hit the
# fallback literal, so this drives a scratch roster naming a callsign the literal
# does NOT contain. Only a script that actually READ the file can accept it.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
SEND="spikes/harness/send.sh"
fail=0
ck() { if [ "$1" = 0 ]; then echo "  ok    $2"; else echo "  FAIL  $2"; fail=1; fi; }

# §10: the fixture lives inside the workspace.
T="$(mktemp -d "$(pwd)/.tmp_test_send.XXXXXX")"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/spikes/harness" "$T/prompts" "$T/inbox/archive"
cp "$SEND" "$T/spikes/harness/send.sh"

# A callsign absent from the no-roster fallback literal, so accepting it PROVES
# the roster was read rather than the literal being hit.
printf '# scratch\nZZ-ONLY-IN-ROSTER\n' > "$T/roster.txt"
printf '# brief\n' > "$T/prompts/ZZ-ONLY-IN-ROSTER.md"

out="$( cd "$T" && sh spikes/harness/send.sh ZZ-ONLY-IN-ROSTER "hello" 2>&1 )"
rc=$?
ck "$rc" "a roster-only callsign is accepted (proves the roster was READ, not the fallback literal)"
case "$out" in *"bad flag in substitute"*) ck 1 "sed parsed its expression and filename as two arguments";; *) ck 0 "sed parsed its expression and filename as two arguments";; esac
[ -s "$T/inbox/ZZ-ONLY-IN-ROSTER.md" ] && ck 0 "the message was actually queued" || ck 1 "the message was actually queued"

# THE CLASS. An unreadable/empty roster must REFUSE, not report every callsign
# undeclared and every inbox quiet. This is the reading nobody investigates.
: > "$T/roster.txt"
out2="$( cd "$T" && sh spikes/harness/send.sh --list 2>&1 )"; rc2=$?
[ "$rc2" -ne 0 ] && ck 0 "an empty lane list REFUSES (rc=$rc2)" || ck 1 "an empty lane list refuses instead of printing a false green (rc=$rc2)"
case "$out2" in *"nothing pending"*) ck 1 "--list does not report quiet over an unread roster";; *) ck 0 "--list does not report quiet over an unread roster";; esac

# NEGATIVE CONTROL ON THE FIXTURE ITSELF: the pre-fix line must reproduce the
# defect here, or the checks above are green against a fixture that cannot fail.
brk="$(sed 's/#\.\*\/\/. "\$_ROSTER"/x/' /dev/null 2>/dev/null; printf '%s' "$( { sed 's/#.*//'"$T/roster.txt" ; } 2>&1 )")"
case "$brk" in *"bad flag in substitute"*) ck 0 "negative control: the unspaced form still errors on this sed";; *) ck 1 "negative control: the unspaced form did NOT error, so this box cannot reproduce the defect and the checks above prove nothing";; esac

[ "$fail" = 0 ] && echo "send: the roster is READ, and an unread roster refuses instead of reporting quiet"
exit "$fail"
