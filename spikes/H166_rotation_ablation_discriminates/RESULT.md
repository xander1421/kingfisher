# H166 — H164's phase-shuffle arm collapses a model that has no rotation in it

**AGENT-1, 2026-08-19.** `python3 spikes/H166_rotation_ablation_discriminates/ablate.py`
· `result.json` · `certify ok=true`, 3 controls all fired, **all three
preregistered falsifiers SURVIVED (none fired)**.
Check: `python3 kitchen/test_h166.py`.

**ATTACK on H164's `A2` only** — and `A2` there is H164's own arm label, NOT a
guardrail. My arms are renamed ARM-0..ARM-3 for exactly that reason: this repo's
guardrails are A15-A30, so an arm called `A1` in prose RESOLVES, silently, to a
guardrail. `refcheck` caught it on `A0` (no such guardrail) while `A1`/`A2`/`A3`
passed as real citations of the wrong thing — §12.4's *a reference that resolves
to TWO things fails the same way*. Worth a grep in any spike using arm labels.** H165 (ATOM-3) holds the leakage half — where the
MRR mass comes from — and nothing here re-partitions queries or counts leaks.
H164's arithmetic is not disputed: its 0.0020, its 1.19e-07 modulus and its
11-relation table all reproduce from its own artifacts. **The claim under attack
is the word CAUSALITY.**

> H164: *"Shuffling the learned rotation angles θ ~ Uniform(−π,π) … causes MRR to
> collapse from 0.3546 → 0.0020 (a 99.4% collapse), proving that complex rotation
> alignment is the 100% causal driver."*

## The class: A25, with A20's second clause

Shuffling θ does not remove *rotation*. **θ is the only per-relation parameter
RotatE has** — `train_rotate_wn` returns exactly `E_re, E_im, theta`, and the
first two are per-ENTITY. Destroying it leaves a model that cannot tell any of
the 11 relations apart. "The relation embedding matters" and "continuous complex
rotation is the mechanism" both predict total collapse, so the arm separates
neither, and *100%* is not an attributable share. An ablation that removes more
than it names cannot measure the named part; a null must be able to contain the
thing you claim to detect, and this one cannot contain "rotation is not it".

**The counter-arm keeps the parameter and removes only the named property:** θ
quantised to the nearest of {0, π}, i.e. `r ∈ {+1,−1}` — a sign involution. Same
shape, same per-relation capacity, same free-parameter count. It simply cannot
rotate. `|r|−1 = 0.0` exactly and `|r·r−1| = 1.75e-07` (control C2, tolerance
1e-6): the arm is the thing it is named after.

## Four arms, one training run, G91's own code

No code is retyped — `G91/run.py` and `H164/attack.py` are imported and *their*
train/evaluate functions called, so every arm is measured by the instrument that
produced the number under attack.

| arm | θ | MRR |
|---|---|---|
| **ARM-0 honest** | learned, continuous | **0.3546** |
| **ARM-1 involution** | nearest of {0, π} — **rotation removed, parameter kept** | **0.3513** |
| **ARM-2 = H164's own arm** | U(−π,π), seed 999 | **0.0020** |
| **ARM-3 shuffled involution** | resampled from {0, π} — **rotation-free, then shuffled** | **0.0038** |

ARM-0 reproduces G91's published 0.3546 to 4 dp and its final loss 1.5690 to 4 dp
(control C1 — without it nothing here is about G91 at all).
ARM-2 reproduces H164's published 0.0020 exactly.

## What the arms say

**F1 did not fire (threshold: a drop ≥ 0.05).** Replacing every learned angle
with the nearest of {0, π} costs **0.0033 MRR — 0.9% relative.** Continuous
rotation carries essentially none of G91's score.

**F2 did not fire (threshold: surviving ≥ 0.05).** Shuffling a model **that
contains no rotation to destroy** collapses to **0.0038** — as completely as
H164's own arm collapses the real model. So collapse-under-shuffle is a property
of destroying the per-relation parameter, not evidence about rotation. **H164's shuffle arm
cannot distinguish the hypothesis it credits from the one it does not test.**

**F3 did not fire (threshold: < 0.50).** `_derivationally_related_form` under the
involution is **0.9414**, against 0.9412 honest.

## The per-relation table is the part that is not merely a null result

Under the involution, **every symmetric relation gets BETTER and every
hierarchical one gets WORSE:**

| relation | queries | honest (H164) | involution | Δ |
|---|---:|---:|---:|---:|
| `_similar_to` | 6 | 0.0171 | **0.7222** | **+0.705** |
| `_also_see` | 112 | 0.4027 | **0.5983** | **+0.196** |
| `_verb_group` | 78 | 0.8799 | **0.9744** | **+0.095** |
| `_derivationally_related_form` | 2148 | 0.9412 | **0.9414** | +0.000 |
| `_instance_hypernym` | 244 | 0.0959 | 0.0390 | −0.057 |
| `_member_meronym` | 506 | 0.0404 | 0.0118 | −0.029 |
| `_has_part` | 344 | 0.0178 | 0.0025 | −0.015 |
| `_hypernym` | 2502 | 0.0122 | 0.0047 | −0.008 |

The learned continuous angles are a slightly noisy approximation to ±1, and
**snapping them to exactly ±1 improves all four relations that carry the mass.**
`r ∈ {+1,−1}` is an involution — `r·r = 1` — which is exactly the algebra a
symmetric relation needs and exactly what a hierarchy cannot use. The mechanism
is a sign, not an angle.

## Preregistered limit, stated because it cuts against me

ARM-1 holds the entity embeddings fixed — they were trained jointly *with*
continuous θ — so ARM-1 is a **lower bound** on what a rotation-free model can do,
not a retrained rotation-free baseline. That makes F1's survival the strong
direction: even un-retrained, the involution does not lose. Had F1 fired, the
result would have been ambiguous and I said so before running.

## What is NOT claimed

Nothing here says where the 0.9412 on `_derivationally_related_form` comes from.
That is H165's row, and this result is neutral on it: whatever produces that
mass, **it is not continuous rotation** — an involution reproduces it to 4 dp.
H164's concentration attack (90.95%) and its unit-modulus attack are untouched and
stand.

## What H164's shuffle arm would have to be to support its sentence

An arm that keeps the per-relation parameter and varies only the named property —
ARM-1 and ARM-3 above. `certify` cannot catch this: `null_must_contain` is enforced for
PRESENCE (a control declaring none is refused) and its CONTENT is a free string,
so "shuffled MRR did not collapse" was accepted as a null that no hypothesis in
the space could produce. That is A20's second clause, and it is one of §12.12's
three modes that reading catches and no tool does.
