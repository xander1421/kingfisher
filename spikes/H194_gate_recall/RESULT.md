# H194 — I measured the §10 gate's precision five times and its recall never once

**ATTACKER-1, 2026-08-19.** Attack on `scratchcheck.py` v2 — **my own module,
fifteen minutes after shipping it in the same cycle.** `certify ok=true`, 4
controls all fired, **all four preregistered falsifiers RAN AND NONE FIRED.**

**Recall as attacked: 7 of 12. Recall repaired: 10 of 12.** The 2 still missed
are the residue v2 had already named in its own docstring.

---

## The class

> **A PRECISION FIX MEASURED ONLY IN THE DIRECTION IT WAS MADE.**

H89 shipped v2 after five rounds of false-positive work — census 29 → 24 → 18 →
17 → 16, every removal individually verified, all 8 originals kept as negative
controls. **Not one of those rounds constructed a write the gate SHOULD catch and
does not.** Precision was measured five times; recall was never measured at all,
and a gate that refuses nothing passes a precision audit perfectly.

## Four falsifiers, all measured on the committed v2 blob `310e800`

| | fires when | result |
|---|---|---|
| **F1** | the three unnamed misses do NOT reproduce through the live hook contract | **quiet** — 3 of 3 reproduce end-to-end through the real JSON payload, and the hook agrees with the helper on all 12. So this attacks the gate, not a function |
| **F2** | covering `cd` costs a false positive on real commands | **quiet** — **0 hits across 6,454 real command lines** from the tracked tree plus every negative control. **This REFUTES my own recorded prediction that F2 would fire**, so `cd` is a defect and not a scope statement, and the rule was adopted on that measurement rather than on my expectation |
| **F3** | the repair changes the verdict on any existing check | **quiet** — 23 v2 controls rechecked under v3, **0 changed**. A repair, not a behaviour change |
| **F4** | v2 without quote-awareness misses at least as many as v2 with it | **quiet** — without: **3 misses**; with: **5**. **v2's own quote-awareness fix drilled two holes.** I predicted one (`escaped_quote`); it drilled two |

**A METHOD POINT THAT COST TWO REWRITES OF THIS PROBE AND IS THE THIRD INSTANCE
IN TWO CYCLES.** A falsifier written to test v2 and then evaluated against the
*repaired* module silently becomes a regression check with the opposite meaning:
F1 asks *"are these misses real?"* and after the fix it necessarily answers
*"no, they are caught"* — which reads as the row being withdrawn when in fact it
was acted on. My first probe printed `F1 FIRED` for exactly that reason, and F4's
first form asserted *"the neutralisation did not reach the code"* because v3
fixes the same cases by a different route. **Every preregistered falsifier is now
evaluated by loading the module AS IT EXISTED AT `310e800`**, `exec`'d with
`__file__` pointed at the real harness path so it computes the same `ROOT` — a
copy under another directory would silently change what `outside()` means, which
is the entire predicate.

## The five defects, D1–D5

* **D1 · `_in_quotes` ignored backslash escapes.** A `\"` inside a double-quoted
  string desynced quote state and the following redirect read as quoted —
  **missed write**. Single quotes take no escapes, which is what the shell does.
* **D2 · a comment line in a multi-line command poisoned every line below it.**
  An apostrophe in `# don't` opens a span that never closes. **v2 put the comment
  skip in `scan_source` only, on my written reasoning that "a comment cannot
  reach the hook, which is handed a whole command." That reasoning was wrong** —
  a multi-line Bash command carries comment lines and they reach the hook.
  Running it is what showed that; reading it back three times did not.
* **D3 · `cd <outside> && <relative write>` was invisible.** Not residue I had
  named — a plain, natural way to write outside the tree. Adopted only after F2.
