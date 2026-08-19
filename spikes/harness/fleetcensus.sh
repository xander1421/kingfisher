#!/bin/sh
# fleetcensus.sh — who has WORKED vs who is DECLARED, and the difference.
#
# WHY (H170). Quorum was being computed over the DECLARED set (roster.txt), and
# a count over a declared set cannot detect a member that was never declared.
# `bringup.sh` reported "quorum 5/5" while six callsigns with 101 DONE lines
# between them were invisible — GROK-LOCAL alone has more than any Claude lane.
# Same family as allocid.sh's H57 bootstrap: an allocator whose free list reads
# fewer sources than the namespace lives in.
#
# AND THE INSTRUMENT THAT FOUND IT HAD THE DEFECT TOO. My first census matched
# signers with `[A-Z][A-Za-z0-9_-]+`, which CANNOT EXPRESS A LOWERCASE CALLSIGN,
# so `ok-1` — rostered, live, 18 DONE lines — was invisible to the tool judging
# standing, and it was the one lane whose standing had been contested. A30:
# test the property, not the vocabulary.
#
# SO THE MATCHER IS DERIVED, NEVER TYPED. roster.txt is the character-set
# authority (AGENT-1). A hand-written regex encodes what its author expected
# callsigns to look like; reading the roster encodes what they ARE. That is the
# whole fix, and it is why this is a script and not a rule in a document.
#
# It also catches the near-miss that started this: the roster carries `GEMINI-1`
# while 22 DONE lines are signed `GEMINI`. Those are different strings, and a
# census keyed on either one alone reports the other as absent.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"

# --selfcheck — AND IT PLANTS, because a matcher that finds NOTHING satisfies
# every "no false positives" test ever written. That is not hypothetical here:
# v1 matched `[A-Z]...`, found no lowercase callsign, and would have passed any
# check that only asked whether its output was wrong. It was not wrong. It was
# EMPTY, and empty read as clean. (AGENT-1: "F1 is worthless without C1".
# Third lane to tell me this after ATTACKER-1 on the determinism gate and ok-1
# on allocid.sh — the negative arm is what converts a check into evidence.)
if [ "${1:-}" = "--selfcheck" ]; then
  d=$(mktemp -d "$PWD/.fleetcensus_sc.XXXXXX") || exit 2   # inside the workspace: §10
  trap 'rm -rf "$d"' EXIT
  printf 'PLANTED-lower-1
PLANTED-UPPER
' > "$d/roster.txt"
  # THE PLANTED LOWERCASE NAME MUST BEGIN LOWERCASE. v1 of this fixture planted
  # `PLANTED-lower-1`, which an uppercase-only matcher still finds, so the
  # control passed against a deliberately broken copy — a negative arm that
  # could not fire, inside the block written to stop exactly that.
  # two planted callsigns the old matcher could not both see, plus two prose
  # fields that must NOT be mistaken for callsigns
  { echo 'DONE X1 planted-lower-1 body'; echo 'DONE X2 planted-lower-1 body'
    echo 'DONE X3 PLANTED-UPPER body';   echo 'DONE X4 PLANTED-UPPER body'
    echo 'DONE X5 (auditing session, CEO-authorised) body'
    echo 'DONE X6 — body'; } > "$d/CHANNEL.md"
  got=$(cd "$d" && awk '/^DONE /{print $3}' CHANNEL.md | grep -xE '[A-Za-z][A-Za-z0-9_-]*' | sort -u | tr '
' ' ')
  fail=0
  case "$got" in *planted-lower-1*) echo "  ok   C1 planted LOWERCASE callsign is found";; *)
      echo "  BAD  C1 planted lowercase callsign MISSING — the v1 defect is back"; fail=1;; esac
  case "$got" in *PLANTED-UPPER*)   echo "  ok   C1 planted uppercase callsign is found";; *)
      echo "  BAD  C1 planted uppercase callsign MISSING"; fail=1;; esac
  case "$got" in *auditing*|*"—"*)  echo "  BAD  F1 PROSE became a callsign — the instrument manufactures lanes"; fail=1;; *)
      echo "  ok   F1 prose callsign-fields are not promoted to callsigns";; esac
  [ "$fail" = 0 ] && echo "fleetcensus selfcheck: a planted callsign of EITHER case reaches the census, and prose does not"                   || echo "fleetcensus selfcheck: FAILED"
  exit "$fail"
fi

declared=$(sed 's/#.*//' roster.txt | awk 'NF{print $1}')
# THE INSTRUMENT MANUFACTURED LANES (ATOM-3). An unanchored match over field 3
# yields `(auditing` and `—` from DONE lines whose callsign field is PROSE — five
# of them, and four are MY OWN, signed "(auditing session, CEO-authorised)". So
# this census invented callsigns out of its own author's signature. The field is
# now anchored WHOLE: a callsign is the entire token or it is not a callsign.
signed=$(awk '/^DONE /{print $3}' CHANNEL.md \
         | grep -xE '[A-Za-z][A-Za-z0-9_-]*' | sort -u)

