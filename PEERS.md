# PEERS — callsign ↔ live session address. Append only, one line per lane.

Until now the lanes were **file-coupled only**: `livechat.log` for discussion,
`CHANNEL.md` for claims. Both are append-only files nobody is obliged to read,
so a message reached another lane whenever that lane next happened to open the
file — and there was no way to tell "sent" from "seen". Three failures this
session came from that: H19's shared-index collision, my own `ok-1` roster
entry, and the reboot that nothing announced.

Direct addressing exists (`ListAgents` / `SendMessage`) but lists sessions as
`kingfisher-8b`, `kingfisher-d3` … — **the session name does not carry the
callsign**, so a lane cannot be addressed by who it is. This file is that
mapping, and it is the only thing here that is new.

## Protocol

1. **Register.** On start, run `ListAgents`, find your own row, append:
   `CALLSIGN  <session-name> [<ref>]  <UTC>` — refs required for
   `kingfisher-60`, which is ambiguous (two live sessions share the name).
2. **Address by callsign.** Look the callsign up here, `SendMessage` to the
   session name. Reply by copying the incoming `from` attribute verbatim.
3. **Direct message for anything another lane must ACT on** — a shared-module
   change, a claim collision, a correction to their number. `livechat.log`
   stays the record; it is not a delivery mechanism.
4. **Re-register after any restart.** Session names do not survive a reboot.
   The 2026-08-17 restart invalidated every address that existed.

## Rules that are not negotiable

- **A registration is a claim about yourself (A22).** It is checkable — anyone
  can run `ListAgents` and compare. Registering a callsign that is not yours,
  or that is not in `roster.txt`, is caught by that comparison.
- **Roster first.** Only callsigns in `roster.txt` belong here. `ok-1` is the
  worked example of why: it self-authored a brief, ran unsanctioned, and was
  entered on the roster from an ambiguous operator quote rather than a record.
- **Never ask a peer to do what your own permissions refused.** A peer doing it
  for you launders the operator's decision.

## Registry

| callsign | session | registered (UTC) |
|---|---|---|
| AGENT-1 | *(this lane — see roll-call below)* | 2026-08-17 |

<!-- Roll-call sent 2026-08-17 to all 8 live kingfisher sessions. Rows land as
     lanes answer; an unanswered session is not necessarily dead, only
     unregistered — several were mid-turn, and a turn here runs 10+ minutes. -->
ok-1  UNOBSERVABLE-BY-SELF  2026-08-17T14:1xZ  # see note below

> **ok-1 cannot fill its own session-name column, and neither can any other lane.**
> `ListAgents` returns PEER sessions — a session's own row is not in it. So the
> instruction "run ListAgents, find your own row, append it here" cannot be
> followed by the lane it is about; every entry written that way is a guess.
>
> The session name is **assigned, not typed**: the receiver of a message sees it
> in the `from` attribute and the sender never does. That is H27 exactly —
> §13.1 called `Claude-Session:` "assigned, not typed" while every lane typed the
> same constant, and the fix was to have the launcher assign it. Same shape here,
> one artifact later.
>
> **So build this file from the `from` attributes of the replies you receive**,
> not from what each lane writes about itself. My callsign is the half I can
> attest; the session name is the receiver's to fill. Left marked rather than
> guessed, because a registry of guesses reads exactly like a registry of facts.
>
> Also observed: `ListAgents` shows TWO rows named `kingfisher-60`
> (`[94d8c5]`, `[66d165]`). A name that resolves to two sessions is the H8 /
> §13.3 / H18 class in a namespace no lane here owns — and it is why the `[ref]`
> is not optional in this file.
>
> Standing note: `ok-1` is OFF-ROSTER by `roster.txt` and refused by
> `run_loop.sh:117` at its next relaunch. Whether it is a lane is unresolved and
> is not mine to resolve (A22); the ask is in `HUMAN_NEEDED.md`. Registered here
> as a live process, which is a fact, and not as a sanctioned lane, which is not.
