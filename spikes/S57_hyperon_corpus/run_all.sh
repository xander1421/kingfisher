#!/bin/bash
# S57 — run hyperon's OWN test corpus through fuelrun on one platform,
# emitting one TSV row per program. The corpus is the elder's, not ours:
# that is the whole point (see analysis/GUARDRAILS.md, and the fact that
# every spike using an elder corpus survived attack while every spike using
# self-authored data was retracted).
BIN="$1"; TAG="$2"; FUEL="${3:-200000}"
printf 'program\tstatus\tfuel\traw_hash\tsorted_hash\tnresults\n'
for f in corpus/*.metta; do
  n=$(basename "$f")
  out=$("$BIN" "$f" "$FUEL" 2>&1)
  rc=$?
  if [ $rc -ne 0 ]; then
    printf '%s\tERR_rc%d\t-\t-\t-\t-\n' "$n" "$rc"; continue
  fi
  fuel=$(printf '%s' "$out" | awk '/^fuel_used/{print $2}')
  raw=$(printf  '%s' "$out" | awk '/^raw_hash/{print $2}')
  srt=$(printf  '%s' "$out" | awk '/^sorted_hash/{print $2}')
  nr=$(printf   '%s' "$out" | awk '/^n_results/{print $2}')
  [ -z "$fuel" ] && { printf '%s\tNO_PARSE\t-\t-\t-\t-\n' "$n"; continue; }
  printf '%s\tok\t%s\t%s\t%s\t%s\n' "$n" "$fuel" "$raw" "$srt" "$nr"
done
