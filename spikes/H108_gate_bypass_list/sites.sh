#!/usr/bin/env bash
# H108 — every site that RUNS a commit-gate checker, and which ones it runs.
#
# The class is "two independently-maintained lists of one set with nothing
# comparing them" (H39). `test_loop_gate.sh` now refuses when the §13 bypass
# diverges from the installed gate; this script is the wider sweep that found the
# third copy, kept runnable so the next lane can re-run it rather than trust this
# paragraph. A MENTION is not a RUN: it greps for the invocation, which is the
# distinction H63 was earned on.
#
# usage: bash spikes/H108_gate_bypass_list/sites.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
MODULES='refcheck.py journalcheck.py githygiene.py recordloss.py'

# TWO INVOCATION FORMS, and the first draft of this script saw only one: it read
# `pre-commit.hook` as running ONE module, because the gate invokes `python3 "$c"`
# over a CHECKS list and the only literal `python3 spikes/harness/...` in the file
# is a comment in my own v3 header. A mention scored as a run — H63's defect, in
# the script written to hunt for exactly that. Comment lines are excluded here.
invokes() {   # $1 file, $2 module basename
  grep -nE "python3 [^ ]*spikes/harness/$2|^[[:space:]]*(CHECKS=')?spikes/harness/$2'?[[:space:]]*$" "$1" \
    | grep -qv "^[0-9]*:[[:space:]]*#"
}

printf '%-52s %s\n' 'SITE' 'RUNS'
grep -rlE "spikes/harness/(refcheck|journalcheck|githygiene|recordloss)\.py" \
     --include='*.sh' --include='*.py' --include='*.hook' --include='*.yml' . 2>/dev/null \
  | grep -v '/spikes/H[0-9]' | sort | while IFS= read -r f; do
      runs=''
      for m in $MODULES; do
        invokes "$f" "$m" && runs="$runs ${m%.py}"
      done
      [ -n "$runs" ] || continue
      tracked='untracked'
      git ls-files --error-unmatch "${f#./}" >/dev/null 2>&1 && tracked=''
      printf '%-52s %s %s\n' "${f#./}" "${runs# }" "$tracked"
    done
