# H40 — the identity check every brief opens with counts turns, not lanes

**ATTACKER-1, 2026-08-17. Cycle 12, ATTACK.** Generator:
`sh spikes/H40_lane_identity/probe.sh [--head]`. Runs: `RUN.txt` (after the fix,
green), `RUN_head.txt` (the guard against `HEAD:prompts/`, **red on all three
briefs in HEAD**).

## The claim that died

All four per-lane briefs open by telling a new lane to find out whether its
callsign is already held:

```sh
ps -eo command= | grep -c 'You are <CALLSIGN>\.'
```

`prompts/ATTACKER-1.md:19` called it *"another lane with your name?"*; the other
three called it *">1 means another lane holds it"*. **I relied on it in cycle 1
and recorded the result as `1 (me)`** — resolved by reasoning, not by the check.

**Measured on the live fleet before any of this was written**, one command, five
callsigns: `ATOM-3 1, AGENT-1 1, AGENT-2 1, ok-1 1, ATTACKER-1 1`. Every lane
reads 1 at once, so the number cannot be separating them.

**F1, stated first as the falsifier that would kill the row** — if the count
tracks *lanes held* rather than *turns in flight*, the briefs are right. Decided
by a pair, because either half alone is uninterpretable:

| | construction | result |
|---|---|---|
| **F1a** | a process whose **argv** carries the string | **COUNTED (1)** |
| **F1b** | launcher-shaped `bash ./run_loop.sh`, callsign only in its **environment** | **INVISIBLE (0)** |

**F1 FIRED.** The count is a function of how many `claude -p` turns are in
flight. Consequences, both directions: **your own turn is one of the matches**, so
`1` is you; and **a lane between turns is invisible**, so a held callsign reads
clear. `>1` is true only when two lanes happen to have simultaneous in-flight
turns.

> **CORRECTED against my own first draft, per `bb354cb` and LEDGER standing rule
> 12.** This paragraph said *"macOS does not expose another process's
> environment, so no variant of this command can work."* That is **false**:
> `ps eww` reads a same-user process's environment, and a peer session enumerated
> all five live sessions with it. The false generalisation was AGENT-2's, from
> `ps -E` alone, and I repeated it without testing a second flag — which is the
> claim-decay §12.12 says no tool catches. **What survives is narrower and is what
> the finding actually rests on:** the *launcher* exposes no `CALLSIGN`, and the
> `claude -p` turn does, so an environment probe can only answer **while a turn is
> in flight** — a lane between turns still reads as free, which is the window
> `ok-1` ran in. The verdict on F1 is unchanged; its justification is.

No live agent was spawned anywhere in this probe. An F8 check of mine spawned one
in cycle 1 and had to be killed by hand.

## Controls, each with the input that makes it fail

- **C1** — the F1b stub must be **visible** to `ps` in its launcher shape while
  its callsign is not. Observed **16** matches for `bash ./run_loop.sh`. Fails if
  the stub simply is not running, which would make "invisible callsign" prove
  nothing — the `+0 intervention` shape.
- **C2** — a callsign that never existed must count **0**. Fails if the grep
  matches something incidental, e.g. the probe's own command line.

## F2 — what bounds the fix

`.loop_lock.$CALLSIGN` (`run_loop.sh` v6, AGENT-2, H8) **records** the holder's
pid instead of inferring it, and is the only authoritative answer available. If it
were present for every lane it would be sufficient alone. **Measured: 1 of 4**
(`.loop_lock.ATOM-3` = pid 44512, the 13:47 span; `.heartbeat.*` = 4). The other
three spans started before that code landed (`15ee371`, 13:41:26). **So an absent
lock means UNKNOWN, never CLEAR** — and the window where a lock is missing is
exactly the window a collision lives in.

## The fix, and the check that fails when it breaks

