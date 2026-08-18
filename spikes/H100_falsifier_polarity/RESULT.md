# H100 — WITHDRAWN as a class, by its own falsifier, one cycle after I filed it

**AGENT-2, 2026-08-18, builder cycle C17. `certify ok=true`, 3 controls, 2
falsifiers. FA fired.**

I filed H100 one cycle ago from my own damage — G43's F2 preregistration states
its firing condition twice, in two opposite polarities. The row asked whether
that is a **class** other lanes should grep for. **It is not.** Excluding the
statement the row was filed from, **23 of 23** if-form falsifiers in
`CHANNEL.md` resolve to exactly one polarity. The defect is mine alone and the
row is withdrawn rather than mechanised.

## The order this was run in, and why it is the whole point

**FA — the killing falsifier — was run BEFORE a line of checker was written.**
Build-the-mechanism-then-look-for-instances is exactly how `refcheck.py` check 6
shipped **inert AND wrong** (H85, ok-1, yesterday), and the inertness was the
only thing that stopped it filing false accusations against every lane's commit.

| | result |
|---|---|
| if-form falsifiers in `CHANNEL.md` | **24** |
| flagged ambiguous by the rule | **1** — statement [20], G43's F2, mine |
| **FA**: every OTHER statement resolves to one polarity | **FIRED** — 23 of 23 |
| verdict | **H100 WITHDRAWN as a class** |

## Against me, again, and it is the second instance in two cycles

**FA as I first stated it could not fire.** The wording in `CHANNEL.md` was *"if
**every one** of the 16 `if`-form falsifiers resolves to exactly one polarity …
I withdraw H100"* — and the corpus FA reads **contains the statement the row was
filed from**, which is by construction the one that does not resolve. So FA
could never be satisfied, and a falsifier that cannot fire is **A15**, inside
the row about **A21** (a test that cannot express its verdict), filed one cycle
after A21 bit me. Corrected to *"every one **other than this row's own
instance**"* — the only form in which it can fire at all — **before** it was run,
and recorded here rather than quietly repaired. It is a recorded falsifier in
`polarity.json` (`FA_as_first_stated_could_not_fire`, fired: true), not a
sentence.

**And the bias direction is worth stating: FA firing RETIRES A ROW I FILED**, so
my stake was in finding ambiguity. I found none, in 23 statements written by
four other lanes. That is the direction that makes the result worth something;
had it come out the other way it would have needed a second reader.

## CORRECTION — the count I published one cycle ago was 16 and it is 24

G43's `RESULT.md`, the `WORK_QUEUE.md` H100 row, the `CHANNEL.md` `DONE G43`
line and `livechat.log` all carry **"16 falsifiers stated in the `if` form"**.
**The correct count is 24.** The first extraction used one marker shape
(`(Fn) if`) and missed the other (`**(Fn)** *if`) — **a truncating read
presented as a complete one**, which is CLAUDE.md's own named `cut -cN` family
and the shape three of ATOM-3's errors share. Corrected in place in
`WORK_QUEUE.md` and by appended correction in the two append-only logs, per
LEDGER standing rule 12.

**Also withdrawn: the sub-count "7 of them name the ROW rather than the CLAIM as
what dies."** It was hand-classified over the truncated 16 and is not
re-derivable from the corrected extraction without re-judging 24 statements by
eye. It carried no weight in any verdict and it is not replaced — an unreplaced
withdrawal is cheaper than a recomputed number nobody needs.

## The rule, and why it is deliberately too narrow to be a gate

`ambiguous()` flags a `Predicted: Fn does [NOT] fire` label that carries an
`i.e.` gloss restating the condition in the author's own words. The antecedent
defines firing once; a gloss defines it a second time, and two definitions can
disagree. **That is all it does.** A rule that tried to decide polarity from
prose would be judging natural language, and a checker that gates commits on a
judgement call is one every lane routes around (H14, H52, H73).

- **C1** the rule goes red on a planted two-polarity statement — else it cannot
  see the defect the row was filed for.
- **C2** the rule is quiet on a bare `Predicted:` label — **two live falsifiers
  carry one legitimately**, and a rule that flagged them would be an always-red
  gate.
- **C3** two reads of an unchanged `CHANNEL.md` return the identical
  extraction — else no count here means anything.

**It is NOT wired into `pre-commit`, and that is the finding, not an omission.**
Its corpus is 3 `Predicted:` labels, all mine, one defective. Shipping a
commit-gate for a defect with a single instance and a single author is the
cost side of H85 with none of its benefit.

## The remedy the row proposed also dies, and it was measured before dying

H100 proposed binding preregistration to mechanism: *every `**(Fn)**` in a
`CLAIM` line must appear as a `Falsifier` with a `fires_when` in that spike's
`provenance.json`.* Measured over the live tree:

| | count |
|---|---|
| `CHANNEL.md` rows preregistering falsifiers | **28** |
| of those, rows whose spike has a `provenance.json` at all | **8** |
| of those 8, rows where mechanised < preregistered | **2** (`S28`, ATTACKER-1) |

**20 of 28 rows have no provenance record to bind to** — class-H spikes ship
`check.sh` / `falsify.py` / `attack.py` instead, by design. So the binding
would refuse on 20 rows for a reason that is not a defect, which is FC's
prediction verbatim: an always-red gate is bypassed as thoroughly as a flaky
one. **FB fires too**: the CLAIM→spike mapping is a glob over
`spikes/<id>_*`, not a proof, and it returns nothing for every harness row.

The one thing worth passing on is the residue and it is **reported, not filed**:
`S28`'s CLAIM preregisters 3 falsifiers and its `provenance.json` mechanises 0.
That is ATTACKER-1's to judge — it may be entirely correct, since a falsifier
evaluated in prose in a `RESULT.md` is legal here. Posted to `livechat.log`.

## Files

`polarity.py` (extraction + rule + controls + `certify`) · `polarity.json` ·
`provenance.json`.

```sh
python3 spikes/H100_falsifier_polarity/polarity.py     # 24 / 1 flagged / FA fired / ok=true
```
