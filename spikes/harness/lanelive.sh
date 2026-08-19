# lanelive.sh — "is this pid a LAUNCHER?", the predicate run_loop.sh already uses
# and nothing else did. Sourced, never executed. ok-1, H243, 2026-08-19.
#
# DEFECT REMOVED: `.loop_lock.<CALLSIGN>` was read by six instruments and five of
# them asked only `kill -0`, i.e. "is some process alive with this number". A pid
# is not an identity: this fleet burns ~1300 pids/minute, so a 99999-pid space
# wraps in about 75 minutes and a dead lane's recorded pid becomes somebody
# else's. run_loop.sh's acquire path says exactly this in its own comment and is
# the only reader that acted on it.
#
# MEASURED before the fix (`spikes/H243_lock_liveness/probe_prefix.out`):
# `bringup.sh --check` reported a lane UP off a lock naming a live `sleep`, and
# `fleetcensus.sh` scored the same lock CONSTITUTED. The supervisor's UP means
# "not MISSING", which means NOT RELAUNCHED -- a dead lane with a recycled pid is
# never restarted, and a dead lane has no next cycle.
#
# Check that fails when this breaks: `bash spikes/H243_lock_liveness/probe.sh`.
launcher_alive() {                    # launcher_alive <pid> -> 0 if a live launcher
  case "${1:-}" in ''|*[!0-9]*) return 1 ;; esac
  ps -p "$1" -o command= 2>/dev/null | grep -q 'run_loop\.sh'
}
