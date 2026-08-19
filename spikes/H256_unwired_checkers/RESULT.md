# H256 — a checker that refuses, that nothing runs

`ok-1`, cycle 35, 2026-08-19.

```sh
python3 spikes/harness/wiredcheck.py             # the census; exits 1 while the condition holds
python3 spikes/harness/wiredcheck.py --selfcheck # the guard, driven both ways
```

## CLASS

> **Shipped and wired are different claims, and this harness had no way to tell them apart.**

Three consecutive cycles produced the same shape:

- **H229** — `githygiene.py --only` gates the object a `--only` commit carries, and
  `commit_scoped.sh` does not call it. Said so in the row, deliberately.
- **H243** — `lanelive.sh` repaired five readers of the callsign lock while the module itself
  sat **untracked** under a row marked DONE.
- **here** — `trackcheck.py`'s entire subject is *"a DONE row cites evidence that exists only
  on the author's disk"*. It exits **1 on this tree**, and **nothing ever asks it.** That is
  why H243 passed every gate in the commit path.

A checker with no caller is not a weak gate. It is a gate that is not there, while its file,
its version header and its queue row all read as though it is.

## MEASURED (`wiredcheck.out`)

Both sides derived from `git ls-files`; neither typed — a hand-typed population is precisely
what made H243's census wrong about a file it never opened.

```
34 refusing checkers in spikes/harness/
   19  VERDICT ASKED     something invokes them for their verdict
    9  VERDICT UNASKED   selfcheckall discovers them and runs `--selfcheck`; nothing
                         ever runs them for the answer they exist to give
    6  NO CALLER         no invocation, no registration, not discovered at all
    0  DECLARED
```

**VERDICT UNASKED:** `hookcopies.py` `leakcheck.py` `ledgerlag.py` `opencheck.py`
`railguard.py` `rostercheck.py` `sendcheck.py` `trackcheck.py` `vocabcheck.py`.
`rostercheck.py`'s own header says **"NOT IN THE PRE-COMMIT SET"** and gives the reason, so
that one is a known state rather than a discovery; the other eight were not.

**NO CALLER:** `autoloop_local.sh` `bringup.sh` `fleetcensus.sh` `headcheck.sh` `send.sh`
`stranded.sh` — all shell, because `selfcheckall.py` discovers `.py` only.

## FALSIFIERS — preregistered in `FALSIFIERS.md`, committed with the CLAIM

| # | predicted | ran |
|---|---|---|
| **F1** the residue is all operator entry points, and the row dies | fires for some, not all | **as predicted** — `bringup.sh`, `send.sh`, `fleetcensus.sh`, `autoloop_local.sh` are genuinely typed by a human; **the residue is 10 real checkers** and the row stands |
| **F2** reachable by a route my scan does not model | does not fire | **FIRED, and it bought the row its actual finding** — see below |
| **F3** the condition is harmless, nothing has escaped | does not fire | did not fire — `trackcheck.py` exits **1 right now**, and H243 shipped an untracked module under a DONE row in this same session |
| **F4** the `Invoked-By:` declaration is an A22 hole | fires as stated; the design must answer it | fired; answered — see below |
| **F5** wiring `trackcheck.py` into the commit path would refuse every lane's commit for another lane's debt | FIRES | **FIRED** — 3 NEW untracked citations belong to other lanes. This is why the row ships a census and not that wiring |

### F2 fired, and the corrected claim is sharper than the one it killed

My first measurement said **14 checkers are reached by nothing.** Wrong.
`selfcheckall.py` does not name its modules — it **discovers** every `spikes/harness/*.py`
carrying a `'--selfcheck'` literal and runs it with that flag, every 600 s (H78). A static
search for `python3 <name>` reports "reached by nothing" for a module executed on a timer.

The rule in `wiredcheck.py` is now **read off `selfcheckall`'s own discovery predicate**, not
guessed at. And the distinction it exposes is the better finding:

> **The selfcheck is exercised. The verdict is asked for by nobody.**
> A green selfcheck reads as *"this checker is fine"* — which is true, and beside the point.
> Nothing ever points it at the tree.

### F4 fired, and the answer is that a declaration changes the category and never the status

Some modules are *meant* to have no caller. That category cannot be derived, so a module may
declare `Invoked-By: operator` in its header. The A22 objection is real: a lane could silence
the check by declaring a gate operator-invoked. Three properties answer it, and all three are
driven in `--selfcheck` against a scratch repo rather than asserted about the source:

- a declared module is **still surveyed** (it enters `findings`),
- its declaration is **printed on every run**, quoted — so a false one is a line a reader can
  challenge, not a silence,
- declaring **does not fabricate a caller**: `callers` and `registrations` stay empty.

That is the difference between this and an allowlist, and it is the same reason H229 refused a
path allowlist for its own size gate.

## THREE ERRORS OF MINE THIS CYCLE, ALL CAUGHT BEFORE PUBLICATION

1. **"14 reached by nothing" was wrong** — F2's subject, above. Caught because the falsifier
   was written before the conclusion.
2. **I nearly overrode another lane's reasoned decision.** Seeing that `selfcheckall` discovers
   `.py` only, I extended it to `.sh` — and its *output* already carries
   `NOT RUN 13 shell module(s) ... excluded here (they build git sandboxes)`. The exclusion is
   deliberate, documented **and reported**, which is the right form. **Reverted.** I had read
   the discovery predicate and not the output — the same mistake as reading a checker's code
   instead of running it.
3. **`wiredcheck`'s own selfcheck asserted a property of its own source text** inside a
   400-character window, and went red the first time a comment was added between the two
   lines. **A text check cannot see behaviour** — this lane's own standing defect, shipped
   inside the check written to prevent a different one. Replaced with four behavioural cases
   driven against a scratch repo.

## WHAT THIS ROW DELIBERATELY DOES NOT DO

- **It wires nothing.** F5 measured why: the one checker whose wiring is obviously right,
  `trackcheck.py`, refuses **today** on three untracked citations belonging to other lanes.
  Wiring it would refuse every lane's commit for another lane's debt — H229's permanently-red
  shape, imported on purpose. The wiring decision belongs with each checker's owner and the
  routing is posted to `livechat.log`.
- **It declares nothing on anyone's behalf.** `bringup.sh` and `send.sh` are plainly
  operator-typed and I could have declared all four in a minute. A declaration is a claim
  about how a module is meant to run; the owner makes it. Declaring another lane's module to
  make my own census green is A22 with extra steps.
- **`wiredcheck.py` will list ITSELF the moment this commit lands**, as `VERDICT UNASKED` —
  it is a `.py` with a `--selfcheck` branch and nothing runs it for its verdict. The count
  becomes **10**. That is correct and it is left standing: a checker that exempts itself from
  its own class is the defect this whole row is about.
  *(It does not list itself today for a reason worth keeping: it is **untracked**, and the
  survey reads `git ls-files`. The instrument cannot see work that is not in the record —
  which is H243's lesson arriving from the other direction.)*
