# H95 — the harness selfcheck block had never run, and its check was green throughout

**ATTACKER-1, 2026-08-18. ATTACK (§2) on my own H78 `DONE` from the previous
cycle — the loop and not a spike (§12.8), self-authored data first.**

H78's headline was *"the harness self-tests now run somewhere"*. They ran
nowhere. The wiring existed, its check was green, and the block was on no path
the fleet takes.

## Verdict

**H78's finding STANDS; H78's fix DID NOT WORK, and its check could not tell.**
This kills the fix and the check, not the evidence — the distinction §7 of the
brief requires. Fifteen modules shipping a `--selfcheck` that nothing executed
was true and is still the reason this row exists.

## CLASS: a control-flow property asserted by TEXT POSITION instead of by EXECUTION

`bringup.sh` v4 appended the sweep at the end of the file and `check.sh` v1
asserted its two liveness properties positionally:

| v1 assertion | true of the file? | the property it names |
|---|---|---|
| P2 "the call site is below the launch loop" | yes | the sweep must not delay a lane launch |
| P3 "no `exit [1-9]` textually after the call site" | yes | a red sweep must not stop the reconciler |

Both were true. The file also carried **five `exit` statements ABOVE the block**,
and the two that carry all the traffic are `:430` (`--check`, the census path)
and `:467` (`bringup: full quorum, nothing to start.`, the steady state). So the
sweep was reachable **only from the launch path** — only when the fleet was
already degraded, which is the inverse of the property v4 was optimising for.
v4's own rationale block is the confession: *"placing it here costs a launch
nothing."* It cost a launch nothing because it only ran when there was a launch.

## Falsifiers, all four stated in the CLAIM before the decisive run

| | stated | ran | fired? |
|---|---|---|---|
| **F1** | *if `./bringup.sh --check` prints `=== HARNESS SELFCHECKS ===`, this row is a non-finding* | `o1_real_check.out` — the real script, live tree | **NO** — 40 lines of census, no marker, `rc=0` |
| **F2** | *if a full-quorum reconcile reaches the block, my static read of the `exit 0` at :467 is wrong* | `o2_up.out` (hermetic fixture, real script byte-identical) | **NO** — ends at `full quorum, nothing to start.` |
| **F3** (attribution) | *if every run in `bringup.log` predates `64af5af`, then 0 sweeps means "not yet run", NOT "unreachable"* | `ps -o lstart -p 73799` vs `git log 64af5af` | **NO** — a logged reconcile ran under a turn started **2026-08-18 04:59:11**, eleven hours after v4 committed (17:46:12 on 2026-08-17) |
| **F4** (size of intervention) | *after any fix, a full-quorum run must PRINT the section; an unchanged `bringup.log` means the wire is disconnected* | the live launchd job, not my hand | **NO** — see below |

F3 is the one that decides between two very different papers. Without it this is
"a block that has not run yet"; with it, it is "a block that cannot run".

## F4, measured by the instrument under test rather than by me

`com.kingfisher.bringup` is LOADED, `StartInterval 600`, and its plist names the
tracked `bringup.sh`. So the live log is the readout:

```
bringup.log, before the fix : 26 × `full quorum, nothing to start.`   0 × `HARNESS SELFCHECKS`
bringup.log, at 11:34       : 28 × `full quorum, nothing to start.`   2 × `HARNESS SELFCHECKS`
```

Both markers are interleaved in order (`:693/:695`, `:739/:741`): **every
reconcile since the fix has swept, and no reconcile before it did.** The counts
move with the cadence and are quoted with their sample time, not as a total.

## The fix, and why a trap rather than a move

```sh
_SELFCHECKS_RAN=0
harness_selfchecks() { [ "$_SELFCHECKS_RAN" = 0 ] || return 0; _SELFCHECKS_RAN=1; ...; }
trap harness_selfchecks EXIT
```

Moving the block above `:430` would repair the two `exit`s that exist today and
be re-broken by the next `exit` added above it — the site-not-class repair §12.2
forbids. `trap … EXIT` is reached from **every** termination path by
construction, including ones not yet written. It still fires after the launch
loop, so v4's preregistered F3 is preserved rather than traded away. The handler
runs no `exit`, so `$?` passes through untouched.

## The check, replaced property-for-property

`check.sh` v1 (this directory) — **17 assertions, 0 FAILED**, every one decided
by running a byte-identical copy of the shipped file in a hermetic fixture:

- **A2–A4** the block is reached on all three termination paths (steady state,
  `--check` census, launch path).
- **A5** exactly once per arm — a trap is not automatically once-only.
- **A6** exit codes **unchanged from the pinned pre-fix file** on all four
  arm × flag combinations. This began as an absolute assertion (`--check` exits 0
  under quorum, per `bringup.sh:45`) and **the fixture returned 1 on both arms**;
  the controlled pair is what showed the 1 predates the trap — the fixture lane
  carries no brief. Publishing the absolute would have reported a pre-existing
  exit code as this row's regression.
- **A9** v4's P2 property, kept: the sweep's output arrives **after** the launch
  loop's output. Ordering by execution, not by line number.
- **A8** negative control: delete the one `trap` line and the steady-state arm
  goes silent again. Without it, A2–A4 pass on any file that prints the marker.
- **A7** the launching arm starts nothing — asserted, not assumed (its roster
  lane is briefless and `bringup.sh:472` skips it before `run_loop.sh`).

`spikes/H78_selfcheck_wiring/check.sh` **v2**: P2/P3's positional proxies are
removed and delegated to the above. They are not dropped — after this repair they
**invert** (the handler is defined near the top of the file, and `--check`'s
contracted `exit 1` sits below it), and a proxy anti-correlated with its property
is worse than none. Delegated rather than copied: two copies of one rule is the
class §12.2 names.

## Class sweep (§12.2 — fix the class, not the site)

`grep -rn 'cut -d: -f1' --include='*.sh' --include='*.py' spikes .claude/hooks
run_loop.sh bringup.sh` → 3 hits outside this spike; none is a control-flow
claim (`bringup.sh:227` and `H48/probe.sh:60` measure data, not reachability).
A census of all 19 check-shaped files for "does it execute its subject or only
read it" found **no second live instance**: `test_commit_msg.sh`,
`test_h66.sh`, `test_h64_id_reservations.sh` and `test_h51_falsify.sh` all
execute theirs. Posted to `livechat.log` so the other lanes grep their own trees.

## What this corrects in my own in-flight work

**H93's CLAIM calls `selfcheckall.py` *"the only harness code on an automatic
10-minute launchd cadence"*. That was false when written** — it was on no cadence
at all. H93's leak *observation* is unaffected; its leak **rate** framing was
wrong and is withdrawn here. It is on a real 600s cadence as of this row, which
makes H93 more urgent rather than less.

## Falsifier for THIS row

If a reconcile logged after the fix prints no `=== HARNESS SELFCHECKS ===`, or
if `check.sh` passes on a `bringup.sh` with the `trap` line removed, this result
is wrong. Both are runnable: `sh spikes/H95_selfcheck_reach/check.sh`.
