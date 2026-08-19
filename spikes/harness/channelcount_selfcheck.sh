# channelcount_selfcheck.sh v1 (H244, ATOM-3) — sourced by channelcount.sh --selfcheck.
#
# SIX ARMS IN FOUR SHAPES, because error 41 shipped a two-sided control whose
# both sides were the SAME shape and it passed over 3,145 false hits. A control
# that only ever asks "does it count?" cannot tell a correct counter from one
# that counts everything.
#
#   FLAG      1  a truncated file: anchored count holds while the file count collapses
#   FLAG      2  a lane whose every line was truncated is still counted (GROK-LOCAL shape)
#   NOT-FLAG  3  a file that only ever grew: anchored == file count, no inflation
#   NOT-FLAG  4  `DONE-PARTIAL` is not a DONE (§2: PARTIAL is not a verdict)
#   REFUSE    5  a rev that does not resolve REFUSES; it does not report 0
#   REFUSE    6  a CHANNEL.md git has never seen REFUSES; it does not report 0
#
# Arms 5 and 6 are the ones that matter most for this lane: five separate
# truncated-instrument defects this span were each read as a healthy small
# number. **If a check's healthy answer is a zero, it cannot tell you the
# instrument ran.**
#
# The fixture lives under .scratch/ (gitignored, §10-sanctioned) and NEVER
# inside spikes/ — H223 is this lane's own row about a materialised tree placed
# where the instruments walk.
fail=0
ok()  { echo "  ok   $1"; }
bad() { echo "  BAD  $1"; fail=1; }

T="$(pwd)/.scratch/channelcount_selfcheck.$$"
rm -rf "$T"; mkdir -p "$T" || { echo "cannot create fixture"; exit 3; }
trap 'rm -rf "$T"' EXIT INT TERM

( cd "$T" && git init -q . && git config user.email a@b && git config user.name a ) || exit 3

wr() { printf '%s\n' "$2" >> "$T/CHANNEL.md"; ( cd "$T" && git add CHANNEL.md && git commit -qm "$1" ); }

wr c1 'DONE A1 GROK-LOCAL'
wr c2 'DONE A2 GROK-LOCAL'
wr c3 'DONE A3 AGENT-1'
wr c4 'DONE-PARTIAL A4 AGENT-1'
GREW=$(KF_ROOT="$T" KF_REV=HEAD sh "$MOD" total)
FILE_GREW=$(grep -c '^DONE ' "$T/CHANNEL.md")

# --- ARM 3 (NOT-FLAG): a file that only grew must agree with itself -----------
if [ "$GREW" = "$FILE_GREW" ] && [ "$GREW" = 3 ]; then
  ok "a file that only grew: anchored ($GREW) == file ($FILE_GREW), no inflation"
else
  bad "grew-only fixture disagrees: anchored=$GREW file=$FILE_GREW (expected 3/3)"
fi

# --- ARM 4 (NOT-FLAG): DONE-PARTIAL is not a DONE ----------------------------
if [ "$GREW" = 3 ]; then
  ok "DONE-PARTIAL is not counted (§14.2's own '^DONE' would have said 4)"
else
  bad "DONE-PARTIAL miscounted: got $GREW, expected 3"
fi

# --- now truncate, exactly as 228fc46 did ------------------------------------
printf '%s\n' 'DONE A3 AGENT-1' > "$T/CHANNEL.md"
( cd "$T" && git add CHANNEL.md && git commit -qm 'rotated' )
CUT=$(KF_ROOT="$T" KF_REV=HEAD sh "$MOD" total)
FILE_CUT=$(grep -c '^DONE ' "$T/CHANNEL.md")

# --- ARM 1 (FLAG): the anchored count survives the truncation ----------------
if [ "$CUT" = "$GREW" ] && [ "$FILE_CUT" -lt "$GREW" ]; then
  ok "truncation: anchored holds at $CUT while the file count falls to $FILE_CUT"
else
  bad "truncation arm did not reproduce the defect: anchored $GREW->$CUT, file $FILE_GREW->$FILE_CUT"
fi

# --- ARM 2 (FLAG): a wholly-truncated lane is still counted ------------------
GL=$(KF_ROOT="$T" KF_REV=HEAD sh "$MOD" lane GROK-LOCAL)
GL_FILE=$(grep -cE '^DONE [^ ]+ GROK-LOCAL( |$)' "$T/CHANNEL.md")
if [ "$GL" = 2 ] && [ "$GL_FILE" = 0 ]; then
  ok "a lane truncated out of the file entirely still counts $GL (the file says $GL_FILE)"
else
  bad "wholly-truncated lane: anchored=$GL file=$GL_FILE (expected 2 and 0)"
fi

# --- ARM 5 (REFUSE): an unresolvable rev must refuse, not answer 0 -----------
out=$(KF_ROOT="$T" KF_REV=deadbeefdeadbeef sh "$MOD" total 2>&1); rc=$?
if [ "$rc" = 3 ] && [ "$out" != 0 ]; then
  ok "an unresolvable rev REFUSES (rc=$rc), it does not report 0"
else
  bad "bad rev gave rc=$rc out='$out' -- a dead instrument reported a count"
fi

# --- ARM 6 (REFUSE): a file git has never seen must refuse -------------------
out=$(KF_ROOT="$T" KF_CHANNEL=NOSUCH.md sh "$MOD" total 2>&1); rc=$?
if [ "$rc" = 3 ]; then
  ok "a CHANNEL git has never seen REFUSES (rc=$rc), it does not report 0 big cycles"
else
  bad "unknown path gave rc=$rc out='$out' -- absence read as zero work"
fi

# --- the check must be able to FAIL: kill the anchor and arm 1 must go red ---
# MUTATION, run last and on a COPY -- error 47 was this lane mutating a shared
# harness module in place while four lanes imported it.
# The mutant must be a FAITHFUL unanchored counter, not merely a broken pipe.
# A first version substituted `cat "$CHANNEL"`, which drops the `+` diff prefix,
# so the mutant answered 0 for the wrong reason -- it would have gone red even
# if the anchor were irrelevant. This one reads the SAME lines the file holds
# now and prefixes them exactly as a diff would, so the ONLY difference from
# the real module is where the lines come from.
sed 's|git log -p --format=.. "\$REV" -- "\$CHANNEL"|sed "s/^/+/" "$CHANNEL"|' "$MOD" > "$T/mutant.sh"
mut=$(KF_ROOT="$T" sh "$T/mutant.sh" total 2>&1 | tail -1)
if [ "$mut" = "$FILE_CUT" ] && [ "$mut" != "$CUT" ]; then
  ok "mutation control: a faithful unanchored counter answers $mut (= the file), not $CUT"
else
  bad "mutation control: unanchored form answered '$mut'; file=$FILE_CUT anchored=$CUT -- arm 1 proves nothing"
fi

[ "$fail" = 0 ] && echo "selfcheck: the count is anchored to history, not to the file's current bytes"
exit "$fail"
