# H122 — the gate prints its reason; nobody read it, including me one cycle ago

**ATTACKER-1, 2026-08-18. ATTACK on my own H116, published one cycle earlier, and
on an attribution this whole repo has been repeating.**

## Verdict

**H116's number stands: `quiet.sh` refused in 0 of 6 samples. Its CAUSE is
retracted.** I wrote *"a five-lane fleet is exactly what `quiet.sh` exists to
refuse, so the refusal is structural"* — having read the **exit code** and
supplied a cause that fitted my row. The gate prints its reason. I sent it to
`/dev/null`.

**CLASS: correct numbers, wrong cause** — CLAUDE.md's second unmechanisable
failure, in the lane whose job is to catch it.

## What the reason actually is

`spikes/quiet.sh:99–101`:

```sh
awk -v l="$LOAD" -v m="$LIMIT" 'BEGIN{exit !(l>m)}' && FAIL="$FAIL loadavg($LOAD>$LIMIT)"
[ "$NCONT" -gt 0 ] && [ "${QUIET_ALLOW_CONTAINERS:-0}" != "1" ] && FAIL="$FAIL containers($NCONT)"
```

**Two independent arms, and they behave completely differently:**

| arm | trips when | who can clear it |
|---|---|---|
| `loadavg` | load > ncores/4 (**3.50** on 14 cores) | the fleet — it varies with what is running |
| `containers` | **`NCONT > 0`. Any container. At any load.** | **nobody in this project** |

Four containers have been up throughout, and none is ours:
`chatter-livekit`, `chatter-vault`, `chatter-rustfs`, `chatter-spicedb-1`
(livekit, vault, rustfs, spicedb images). The only file in this repo that has
ever named them is the `CHANNEL.md` line I wrote an hour ago.

**Therefore: stopping the fleet cannot make this gate pass.** That is decidable
from line 100 alone, without a borderline load sample.

## The separation, measured rather than argued

`QUIET_ALLOW_CONTAINERS=1` is the gate's own documented override, which makes it
a natural control — disable the container arm and whatever is left is load:

```
load=11.27  plain=[loadavg(11.27>3.50) containers(4)]  containers-allowed=[loadavg(11.27>3.50)]
load=11.81  plain=[loadavg(11.81>3.50) containers(4)]  containers-allowed=[loadavg(11.81>3.50)]
load=12.54  plain=[loadavg(12.54>3.50) containers(4)]  containers-allowed=[loadavg(12.54>3.50)]
```

**And the one observation that settles it**, taken at 13:52 before this probe's
own load arrived: `loadavg 3.36` — **under** the 3.50 limit — with the refusal
reading `containers(4)` **alone**. The container arm refuses a machine the load
arm calls quiet.

## Falsifiers

| | stated in the CLAIM | result |
|---|---|---|
| **F1** | *if repeated sampling shows `loadavg` tripping and not `containers`, my correction is wrong and H116 stands* | **PARTIALLY FIRED, against my own correction.** `loadavg` trips in 8 of 8 samples too. My CLAIM predicted *"the trip is `containers`, not load"* and **that prediction was too strong** — both arms trip most of the time. What survives is the asymmetry: one arm is clearable and one is not |
| **F2** | *if the containers are this project's, "no lane can clear it" is false* | did not fire — four images unrelated to this repo |
| **F3** | *if no other artifact repeats the attribution, this is one lane's error in one document* | did not fire, but **narrower than I expected**: other spikes record `loadavg 55.96 against a 3.50 limit` and `loadavg 6.86 vs …`, which named the load arm **and were true at their sample time**. A dated claim is not a decayed one and none of them is swept into this correction. **What no artifact in this repo has ever recorded is the container arm** |
| **F4** | *if `quiet.sh` already emits the reason machine-readably, the defect is in the CALLERS* | **FIRED, and it is where the fix went.** `quiet.sh --json` emits `"refusals":"loadavg(8.02>3.50) containers(4)"`. **Three callers discarded it with `>/dev/null`** — `autoloop_local.sh`, `spikes/harness/bringup.sh`, and my own H116 probe |

## Why this matters beyond one wrong sentence

Reporting *"quiet.sh REFUSES"* without the reason **makes an unclearable
condition read as a scheduling problem.** Every lane that sees it concludes "run
the benchmark later"; later never comes, because four containers belonging to
another project are the floor. The fleet's own `bringup.sh` census printed
exactly that bare warning to every lane.

## Shipped

- **`spikes/harness/autoloop_local.sh` v3** and **`spikes/harness/bringup.sh`** —
  both now read `--json` and print **which arm refused**:
  `quiet.sh REFUSES [loadavg(16.14>3.50) containers(4)]`.
- **H116's `RESULT.md` corrected in place**, per CLAUDE.md: the number kept, the
  cause withdrawn, the original sentence quoted so the correction is legible.

**Not done, and it is a human's call, not a lane's:** whether to set
`QUIET_ALLOW_CONTAINERS=1` for this host, or stop four unrelated containers, or
accept that no load-bound measurement is valid here. A lane choosing to disable
an arm of the gate it operates under is A22, and the override is recorded in the
`--json` output precisely so that choice is visible when someone makes it.

## An error inside the correction

**I nearly patched the wrong `bringup.sh`.** There are two — the root one on the
launchd path (H78/H95) and `spikes/harness/bringup.sh` — and only the *second*
calls `quiet.sh`. `edits.anchored_replace` refused with `anchor appears 0
time(s)`, which is the entire reason that helper exists and is why CLAUDE.md
forbids `str.replace`. A silent no-op edit here would have left the census
printing the bare warning while I recorded it as fixed.

## Falsifier for THIS row

If `sh spikes/quiet.sh --json` ever reports `"containers":0` while still
refusing on the container arm, or if a caller's printed reason disagrees with
`--json`'s `refusals` field, this result is wrong.
`sh spikes/H122_quiet_cause/probe.sh` re-runs every arm.
