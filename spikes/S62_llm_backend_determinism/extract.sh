#!/bin/sh
# Extract ONLY the generated text from llama-cli output.
#
# The version used in S62/S63 was `awk '/^> /{f=1;next} /^\[ Prompt:/{f=0} f'`.
# It has two defects and they both fabricate AGREEMENT, which is the dangerous
# direction: in a verifier, a comparator that under-reports difference accepts a
# divergent replica.
#   1. it drops every GENERATED line beginning with "> " -- a model asked for a
#      markdown blockquote collapsed to 11 bytes, and three different answers
#      hashed identically.
#   2. an empty capture hashes to da39a3ee5e6b (sha1 of "") and looks perfectly
#      self-deterministic forever. That empty hash appeared in S57, S58, S60,
#      S62 and S63.
#
# This version anchors on the FIRST prompt-echo line only, keeps everything
# after it verbatim, and fails loudly on an empty or missing capture.
#   usage: extract.sh <file>   -> generated text on stdout, or exit 1
set -u
f="$1"
[ -s "$f" ] || { echo "extract: empty output file" >&2; exit 1; }
out=$(tr -d '\r' < "$f" | awk '
  !seen && /^> / { seen=1; next }        # first prompt echo only
  seen && /^\[ Prompt:/ { exit }         # timing line ends generation
  seen { print }                          # everything else verbatim, "> " included
')
[ -n "$(printf '%s' "$out" | tr -d '[:space:]')" ] || {
  echo "extract: captured nothing -- refusing to emit an empty string" >&2; exit 1; }
printf '%s' "$out"
