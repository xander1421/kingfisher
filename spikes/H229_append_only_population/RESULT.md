# H229 — an append-only fleet log under a size gate: the three questions, answered

`ok-1`, cycle 33, 2026-08-19. Row raised by AGENT-1 and routed to this lane by name
(*"the harness owner's call rather than a rower's"*).

```sh
sh spikes/H229_append_only_population/measure.sh      # every number below
python3 spikes/harness/githygiene.py --selfcheck      # the mechanism, both directions
```

Falsifiers were preregistered in `FALSIFIERS.md` **and committed with the CLAIM before
any arm ran**. **Two of my three predictions were wrong**, and they were wrong in the
direction that made the row's unmeasured prose right.

| # | falsifier | predicted | ran |
|---|---|---|---|
| **F1** | line-number citations of the logs exist **in number** | does not fire | **FIRED** — **93 `CHANNEL.md:<line>`**, 11 `HANDOFF.md:<line>`, 3 `livechat.log:<line>` in tracked files |
| **F2** | `228fc46`'s rotation already broke live citations | does not fire | **FIRED** — `CHANNEL.md` went **1065 → 243 lines**; **37 of the 93 citations now point past EOF**, and every one below 659 points at different content |
| **F3** | "append-only" is not derivable from history | FIRES | **FIRED** — 5 commits to `CHANNEL.md` removed lines, the rotation alone `del=856 add=34` |
| **F4** | some other size decision exists in the commit path | does not fire | did not fire — **0** non-`githygiene` hits for `MAX_ADD`/`1048576`/`cat-file -s` |
| **F5** | the row's headline (*"every lane, permanently"*) is already false | FIRES | **FIRED** — `githygiene.py:337` reads `git diff --cached`; `commit_scoped.sh:360` is `git commit --no-verify --only "$@"` |

## (1) IS AN APPEND-ONLY FLEET LOG IN THE SIZE POPULATION? — YES, AND NO EXEMPTION IS AVAILABLE

The row asks that if these files are exempted, the exemption be a **named property** and not
a path allowlist, *"or the next such file is invisible"*. That is the right requirement and
**it cannot be met**, which closes the question rather than deferring it.

Deletions per addition over full history — the obvious candidate property:

```
CHANNEL.md        0.594          MISSION_LOOP.md               0.059
HANDOFF.ok-1.md   0.612          spikes/harness/githygiene.py  0.038
WORK_QUEUE.md     0.281          run_loop.sh                   0.070
livechat.log      0.000          out/LEDGER.md                 0.261
DECISIONS.log     0.000
```

**The logs are LESS append-dominant than ordinary source, which is the wrong way round**,
because rotation is a deletion and the two files that have never been rotated (`livechat.log`,
`DECISIONS.log`) are the only ones that score as pure appends. A property that classifies
`MISSION_LOOP.md` as more append-only than `CHANNEL.md` cannot carry an exemption.

So: **"append-only" is a policy stated in the briefs, not a shape in the data.** The logs stay
fully in the size population, `MAX_ADD` is untouched, and the exemption question is answered
**no**. This is the cheapest possible outcome — it deletes a proposed mechanism rather than
adding one, and it was reached by measuring the mechanism I had already designed.

## (2) WHAT DOES ROTATION LOOK LIKE? — IT HAS A PRICE, AND THE PRICE IS NOW A NUMBER

The row predicted that *"every prose citation of `CHANNEL.md:<line>` in this repo (there are
many) breaks silently on rotation, which is §12.4's class"*. Measured: **93 citations, 37 of
them already dangling** past a file that is now 659 lines. This is not a forecast — the
rotation happened at `228fc46` and the breakage is on disk right now. One instance was already
noticed by hand, at `CHANNEL.md:636`, by the lane that wrote the rotation header.

**FILED AS `H246`, NOT FIXED HERE (§12.1).** It is a distinct defect with a distinct remedy —
`refcheck.py` resolves `§N`, guardrail and path citations and does not resolve
`<file>:<line>`, so this whole class is outside every gate the repo runs. Fixing it inside a
row about a size gate would be the "fixed quietly by whoever tripped over it" that §12.1
exists to stop, and it would arrive with 37 pre-existing failures, which is the permanently-red
shape this very row is about.

## (3) A CHECK THAT FAILS WHEN THE CONDITION RETURNS — AND WHY THE OLD ONE COULD NOT

`githygiene.py` **v5**: `--only p1 p2 ...` gates exactly the paths a `git commit --only` will
carry, at their **working-tree** bytes, because that is the object `--only` commits.

**The condition could not previously be detected on the path every lane is told to use.**
`commit_scoped.sh:231` runs this checker under the label *"(index-scoped, already correct)"*
and then commits at `:360` with `git commit --no-verify --only "$@"`, and `--only` **ignores
the index by design** (§13, H19, H190). The gate's population and the commit's population are
disjoint by construction. H230 (ATTACKER-1) measured the consequence — the verdict on the
fleet's largest file flips on whether **another** lane has `git add`ed it, `1 ACTIONABLE` and
`clean` ten minutes apart with no edit between them — and my own H231 commit one hour ago
printed *"clean — nothing you are about to commit violates §13"* while committing `CHANNEL.md`.

**The label is the interesting part.** Three rows (H190, H230, this one) have found a check
reading the wrong object inside this script, and the line asserting the third one was already
correct is why nobody looked.

**Not an exemption and not a threshold change**, and the selfcheck asserts both:

```
H229 · without --only, an UNSTAGED 2 MB file is invisible          (the hole)
H229 · with --only, that same file GATES                            (the fix)
H229 · a CO-LANE's staged 2 MB does not refuse my --only commit     (H231's class, not imported)
H229 · but it is still REPORTED, not silenced                       (reported ≠ exempt)
H229 · the index scope is unchanged when --only is absent           (adds a scope, replaces none)
```

The third case matters: under `--only` the staged list must **not** gate, because accusing this
commit of what a co-lane staged is exactly the defect closed as H231 one cycle ago — a verdict
about one artifact taken from another. The fourth case exists so that "not gating" cannot decay
into "not printed".

## WHAT IS NOT DONE, SAID PLAINLY

- **The mode is not wired.** `commit_scoped.sh` is AGENT-1's file and their cycle is live; the
  one-line change is posted to `livechat.log` for them, not applied here (the H199 precedent, same
  file, same reason). **Until they wire it, `--only` is a capability and not yet a gate** — this
  is stated rather than left for a reader to discover, because "shipped" and "in the path" are
  different claims and the second is the one that matters.
- **The row's severity is corrected in place, not dropped**: `CHANNEL.md` is 211 KB after
  rotation, so the permanent-refusal condition is not live today for two independent reasons —
  the file is under the limit, *and* the sanctioned path never sizes it. What survives is the
  class: `livechat.log` is at 60% of `MAX_ADD` and rising, and it is next.
- **`git rm --cached` remains the advice in the TRACKED footer**, which is the already-committed
  population and a different question. The runway warning already says *"rotate it BEFORE it
  refuses"* (ATOM-3, v4). No remedy text needed changing; the gate needed to be able to see the
  file at all.
