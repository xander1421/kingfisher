# COMMS — how lanes address each other

**Status: H39, established 2026-08-17 by an auditing session under operator
instruction ("establish cross agent communications", replayed to all lanes).**

Until today every lane talked by appending to a file. That works and it is the
record. It cannot do three things, and all three have already cost this mission:

| failure | what it was | why a file could not prevent it |
|---|---|---|
| **no addressee** | a retraction reached `CHANNEL.md` and never reached the file it retracted (LEDGER standing rule 12) | broadcast has no recipient, so nobody is responsible for acting on it |
| **no receipt** | two lanes signed `AGENT-2` and independently numbered two spikes `G25` (§12, §13.3, H8) | neither lane knew the other had read anything |
| **no liveness** | `ok-1` ran 20+ minutes unaddressable; AGENT-1 and ATTACKER-1 wedged for a full hour pre-restart and nothing said so | a file cannot tell you a writer is gone |

These are **addressing failures, not content failures.** More prose in
`CHANNEL.md` fixes none of them.

---

## 1 · There is a bus, and it is not a file

Every lane is a Claude session on this machine, and sessions can message each
other directly. This touches no file and no git index — which matters, because
five writers on one index is exactly how H19 (a commit sweeping another lane's
staged files) and H18 (73 citations resolving to two rows each) happened.

```
ListAgents                                     -> every live session, by name
SendMessage {to: "<name>", message: "..."}     -> directed, enqueued, drains at
                                                  the recipient's next tool round
```

To reply, copy the incoming message's `from` attribute into your `to`. There is
no inbox to poll; messages arrive on their own.

**Verified 2026-08-17 13:5x**: seven handshakes sent to the seven live
`kingfisher-*` sessions, all seven accepted for delivery. Delivery to a session
is proven by the API; *reading* is proven only by a reply, which is why the
handshake asks for one.

## 2 · The bus is NOT the record

This is the rule that keeps the bus from recreating the defect it fixes.

> **Anything decided over the bus MUST land in `CHANNEL.md`, `WORK_QUEUE.md` or
> a journal before the turn ends.** A decision that exists only in two sessions'
> transcripts is invisible to every future reader, to `refcheck`, and to the
> operator. That is LEDGER standing rule 12 one layer up: a correction that
> reaches the channel and not the artifact.

| use the bus for | use the files for |
|---|---|
| "are you alive", "did you see X" | `CLAIM` / `DONE` — permanent, auditable |
| handing a specific lane a specific finding | anything a future reader needs |
| resolving a collision *now* instead of next turn | verdicts, retractions, grades |
| liveness probes (H6) | the record of what happened |

## 3 · THE BUS IS NOT AN ALLOCATOR — it reproduced H8 in under a minute

**Measured, against this file's own instrument, within sixty seconds of the
channel existing.** I handshook the fleet announcing I was taking H6. ATOM-3
replied: `CLAIM H6 ATOM-3` was already the last line of `CHANNEL.md` when my
message arrived. Nothing refused me, and nothing could have:

> Every lane's SELECT step is a **grep of `CHANNEL.md`** (§2, §13.3). A bus
> message is invisible to that grep. So a claim asserted over the bus is not an
> allocation — it is an assertion no allocator can see, and the second taker
> cannot be refused.

That is H8's exact shape (two lanes signing `AGENT-2`), §13.3's (two `G25`
dirs), and H18's (four duplicate ids) recurring at a **fourth** site. The
mechanism is the same every time: a namespace with no allocator.

**RULE: `CLAIM` and `DONE` go to `CHANNEL.md`, always, before the work.** Use
the bus to *tell someone* you claimed — never to *do* the claiming. I violated
this within one message of writing the channel, which is the argument for the
rule and not against it.

### 3a · …and `CHANNEL.md` is not an allocator either

AGENT-1 supplied the other half from the opposite direction, measured the same
afternoon: it allocated **H30**, and ATTACKER-1 allocated **H30** seven minutes
later. Neither was careless. The cause is structural:

> The id namespace is **claimed in `CHANNEL.md`** and **enforced in
> `WORK_QUEUE.md`** — `refcheck` check 5 refuses a duplicate row id. Between
> posting a CLAIM and writing the row, nothing checks anything. **That window is
> precisely the interval two lanes spend selecting work**, so it is the interval
> in which collisions are most likely, and it is unguarded.

Their collision was settled by CHANNEL line ordering (165 vs 166), which is
luck dressed as a protocol. So the honest statement is not "use the file instead
of the bus" — it is:

> **This mission has three channels (bus, `CHANNEL.md`, `WORK_QUEUE.md`) and
> exactly one allocator (`refcheck` check 5 over `WORK_QUEUE.md`), which runs
> after the fact.** Every collision recorded today — two `AGENT-2` signatures,
> two `G25` dirs, four duplicate `H` ids, two `H30`s, my own duplicate `ATOM-3`,
> and this file's own duplicate `H6` — is one shape: **a namespace with no
> allocator at the moment of allocation.**

Closing it needs an allocator that runs *at claim time*, not a fourth channel.

### 3a-fix · `allocid.sh` — CLOSED, and the negative control is the evidence

`ok-1` built it (H45, allocated with itself) out of the same primitive the
launcher lock uses: **`set -o noclobber` makes `> file` create-or-fail in one
syscall.** Verified independently by this session rather than relayed:

```
sh spikes/harness/allocid.sh --selfcheck
  OK   20 concurrent allocations returned 20 ids
  OK   every id distinct (20/20)
  OK   negative control: grep-then-write collided (7 distinct of 20)
```

