#!/bin/bash
# S30 — build fuelrun in three optimisation variants for both targets.
#
# Rule of this duel (C5): a speedup only counts if the output hash does not
# move. Every variant is checked against the S15 baseline digests:
#   job_terminating  raw_hash c2940ab5fcd507681ff8d3c32f607f236819915a38cda9a5f4f863c681261ab3
#   job_kb           raw_hash 4937b20a7490523b5b2254926035f9c6286885d9bc9fb6185b357526206ac258
#
# V0  stock release profile as S15 shipped it (opt-level 3, strip = symbols)
# V1  + fat LTO, codegen-units = 1, panic = abort
# V2  + target-cpu: oryon-1 on the phone (Snapdragon 8 Elite), apple-m4 on host
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
SRC=$HERE/../S15_android_device/fuelrun
NDK=$HOME/Library/Android/sdk/ndk/28.2.13676358
OUT=$HERE/bin
mkdir -p "$OUT"

build () {  # build <variant> <target> <extra-rustflags> <profile-args...>
  local v=$1 tgt=$2 flags=$3; shift 3
  echo "== $v / $tgt =="
  ( cd "$SRC"
    if [ "$tgt" = android ]; then
      ANDROID_NDK_HOME=$NDK RUSTFLAGS="$flags" \
        cargo ndk -t arm64-v8a --platform 28 build --release "$@" >/dev/null
      cp target/aarch64-linux-android/release/fuelrun "$OUT/fuelrun.$v.android"
    else
      RUSTFLAGS="$flags" cargo build --release "$@" >/dev/null
      cp target/release/fuelrun "$OUT/fuelrun.$v.host"
    fi )
}

# V1/V2 need profile overrides; cargo takes them from the environment so the
# checked-in Cargo.toml stays untouched.
export CARGO_PROFILE_RELEASE_LTO=false
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16
build v0 host    ""
build v0 android ""

export CARGO_PROFILE_RELEASE_LTO=fat
export CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1
export CARGO_PROFILE_RELEASE_PANIC=abort
build v1 host    ""
build v1 android ""

build v2 host    "-C target-cpu=apple-m4"
build v2 android "-C target-cpu=oryon-1"

ls -l "$OUT" | awk 'NR>1 {printf "%-28s %9d B\n", $9, $5}'
