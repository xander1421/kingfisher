# H195 — the pin's NAME leaked, and my own row was too wide

**AGENT-1, 2026-08-19. My row, raised from S37's F2 three cycles ago and left
OPEN. Taking it produced a retraction of its severity, which is the result.**

## What the row claimed

> 5 of 12 consumers silently resolve to `S20_verify_kinds/w2_head/trie_witness.py`,
> S20's frozen HEAD pin. **LIVE CONSEQUENCE:** `S36_witnessed_job/attack.py` goes
> on printing `witnessed_accepts_replay: true` after S37 closed that hole, so a
> reader running it tomorrow concludes the fix never landed.

It named three falsifiers. **F1 fired, and it fired for all five.**

## F1 fired: every one of the five resolutions is deliberate

| consumer | what its own source says |
|---|---|
| `S20/verify_kinds.py` | owns the pin; installs it because the working tree was dirty |
| `S24/range_crossover.py` | *"importing S20 inherits that pin, so this spike measures the same verifier S20 did rather than whatever is on disk now"* |
| `S27/verify_floor.py` | *"inherited by importing it, so these numbers stay comparable to S20's and S24's"* |
| `S36/witnessed_job.py` | *"S20's pin of the COMMITTED trie_witness, inherited by importing it"* |
| `S36/attack.py` | no comment — **and its entire finding is *about* the pinned verifier** |

That last row is the one the queue entry called the live consequence, and reading
the file settles it the other way. `attack.py` is the spike that **found** the
soundness hole and proposed `verify_completeness_qbound`; S37 then lifted that
fix into the live module. Its `committed_verifier_accepts_replay: 37` is the
finding, correctly recorded against the verifier it attacked. **Against the live
module the replay is rejected and the finding cannot be reproduced at all.**

**So there was no wrong number.** What was wrong is that the artifact never said
*which* verifier `committed_` meant, and "committed" silently changed meaning
between the attack's commit and now — **claim decay, CLAUDE.md's first
unmechanisable failure**, not a stale measurement. The row's own F1 predicted
exactly this: *"in which case the row is a labelling problem and not a resolution
one."*

## I shipped the wrong fix first, and the artifacts refuted it

My first patch **released** the bare name after S20's own imports, so consumers
would resolve live. Re-running the consumers moved
`S27_verify_floor/verify_floor.json`:

```
-  "slack_pct": 0.0,              +  "slack_pct": -100.0,
-  "verifier_hash_bytes": 22900.15  +  "verifier_hash_bytes": 0
```

**Mechanism, reproduced in A5 rather than recalled:** S84's `counted()` swaps
`TW.hashlib` on the module *it* bound — the pin. Hand it a function from a
different `trie_witness` object and it counts nothing. A counter on one module
and the work on another.

**And I had already declared "no collateral" on the strength of a measurement
that could not see it.** I A/B'd the five consumers on the **md5 of their
stdout**; S27 publishes its numbers to a **JSON file**, and its stdout does not
carry them. That is A20 — a null that cannot contain the effect — and family A:
the instrument could not produce the answer. The stdout md5 said `SAME` for S27
while its published verifier cost went to zero.

## The fix: declaration, not resolution

The gateable invariant is **not** *"nobody is pinned"* — that is false and
actively harmful — it is **"nobody is pinned SILENTLY"**.

- `S20/verify_kinds.py` exports `PINNED_MODULE` (the object its own numbers come
  from) and `USES_S20_PIN`.
- The four inheritors each set `USES_S20_PIN = True` beside the comment that
  already said so in prose. **A comment is not readable by a checker; that gap is
  the whole row.**
- `S36/attack.py`'s output carries `verifier_identity` — module path, sha256, and
  `is_s20_pin` — **read off the loaded module rather than typed**, so it cannot
  drift from what actually ran. A reader after S37 can now tell *"the fix never
  landed"* from *"this measures the code the fix replaced"*.
- `S37/which_module.py` separates **PINNED (declared)** from **PINNED (SILENT)**
  instead of collapsing both into one bucket, and counts them apart.

```
live 7 | declared pin 5 | SILENT pin 0 | unresolved 0
```

## Evidence

`python3 spikes/H195_pin_name_leak/probe.py` — **12/12, `checks failed: 0`.**

| arm | |
|---|---|
| A1 / A2 | at HEAD **0 of 5** consumers declare their pin use; now **5 of 5** |
| A3 / A3b / A3c | **0 silent**, 5 declared, 0 unresolved — a sixth could not hide |
| A4 / A4b | **the resolution is UNCHANGED**: still 5 pinned, 7 live. The row was not "fixed" by unpinning |
| A5 / A5b | the counter sees the pinned module's work and **zero** of the live module's — the 22900→0 mechanism, in six lines |
| A6 / A6b | the attack artifact names its verifier (sha256, `is_s20_pin`), **and the finding is unchanged at 37/37, `falsifier_fired: true`** |

A4 and A6b are the two-sided guards: a labelling fix that moved a resolution or a
measurement would be a different and worse thing than the one this row asked for.

Re-running all five consumers afterwards leaves every published result JSON
byte-identical except `attack.json`, which gains only the `verifier_identity`
block.

## Interrupted mid-cycle, and it is filed as H234

Five of these files reverted to their committed state at ~22:19 while this row
was in flight: a co-lane ran `git stash` on the shared working tree. Recovered
with `git show 'stash@{0}:<path>' > <path>` — deliberately no index operation,
since `git checkout stash@{0} --` would stage into the index five lanes share.
`stash@{0}` was left intact. **The hazard is not lost work; it is that a probe
re-run in that window goes green against pre-edit code and is believed.**
