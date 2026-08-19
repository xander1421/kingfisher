# H207 — `CHANNEL.md` records that work was CLAIMED and has no mechanism that a claim was ever FINISHED

`ATTACKER-1`, 2026-08-19, lane launcher 33038. `certify ok=True`
(`provenance.json`), 5 controls all fired, 3 preregistered falsifiers ran,
**1 fired — F2, exactly as predicted, which is why this ships REPORT-ONLY.**

Preregistered in `CHANNEL.md` **before any code**, including the recorded
predictions *"F1 does not fire, F2 DOES fire, F3 does not fire."* All three
held.

---

## 0 · This row spent three hours being its own subject, and that is the evidence

The turn that claimed H207 **died between EXECUTE and RECORD.** It left
`idscope.py` v5 (+230 lines) and `test_h207_falsify.sh` in the working tree,
`spikes/H207_unclosed_claims/` **empty**, no `WORK_QUEUE.md` row, and nothing
committed — while `CLAIM H207 ATTACKER-1` sat in the append-only log advertising
a hold. **A later lane reading §2 SELECT would skip H207 because a lane holds
it, and no lane held it.**

That is not an anecdote about a crash. It is the exact failure this row names,
produced by the mechanism this row names, against the lane that filed it, inside
the window it was filed in. The recovering turn found it by running
`idscope.py` v5 on the live tree and reading `ROWLESS H207 is CLAIM in
CHANNEL.md and has NO WORK_QUEUE.md row` in its own output.

---

## 1 · The finding

`idscope.py` **v5**. v1–v4 asked whether a `DONE` line agrees with the queue.
**Neither direction saw a CLAIM that nothing ever closed**, and `rowless`
filters on `i not in q`, so a CLAIM on a row the queue has ALREADY closed is
dropped before any check runs.

**Live tree, `live_run.out`, at the operating point pinned in
`operating_point.out` (`CHANNEL.md` 951 lines, sha256 and `HEAD` recorded there):**

| | count | gated? |
|---|---|---|
| distinct `CLAIM` subjects in `CHANNEL.md` | **246** | — |
| **DECIDABLE-STALE** — queue row says `DONE`, log never closed it | **4** (`G31`, `H122`, `H207`, `H69`) | **no — reported** |
| in-flight-or-unfiled — counted, never scored | 13 | no |
| unkeyable subject, not id-shaped — counted, never scored | 12 | no |

**`G31`, `H122` and `H69` are `DONE` in `WORK_QUEUE.md` and `§2 SELECT` still
tells every lane to skip them.** One of them, `H122`, is mine. The fourth is
`H207` itself, and it is stale for as long as this write takes: filing the row
below made this cycle's own CLAIM decidable, and posting `DONE H207` closes it.

### This census moves under you, and every movement is attributable

Five lanes append to `CHANNEL.md` while it is being counted, so **a count of it
is a statement about an instant** — Family E, and the reason
`operating_point.out` exists at all. Three observations inside one cycle:

| when | decidable-stale | in-flight | subjects | what moved it |
|---|---|---|---|---|
| before the queue row | 3 | 14 | 245 | — |
| after I filed the H207 row | 5 | 12 | 245 | `H207` became decidable (mine); `AGENT-1` filed an `H209` row |
| pinned run | **4** | **13** | **246** | `DONE H209 AGENT-1` at `CHANNEL.md:949` closed `H209` |

**Not one of those deltas is noise.** Each is one lane's one line, and the
detector names which. The same window moved the reconciliation below (33→32
hand, 4→3 rescued) by exactly one line: `DONE H199 ok-1` at `CHANNEL.md:951`.
**A number from this instrument without its operating point is not wrong, it is
undated** — which is the defect `H206` names in `W9` and the reason it is
recorded here rather than quoted bare.

### F1 did not fire, and the evidence is the COMMITTED module, not the header

The v5 header asserts v4 cannot see this. That assertion is the kind of thing
that decays, so it was **run** (control `c4_v4_is_silent`): `git show
HEAD:spikes/harness/idscope.py` on this same tree prints **0** `UNCLOSED-CLAIM`
lines and mentions `G31`/`H122`/`H69` **0** times, while the queue calls all
three `DONE`. `statuscheck.py` reads status assertions in prose outside the
queue; `stranded.sh` reads uncommitted files. **Code was owed.**

### F2 fired, so this is REPORT-ONLY and the exit code cannot move

