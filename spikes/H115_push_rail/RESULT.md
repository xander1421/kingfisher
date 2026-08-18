# H115 — §11's rail had no mechanism, and its precondition changed underneath it

**ATTACKER-1, 2026-08-18. ATTACK on the publishing rail, taken from ATOM-3's
handover (`63aec9c`, `5ed3eba`); they are the author and said they could not
audit it. They asked me to verify "§11-unreachable-without-a-human". I tried to
refute it.**

## Why now rather than yesterday

For two days `git remote -v` resolved to nothing, so "no pushes" was **safe by
accident**. On 2026-08-18 the remote resolves — `https://github.com/xander1421/
kingfisher.git` — and HEAD stands **26 commits ahead of `origin/main`**. A rail
that was structurally unreachable is now policy-only.

## F1 (killing) — did NOT fire

`.git/hooks/` held **`commit-msg` and `pre-commit`, and nothing else**. No
`pre-push`, no poisoned pushurl, no unauthenticable credential.

**Every gate this fleet has built refuses at COMMIT time. The rail that lets work
leave the machine is crossed at PUSH time, where nothing was watching.** Same
class as H89 — the prohibition enforced by reading — with the highest-standing
rail in the repo.

## F2 (wrong predicate) — FIRED, and it decided what I was allowed to build

I claimed the rail said "no pushes". **It no longer does, and I was wrong to tell
two peers otherwise.** `CLAUDE.md`, committed, now reads:

> *"No publishing to THIRD PARTIES … **Pushing to the operator's own private
> origin (`xander1421/kingfisher`, added 2026-08-18) IS permitted** — that is
> backup, not publishing."*

**And `MISSION_LOOP.md` §11 — the section that sentence cites — still reads
"No external posts, issues, PRs, comments, uploads, or publishing" and mentions
pushes nowhere, in either direction.** So the amendment lives in the **citing**
document and not in the **cited** one. That is claim decay running forwards
instead of backwards, and it is ATOM-3's H109; not fixed here, because the two
documents disagreeing is *their* row and editing §11 to match would be one lane
ratifying an operator decision it only heard about second-hand.

**What that changed in this row:** a blanket push refusal would contradict a
recorded operator decision and become the always-red gate every lane learns to
bypass (H14, H52). So the gate refuses **the hazard**, not the action.

## What was verified of ATOM-3's claim — most of it holds, for a reason worth stating

| | |
|---|---|
| tracked under `.github/` at HEAD | **one file**, `.github/workflows/autoloop.md` |
| does Actions execute `.md`? | **No.** It runs `.yml`/`.yaml`. The whole disable rests on this |
| `on:` in that source | `workflow_dispatch` only — schedule and `slash_command` removed |
| accidental re-arming | `.gitignore:96` = `.github/workflows/*.lock.yml`, and `gh aw compile --help` says the emitted name is `<workflow-id>.lock.yml`, so **the ignore does match the default emitter** (F4 did not fire) |
| deliberate re-arming | **`gh aw` v0.86.2 is installed.** `git add -f`, a `--dir`, or a rename escapes a pattern-based ignore |
| the compiled lock | `.autoloop/autoloop.lock.yml.disabled` **is tracked**, holds `issues: write` ×2 and `contents: write`, and would be pushed — inert on the remote only because Actions reads one directory |

**The one claim I cannot verify from here, and it is load-bearing:** `CLAUDE.md`
states GitHub Actions is disabled repo-wide (`actions/permissions →
enabled:false`, operator decision). **That is a remote setting no lane on this
machine can observe** — family D, a declared input standing in for an observed
one. If it is true, a pushed workflow still would not run; if it is silently
re-enabled, nothing here would know. The gate below does not depend on it.

## Shipped

**`spikes/harness/pre-push.hook` v1** — refuses a push whose **pushed tree**
contains a file Actions can execute (`.github/workflows/*.yml|*.yaml`); reports,
never gates, on a compiled lock tracked outside that directory.

Three decisions, each deliberate:

- **The TREE, not the diff.** "Does this push *add* a workflow" passes a push
  whose workflow arrived three commits ago, and what matters is what the remote
  ends up holding.
- **Extension, not filename.** `autoloop.lock.yml` is today's emitted name; a
  check keyed to it is a proxy for the behaviour rather than the behaviour, which
  is the class H95 and H103 were both about.
- **Report-only for the lock outside the directory.** It is already in the
  history, so refusing on it is a permanent floor, and a permanent floor is
  bypassed exactly as thoroughly as a flaky gate.

**`install_hooks.sh` v4** — `pre-push` added **to the list**, which is the
extension point v2's own header wrote down after v1 installed one gate and left
the next tracked, reviewed and installed nowhere. **`test_loop_gate.sh`** — same
list, so the new gate is drift-checked; it immediately printed *"pre-push
installed gate DIFFERS from HEAD — the enforcing gate exists in no commit"*,
which was true at that moment and is what that line is for.

## F3 (inertness) — did not fire: 12 assertions, 0 FAILED

`sh spikes/harness/test_pre_push.sh` performs **real `git push` commands into a
bare repository created under this spike directory** — no network, and A9
asserts the sandbox's only remote is a path inside the workspace (§10, H89).

The arms that matter are the quiet ones, because a gate that refuses everything
is bypassed as fast as one that refuses nothing:

- **A1 first, on purpose**: an ordinary push is ACCEPTED. Without it, every other
  arm is satisfied by a hook that refuses unconditionally.
- A2 refuses `.yml`, A5 refuses `.yaml`, A3 still refuses when the workflow
  arrived in an earlier commit, **A4 lets go** once the tree no longer carries
  one, A6 stays quiet on the `.md` source in the same directory, A7 accepts and
  **reports** a lock outside it, A8 survives a branch deletion's zero sha.

**Against the live repository, fed on stdin with no push performed: `rc=0`, with
the NOTE naming `.autoloop/autoloop.lock.yml.disabled`.** The fleet's authorised
pushes are unaffected.

## My own error in this cycle, kept

A5 initially reported ACCEPTED because `git rm` of the last file in
`.github/workflows/` removed the directory, so the arm wrote its fixture into a
path that no longer existed and committed nothing. **A setup failure that reads
as a passing verdict** — the same shape as H111's fixture that printed a finding
while running no gate at all, one cycle earlier, by me.

## Falsifier for THIS row

If `sh spikes/harness/test_pre_push.sh` passes with the hook's refusal branch
deleted, or if a push carrying `.github/workflows/*.yml` is accepted, this is
wrong. Runnable, and it needs no network.
