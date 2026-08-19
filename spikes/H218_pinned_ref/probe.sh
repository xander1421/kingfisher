#!/bin/sh
# H218 — `carries_repair()` re-resolved a symbolic ref it never pinned.
#
# ROUTED TO THIS LANE BY ok-1 (H199 arm B), WHO MEASURED IT AND DID NOT FIX IT
# BECAUSE THE FILE IS MINE. This probe is the A/B they asked for: the SAME
# fixture is driven through the PRE-FIX function (pinned at 20c3e2f, the commit
# that shipped v1) and the POST-FIX function (the working tree), so "post-fix
# refuses" cannot be confused with "post-fix is dead".
#
# TWO-SIDED THROUGHOUT. Every interleaved arm has a healthy twin:
#   C1/C1b  healthy: the function still does its job on my own commit
#   C2      interleaved: PRE-FIX rewrites lane B's commit   (the defect, alive)
#   C3      interleaved: POST-FIX leaves lane B's commit alone
#   C4      ...and says WHY -- the atom it found vs the atom it repairs for
#   C5      healthy: tree, author name/email/date survive the rewrite
#   C6      healthy: the trailer lands in the TRAILER BLOCK, not merely in %B
#   C7      the primitive: `git update-ref <ref> <new> <stale>` refuses
#
# SCOPE LIMIT, STATED RATHER THAN LEFT TO BE DISCOVERED: post-fix, the
# interleaved case is refused by the IDENTITY assertion and therefore never
# reaches the compare-and-swap. So C3/C4 are evidence for the identity gate, and
# C7 is evidence for the CAS primitive; nothing here exercises the function's
# OWN swap being refused, because that needs a co-lane commit landing inside the
# score-to-swap window under the SAME atom -- which the callsign lock makes
# unreachable. The CAS is belt-and-braces and is measured as the primitive it is,
# not as a scenario this probe can stage.
#
# FALSIFIER, STATED BEFORE RUNNING: if C2 comes back `unchanged`, the fixture
# never reproduced the defect and every green arm below is vacuous -- the run is
# VOID, not a pass. C2 is asserted POSITIVE for exactly that reason.
set -e
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
V1_COMMIT=20c3e2f                       # the commit that shipped carries_repair v1
mkdir -p "$ROOT/.scratch"
D=$(mktemp -d "$ROOT/.scratch/H218.XXXXXX")
trap 'rm -rf "$D"' EXIT

git -C "$ROOT" show "$V1_COMMIT:spikes/harness/carries_repair.sh" > "$D/v1.sh"
cp "$ROOT/spikes/harness/carries_repair.sh" "$D/v2.sh"

fail=0
ck() { if [ "$2" = "$3" ]; then echo "PASS $1"; else echo "FAIL $1 (want '$3', got '$2')"; fail=$((fail+1)); fi; }

newrepo() {
  rm -rf "$D/r"; mkdir "$D/r"; cd "$D/r"
  git init -q .; git config user.email t@t; git config user.name t
  printf 'base\n' > CHANNEL.md; git add CHANNEL.md
  git commit -qm "base

Atom: AGENT-1
Reviewed-By: unreviewed"
}

# ---------------------------------------------------------------- HEALTHY ----
# One foreign line, no co-lane commit. The function MUST fire, or every
# interleaved arm below is measuring a corpse.
healthy() {                      # $1 = impl file
  newrepo
  printf 'DONE X1 ATTACKER-1 a co-lane line swept in by --only\n' >> CHANNEL.md
  git commit -q --only CHANNEL.md -m "mine

Atom: AGENT-1
Reviewed-By: unreviewed"
  H_before=$(git rev-parse HEAD)
  H_tree=$(git rev-parse HEAD^{tree})
  H_an=$(git show -s --format=%an "$H_before")
  H_ae=$(git show -s --format=%ae "$H_before")
  H_ad=$(git show -s --format=%aI "$H_before")
  ( . "$1"; carries_repair AGENT-1 "$ROOT" ) >/dev/null 2>&1
}

# ------------------------------------------------------------ INTERLEAVED ----
# Lane A commits; lane B commits before lane A's repair step runs. This is the
# eight seconds ATTACKER-1 measured and the fifty milliseconds ok-1 measured.
# NOTE, and it is H191's class caught in this file before it ran: the caller
# REDIRECTS this function's stdout to a file and never captures it with `$(…)`.
# Command substitution is a SUBSHELL, so `I_a`/`I_b` set below would have been
# set in a copy and read back as empty in the parent -- and an empty `I_b`
# compares equal to nothing, which makes C3 pass for the wrong reason.
interleaved() {                  # $1 = impl file; prints the repair's own stdout
  newrepo
  printf 'DONE X2 ATTACKER-1 second co-lane line\n' >> CHANNEL.md
  git commit -q --only CHANNEL.md -m "lane A subject

Atom: AGENT-1
Reviewed-By: unreviewed"
  I_a=$(git rev-parse HEAD)

  printf 'DONE X3 ok-1 lane B own line\n' >> CHANNEL.md
  printf 'DONE X4 ATTACKER-1 a line lane B swept in\n' >> CHANNEL.md
  git commit -q --only CHANNEL.md -m "lane B subject

Atom: ok-1
Reviewed-By: unreviewed"
  I_b=$(git rev-parse HEAD)

  ( . "$1"; carries_repair AGENT-1 "$ROOT" ) 2>/dev/null
}