# A CENSUS OVER AN APPEND-ONLY FILE IS STALE THE MOMENT IT RETURNS (ATOM-3, who
# has paid for it four times). Two honest censuses minutes apart disagreed by +1
# on four callsigns — not an error in either, CHANNEL.md simply grew. So the read
# point is printed with the result and every count below is as-of that line.
printf 'census at CHANNEL.md line %s\n\n' "$(wc -l < CHANNEL.md | tr -d ' ')"
printf '%-20s %5s %5s %5s %5s %5s\n' CALLSIGN DONE ROST BRIEF LOCK STATE
for cs in $(printf '%s\n%s\n' "$declared" "$signed" | sort -u); do
  n=$(grep -cE "^DONE [A-Za-z0-9_.-]+ $cs( |\$)" CHANNEL.md)
  r=$(printf '%s\n' "$declared" | grep -qx "$cs" && echo yes || echo NO)
  b=$([ -f "prompts/$cs.md" ] && echo yes || echo NO)
  # LOCK PRESENCE IS NOT LIVENESS, and this tool shipped with that defect in it.
  # `.loop_lock.GEMINI-1` existed holding pid 95878, dead — the launcher had
  # refused on a missing vendor credential and exited — and the first version of
  # this census reported CONSTITUTED off the file alone. Fifth instance today of
  # a check reading presence as health, inside the tool written to catch that
  # class. The pid is now probed.
  lp=$(cat ".loop_lock.$cs" 2>/dev/null)
  if [ -n "$lp" ] && kill -0 "$lp" 2>/dev/null; then k=yes
  elif [ -n "$lp" ]; then k=stale
  else k=NO; fi
  # DECLARED-DARK is the state the old census could not represent: work in the
  # record, no roster line. It is not "unknown" — it is measured absence.
  if   [ "$r" = yes ] && [ "$k" = yes ]; then st=CONSTITUTED
  elif [ "$r" = yes ] && [ "$k" = stale ]; then st=DECLARED-STALE
  elif [ "$r" = yes ];                   then st=DECLARED-DOWN
  elif [ "$n" -gt 0 ];                   then st=DECLARED-DARK
  else                                        st=UNKNOWN; fi
  printf '%-20s %5s %5s %5s %5s %5s\n' "$cs" "$n" "$r" "$b" "$k" "$st"
done

echo
dark=$(for cs in $signed; do printf '%s\n' "$declared" | grep -qx "$cs" || echo "$cs"; done)

# --- REFUSAL, and it is scoped so it can fire ------------------------------
# ok-1 asked twice for this to refuse rather than report, and they are right
# that a red exit is what converts prose into a gate. But refusing on the CURRENT
# dark set would fire on every run forever, because those 7 callsigns are the
# NORMAL state until the operator adjudicates them — and githygiene's own comment
# is the rule: "a checker that fires on known-accepted items every run is a
# checker everyone learns to ignore" (H14). A gate that is always red is not a
# gate.
#
# So the accumulated set is PINNED BY NAME and the gate scopes to NEW darkness —
# AGENT-2's idscope v4 pattern, which pins 13 ids and gates only on a DONE line
# this tree introduces. It refuses the lane that lets an 8th callsign go dark,
# never the next committer (H72). Removing a name from PINNED is a deliberate
# act that shows in a diff; that is the point.
PINNED='GROK-LOCAL GROK-2 GEMINI AGENT-COORDINATOR BUILDER-1 CLIENT-3 AGENT-2-LANE'
newdark=''
for cs in $dark; do
  case " $PINNED " in *" $cs "*) ;; *) newdark="$newdark $cs" ;; esac
done
nd=$(printf '%s' "$dark" | grep -c . )
work=0; for cs in $dark; do work=$((work + $(grep -cE "^DONE [A-Za-z0-9_.-]+ $cs( |\$)" CHANNEL.md))); done
printf 'declared %s · signed %s · DECLARED-DARK %s callsign(s) carrying %s DONE line(s)\n' \
  "$(printf '%s' "$declared" | grep -c .)" "$(printf '%s' "$signed" | grep -c .)" "$nd" "$work"
[ "$nd" -gt 0 ] && echo "quorum over the roster is not quorum over the fleet — see H170"
if [ -n "$(printf '%s' "$newdark" | tr -d ' ')" ]; then
  echo
  echo "REFUSE: callsign(s) have signed work and are in NO roster:$newdark"
  echo "        Not in the pinned set, so this is NEW — a lane began rowing under a"
  echo "        name nobody declared, which is how ok-1 spent 20 minutes unaddressable"
  echo "        and how GROK-LOCAL reached 67 DONE lines off-roster. Declare it in"
  echo "        roster.txt with a checkable record (a commit, a CHANNEL line, a"
  echo "        MISSION_LOOP section — not a quotation), or add it to PINNED here"
  echo "        deliberately. Allocation is §12/class H and this gate decides nothing."
  exit 1
fi
exit 0
