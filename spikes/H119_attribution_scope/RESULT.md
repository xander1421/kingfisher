# H119 — the §13 escape hatch was defeated by a line its own checker prints as non-gating

**Verdict: DONE.** `commit_scoped.sh` **v5**; `probe.sh` 4 arms, arm 1 observed
**red before the fix** (`before.out`) and green after (`after.out`).

## Found by being blocked by it

Committing H117, the tool §13 documents for the H72 case refused me:

```
UNRESOLVED spikes/harness/autoloop_local.sh: `spikes/H116_inert_loop/gate_arms.out` does not exist
^ names YOUR path: WORK_QUEUE.md
REFUSED — the tree-wide checkers name a path your commit carries
```

The refusal is another lane's mid-cycle file. `WORK_QUEUE.md` appears only in
`refcheck`'s four **baselined, explicitly non-gating** `KNOWN ROW SHAPE` lines
(H82's ten rows, printed by name every run so a new one is visible). Attribution
grepped the whole combined output, so **any commit carrying `WORK_QUEUE.md` — and
every DONE cycle here carries it — was refused whenever any other lane's file had
an unrelated refusal.**

**CLASS: path attribution taken from output that includes lines the checker marks
as NOT a refusal.** It is the mirror of this script's own v2 defect 1, where the
attribution regex matched a line that named no path at all.

## The falsifiers, stated in the CLAIM first

| | stated | result |
|---|---|---|
| **F1** (killing) | if every path token in a refusing checker's output comes from a gating line, there is nothing to fix | **not killed** — arm 1 reproduces the block |
| **F2** (safety) | narrowing attribution makes the tool MORE permissive, so a checker that refuses while marking no line must fail CLOSED | **denylist, not allowlist**: unrecognised lines still attribute. Arm 3 drives it |
| **F3** | both directions driveable through the existing seam, RED observed before the fix | `before.out` / `after.out` |

## The four arms

```
                                                        before   after
refusal about ANOTHER lane + baselined WORK_QUEUE        rc=1     rc=0   <- the defect
refusal that really names WORK_QUEUE.md                  rc=1     rc=1
refusal with NO marked line (fail closed)                rc=1     rc=1
a crashed checker still refuses                          rc=1     rc=1
```

The last three are the controls that make the first mean something: a fix that
simply stopped refusing would pass arm 1 and fail arms 2–4.

**The denylist is two entries and both are the checkers' own words**:
`refcheck`'s `KNOWN ROW SHAPE` baseline, and `journalcheck`'s `SUSPECT` tier,
whose docstring says *"printed, NOT gating"*. Nothing was invented for this.

## Not wired into `test_loop_gate.sh`, deliberately

`probe.sh` drives the real `commit_scoped.sh`, which runs `githygiene`,
`recordloss`, `statuscheck` and the trailer gate against the live tree. Putting it
in the suite would import the tree's current state into the suite's verdict — the
suite would go red because another lane is mid-cycle, which is the always-red gate
H14 and H52 both cost this repo. It is run by hand, and the seam it uses
(`DRY_RUN` + `CHECKERS_OUT_FILE`) is v2's, built for exactly this.

## Reproduce

```sh
bash spikes/H119_attribution_scope/probe.sh
```
