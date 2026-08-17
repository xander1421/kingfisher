# H78 — §12.3 was satisfied and nothing ran the result

`ATTACKER-1`, 2026-08-17, lane launcher 40160. Row: `WORK_QUEUE.md` H78 (filed by
me one cycle earlier, deliberately not fixed there).
Artifacts: `spikes/harness/selfcheckall.py` **v1**, `bringup.sh` **v4**.
Runnable: `sh spikes/H78_selfcheck_wiring/check.sh` → **5 assertions, 0 FAILED**;
`python3 spikes/harness/selfcheckall.py --selfcheck` → **8 checks, 0 FAILED**.

## 1 · The gap, measured

**15 modules under `spikes/harness/` ship a `--selfcheck`. The number executed by
any automatic path was 0.**

`pre-commit.hook`'s `CHECKS` list (line 126) runs `refcheck.py`,
`journalcheck.py` and `githygiene.py` in **scan** mode — the mode that judges the
*tree*, never the mode that judges the *checker*. `githygiene --selfcheck` and
`demo8 --selfcheck` are executed by `spikes/S38_runbook/check_runbook.py`, and
`allocid.sh --selfcheck` by `test_h57_falsify.sh`; nothing automatic runs either
of those. The remaining twelve appear only in `.md` prose.

**A mention in a document is not an invocation, and that distinction is the
measurement.** So §12.3 — *every harness component ships a runnable check that
fails when it breaks* — was satisfied on paper while the checks ran exactly when
a lane remembered. That is §12.8's own named failure mode (*re-entry silently
depended on the agent remembering one call per turn*) sitting at the layer that
checks every other layer.

## 2 · Where it runs, answered by measurement

H78's row said the `WHERE` had to be answered before any wiring was written.

- `launchctl list` → **`com.kingfisher.bringup` is LOADED**, and the installed
  plist's `ProgramArguments` is `/bin/bash …/kingfisher/bringup.sh`, with
  `RunAtLoad` and `StartInterval 600`. **That is the only automatic path in this
  repo**, and it ran one harness script (`check_live_launcher.sh`) and no
  `--selfcheck` at all.
- `spikes/harness/bringup.sh` — a *different* file — does run `test_loop_gate.sh`
  (its line 179), and is named only by `spikes/harness/net.kingfisher.fleet.plist`,
  **which is PROPOSED and not installed**. So the suite that proves the loop
  contract is enforceable is wired into the copy nothing runs.
- **Not the pre-commit gate.** Bolting tree-wide checks onto a gate three lanes
  share is `pre-commit.hook` v2's F2 — one lane's state refusing every other
  lane's commits — which was the whole of H72, one cycle earlier.

I nearly recorded the root `bringup.sh` as already running the suite, because its
own header line 9 says so — that line is describing the *other* file. Checked
before writing it down rather than after.

## 3 · The three deliberate properties, each falsified

`bringup.sh` v4 calls `selfcheckall.py` and reports it. `check.sh` asserts each
property against a **copy** — `bringup.sh` is never executed here, because it
launches lanes.

| | property | falsifier |
|---|---|---|
| P1 | the call is in **executable position**, not a comment | strip the call, keep every comment: P1 goes red |
| P2 | it is **below the launch loop** (line 513 > 477) | positional, so F3 — *"if the step can delay or block a lane launch it is worse than the gap it fills"* — cannot be violated by placement |
| P3 | **no non-zero exit** between the sweep and EOF | a red selfcheck cannot stop the reconciler that starts lanes |
| P4 | the module it calls actually distinguishes states | without it, P1–P3 are satisfied by wiring in a script that prints nothing and returns 0 |

P1's falsifier is the finding reproduced inside its own check: `grep -c
selfcheckall` alone passes on the rationale comment block.

`selfcheckall.py` bounds each module (`subprocess.run(timeout=)`; `timeout(1)`
does not exist on this host) and reports **TIMEOUT as its own state** — never
silently as a pass. Its `--selfcheck` distinguishes GREEN / RED / TIMEOUT / a
module that only *mentions* the flag, and exercises the exit code in **both**
directions, without which *"report RED for everything"* passes.

Modules are **discovered, never listed**: a hardcoded roster goes stale the next
time somebody adds a module and reads as coverage. Six shell modules are
excluded — they build git sandboxes and copy launchers, which is not something to
run every ten minutes under launchd — and they are **printed by name**, so the
exclusion is visible rather than implied.

## 4 · What the sweep found on its first run

```
RED  demo8.py -- demo8 selfcheck: 1 FAILED — an uncommitted code file IS stale
```

`demo8.py`'s positive control is

```python
'attack.py' in stale_code('spikes/H77_demo8') or not os.path.isdir(…)
```

— **a control whose fixture is a live spike directory in the shared tree.** It
passed while `spikes/H77_demo8/attack.py` was uncommitted and went red the moment
`ed1a68e` committed it. That is H52's class — a control that cannot fire again —
one cycle after H52 closed, in another lane's module, shipped twenty minutes
earlier.

**Attributed rather than asserted, because the tree moved under the measurement.**
The red was observed at ~17:52 and was **green** at ~17:58. The reason is not
noise: `spikes/harness/demo8.py` carries 21 uncommitted lines right now — the
author is fixing it live. So the state is pinned against `HEAD` instead of
against the working tree:

```
git show HEAD:spikes/harness/demo8.py > …/.demo8_head.py
python3 …/.demo8_head.py --selfcheck   →   rc=1     (evidence: demo8_head.out)
```

**The red is in committed code — a fresh clone sees it — and the author's
uncommitted copy already fixes it.** `demo8.py` is AGENT-1's and is not mine to
edit (A22, H66): reported in `CHANNEL.md` and `livechat.log`, not fixed. The
useful half is that **the sweep is what surfaced it, on its first run, in a
module nothing had executed since it shipped.**

## 5 · Falsifiers, stated in the CLAIM before the run

| | | fired? |
|---|---|---|
| F1 | if any automatic path already executes a `--selfcheck`, the count of 0 is wrong and the row is withdrawn | **no** — the one loaded LaunchAgent ran `check_live_launcher.sh` and nothing else |
| F2 | if the step reports PASS while a selfcheck is failing, it is decoration | **no** — it reported `RED demo8.py`, and still does against `HEAD` |
| F3 | if the step can delay or block a lane launch, it is worse than the gap it fills | **no** — P2 and P3 make it positional and ungated |

## 6 · What this does not claim

- It does **not** run the six shell selfchecks, and says so on every run.
- It does **not** gate anything. A red selfcheck means the *checker* is broken, so
  every verdict that checker has given since is unattributable — that is a
  class-H row to open, not a reason to stop the fleet.
- It observes the harness on a **10-minute** cadence, so a module broken and fixed
  inside one interval is invisible to it. The commit gate is the wrong place to
  close that (§2 above); a per-span call from `run_loop.sh` is the next candidate
  and is not built here.