Every lane's current cycle has an open CLAIM *by construction* — §2 SELECT posts
the CLAIM first — so a gate on "claim without verdict" is an always-red gate,
which is H14/H52/H73/H124 four times over. v5 scores **only** the mechanically
decidable subset and **counts** the remainder rather than guessing it (H186's
excluded-and-counted discipline). That the arm cannot move the exit code is not
a promise: mutant **`m6_report_becomes_gate`** makes it gate and the suite goes
red naming *"an unclosed claim alone never gates"*.

### F3 did not fire, as predicted — the hole is named and counted

12 subjects are prose-named (`S57-fuel-branch`, `S52-correctness`,
`verifier2-attack`, `refcheck-resolver-attack`, `journalcheck-scope-attack`, …).
`DONE W5-epoch-bisect` and `CLAIM W5` share no key, so **no cross-reference is
possible for them at all.** They are reported as a count, not dropped.

## 2 · The preregistered number was wrong, and `RELEASE` is why

The CLAIM line preregistered a hand count: **32 of 235 CLAIM lines (14%)**, with
a per-lane breakdown. `reconcile.py` recomputes both sides **in one pass over
one file**, because a reconciliation whose two sides come from two programs is
not one:

```
CLAIM lines: 252   distinct CLAIM subjects: 246
  unclosed under the HAND vocabulary    [DONE, RETRACTED, WITHDRAWN]:            32
  unclosed under the SHIPPED vocabulary [DONE, RETRACTED, WITHDRAWN, RELEASE]:   29
RESCUED by treating RELEASE as a closer: 3   H109, H64, S29
```

**The hand count's closer vocabulary was incomplete.** 29 is also exactly
4 + 13 + 12 from the module's own run — **two independently written programs
agreeing on the same total, which is the only reason either number is
quotable**, and they agreed again after the tree moved under both of them.

A control decides whether that reconciliation means anything: a vocabulary that
closed *everything* would explain the gap just as well. `reconcile.py`
**exits** unless the shipped vocabulary is a strict superset that still leaves
claims accused — *"it is not a mute button."*

**And my first draft of that probe got it wrong in my own favour.** It folded
`CORRECTED` into the closer list, "rescued" `H69` — and the module names `H69`
DECIDABLE-STALE in the same run. A reconciliation that disagrees with the module
it reconciles is measuring a third thing. `CORRECTED` is now scored separately
(2 subjects: `H29`, `H69`) under the module's own DRIFT arm, because **whether
that prefix closes a claim is a vocabulary decision nobody has made, and a probe
must not make it silently on the module's behalf.**

---

## 3 · SECOND FINDING, and it is against my own instrument

### CLASS: `cmp -s` (did the bytes change?) stood in for an anchor assertion (did the INTENDED edit apply?) — the two agree on every successful edit and disagree exactly when the editing TOOL fails, so the tool's failure is scored as a finding against the module under test

Measured, not reasoned. `test_h207_falsify.sh` **v1** wrote mutant `m1` as a GNU
`c\` range command. This is BSD sed. sed exited non-zero — `extra characters
after \ at the end of c command` — and left a **zero-byte file**. An empty file
**differs from the source** (the no-op guard passed) and **compiles** (the
compile guard passed), so v1 ran it, saw exit 0, and printed:

```
FAIL m1_release_first_token: suite stayed GREEN with the logic removed
```

**A coverage gap alleged in `idscope.py`, which has none. 1 of 6 mutants, and
the failing verdict was about the wrong subject.**

`CLAUDE.md`'s Editing section names the *other* direction of this: `str.replace`
returns the string **unchanged** when the anchor is absent, so an edit fails by
doing too little of the right thing. **`sed` fails by producing too little of
ANY thing**, and nothing in the tree guarded that.

### The asymmetry underneath it, which is the part worth grepping for

**THE FAILING BRANCH HAD TO SHOW ITS WORK AND THE PASSING BRANCH DID NOT.**
`went red` required `grep FAIL` *and* `grep <want>`. `stayed GREEN` required
only `rc == 0` — which a program that never ran also satisfies.

### v2, and the two controls that keep the repair honest

Two nets, each fired by a **real** one-word sed program that exits 0:

| control | sed | v1 verdict | v2 verdict |
|---|---|---|---|
| `c1_empty_mutant` | `d` | `suite stayed GREEN with the logic removed` | `THE MUTANT IS EMPTY -- the tool produced no program to test` |
| `c2_no_suite_output` | `s/^/#/` | `suite stayed GREEN with the logic removed` | `exited 0 having printed NO suite output -- it never RAN the suite` |
| real one-line mutation | — | `caught` | `caught` |
| no mutation at all | — | `THE MUTATION DID NOT APPLY` | `THE MUTATION DID NOT APPLY` |

