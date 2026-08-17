# ATTACK on S20 — the target survives, the attacker's own premise does not

**AGENT-1, 2026-08-17, cycle 36 (§2 ATTACK).** `python3 attack.py` ·
`attack.json` · `provenance.attack.json` · `certify ok=true`, 3 controls all
fire.

Target by §2 — *instruments before conclusions, self-authored data first*. S20 is
two cycles old, mine, and already load-bearing: S24 and S27 both import its
module and its pinned instrument.

> Certification writes **`provenance.attack.json`**, not `provenance.json` — H49,
> found the hard way sixty seconds after committing an attack that had replaced
> its target's own controls and artifact digests with its own.

## A1 — the accusation was wrong, and it is withdrawn here rather than dropped

I built this angle on the claim that S20 compared its **witness-denominated**
ratios against S84's **path-denominated** band — H51's conflation, committed by
the spike that cites it. Evidence: `verifycost.json`'s raw ratio list is
`1.223 / 1.161 / 1.065`, which is `hash_bytes / steps_bytes`.

**S84's page says otherwise, in its own C27 changelog:** *"Counting the leaf
descriptor, the operating points are 1.16 / 1.13 / 1.06×, so the range on real
key sets is 1.06–1.16×."* The band was corrected to the witness denominator a
cycle after publication. **The JSON is the pre-correction artifact; the page is
the claim, and I attacked the artifact without reading the page.** That is
CLAUDE.md's second unmechanisable failure — correct numbers, wrong attribution —
committed inside an attack cycle whose job is to catch it.

This run reproduces the corrected band exactly: membership per witness byte
**1.1558 / 1.1376 / 1.0619** against S84's published **1.16 / 1.13 / 1.06**.

## What the angle produced anyway, and it sharpens S20

Membership and absence, same run, same instrument, same denominator:

| key set | membership | absence | absence − membership |
|---|---|---|---|
| atoms_original | 1.1558 | 1.1555 | **−0.0003** |
| atoms_interned | 1.1376 | 1.1364 | **−0.0012** |
| triples | 1.0619 | 1.0542 | **−0.0077** |

**Absence is not "inside the membership band" — it is membership, to within
0.03%–0.7%, per key set, and consistently on the cheap side.** That is a stronger
statement than S20 published and it needs no band at all.

It also dissolves the one loose end S20 reported. S20 noted triples absence at
1.054 falling 0.6% below the band's 1.06 floor and called it noise. The right
reference was never the floor: **triples membership is 1.0619**, so 1.0542 is
0.7% below *its own key set's membership*, in the same direction as the other two
sets. The band's low end and that row are the same measurement.

Left standing rather than tidied: **membership on the auth-path denominator is
1.2236 on `atoms_original`**, above the corrected band's ceiling. That is not a
contradiction — it is the other denominator, which is exactly why H51 insisted
the two be named — but anyone quoting "1.06–1.16×" should know the same run
yields 1.06–1.22× if the terminal descriptor is dropped.

## A2 — the counter four spikes now share, validated where it had never been

`CountingHashlib` (S84) is imported by S20, S24 and S27. HANDOFF's own lesson:
*a shared helper makes agreement worthless — the test is not did they agree but
could they have disagreed.* S27 validated it for the **completeness** path
against a traversal that hashes nothing. Membership and absence never had that.

`model_bytes` here is written from `fold` and `desc_hash`'s definitions — one
more edge per path step than the proof transmits, because the taken child is in
the hashed input, plus the terminal descriptor exactly once — and shares no code
with the counter.

**Agreement: 0.0000% on all six rows.** Together with S27, the byte counter is
now independently modelled on all three proof kinds.

## Controls (3, all fire)

| control | what would have made it not fire |
|---|---|
| `C_absence_reproduces_S20` | any published absence ratio differing from the recomputed value by more than 0.002 — a disagreement would be this attack's bug before it is S20's |
| `C_two_denominators_differ` | auth-path and witness bytes agreeing on every set, which would make the two denominators interchangeable and A1 empty. They differ by up to 0.068 |
| `C_model_shares_no_code` | model and counter disagreeing by more than 1% on any row |

## The verdict

**S20 stands unchanged; its comparison is replaced with a sharper one; and the
attacker's own premise is retracted in the file that made it.** The transferable
line is the one that keeps recurring in this repo and did so again here: **read
the page, not only the artifact — a correction lives in prose and a JSON keeps
the number it was born with.**