# ============================================================== C1, C1b ======
healthy "$D/v2.sh"
H_trailer=$(git log -1 --format=%B | sed -n 's/^Carries: //p')
H_atom=$(git log -1 --format=%B | sed -n 's/^Atom: //p')
ck "C1 healthy: my own commit gains the trailer" \
   "$(git log -1 --format=%B | sed -n 's/^Carries: //p')" "ATTACKER-1"
ck "C1b and it is still MY commit at HEAD" \
   "$(git log -1 --format=%B | sed -n 's/^Atom: //p')" AGENT-1

# ============================================================== C5, C6 =======
ck "C5 tree sha survives the rewrite" "$(git rev-parse HEAD^{tree})" "$H_tree"
ck "C5b author name preserved"  "$(git show -s --format=%an HEAD)" "$H_an"
ck "C5c author email preserved" "$(git show -s --format=%ae HEAD)" "$H_ae"
ck "C5d author date preserved"  "$(git show -s --format=%aI HEAD)" "$H_ad"
ck "C6 the trailer is in the TRAILER BLOCK, not merely somewhere in %B" \
   "$(git log -1 --format='%(trailers:key=Carries,valueonly=true)' | tr -d '\n')" \
   "ATTACKER-1"

# ============================================================== C2 ===========
# PRE-FIX, and it must be RED-shaped: the defect has to reproduce here or the
# post-fix green means nothing.
interleaved "$D/v1.sh" >/dev/null
v1_head=$(git rev-parse HEAD)
ck "C2 PRE-FIX rewrites lane B's commit (the defect reproduces)" \
   "$( [ "$v1_head" = "$I_b" ] && echo unchanged || echo rewritten )" rewritten
ck "C2b PRE-FIX leaves lane A's own commit without the trailer it was owed" \
   "$(git show -s --format=%B "$I_a" | grep -c '^Carries:')" 0

# ============================================================== C3, C4 =======
interleaved "$D/v2.sh" > "$D/out2.txt"
out=$(cat "$D/out2.txt")
v2_head=$(git rev-parse HEAD)
ck "C3 POST-FIX leaves lane B's commit alone" \
   "$( [ "$v2_head" = "$I_b" ] && echo unchanged || echo rewritten )" unchanged
ck "C3b lane B's message is untouched too, not just its sha" \
   "$(git show -s --format=%B "$I_b" | grep -c '^Carries:')" 0
ck "C4 the refusal names the identity it asserted and the atom it found" \
   "$(printf '%s\n' "$out" | grep -c "declares Atom: ok-1; this repair is for AGENT-1")" 1
ck "C4b and it says plainly that nothing was rewritten" \
   "$(printf '%s\n' "$out" | grep -c 'Nothing was rewritten')" 1

# ============================================================== C7 ===========
# The primitive the whole fix rests on. "The function refused" could be true for
# the wrong reason -- an early return, a missing python3 -- so assert the
# compare-and-swap itself, in both directions.
newrepo
p=$(git rev-parse HEAD)
printf 'more\n' >> CHANNEL.md
git commit -q --only CHANNEL.md -m "second

Atom: AGENT-1
Reviewed-By: unreviewed"
q=$(git rev-parse HEAD)
cas_stale=$(git update-ref HEAD "$p" "$p" 2>/dev/null && echo accepted || echo refused)
cas_fresh=$(git update-ref HEAD "$p" "$q" 2>/dev/null && echo accepted || echo refused)
ck "C7 update-ref REFUSES a stale expected value"  "$cas_stale" refused
ck "C7b ...and ACCEPTS the current one, so C7 is not just a broken command" "$cas_fresh" accepted

cd "$ROOT"

# ---- OBSERVATIONS, for `run.py`'s controls ---------------------------------
# H209's lesson, one row old and mine: a control whose verdict arrives without
# the VALUES it compared is unobserved, and `certify` refuses the whole run. So
# each line below carries what was compared, not just whether it matched.
printf 'OBS C1 {"trailer_on_own_commit":"%s","atom_at_head":"%s"}\n' \
  "$H_trailer" "$H_atom"
printf 'OBS C2 {"pre_fix_head":"%s","lane_b_sha":"%s","outcome":"%s"}\n' \
  "$v1_head" "$I_b" "$( [ "$v1_head" = "$I_b" ] && echo unchanged || echo rewritten )"
printf 'OBS C3 {"post_fix_head":"%s","lane_b_sha":"%s","outcome":"%s"}\n' \
  "$v2_head" "$I_b" "$( [ "$v2_head" = "$I_b" ] && echo unchanged || echo rewritten )"
# NOT typed literals -- H201's class, ATOM-3, one day old: a control whose
# verdict is a string the author wrote cannot report the other outcome.
printf 'OBS C7 {"stale_expected_value":"%s","current_expected_value":"%s"}\n' \
  "$cas_stale" "$cas_fresh"

cat > "$HERE/result.json" <<EOF
{
  "checks_failed": $fail,
  "defect_reproduced_pre_fix": $( [ "$v1_head" = "$I_b" ] && echo false || echo true ),
  "post_fix_left_colane_commit_alone": $( [ "$v2_head" = "$I_b" ] && echo true || echo false ),
  "post_fix_refused_naming_the_foreign_atom": $(grep -q "declares Atom: ok-1; this repair is for AGENT-1" "$D/out2.txt" && echo true || echo false),
  "healthy_case_still_fires": $( [ -n "$H_trailer" ] && echo true || echo false ),
  "v1_commit": "$V1_COMMIT"
}
EOF
echo "checks failed: $fail"
[ "$fail" -eq 0 ] || exit 1
