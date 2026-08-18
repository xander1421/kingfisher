#!/usr/bin/env bash
# H95 · mkfixture.sh v1 — build a hermetic sandbox that runs THE REAL bringup.sh
# on both arms of the reachability question, and LAUNCHES NOTHING.
#
# Why a sandbox and not the live script: the default (no-flag) path of the real
# bringup.sh ends in a launch loop. `--check` is safe by contract and is arm O1,
# but it exits at :430 and therefore cannot answer what the DEFAULT path does.
# bringup.sh:60 does `cd "$(dirname "${BASH_SOURCE[0]}")"`, so a byte-identical
# COPY in a sandbox reads that sandbox's roster.txt/prompts/spikes — which is
# exactly the isolation needed, with no edit to the subject.
#
# WHY NOTHING LAUNCHES ON THE DOWN ARM: bringup.sh:472 skips any roster lane
# with no `prompts/<lane>.md` and `continue`s BEFORE the `./run_loop.sh &` line.
# The down arm's callsign is `ZZZQ-9`, deliberately briefless. Asserted, not
# assumed: check.sh greps the arm's output for `launched` and fails if present.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
ARM=$1              # up | down
FIX="$HERE/fixture_$ARM"

rm -rf "$FIX"; mkdir -p "$FIX/prompts" "$FIX/spikes/harness"

# The subject, byte-identical. cmp is asserted by check.sh: a fixture running a
# MODIFIED copy would prove nothing about the shipped file.
cp "$ROOT/bringup.sh" "$FIX/bringup.sh"

# roster: UP arm names a callsign this host really is running (so MISSING is
# empty and the full-quorum branch is taken); DOWN arm names one that is not.
if [ "$ARM" = up ]; then echo 'ATTACKER-1' > "$FIX/roster.txt"
else                     echo 'ZZZQ-9'     > "$FIX/roster.txt"; fi

# run_loop.sh must PARSE: bringup.sh:442 refuses to launch when `bash -n` fails,
# and that refusal exits at :448 — above 511, which would confound the down arm
# with a different early exit.
printf '#!/usr/bin/env bash\n: # H95 fixture stub, never executed (no brief)\n' > "$FIX/run_loop.sh"
chmod +x "$FIX/run_loop.sh"

# selfcheckall.py STUB. The question is whether line 511 is REACHED, not what
# the real 9-module sweep prints; the real one also writes into the shared tree
# and takes seconds. A stub keeps the fixture hermetic and bounded.
printf '#!/usr/bin/env python3\nprint("H95_STUB_SELFCHECKALL_RAN")\n' > "$FIX/spikes/harness/selfcheckall.py"

: > "$FIX/CHANNEL.md"        # lane_lastwork() reads it; empty is a valid input
echo "$FIX"