`guard_ab.sh` runs **both chains over the same inputs** and refuses to print the
table unless v1 accuses on both degenerate mutants, v2 accuses on neither, **and
the two agree on a real mutation and on no mutation** — without those last two
rows, v2 would be a different test wearing the name of a repair.

The two controls live inside the shipped suite, not beside it: `mutate()` now
sets a `verdict` variable that one reporting step reads, and a 4th argument
inverts an arm, **so a control exercises the shipped guard chain rather than a
copy of it.** `test_h207_falsify.sh` v2: **6 → 9 checks, 9 passed, 0 failed.**

### Class sweep — 1 live instance, 3 latent, 1 already guarded

`noop_probe.py` applies every mutation in each unguarded sibling driver to
today's source and asks whether it is a **no-op**, which those drivers score as
*"the check is INERT"* — the same false accusation in the other polarity.

```
H114_status_decay/falsify.py         5 mutations, NO-OP: 0
H85_check6_scope/falsify.py          2 mutations, NO-OP: 0
H94_record_loss/falsify.py           6 mutations, NO-OP: 0
H88_sentinel_branch/h98_falsify.py   EXCLUDED -- asserts `V3_LOOP in src` and `text != src`
0/13 mutations across 3 unguarded drivers are NO-OPS against today source
```

**The class is LATENT at those three sites and was LIVE only at mine.** They are
not touched here: they are other lanes' spikes, they are correct today, and
§12.1 says a harness defect is a queue row and not a side fix. Filed as **H217**
for whoever owns them — the id is `sh spikes/harness/allocid.sh H` **read into
this document**, and it caught me: this paragraph said `H211`, typed from memory,
which is precisely the error H206's own row records its author making twice in
three cycles. A rule you can quote and still break is a rule you have not
mechanised, and reading the allocator's output is the mechanisation.

`test_h13`, `test_h16`, `test_h51`, `test_h57`, `H7/falsify.py`, `H41`,
`M1_9/mutate.py` and `H88/h98` all assert their anchor or their restore.
**v1 was the only driver in the tree using a tool with the empty-output failure
mode.** The probe **refuses** rather than publishing a clean sheet: zero
mutations parsed exits `VOID: no mutation parsed, so 0 no-ops is a statement
about this probe` — and it fired for real on the first run (`NameError:
__file__`), which is the only reason the `0/13` above is worth reading.

---

## 4 · Errors this cycle, at the cause

1. **The reconciliation probe folded `CORRECTED` into the closer list** and
   produced a number that contradicted the module in the same run. Caught by
   cross-checking against the module instead of reading the probe's own output.
2. **`certify` refused three times and every refusal was correct**: `deps` must
   be directories (naming a file *"silently produced a fake dirty verdict"*);
   five controls and three falsifiers with no `null_must_contain`; nine
   artifacts resolved against the CWD rather than the repo root — *a check whose
   verdict depends on where you stood is family B.* **That third one is not a
   novel observation and is not claimed as one: `WORK_QUEUE.md` **H211**, filed
   by another lane, is that exact class against `provenance` itself. My refusal
   is one more instance of a row already open.**
3. **My own §10 scratch gate refused a `/tmp` redirect** written while probing
   this defect. Rerouted to `.scratch/`, not widened.

## 5 · Falsifier

A run of `idscope.py` **v4 as committed** naming any of `G31`/`H122`/`H69`, or a
sibling falsifier driver already refusing a degenerate mutant, would have
refuted this row before a line was written. Both were run. Neither did.

## 6 · Reproduce

```sh
python3 spikes/harness/idscope.py --selfcheck        # count from selfcheck.out, never quoted here
python3 spikes/harness/idscope.py                    # live tree
bash    spikes/harness/test_h207_falsify.sh          # 9 mutants/controls
bash    spikes/H207_unclosed_claims/guard_ab.sh      # v1 vs v2, same inputs
python3 spikes/H207_unclosed_claims/reconcile.py     # 33 hand / 29 shipped
python3 spikes/H207_unclosed_claims/noop_probe.py    # class sweep
python3 spikes/H207_unclosed_claims/certify_h207.py  # ok = True
```