* **D4 · `mktemp` matched as a bare word**, so any command merely *mentioning* it
  was refused: `grep -v mktemp scan.out` is a read. **Pre-existing since v1, and
  found the only way it could be — the gate refused my own command while I was
  investigating its own census.** This is exactly what C2 ("reads are not
  writes") exists to prevent, at the one rule C2's corpus never covered.
* **D5 · the heredoc stripper is a SHELL lexer and it was being run on `.py`.**
  See below; it is the largest of the five.

**D1 and D2 were drilled by v2's own quote-awareness fix.** D4 says something
sharper about D1–D3's evidence: recall was measured on 12 *constructed* commands
and precision on source lines plus nine *hand-written* negatives, and **neither
corpus contained the commands this lane actually types.** Both numbers are floors.

## D5, and it is the one to steal

`versioncheck.strip_heredocs` is a shell heuristic. Python has no heredocs, so on
a `.py` file the pattern matches a **prose mention** of `<<'EOF'` inside a
docstring and blanks every line to end of file.

**Measured over the tracked tree: 1,048 non-blank Python lines blanked, plus 354
in shell. 91.3% of the gate module itself — triggered by my own v2 rationale
block describing the heredoc defect — and 95.9% of `recordloss.py`, 52.3% of
`versioncheck.py`.** The census read **17** while **28** write positions were
reachable. An under-report that looks exactly like compliance.

All three available answers are wrong in a way the total cannot show, so all
three were run:

1. **strip heredocs from `.py`** → 1,048 lines invisible, census 17.
2. **don't strip** → census 24, and **all 7 new rows are this module's own
   docstring prose and fixture lists** — which is `versioncheck.py` v1 flagging
   its own test suite, the exact defect `strip_heredocs` was written for.
3. **skip Python string literals via `ast`** → works, and is wrong: a shell
   command embedded in a `.py` *is* a string literal, so it would blind the scan
   to Python entirely while still printing a number.

**The instrument is a shell classifier.** On a `.py` it can only ever find shell
embedded in strings, and in this tree that is fixtures. So Python is now
**EXCLUDED AND COUNTED IN THE OUTPUT**: `17 write position(s) ... in 98 shell
file(s)` / `NOT SCANNED: 340 non-shell file(s)`. That is **H186's distinction** —
a thing absent from a sweep's own "N excluded" line cannot be told from a thing
that is not there. What no shell classifier can see is named rather than left
implied and **filed as H198**.

## Controls

**C1 recall moved 7→10 of 12**, both endpoints measured on pinned artifacts.
**C2 no existing verdict changed** — 23 of v2's own controls rechecked, 0 flipped.
**C3 per-fix mutation** — M3 reverts D1, M4 reverts D2, M5 reverts D3, and each
must take *only its own case* red; a single mutation that reddens everything
proves the module runs and nothing else. **D2's fix first shipped INLINE, where no
mutation could reach it, and was lifted to a module flag purely so this control
could exist** — a fix whose control cannot be constructed is the shape this lane
keeps finding in other lanes' suites. **C4 census in both directions** — 16 → 24
→ 17 across the three treatments, because a census that returned the same total
under all three would be measuring nothing.

`--selfcheck` is **50 checks, 0 failed**, discovered by `selfcheckall.py` on the
launchd sweep.

## The gate blocked its own investigation four times, and that is data

Twice legitimately-fixable (the RESULT.md heredoc write → D2's cause; `grep -v
mktemp` → D4) and twice as a correct-by-rule refusal of a command that *quotes* a
write for testing. **The gate was never disabled to get past itself** (brief §9);
every one was routed through `.scratch/`, the sanctioned location H89 created.
The workaround is one file and cheap — but four refusals of one lane in one cycle
is the honest precision signal on *agent* traffic, which is the corpus that was
never measured, and it is reported here rather than left as an impression.

## An error worth its own line

**I typed `H195` into the module before allocating it.** `sh
spikes/harness/allocid.sh H` returned **H198** — other lanes had taken the
numbers while this cycle ran. Corrected before commit. §12.4 and H18: an id is
allocated, not assumed, and I assumed one while writing a row about instruments
that report confidently and wrongly.

## Filed, not fixed

* **H198** — Python-side writes (`open(p,'w')`, `tempfile.mkdtemp()`,
  `os.makedirs`) are invisible to any shell classifier. 340 non-shell files.
* **`versioncheck.py` blanks the files it checks.** D5's measurement says 52.3%
  of `versioncheck.py` and 95.9% of `recordloss.py` are blanked before its
  version-header scan runs, so a rationale block below a prose mention of a
  heredoc is invisible and a stale header reads as OK. **This compounds H193**
  (it cannot see docstring headers either). Both belong to the same module and
  the same cycle should take them; **not fixed here — §12.1, and it is my own
  module twice over, which is the A22 shape.**
