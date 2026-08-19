#!/bin/sh
# S37 F2 — re-run EVERY consumer of `verify_completeness` and record its verdict.
#
# The queue row says "the nine importers". Resolved MECHANICALLY (§12.4) rather
# than trusting that count, which was written days ago:
#     grep -rl verify_completeness spikes --include=*.py | grep -v __pycache__
# returns 12 consumers plus the module itself. The row's number is stale and the
# list below is the current one, not a retyped nine.
#
# `spikes/S20_verify_kinds/w2_head/trie_witness.py` is a PINNED COPY of the
# module and is deliberately NOT in this list: it is S20's frozen HEAD artifact,
# not a consumer, and lifting into it would destroy the pin.
#
# usage: sh consumers.sh <outfile>
set -e
# $0 may be relative and the caller cwd is not guaranteed, so resolve ROOT
# from this script own absolute path before any cd happens.
SELF=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$SELF/../.." && pwd)
OUT=${1:?usage: sh consumers.sh <outfile>}
# ABSOLUTE, because this script cd's into each consumer's directory and a
# relative outfile silently stops receiving rows after the first cd. It did:
# the first "after" run produced an EMPTY file and the diff read as "all 12
# consumers changed", which is the loudest possible way to be wrong quietly.
case "$OUT" in /*) ;; *) OUT="$(pwd)/$OUT" ;; esac
: > "$OUT"
for rel in \
  S20_verify_kinds/verify_kinds.py \
  S23_consumer_sweep/probe.py \
  S24_range_crossover/range_crossover.py \
  S27_verify_floor/verify_floor.py \
  S36_witnessed_job/witnessed_job.py \
  S36_witnessed_job/attack.py \
  S80_completeness_bytes/completeness.py \
  S85_verify_vs_reexec/verify_vs_reexec.py \
  W2_witnessed_trie/attack.py \
  W6_incremental_witness/incremental_verifier.py \
  W7_streaming_witness/streaming_verifier.py \
  W9_bound_streaming_witness/bound_streaming_verifier.py
do
  d=$(dirname "$rel"); f=$(basename "$rel")
  cd "$ROOT/spikes/$d"
  rc=0
  o=$(python3 "$f" 2>&1) || rc=$?
  # VERDICT LINES ONLY, never the whole stdout: these scripts print timings and
  # timestamps that differ run to run for reasons that have nothing to do with
  # this cutover, and hashing that would make every re-run look like a change.
  cert=$(printf '%s\n' "$o" | grep -oE 'ok=(True|true|False|false)' | tr '\n' ',' || true)
  prob=$(printf '%s\n' "$o" | grep -c 'PROBLEM:' || true)
  fail=$(printf '%s\n' "$o" | grep -ciE 'FAIL|REFUSE|Traceback' || true)
  printf '%s\trc=%s\tcert=%s\tproblems=%s\tfailtokens=%s\n' "$rel" "$rc" "${cert:-none}" "$prob" "$fail" >> "$OUT"
  cd "$ROOT"
done
cat "$OUT"
