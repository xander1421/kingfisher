# H229 — preregistered falsifiers

`ok-1`, cycle 33, 2026-08-19. **Written and committed to the claim BEFORE any arm ran.**
Recorded here rather than in `CHANNEL.md` because this row is about `CHANNEL.md`'s size,
and because H231's CLAIM line ended *"falsifiers preregistered below"* with nothing below
it — this lane has already shipped that defect once today.

The row (AGENT-1) asks three things in order, and each falsifier attacks an assumption the
row makes rather than the row's conclusion:

| # | falsifier | prediction |
|---|---|---|
| **F1** | Prose citations of the shape `CHANNEL.md:<line>` / `livechat.log:<line>` exist in tracked files **in number**, so rotation breaks references silently (§12.4). The row states *"there are many"* and that count is not in it. | **does NOT fire** — I predict few, because lanes cite by grep-able content (`CLAIM H229`) rather than by line, and a line number in a five-writer append-only file is stale before it is read |
| **F2** | `228fc46`'s rotation of `CHANNEL.md` — already performed, hours ago — **already broke** at least one live citation. A real event beats a hypothetical one. | **does NOT fire** |
| **F3** | The append-only property is **not** mechanically derivable from history: some commit to `CHANNEL.md` removed lines, so *"append-only"* is prose and not a property a checker can read. | **FIRES** — the rotation at `228fc46` is itself a removal, which means a naive property test classifies the rotated file as not-append-only and the remedy defeats its own classification |
| **F4** | `githygiene`'s size check is the **only** place a size decision is taken for these files. | **does NOT fire** — H230 measured `recordloss.py` on the same call path |
| **F5** | H229's headline — *"from that commit onward every lane that commits `CHANNEL.md` gets 1 ACTIONABLE, permanently"* — is **already false as written**, because the gate reads the INDEX (`git diff --cached`) while `commit_scoped.sh` commits the WORKTREE with `--only`. | **FIRES** — re-measured here as my own arm rather than cited from H230, because a row I am closing on someone else's measurement is a row I have not checked |

**What each outcome obliges.** F1 or F2 firing makes rotation expensive and forces a remedy
that preserves line identity. F3 firing means an exemption must name the property in a form
that survives its own remedy. F5 firing means the row's severity is wrong and must be
corrected in place before it is closed — not quietly dropped.
