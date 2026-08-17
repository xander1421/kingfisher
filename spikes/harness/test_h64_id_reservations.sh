#!/usr/bin/env bash
# test_h64_id_reservations.sh — H64, ATOM-3, 2026-08-17.
#
# THE DEFECT. Three harness modules carry SYNTHETIC ids inside their selfcheck
# strings — `H91`, `H99` in `idscope.py`, `S96`–`S99` in `journalcheck.py` and
# `refcheck.py` — reserved by convention and by nothing else. `allocid.sh`
# deliberately does not scan code (H57's attack measured why: scanning code
# reserves `Q2`, `Q3`, `B6`, `B16`, which are variable names and grep flags), so
# the allocator CANNOT SEE a fixture. When real allocation reaches H91,
# `refcheck` check 5 and `idscope` read a selfcheck string as a queue row.
#
# WHAT THE ROW GOT WRONG, MEASURED 2026-08-17 16:5x. It says the fixtures sit
# high "so they would not collide", distance "34 allocations for H". The highest
# real CLAIM was H68 — and `.ids/H91` and `.ids/H99` ALREADY EXISTED. Nothing had
# handed out 91 ids; they were SEEDED FROM PROSE, because `allocid.sh` v2 seeds
# from every tracked `*.md` and the H64 row itself names all six. **The row
# documenting the hazard reserved the ids it warns about.**
#
# SO THE COLLISION IS ALREADY PREVENTED, BY NOTHING ANYONE DESIGNED — and an
# accident is not a mechanism. These six are the ONLY ids in the pool with no
# queue row and no claim, which makes them exactly what a tidy-up of `.ids/`
# deletes first, and deleting one silently restores the collision with no error
# anywhere. That is what this check exists to make loud. `.ids/README` says the
# same thing at the place the deletion would happen; this is the part that fails.
#
# NOT FIXED BY EDITING THE CARRIERS: `journalcheck.py` and `refcheck.py` are
# ok-1's, `idscope.py` is ATTACKER-1's, `allocid.sh` is AGENT-1's and was
# rewritten the same hour. The remedy had to work without touching any of them,
# and it does: the reservation lives in the allocator's OWN namespace, which is
# the one thing the allocator is guaranteed to consult.
#
# CHECKED AND REJECTED, recorded so it is not re-tried: writing the reason INTO
# `.ids/H91` does not survive. `allocid.sh:118` is `: > "$IDS/$i"` and truncates
# every seeded id file on every invocation, so the content is erased by the next
# allocation. Hence a README beside them rather than content inside them.
#
# run: bash spikes/harness/test_h64_id_reservations.sh
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
ROOT=$(pwd)
IDS="$ROOT/.ids"

pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  ok   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL %s\n' "$1"; }

# DERIVED FROM THE MODULES, NOT TYPED HERE. A hard-coded list would go stale the
# moment a module adds a fixture, and would then report green over exactly the
# gap it exists to close — the shape H30 names (a missing input degrading a
# mechanism to a no-op that still reports success).
CARRIERS="spikes/harness/idscope.py spikes/harness/journalcheck.py spikes/harness/refcheck.py"
FIXTURES=$(grep -ohE '\b[HS]9[0-9]\b' $CARRIERS 2>/dev/null | sort -u)

echo "H64 · fixture ids must be unallocatable, and the reservation must be durable"
echo

# ---- C1 . the scan found something, or every check below is vacuous ---------
# A29: a probe that cannot show it reached its target has produced no evidence.
n=$(printf '%s\n' "$FIXTURES" | grep -c '[HS]')
if [ "$n" -ge 4 ]; then
  ok "C1 found $n fixture id(s) in the three carriers: $(echo $FIXTURES | tr '\n' ' ')"
else
  bad "C1 scan found only $n fixture ids — the pattern no longer matches the carriers, so C2-C4 prove nothing"
fi

# ---- C2 . every fixture is RESERVED in the allocator's own namespace --------
for f in $FIXTURES; do
  [ -e "$IDS/$f" ] && ok "C2 $f is reserved (.ids/$f exists, so alloc's noclobber refuses it)" \
                   || bad "C2 $f IS ALLOCATABLE — .ids/$f is missing; the next $f allocation collides with a selfcheck string"
done

# ---- C3 . and the reservation survives a fresh clone ------------------------
# An untracked reservation is no reservation: it protects this working tree and
# nothing else, which is H60's class (work on disk that is not in the repo).
for f in $FIXTURES; do
  git -C "$ROOT" ls-files --error-unmatch ".ids/$f" >/dev/null 2>&1 \
    && ok "C3 $f reservation is tracked (survives a clone)" \
    || bad "C3 .ids/$f is UNTRACKED — the reservation does not exist in a fresh clone"
done

# ---- C4 . the README that stops the deletion is present and names them ------
# The check is what fails; the README is what prevents. Both, because nobody
# runs a check before deleting a file that looks like junk.
if [ ! -f "$IDS/README" ]; then
  bad "C4 .ids/README is gone — nothing at the site of the deletion says these files are reserved"
else
  miss=""
  for f in $FIXTURES; do grep -q "\b$f\b" "$IDS/README" || miss="$miss $f"; done
  [ -z "$miss" ] && ok "C4 .ids/README names every fixture id it protects" \
                 || bad "C4 .ids/README does not name:$miss — a reader deleting those sees no warning"
fi

# ---- C5 . TWO-SIDED: the mechanism must actually be able to refuse ----------
# Without this, C2 is a statement about files existing rather than about the
# allocator honouring them. Runs alloc's exact primitive on a scratch pool.
sc="$ROOT/spikes/harness/.h64.$$"
mkdir -p "$sc"
: > "$sc/TAKEN"
if ( set -C; : > "$sc/TAKEN" ) 2>/dev/null; then
  bad "C5 noclobber did NOT refuse an existing id file — reservation cannot work on this platform"
else
  if ( set -C; : > "$sc/FREE" ) 2>/dev/null; then
    ok "C5 the primitive refuses a taken id and accepts a free one (so C2 means something)"
  else
    bad "C5 noclobber refused a FREE id — the primitive is broken, C2's reading is unsafe"
  fi
fi
rm -rf "$sc"

echo
echo "-------------------------------------------------------------"
printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
