#!/bin/sh
# S57 v2 — run hyperon's OWN test corpus through fuelrun on one platform.
#
# v1 had three defects an attacker found, all fixed here:
#   1. it grepped four fields and hardcoded status='ok', so mkdocs.metta was
#      recorded OK when it was actually FUEL_EXHAUSTED. status is now compared.
#   2. #!/bin/bash — Android has no bash, so the device TSV was really produced
#      by mksh+toybox awk while the Mac ones used bash+BSD awk. Now /bin/sh.
#   3. the result hashes are low-entropy (35 distinct over 67 programs) because
#      hyperon's outputs are almost all () and (Error ...). The discrimination
#      lives in the ASSERTIONS, not the hash, so count them explicitly:
#      n_unit  = passing assertEqual results
#      n_error = (Error ...) atoms, mostly unresolved Python imports
BIN="$1"; FUEL="${2:-2000000}"
printf 'program\tstatus\tfuel\traw_hash\tsorted_hash\tnresults\tn_unit\tn_error\n'
for f in corpus/*.metta; do
  n=`basename "$f"`
  out=`"$BIN" "$f" "$FUEL" 2>&1`
  if [ $? -ne 0 ]; then printf '%s\tCRASH\t-\t-\t-\t-\t-\t-\n' "$n"; continue; fi
  st=`printf '%s' "$out"   | awk '/^status/{print $2}'`
  fuel=`printf '%s' "$out" | awk '/^fuel_used/{print $2}'`
  raw=`printf '%s' "$out"  | awk '/^raw_hash/{print $2}'`
  srt=`printf '%s' "$out"  | awk '/^sorted_hash/{print $2}'`
  nr=`printf '%s' "$out"   | awk '/^n_results/{print $2}'`
  # count result-atom kinds in the --- results --- block
  nu=`printf '%s' "$out" | awk '/^--- results ---/{r=1;next} r&&/\(\)$/{c++} END{print c+0}'`
  ne=`printf '%s' "$out" | awk '/^--- results ---/{r=1;next} r&&/\(Error/{c++} END{print c+0}'`
  [ -z "$fuel" ] && { printf '%s\tNO_PARSE\t-\t-\t-\t-\t-\t-\n' "$n"; continue; }
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$n" "$st" "$fuel" "$raw" "$srt" "$nr" "$nu" "$ne"
done