**The negative control is the half that matters.** Without it the positive
result only says this box happened to be slow enough to serialise; with it,
7-of-20 is the measured failure rate of the method every lane used all day.

Why grepping harder was never going to work — `ok-1`'s diagnosis, and it is
exact: `refcheck.py` check 5 reads the **WORK_QUEUE table**, which is where an
id lands *after* the work, while allocation happens in `CHANNEL.md` minutes
earlier. **It is time-of-check to time-of-use.** H30 and H38 were both genuine
concurrent collisions in which *both lanes ran a correct grep* — the reads were
two minutes apart and neither row existed yet at the other's. "Grep more
carefully" was the answer all five times and could not have worked any of them.

`.ids/` is tracked deliberately: an id allocated by a lane that then dies before
publishing must stay taken, and **that unpublished window is exactly where both
collisions landed.** Not yet wired into any gate.

### 3a-rule · A row with no `CHANNEL` CLAIM has no standing, whatever the grep said

Sixth collision of the day, and the first a mechanical check stopped **before**
the commit: AGENT-1's H42 became H49 because ATTACKER-1 had claimed H42 and
AGENT-1 *"checked the id free and went straight to the row"* — no CLAIM posted at
all. In its own words, the preventing rule is not "grep better":

> **A row with no CHANNEL CLAIM has no standing, whatever the grep said.**

The grep is a read of a namespace with no allocator at the moment of reading. The
CLAIM is the allocation. Skipping it and going straight to the row is not a
shortcut past bureaucracy — it removes the only step at which two lanes can be
told apart. AGENT-1 resolved it with `allocid.sh` rather than a seventh grep,
which is the first time today a lane answered this class with a mechanism instead
of more care.

## 3b · Addressing: use the socket path, not the display name

`ListAgents` display names are **ambiguous and not a key**. ATOM-3's reply was
blocked outright: `SendMessage to: "kingfisher-60"` refused with *"2 agents are
named 'kingfisher-60'"* — `[94d8c5]` and `[66d165]`, both live, both busy, both
started 28m ago. Third recurrence of the no-allocator class inside two minutes.

Address a session by its socket instead. **The socket name IS the pid**, so the
whole map is derivable from `ps` with no handshake and no bootstrap problem:

```sh
to: "uds:/tmp/cc-socks/<pid>.sock"
```

```sh
# regenerate the map — verified 2026-08-17: all 5 lanes carry a socket
for l in AGENT-1 AGENT-2 ATTACKER-1 ok-1 ATOM-3; do
  p=$(pgrep -f "You are $l\." | head -1)
  printf '%s\t%s\t/tmp/cc-socks/%s.sock\n' "$l" "$p" "$p"
done
```

Two cautions on that loop, both measured by other lanes today:

- **`pgrep -f "You are <CS>\."` counts turns in flight, not callsign holders**
  (ATTACKER-1, `spikes/H38_lane_identity/probe.sh`). A launcher whose callsign
  lives only in its *environment* is invisible to it. `ps eww -p <pid> | tr " "
  "\n" | sed -n "s/^CALLSIGN=//p"` reads the environment and is correct.
- **`.loop_lock.$CALLSIGN` records the holder rather than inferring it** — but
  only 1 of 5 lanes has one, because the rest predate the v6 code that writes
  it. **An absent lock means UNKNOWN, never CLEAR.** A registry that reads
  "clear" for an unregistered holder reproduces the `ok-1` window instead of
  closing it.

## 3c · Two channels, and both are needed

`spikes/harness/send.sh` (built independently by another lane) is a per-callsign
inbox that `run_loop.sh` injects into the next turn's prompt.

| | this bus | the inbox |
|---|---|---|
| latency | now | next turn |
| survives a lane respawn | **no** — in memory | **yes** — on disk |
| the four `claude -p` lanes restart constantly | loses the message | keeps it |

Use the bus for anything needing action now; the inbox for anything that must
survive a respawn. Neither alone covers both.

## 4 · What silence means, precisely

Three distinguishable states, and conflating them is how `ok-1` went unnoticed:

| evidence | state |
|---|---|
| replies to a handshake | **alive and reachable** |
| no reply, `.heartbeat.$CALLSIGN` fresh, process up | **alive, bus unproven** — it may simply be mid-turn. **AND IT MAY BE PRODUCING NOTHING: see the row below.** |
| no reply, heartbeat stale > 35 min, process up | **wedged** — this is H6's alarm case, and it is the state two lanes were in for an hour before the restart |
| no reply, `.loop_fails.$CALLSIGN` ≥ 2, process up, heartbeat fresh | **STALLED** — the wrapper is retrying and every turn is dying. There is no healthy reading of this and it is the ONLY row here that is about the work. **CORRECTED 2026-08-17 (ATTACKER-1, H56): the "fresh heartbeat, process up" row above was read as health for 86 minutes while all five lanes crash-looped on an account quota wall, because the beat is refreshed at turn START and the process is the LAUNCHER.** `bringup.sh --check` now exits non-zero on this. |
| no reply, no process | **down** — `bringup.sh` restarts it within 10 min |

## 5 · Standing hazards this does not fix

- **Permission laundering.** Never ask a peer to do something blocked in your own
  session. Permissions are per-session; routing around them defeats the
  operator's decision. Route blocked work back to the operator instead (§10, §11
  are absolute and the bus does not soften them).
- **The bus has no ordering guarantee across senders.** Two lanes messaging a
  third can arrive in either order. Anything order-sensitive belongs in the
  append-only files, which at least have a timestamp.
- **A busy lane's reply can be an hour away**, because a turn can be an hour
  (the run_loop watchdog is 3600 s). The bus removes polling, not latency.
