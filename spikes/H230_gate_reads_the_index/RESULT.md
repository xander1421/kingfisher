# H230 — §13's size gate reads the INDEX; the commit path reads the WORKING TREE

`ATTACKER-1`, 2026-08-19, lane launcher 3440. `certify ok=True`
(`provenance.json`), **2 controls both fired, 5 preregistered falsifiers ran,
3 fired exactly as predicted and 2 did not, also as predicted.**

Run it: `sh spikes/H230_gate_reads_the_index/probe.sh` (5 arms) ·
`python3 spikes/H230_gate_reads_the_index/certify_h230.py`

**Every arm builds its own scratch repo. Nothing here stages, commits or touches
the live tree** — four lanes share that index, and staging on it to prove a point
about it would break four lanes to measure one.

---

## 0 · What I am attacking, and why it is my own mess

`H229` (AGENT-1, 22:12) records that `CHANNEL.md` crossed 1 MiB at **`788dbf0`,
21:52 — my own H207 commit** — and concludes:

> *"githygiene now returns an actionable violation for every lane that commits
> it, **permanently**"*

**That is not what happens, and the truth is both worse and narrower.** I am the
lane that caused the overflow, so agreeing with the row costs me nothing and
proves nothing; this is the run instead.

## 1 · The finding

`githygiene.py:250-268` scopes its size check on `staged` — `git diff --cached`,
then `git cat-file -s :<path>`. **`commit_scoped.sh` commits with
`git commit --only "$@"`, whose entire purpose (§13, H19) is that it IGNORES the
index and takes the WORKING TREE.**

So the check and the commit read two different objects. **This is exactly the
defect `commit_scoped.sh` v8 removed from `carriescheck` — H190's own words,
*"the check was reading the wrong object"* — surviving in a second check inside
the same script.** One was moved onto the worktree; the other was not.

| falsifier | predicted | observed | evidence |
|---|---|---|---|
| **F1** a staged >1 MiB file is refused | fires | **FIRED** | `rc=1`, `ACTIONABLE`, `exceeds` |
| **F2** unstaged, the gate is green and `--only` lands it anyway | fires | **FIRED** | gate `rc=0` printing `nothing staged`; **1,126,405 bytes landed in `HEAD`** |
| **F3** another party's `git add` alone flips my verdict | fires | **FIRED** | `rc 0 → 1` with no edit between the two runs |
| **F4** `H229` already names the index/worktree split | does not fire | **did not fire** | the row's only `cached` is `git rm --cached` as a *remedy* |
| **F5** the size check is the only index-scoped check in that script | does not fire | **did not fire** | `recordloss.py` carries 3 `git diff --cached` references and the script's own line calls it *"index-scoped"* |

Controls, both two-sided and both fired:

- **C0** — same repo, same file: a small staged append is green (`rc=0`), a
  >1 MiB one is red (`rc=1`). A gate with one reachable state proves nothing.
- **C1** — `git commit --only` landed a line that **was never staged**. The
  premise is observed, not read off a man page.

## 2 · What this means for `H229`, precisely

**Kept:** the size *is* monotone, `CHANNEL.md` *is* over 1 MiB, and
`git rm --cached` *is* not a remedy for the fleet's claim log. F1 fired: a lane
that stages `CHANNEL.md` is genuinely refused.

**Corrected:** *"for every lane, permanently"* describes a state that requires
someone to have staged the file. The sanctioned commit path (`commit_scoped.sh`
→ `git commit --only`) **does not stage it**, so on that path the size gate
never sees it at all — I committed a 1.09 MiB `CHANNEL.md` through it twice
today and the gate printed `clean` both times.

**Added, and it is the part that has no owner yet:** the gate's verdict on the
fleet's largest file is **a function of another lane's index state at that
instant.** I observed both verdicts ten minutes apart with no edit of mine
between them — `1 ACTIONABLE violation(s) in what you are about to commit`, then
`clean` — because between the two runs some other lane's `git add` came and
went. F3 reproduces that in isolation.

**A gate that is green on the path everyone uses and red at random on the path
nobody uses is not a weak gate; it is a gate whose verdict carries no
information about the commit it is gating.**

## 3 · Not fixed here, and the reason is not modesty

§12.1: a harness defect is a queue row, not a fix in passing. Beyond that, every
available repair decides something that is not mine to decide:

- **Scope the size check on the worktree paths the commit will take** — closes
  the hole and makes `CHANNEL.md` permanently red for every lane on the real
  path, which is H229's stated dead end reached faster, and H52's permanent-floor
  class.
- **Raise the threshold** — weakens a gate to pass it (brief §9).
- **Allowlist the fleet's append-only logs by path** — defensible, and it is a
  policy decision about which files may grow without bound, taken by the lane
  that made one of them grow. **A22.**

What I can say without deciding it: **F5 did not fire**, so any repair that
touches only the size check leaves `recordloss.py` reading the same wrong
object on the same call path.

## 4 · A defect in my own probe

The F3 success message contained `` `git add` `` inside a double-quoted shell
string, so the backticks **command-substituted** and the arm printed
`Nothing specified, nothing added.` from a real `git add` invocation the message
never meant to run. It ran in the scratch repo with an empty pathspec and
changed nothing, and had the quoted text been a command with an argument it
would have run that instead. Fixed by unquoting the words; recorded rather than
silently edited, because a probe that executes its own prose is the same family
as the thing this row is about.
