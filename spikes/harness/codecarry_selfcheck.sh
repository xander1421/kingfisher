# codecarry_selfcheck.sh v1 (H257, ATOM-3) — sourced by codecarry.sh --selfcheck.
#
# FOUR SHAPES, not four verdicts of one shape (error 41):
#   FLAG      1  a foreign-named version block, no Carries -> named
#   NOT-FLAG  2  the same block WITH a correct Carries: -> silent
#   NOT-FLAG  3  a lane adding its OWN version block -> silent
#   NOT-FLAG  4  a foreign block present only as CONTEXT (untouched) -> silent
#   MEASURE   5  the v0 pattern re-run beside this one: the repair is measured,
#                not asserted. v0 matched prose (`FIRED on v0 (AGENT-2 named...`)
#                and returned 33% false positives on the real history.
#   REFUSE    6  a scan that walks no commits refuses rather than printing 0 hits
fail=0
ok()  { echo "  ok   $1"; }
bad() { echo "  BAD  $1"; fail=1; }

T="$(pwd)/.scratch/codecarry_selfcheck.$$"
rm -rf "$T"; mkdir -p "$T/spikes/harness" || { echo "cannot create fixture"; exit 3; }
trap 'rm -rf "$T"' EXIT INT TERM
( cd "$T" && git init -q . && git config user.email a@b && git config user.name a ) || exit 3

commit() {  # $1 subject, $2 Atom, $3 Carries (may be empty)
  # THE BLANK LINE IS LOad-BEARING AND ITS ABSENCE COST THREE ARMS. Without a
  # blank line after the subject git parses NO trailers at all -- `Atom` and
  # `Carries` both came back EMPTY, so the arms were being decided by empty
  # strings rather than by the check. Same class as the H244 fixture that
  # measured the real repo and went green. The fixture asserts its own trailers
  # below, because a fixture that cannot be shown to work is not a control.
  # Built in a variable, not by interpolating a command substitution next to
  # the following line: `$( )` STRIPS the trailing newline, so `Carries: X` and
  # `Atom: Y` landed concatenated on ONE line and git parsed neither.
  msg="$1

"
  [ -n "$3" ] && msg="${msg}Carries: $3
"
  msg="${msg}Atom: $2"
  ( cd "$T" && git add -A && git commit -q -m "$msg" )
  got=$( cd "$T" && git log -1 --format='%(trailers:key=Atom,valueonly,separator=%x20)' | tr -d ' ' )
  [ "$got" = "$2" ] || { echo "  BAD  fixture commit '$1' parsed Atom as '$got', not '$2'"; fail=1; }
}
F="$T/spikes/harness/thing.sh"

printf '# thing\n' > "$F";                                    commit base ok-1 ''
printf '# v2 (H900, ATOM-3, 2026-08-19). foreign, undeclared\nreal_code=1\n' >> "$F"; commit cap1 ok-1 ''
printf '# v3 (H901, AGENT-1, 2026-08-19). foreign, declared\n' >> "$F";              commit cap2 ok-1 'AGENT-1'
printf '# v4 (H902, ok-1, 2026-08-19). own block\n' >> "$F";                         commit own  ok-1 ''
printf 'unrelated=2\n' >> "$F";                               commit ctx  ok-1 ''

OUT=$(KF_ROOT="$T" sh "$MOD" 20 2>&1)
HITS=$(printf '%s\n' "$OUT" | grep -c 'names:')

# 1 FLAG
if printf '%s\n' "$OUT" | grep -q 'names:ATOM-3'; then
  ok "an undeclared foreign version block is NAMED"
else bad "the undeclared foreign block was not named -- output: $OUT"; fi
# 2 NOT-FLAG (declared)
if printf '%s\n' "$OUT" | grep -q 'names:AGENT-1'; then
  bad "a CORRECTLY DECLARED Carries: was still reported -- the check punishes compliance"
else ok "a correctly declared Carries: is silent"; fi
# 3 NOT-FLAG (own)
if printf '%s\n' "$OUT" | grep -q 'names:ok-1'; then
  bad "a lane's OWN version block was reported as foreign"
else ok "a lane's own version block is silent"; fi
# 4 NOT-FLAG (context) — the last commit touches the file but adds no block
if [ "$HITS" = 1 ]; then
  ok "a foreign block surviving as diff CONTEXT is not re-reported ($HITS hit total)"
else bad "expected exactly 1 hit across 5 commits, got $HITS -- context is being counted"; fi

# 5 MEASURE the repair: the v0 pattern must ALSO match a prose line, this one must not.
PROSE='+#    FIRED on v0 (AGENT-2 named as carried by AGENT-2-INT, which is one'
v0=$(printf '%s\n' "$PROSE" | grep -cE "v[0-9]+ \([^)]*(AGENT-2)")
v1=$(printf '%s\n' "$PROSE" | grep -cE "^\+#[[:space:]]*v[0-9]+ \(H[0-9]+, (AGENT-2),")
if [ "$v0" = 1 ] && [ "$v1" = 0 ]; then
  ok "the repair is measured: v0 matches the real prose false positive, v1 does not"
else bad "repair unmeasured: v0=$v0 v1=$v1 on the line that produced the 33% rate"; fi

# 6 REFUSE
out=$(KF_ROOT="$T" sh "$MOD" 0 2>&1); rc=$?
if [ "$rc" = 3 ]; then ok "a scan walking no commits REFUSES rather than printing 0 hits"
else bad "0-commit scan gave rc=$rc out='$out' -- a dead scan reported a clean tree"; fi

[ "$fail" = 0 ] && echo "selfcheck: shared-code capture is detected, compliance is not punished, and the repair is measured"
exit "$fail"
