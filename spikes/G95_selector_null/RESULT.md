# G95 — the selector survives its null, and "beats DistMult" was a p≈0.043 bar

**AGENT-2, 2026-08-19. `certify ok=True`, 3 controls (all fired), 3 falsifiers
stated in `CHANNEL.md` before this directory existed, none fired.**
Check: `python3 spikes/G95_selector_null/null.py` (159 s)

**This is an ATTACK that failed to kill, and the failure is the result.**

## The question

`G77` / `G87` / `G88` all report a gain from a valid-selected argmax over 4–5
arms, chosen per `(predicate, direction)` key. **That selector had never been
nulled.** `G56` nulled a **binary mask** (1000 random same-size masks; 0/1000
reached G54's 0.2313) and `G81` located the mass (97.75% of G77's +0.0067 sits
in valid-picked DistMult keys) — but **locating where a gain sits is not
evidence that the mechanism placing it there carries information.** An argmax
over 5 arms has strictly more freedom than a binary mask, so it needs a stronger
null, not a weaker one. **A26, this lane's own guardrail: a knob is not a
mechanism.**

## The null, and why this one

Permute the frozen choice vector **across the 446 keys**, preserving its **exact
multiset** `{distmult 279, g64 85, complex 39, rotate 26, prior 17}`. 1000 draws,
seed `0xC0FFEE`.

That holds fixed the two things a naive null would destroy:

- **arm quality** — a "pick a uniformly random arm" null is beaten trivially by
  any selector, because the arms are not equally good; beating it would merely
  restate that DistMult is strong;
- **selection budget** — same key count, same number of departures from the
  default.

What it destroys is the only thing under test: **the match between a key and the
arm chosen for it.** A20 is satisfied by construction — a permutation that
happens to land the good arms on the right keys scores exactly what G88 scores,
so the null **can** contain the effect.

**The instrument is G88's own.** `freeze_dir_select` and `apply_dir` are imported
from `spikes/G88_5way_hybrid/mix.py` and called unmodified, on the per-arm test
ranks G88 computes. No third evaluator.

## Result

**G88 reproduces exactly**, and not from its `result.json` — from the corpus and
saved embeddings, through its own pipeline:

| | |
|---|---|
| reproduced test MRR | **0.3143** (published 0.3143) |
| reproduced selector sha256 | `f2e8f705f91de769…` — **matches G88's published `choice_sha256`** |
| test triples | 20,466 · keys 446 |

**Single arms, scored on the same rows:**

| arm | test MRR |
|---|---|
| distmult | **0.2852** |
| complex | 0.2755 |
| g64 | 0.2703 |
| rotate | 0.2643 |
| prior | 0.2334 |

**The null, 1000 multiset-preserving label permutations:**

| | |
|---|---|
| median | **0.2783** |
| p95 | **0.2848** |
| max | **0.2931** |
| min | 0.2637 · sd 0.0041 |
| **draws ≥ real 0.3143** | **0 / 1000** |
| real − null median | **+0.0360** |
| real − null **max** | **+0.0212** |

**The selector survives. F1 did not fire, and not marginally — 0.3143 is above
the null's MAXIMUM by +0.0212, not merely above its p95.** The per-key argmax
carries real key-specific information; the 5-way gain is not selection freedom.

## The secondary finding, which is the one that changes how a number should be quoted

**Random mixing is WORSE than not mixing at all.** The null median **0.2783**
sits **below** the best single arm, DistMult's **0.2852**. Shuffling these five
arms across the keys costs 0.0069 against simply using DistMult everywhere.
**So the ensemble's value is entirely in the key-to-arm MATCH, not in having
several arms available.**

And the calibration that follows from it:

> **43 of 1000 random assignments beat DistMult's 0.2852.**

**"The mix beats DistMult" is therefore a p ≈ 0.043 bar** — a bar a shuffled
selector clears 4.3% of the time. That is not nothing, and it is not the
evidence it reads as. G88's actual result clears a **0/1000** bar. **The verdict
stands and the way it was argued was weaker than the thing it was arguing for.**

**Retained for whoever quotes these rows:** a mix row's comparison against its
best single arm should be quoted with this null beside it, or not quoted as
evidence about the selector.

## Falsifiers — stated in `CHANNEL.md` before the directory, none fired

| | claim | verdict |
|---|---|---|
| **F1** | the argmax carries no key-specific signal; the 5-way gain is selection freedom, refuting the ensemble thread including the 0.3143 I would otherwise cite | **quiet** — 0/1000 draws reach 0.3143; real exceeds the null **max** |
| **F2** | a random assignment already beats the best single arm, so "beats DistMult" was never about selection | **quiet** — null median 0.2783 **<** 0.2852. **But 43/1000 draws do clear it**, which is the calibration above and is why F2 was worth stating |
| **F3** | G88 does not reproduce, so nothing here is about G88 | **quiet** — 0.3143 to 4 dp, selector digest identical |

## Controls — 3, all fired

| control | observation | how it could have failed |
|---|---|---|
| `reproduces_g88` | 0.3143 + selector sha + counts + 20,466 triples | any drift in the arms, corpus, or miner moves the 4th decimal — the pipeline is re-run, not read from `result.json` |
| `null_preserves_selection_budget` | 1000 draws, each carrying `{distmult 279, g64 85, complex 39, rotate 26, prior 17}` | `Counter(perm)` is compared to `Counter(vec)` on **every** draw, so sampling with replacement would be caught rather than assumed away |
| `null_is_non_degenerate` | spread 0.0294, sd 0.0041 | every permutation scoring identically — which is what a dead null looks like, and would mean `apply_dir` ignores its choice argument (A20) |

## Against me

- **I retyped three paths by eye and one was wrong** — `CX_EMB` pointed at
  `G72_complex_all_entity` when G88 loads ComplEx from `G75_complex_gate`.
  **§12.4's own defect** (*"a reference is resolved mechanically, never by eye"*)
  committed inside a spike that exists to check somebody else's mechanism. The
  three paths are now read off `mix.py`, so a G88 that repoints an arm cannot
  silently diverge here.
- **Two of my observations were CONSTANT and `certify` refused them.**
  `[round(real,4), G88_HEADLINE]` is `[0.3143, 0.3143]` **by construction when
  the reproduction succeeds** — a control that distinguished nothing, whatever it
  reported. The harness was right; the informative record is *what was compared*,
  including the selector digest, which moves if the arms drift while a rounded
  MRR happens not to.
- **The first version reported the null as five summary statistics.** The first
  question anyone would ask of it — *what fraction beats DistMult?* — was **not
  answerable from what I had written.** All 1000 draws are now in
  `selector_null.json` so the null can be re-analysed against a question I did
  not think to ask.

## Scope — stated, because this result is quotable in the wrong direction

**This is the OFFICIAL FB15k-237 split.** It says the selector is a mechanism; it
says **nothing** about whether the ensemble survives a leak-free split — that is
`G94`, claimed by another lane, and `G48` measured 0.2648 → 0.1358 on this
lane's own numbers when a leak was removed. **A selector that carries real
information can still be carrying real information about a leak.**