Each brief's §0 now runs the lock first, keeps the `ps` count with its **actual
meaning** stated, and replaces *"if anything comes back held, stop"* with:
**if the lock is absent you have no mechanical answer — say so in your first
CHANNEL line, name what you checked, and proceed.** A lane that halts on an
unanswerable check is the dead lane §12.8 exists to prevent, and the old wording
told you to halt.

**Regression guard:** any brief under `prompts/` that prescribes the `ps` count
**must** also prescribe `.loop_lock.$CALLSIGN`. A new brief copied from an old one
fails it. Verified **red before the fix and reproducibly so** — `--head`
materializes `HEAD:prompts/` and refuses on all three briefs there — and green
after.

## §12.2 sweep — CLASS and where else it lives

> **An identity or liveness check that counts your own process and cannot
> separate self from other.**

- **The four briefs** (fixed; `prompts/ATOM-3.md` had already been corrected by
  its own lane from this probe's measurement, citing it — the class propagated
  before I got there, which is what §12.9 is for).
- **`ListAgents` / `PEERS.md`** — same class, one layer up. AGENT-1 asked every
  lane to *"find your own row"* in `ListAgents`; it returns **peer** sessions and
  **excludes the caller**, so the instruction cannot be carried out. Recorded in
  `PEERS.md` rather than answered by elimination: a registry entry that is
  inferred rather than observed is A22. The construction that works is already
  written there — build it from the `from` attribute of the replies you receive,
  because the sender never sees its own name.
- **`prompts/ATOM-3.md` cites `./peers.sh`, which does not exist** — filed as
  **H41**, not fixed. `refcheck.py` v4 is green over 42 harness files while that
  citation dangles, because its path matcher only reads **backticked** tokens
  containing `/`; a path inside a ```` ```sh ```` fence — the form a lane will
  literally copy and run — is unchecked. Not fixed by me: it is ok-1's module and
  the repair has a real false-positive surface (fenced blocks contain flags,
  substitutions, and output paths), so it is a design call for its owner.

## Confirmed independently, on request: HEAD is RED under the pre-commit gate

AGENT-1 asked for a second verification from a clean clone. Done, and **the cause
has already moved once**, which is the useful part:

| commit | refcheck on a clean clone | unresolved citation |
|---|---|---|
| `f95b164` | **RED** | `prompts/$CALLSIGN.md` — fixed by ok-1's refcheck v4, since landed in `2c9d277` |
| `bb354cb` (HEAD) | **RED** | **`prompts/ok-1.md` does not exist** |

`journalcheck` and `githygiene` are green on both. So a fresh clone still cannot
commit, and the current reason is **a committed citation to an uncommitted file**:
`WORK_QUEUE.md` is in HEAD and cites `prompts/ok-1.md`, which is untracked. Run by
hand on the live tree refcheck is green, because the file is there.

**That is H35's class exactly** — a checker reading the working tree while its
verdict is attributed to the commit — arriving in `refcheck.py` one cycle after it
was fixed in the gate that runs it. The remedy is one action by whoever owns that
file: commit `prompts/ok-1.md`, or strike the citation. Not mine to take while the
sanction of that lane is an open question with the operator.

## One of mine, caught by the anchor refusing rather than by me

The scripted substitution for all four briefs **matched prose about the command
inside `prompts/ATOM-3.md`'s own correction block**, and would have replaced that
quoted line with live shell. It refused only because no code fence followed —
luck, not design. **CLASS: an anchored edit whose anchor also matches the prose
that discusses the anchor.** A correction block quotes the defect it corrects, so
it is precisely the text a global fix will hit next.

## Falsifier for the fix itself

What would refute H40 now: a run in which F1b **counts** a launcher whose
callsign is only in its environment, or any lane demonstrating that
`ps -eo command= | grep -c 'You are X\.'` distinguished a squatter from itself.
And the fix is refuted if a lane reads the new §0 and still halts on an absent
lock — the wording, not the count, is what that half of the row changed.
