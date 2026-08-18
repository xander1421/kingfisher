# H106 — the only enforcing gate in this repo is installed by a truncating write, and it refused a live commit

**AGENT-2, 2026-08-18. ATTACK on the loop (§12.8), and I did not go looking for
it: it refused my own commit.** `certify ok=true`, 3 controls, 2 falsifiers
stated in `CHANNEL.md` before the decisive run. **Neither fired.**

## The observation

```
.git/hooks/pre-commit: line 252: unexpected EOF while looking for matching '"'
```

`git commit` for the H100 retraction was **refused by a shell syntax error
inside the gate**. One command later, `bash -n .git/hooks/pre-commit` was
**clean**, both installed gates were **byte-identical to their tracked
sources**, and the retry passed as `06efe7e`. **A gate that refuses a commit and
is provably sound a second later has refused for a reason no lane can
diagnose** — and the lane's only visible option is `--no-verify`, which is how a
gate stops being a gate.

Corroboration measured before the row was claimed: `.git/hooks/pre-commit` and
`spikes/harness/pre-commit.hook` both carry mtime **11:44:43** — a lane edited
the source and installed it — and the refused commit sits inside that minute
(the successful retry is timestamped 11:45:05).

## The class, and the grep that shrank the row

**A shared executable is replaced by an in-place truncating write, so any
process executing it during the window runs a partial file.**
`install_hooks.sh` v2 line 35 is `cp "$src" "$dst"`. `cp` opens the destination
with `O_TRUNC` and streams into it. **Five lanes are instructed to run this
installer after any pull (`prompts/AGENT-2.md` §7) while all five commit
continuously.**

§12.2 says fix the class, not the site, so the harness was grepped **before**
the row was claimed — and the answer makes the row smaller, not bigger:

| | count |
|---|---|
| `cp`/`install` calls in the harness | **21** |
| of those, writing into a `mktemp -d` fixture no other process executes | **20** |
| **live instances** | **1** — `install_hooks.sh:35` |

The four `> roster.txt` writes in `test_loop_gate.sh` are under the `cd "$T"` at
line 74 and are scratch, not the repo's roster. **Checked rather than assumed: a
`> roster.txt` in the repo root would have been the larger finding, and I would
rather have found that one.**

## Measured before repairing anything

One writer looping the installer over this repo's own `pre-commit.hook`
(13,863 bytes), one executor looping `sh -n` on the live path, 6 s per arm:

| arm | executions | parse failures | writes |
|---|---|---|---|
| `cp` run 1 | 1,120 | **31** | 52,313 |
| `cp` run 2 | 1,196 | **21** | 58,607 |
| **`mv` (rename(2))** | 1,167 | **0** | 24,642 |

Sample failure, from the cp arm, on a copy of the real gate:
`live.sh: line 126: syntax error near unexpected token '('`.

- **F1** *if the `cp` arms produce zero partial reads, the mechanism is wrong
  and I publish the observation with its cause unattributed.* **Did not fire** —
  52 failures in 2,264 executions.
- **F2** *if the `mv` arm's failure rate is not zero, the fix is fiction*
  (H95's F4, another lane's shape, taken deliberately). **Did not fire** — 0 in
  1,167.
- **C1** each arm parsed successfully many times, so a zero is not an executor
  that never executed (A15) · **C2** each arm rewrote the live file thousands of
  times · **C3** two independent `cp` runs agree on the sign.

**Ceiling, recorded in `race.json` and not only here:** the arms are matched on
wall clock and executor load, **not on write count** — rename costs a copy plus
a rename, so the `mv` arm writes ~45% as often in the same 6 s. It does not
rescue the zero: **rename(2) has no window at all, so its exposure is zero at
any write rate**, while `cp`'s grows with it. Said plainly because a reader
comparing 52-in-2,264 against 0-in-1,167 is entitled to know the denominators
are not the same experiment.

## The fix, and the check that fails when it breaks (§12.3, §12.7)

`install_hooks.sh` **v3**: write a **sibling** temp, `chmod +x` it, `mv -f` it
into place. Sibling and not `$TMPDIR` on purpose — **rename across filesystems
is not atomic and would reintroduce the defect quietly.** `chmod` happens before
the file is visible under the live name, so no executor sees a non-executable
gate either.

```sh
sh spikes/harness/install_hooks.sh --selfcheck
```

**The defect is invisible to a content comparison — v2 and v3 install
byte-identical files.** What separates them is whether the destination is the
*same file* afterwards: truncate-in-place keeps the **inode**, replace-by-rename
does not. So the inode is the observable. The selfcheck asserts it changes on
reinstall, asserts the result is executable, and carries a **positive control**
that a deliberate `cp` leaves the inode unchanged — without which the test could
not fail (A15) and would pass over a reinstated `cp`.

Installed and verified: both gates identical to source, executable, no leftover
`*.tmp.*`.

## Files

`race.py` (both arms, controls, `certify`) · `race.json` · `provenance.json`,
and the fix in `spikes/harness/install_hooks.sh` v3 with its rationale block.

```sh
python3 spikes/H106_hook_install_race/race.py     # ~18 s, ok=true
sh spikes/harness/install_hooks.sh --selfcheck    # deterministic, no timing
```
