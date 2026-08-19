#!/usr/bin/env bash
# H232 — the callsign lock is written once and never read again, so it cannot
# exclude anything after t=0. ok-1, 2026-08-19.
#
# SEAM (H219's lesson: a probe with no seam measures whatever is on disk and
# prints it under whichever label the caller believed). KF_TEST_LAUNCHER selects
# the launcher under test; the banner prints the version of WHATEVER it was
# handed, read as the highest `# vN` in the file rather than the last one, because
# run_loop.sh's rationale blocks are in file order and not in version order.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LAUNCHER="${KF_TEST_LAUNCHER:-$ROOT/run_loop.sh}"
SB="$ROOT/.scratch/h232_sb.$$"
pass=0; fail=0
ck() { if [ "$2" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1";
       else fail=$((fail+1)); printf '  FAIL  %s (want %s, got %s)\n' "$1" "$3" "$2"; fi; }

ver=$(grep -oE '^# v[0-9]+' "$LAUNCHER" | grep -oE '[0-9]+' | sort -n | tail -1)
echo "H232 probe — launcher under test: $LAUNCHER (v${ver:-?})"

# ---------------------------------------------------------------- A1 · STRUCTURE
# Does any read of $LOCK occur INSIDE the turn loop? Extracted mechanically: the
# loop is the region between the top-level `while` and the top-level `done`
# (column 0, so a nested loop cannot be mistaken for it). Reading this by eye is
# what §12.4 forbids, and a grep over the whole file cannot answer it -- the
# acquire at the top reads $LOCK three times and would score as "covered".
read -r lo hi <<EOF
$(awk '/^while /{w=NR} /^done$/{if(w && !d){d=NR}} END{print w, d}' "$LAUNCHER")
EOF
inside=$(awk -v lo="$lo" -v hi="$hi" 'NR>lo && NR<hi && /\$LOCK|\.loop_lock/ && !/^ *#/ {n++} END{print n+0}' "$LAUNCHER")
echo "A1 · turn loop is lines ${lo}-${hi}; \$LOCK reads inside it: ${inside}"

# ------------------------------------------------------------- A2 · BEHAVIOUR
# A launcher that has LOST the lock: does it keep producing turns?
mkdir -p "$SB/bin" "$SB/prompts" "$SB/fake"
# +x IS LOAD-BEARING: the launcher detaches with `nohup "$0"`, which EXECs the
# copy, so a 644 copy dies at exec and every arm below reports a launcher that
# "produced no turns" -- measured, and it is why the precondition check exists.
cp "$LAUNCHER" "$SB/run_loop.sh"; chmod +x "$SB/run_loop.sh"
printf '# L232 — scratch brief for the H232 probe\n' > "$SB/prompts/L232.md"
cat > "$SB/bin/claude" <<'STUB'
#!/usr/bin/env bash
echo turn >> turns.log
exit 0
STUB
chmod +x "$SB/bin/claude"
# A process that looks like a launcher to `ps` without being one -- the same
# fixture test_loop_gate.sh uses, including the trailing `exit 0`: bash EXECs the
# last simple command, so a fixture ending in `sleep` reports `sleep 30` to ps and
# resembles nothing.
printf '#!/usr/bin/env bash\nsleep 30\nexit 0\n' > "$SB/fake/run_loop.sh"

cd "$SB" || exit 1
bash fake/run_loop.sh & thief=$!
ck "fixture thief is indistinguishable from a launcher to ps" \
   "$(ps -p "$thief" -o command= 2>/dev/null | grep -c 'run_loop\.sh')" "1"

: > turns.log        # created here so the poll below cannot report a missing file
PATH="$SB/bin:$PATH" CALLSIGN=L232 MAX_TURN=10 BACKOFF_STEP=1 \
  bash ./run_loop.sh >launch.out 2>&1
n=200; while [ "$n" -gt 0 ] && [ "$(wc -l < turns.log)" -lt 2 ]; do sleep 0.1; n=$((n-1)); done
ck "the launcher under test runs turns at all" \
   "$([ "$(wc -l < turns.log)" -ge 2 ] && echo yes || echo no)" "yes"
held=$(cat .loop_lock.L232 2>/dev/null)
ck "  and it recorded itself as the holder" \
   "$([ -n "$held" ] && ps -p "$held" -o command= 2>/dev/null | grep -c 'run_loop\.sh' || echo 0)" "1"

echo "$thief" > .loop_lock.L232          # the steal: another live launcher now holds it
t1=$(wc -l < turns.log)
sleep 8
t2=$(wc -l < turns.log)
echo "A2 · turns before steal ${t1}, after 8s ${t2}; lock now ${thief} (the thief)"
ck "a launcher that has lost the lock stops producing turns" \
   "$([ "$t2" -eq "$t1" ] && echo stopped || echo running)" "stopped"
ck "  and says which pid holds the callsign now" \
   "$(grep -c "$thief" loop_L232.log launch.out 2>/dev/null | awk -F: '{s+=$2} END{print (s>0)?1:0}')" "1"

pkill -f 'You are L232\.' 2>/dev/null
[ -n "${held:-}" ] && kill "$held" 2>/dev/null
kill "$thief" 2>/dev/null

# ------------------------------------------------------- A2b · THE OTHER SIDE
# An ABSENT lock must be RE-ACQUIRED, never fatal. bringup.sh:819 deletes a lock
# it has classified stale, a probe can leave one behind, and `rm` is one keystroke
# from `rm -f .loop_lock.*` -- a retire-on-any-mismatch would hand any of them the
# power to kill a healthy lane, which is the defect this row removes, inverted.
: > turns_b.log
cat > bin/claude <<'STUB'
#!/usr/bin/env bash
echo turn >> turns_b.log
exit 0
STUB
chmod +x bin/claude
printf '# L233 — scratch brief\n' > prompts/L233.md
PATH="$SB/bin:$PATH" CALLSIGN=L233 MAX_TURN=10 BACKOFF_STEP=1 \
  bash ./run_loop.sh >launch_b.out 2>&1
n=200; while [ "$n" -gt 0 ] && [ "$(wc -l < turns_b.log)" -lt 2 ]; do sleep 0.1; n=$((n-1)); done
ck "the L233 launcher is producing turns before its lock is touched" \
   "$([ "$(wc -l < turns_b.log)" -ge 2 ] && echo yes || echo no)" "yes"
rm -f .loop_lock.L233                     # the third-party delete
b1=$(wc -l < turns_b.log); sleep 6; b2=$(wc -l < turns_b.log)
ck "a lane whose lock was DELETED keeps running" \
   "$([ "$b2" -gt "$b1" ] && echo running || echo stopped)" "running"
ck "  and takes its own lock back" \
   "$(_p=$(cat .loop_lock.L233 2>/dev/null); [ -n "$_p" ] && ps -p "$_p" -o command= 2>/dev/null | grep -c 'run_loop\.sh' || echo 0)" "1"

# ------------------------------------------------------ A2c · pid REUSE GUARD
# LIVENESS IS pid + COMMAND. ~1300 pids/minute through a 99999 space wraps in
# about 75 minutes here, so a lock naming a REUSED pid that belongs to something
# other than a launcher must NOT retire the lane -- `kill -0` alone reports HELD
# for it, and the acquire path already refuses to make that mistake.
sleep 30 & impostor=$!
echo "$impostor" > .loop_lock.L233
c1=$(wc -l < turns_b.log); sleep 6; c2=$(wc -l < turns_b.log)
ck "a lock naming a live NON-launcher does not retire the lane" \
   "$([ "$c2" -gt "$c1" ] && echo running || echo stopped)" "running"
kill "$impostor" 2>/dev/null
pkill -f 'You are L233\.' 2>/dev/null
_l233=$(cat .loop_lock.L233 2>/dev/null); [ -n "$_l233" ] && kill "$_l233" 2>/dev/null
cd "$ROOT" || exit 1
rm -rf "$SB"

# --------------------------------------------------------------- A3 · THE LIVE
# One row per callsign: live launcher ROOTS (ppid 1) against the recorded holder.
echo "A3 · live fleet, callsign -> launcher roots / lock"
python3 - <<'PY'
import subprocess, os, re, collections
ps = subprocess.run(['ps','-eo','pid,ppid,command'],capture_output=True,text=True).stdout.splitlines()
roots, turns = set(), {}
for ln in ps[1:]:
    m = re.match(r'\s*(\d+)\s+(\d+)\s+(.*)', ln)
    if not m: continue
    pid, ppid, cmd = int(m.group(1)), int(m.group(2)), m.group(3)
    if 'run_loop.sh' in cmd and ppid == 1: roots.add(pid)
    t = re.search(r'You are ([A-Za-z0-9._-]+)\.', cmd)
    if t and cmd.strip().startswith(('claude','gemini','grok')): turns.setdefault(t.group(1), []).append(pid)
locks = {}
for f in os.listdir('.'):
    if f.startswith('.loop_lock.'):
        try: locks[f[len('.loop_lock.'):]] = int(open(f).read().strip())
        except Exception: locks[f[len('.loop_lock.'):]] = None
# A root's callsign is not in its argv (H40), so attribute by descent: a root
# owns the turns whose ancestry reaches it.
parent = {}
for ln in ps[1:]:
    m = re.match(r'\s*(\d+)\s+(\d+)\s+', ln)
    if m: parent[int(m.group(1))] = int(m.group(2))
def root_of(pid):
    seen = set()
    while pid in parent and pid not in seen and parent[pid] != 1:
        seen.add(pid); pid = parent[pid]
    return pid
owned = collections.defaultdict(set)
for cs, pids in turns.items():
    for p in pids: owned[cs].add(root_of(p))
print(f"    {'callsign':14s} {'roots with a turn in flight':30s} lock")
dup = 0
for cs in sorted(set(list(owned) + list(locks))):
    rs = sorted(owned.get(cs, []))
    if len(rs) > 1: dup += 1
    print(f"    {cs:14s} {str(rs):30s} {locks.get(cs)}"
          + ("   <-- TWO LANES ON ONE CALLSIGN" if len(rs) > 1 else "")
          + ("   <-- HOLDER IS NOT ONE OF THEM" if rs and locks.get(cs) not in rs else ""))
print(f"    callsigns with more than one live root: {dup}")
PY

echo
echo "probe: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ]
