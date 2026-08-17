#!/usr/bin/env bash
# scope_probe.sh — H57 ATTACK. What does allocid.sh v2's seed STILL not see?
#
# The v2 rationale claims the seed reads "every place an id can be spoken for".
# That is the claim to attack, and it is attacked the only way a scope claim can
# be: enumerate the namespace from a WIDER source than the instrument uses, and
# subtract.
#
# WIDER SOURCE: every tracked file of any type (`git ls-files`), binaries
# excluded with `grep -I` because a 6 MiB shared object matching `S30` is a byte
# coincidence, not an allocation -- 21 such files matched on the first run and
# they are noise, not ids.
#
# usage: bash spikes/H57_allocid_scope/scope_probe.sh [PREFIX...]
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
for p in "${@:-H S G W M Q B N V C L D U}"; do
  seed=$( { ls spikes 2>/dev/null | grep -oE "^${p}[0-9]+"
            git ls-files -z -- '*.md' '*.log' | xargs -0 grep -ohIE "\b${p}[0-9]+\b" 2>/dev/null
            grep -ohIE "\b${p}[0-9]+\b" WORK_QUEUE.md CHANNEL.md livechat.log 2>/dev/null
          } | sort -u )
  all=$(git ls-files -z | xargs -0 grep -ohIE "\b${p}[0-9]+\b" 2>/dev/null | sort -u)
  miss=$(comm -13 <(printf '%s\n' "$seed") <(printf '%s\n' "$all") | tr '\n' ' ')
  printf '%-3s seed=%-4s tracked=%-4s NOT-IN-SEED: %s\n' \
    "$p" "$(printf '%s\n' "$seed" | grep -c .)" \
    "$(printf '%s\n' "$all" | grep -c .)" "${miss:-none}"
done
