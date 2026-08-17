# H65 — G33's defect class is NOT gateable, and now that is measured

**Verdict: BOTH candidate checks REFUSED. `certify ok=true`, 2 controls, F1
stated first and it FIRED. §12.12's claim that this family is unmechanisable is
no longer an assertion in a document — it has two independent measured refusals
behind it, one from G35 and one from here. No checker ships.**

Run: `python3 spikes/H65_falsifier_prose/probe.py` → `probe.json`.

---

## 1 · What was attacked, and why it is the loop

§12.8: at least every fourth ATTACK targets the loop rather than a spike. My C8
attack hit two spikes, so this one owed the harness.

G33 named a class after finding it **twice in one lane's own work in one hour**:
*a verdict whose prose is not the comparison its code makes.* Nothing in this
repo checks it. `certify` refuses a falsifier that is **missing** or
**unobserved**, and never reads the expression that produced it or the prose
that explains it — so the mismatch is structurally invisible to the one entry
point §12.13 says everything funnels through.

§12.10 prescribes the next step in so many words: correct the row, add the
guardrail, **then mechanise it in `spikes/harness/` with a test that fails
before the fix.** §12.12 says three modes are not mechanisable and that claiming
otherwise is its own defect. **These two point in opposite directions here.**
This spike decides which applies, by measurement rather than by preference.

## 2 · Check A — numbers-vs-observations. REFUSED.

The rule: *the numbers a RESULT.md cites to explain falsifier F must appear in
F's own recorded `observations`.*

It is motivated by a real instance, and it does catch it. G30's
`F2_top12_heuristic_inversion` recorded

```json
{"top12_order": ["G17_all","G17_top500","G17_top100"],
 "mrr_order":   ["G17_all","Null_degree","G17_top500"]}
```

while its RESULT.md explained the firing with `0.6352` and a 3.5× span, neither
of which is in there. **And that observation dict holds `Null_degree` in slot 1
of the MRR order — the correct explanation, which took a hand audit a cycle
later to find. The right answer was in the provenance record the whole time.**

| measured across the tree | |
|---|---|
| falsifier explanations examined | 9 |
| numbers cited in them | 37 |
| absent from that falsifier's own observations | **31 (83.8%)** |
| known true instance (G30 F2) flagged | **yes** — 3 of 3 |

**F1 fired.** The check flags the one instance known to be real *and* flags 83.8%
of everything else, so it cannot separate a defect from an ordinary derived
number. The noise is two kinds, and both are legitimate:

- **Derived quantities.** G30's F1 cites `80.55` — that is 0.0508/0.0631 as a
  percentage. Correct, load-bearing, and stored by no artifact.
- **Paragraph attribution.** G34's F1/F2/F3 each score 7/8 because they are
  explained in one block and my matcher hands every number in it to all three.
  That is a defect in *my probe*, not in G34, and it is not fixable in general:
  which number explains which falsifier is a question about prose.

**So the check is refused rather than shipped.** This lane published a
non-decidable measurement once today already (G35's 433 of 1070) and caught it
before it reached a ledger. Shipping the second one, in the cycle after writing
that sentence, would be worse than the first.

## 3 · Check B — verdict-word-vs-recorded-flag. Decidable, and the tree is clean.

The rule: *the `FIRED`/`SURVIVED` word in the RESULT.md paragraph naming F must
match F's recorded `fired` boolean.* Fully decidable — no derived-number
ambiguity, nothing to interpret.

| | |
|---|---|
| falsifiers where RESULT.md states an unambiguous verdict | 7 |
| where that verdict **contradicts** the recorded flag | **0** |

**Nothing to gate.** A checker that has never had anything to say is not worth
adding to a commit path, and C2 is what makes this a real zero: it asserts the
probe **reached** 7 unambiguous verdicts, so `0 contradictions` means *no
contradictions* rather than *nothing was examined* — the distinction that made
`test_loop_gate.sh`'s 15-check suite pass over a live defect.

## 4 · Controls

- **C1 — the probe finds the known instance.** A negative is evidence only if
  the search could have found something. G30's F2 is the one case already proven
  defective; C1 requires it to be flagged. *Fails if* a wrong paragraph matcher
  or a wrong provenance key returned a clean tree for everything, including the
  spike known to be broken.
- **C2 — check B reached real falsifiers.** *Fails if* zero unambiguous verdicts
  were examined, which would make `0 contradictions` meaningless.

Both pass.

## 5 · What this settles

**§12.12 is upheld, and it is now evidenced rather than asserted.** Two
independent attempts to mechanise the prose-vs-code gap have now been measured
and refused on the same grounds — the ordinary, correct case is
indistinguishable from the defect, because both involve prose referring to
numbers that no artifact stores:

| attempt | measured | outcome |
|---|---|---|
| G35 — a number in a RESULT.md with nothing behind it | 433 of 1070 unbacked, dominated by derived ratios | refused |
| H65 — a number explaining a falsifier absent from its observations | 31 of 37 (83.8%), known instance flagged along with everything else | refused |

The defence stays what §12.12 and §7 say it is: **state the falsifier before
running, then run it**, and read. That is how both instances were actually
caught, and this spike is evidence that there was no cheaper route available —
not an argument that one should not have been looked for.

**One thing worth carrying forward, and it is free:** G30's correct explanation
was sitting in its own `observations` dict while the RESULT.md said something
else. When a falsifier fires, **the observation dict is the thing to read** —
it is what was actually recorded, and the prose is what someone believed.
