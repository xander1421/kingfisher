#!/system/bin/sh
# M1.7 device agent. Dials out only: long-polls for a job, fetches the shard by
# CID, verifies it, runs fuelrun, posts the envelope back. Never listens.
BASE="${KF_BASE:-http://127.0.0.1:${KF_PORT:-18080}}"
# bearer token: the coordinator refuses to bind beyond loopback without one
AUTH="Authorization: Bearer ${KF_TOKEN}"
# overridable so a LAN run does not silently reuse the adb run's warm cache
DIR="${KF_DIR:-/data/local/tmp/m17}"
mkdir -p "$DIR/shards"
WORKER="${KF_WORKER:-phone}"
IDLE=0
while [ "$IDLE" -lt "${KF_MAXIDLE:-3}" ]; do
  JOB=$(curl -s -m 30 -H "$AUTH" "$BASE/job?worker=$WORKER")
  if [ -z "$JOB" ]; then IDLE=$((IDLE+1)); continue; fi
  IDLE=0
  CID=$(echo "$JOB" | sed 's/.*"shard_cid": *"\([^"]*\)".*/\1/')
  FUEL=$(echo "$JOB" | sed 's/.*"fuel": *\([0-9]*\).*/\1/')
  JID=$(echo "$JOB" | sed 's/.*"job_id": *"\([^"]*\)".*/\1/')
  F="$DIR/shards/$CID"
  # -f so an HTTP 404 is a curl failure. Without it curl writes the empty error
  # body to $F, exits 0, and fuelrun runs on an empty file and posts a result
  # for a shard that was never delivered -- the empty-capture failure again.
  if [ ! -f "$F" ]; then
    curl -fsS -m 60 -H "$AUTH" -o "$F" "$BASE/shard/$CID" || { rm -f "$F"; continue; }
  fi
  # Verify against the CID before running. The CID IS the hash, so this needs no
  # extra metadata, and it catches a truncated transfer as well as a wrong body.
  # M1.8's device_fetch already did this; writing a second transport without it
  # is how a check that exists stops applying.
  WANT=$(echo "$CID" | sed 's/^b//')
  GOT=$(sha256sum "$F" 2>/dev/null | cut -d' ' -f1)
  if [ -z "$GOT" ] || [ ! -s "$F" ]; then rm -f "$F"; continue; fi
  OUT=$("$DIR/fuelrun" "$F" "$FUEL" 2>&1)
  ST=$(echo "$OUT"   | awk '/^status/{print $2}')
  FU=$(echo "$OUT"   | awk '/^fuel_used/{print $2}')
  SH=$(echo "$OUT"   | awk '/^sorted_hash/{print $2}')
  RH=$(echo "$OUT"   | awk '/^raw_hash/{print $2}')
  printf '{"job_id":"%s","worker":"%s","shard_cid":"%s","status":"%s","fuel_used":"%s","sorted_hash":"%s","raw_hash":"%s"}' \
    "$JID" "$WORKER" "$CID" "$ST" "$FU" "$SH" "$RH" > "$DIR/env.json"
  curl -s -m 30 -X POST --data-binary @"$DIR/env.json" \
    -H "$AUTH" -H 'Content-Type: application/json' "$BASE/result" >/dev/null
done
echo "agent exiting after $IDLE idle polls"
