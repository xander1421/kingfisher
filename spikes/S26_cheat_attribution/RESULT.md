# S26 — the quorum catches every lie and names the liar, once someone reads the field

**AGENT-1, 2026-08-17.** `python3 cheat_attr.py` · `cheat_attr.json` ·
`certify ok=true`, 4 controls all fire, **falsifier did NOT fire**.

M1-DEMO (§8) item 5 is *"byte-compare verdicts incl. one injected cheat caught
and one deterministic-fault job agreed and 'paid' in points"*. The
deterministic-fault half exists — `(flip)` is the corpus's own positive control
and M1.8 records it refused. **The injected-cheat half had never been run.**

## What reading the code said first

`q3.py::adjudicate` returns `(verdict, key, agree_count, dispatched, returned,
domains)`. It takes the majority key with `Counter(live).most_common(1)[0]` and
**never returns which envelope disagreed**. `test_adjudicate.py` asserts
`adj([ok, ok, bad])[0] == 'MAJORITY'` — the verdict, not the defendant. A
protocol that pays or slashes cannot act on a verdict with no defendant.

## The falsifier, stated before the run

> If the dissenting worker IS identifiable from what the pipeline already
> records, then the gap is REPORTING and not evidence, and the fix is a field
> rather than a protocol change.

**It did not fire.** Over the committed 64-program, 4-worker M1.8 run:

| | count |
|---|---|
| cheats injected (one per envelope, one byte of the field the key reads) | **200** |
| caught — agreeing seats dropped | **200 / 200** |
| **attributed to exactly one worker** | **200 / 200** |
| envelopes where a cheat is inexpressible | **56** |

Per worker, identically: `host-a`, `host-min`, `host-x86`, `phone` — 50 injected,
50 named, 0 unnamed. **Attribution is a set difference over data `result.json`
already carries**, so the missing piece is one field in `adjudicate`'s return,
not a protocol change. Filed as **M1.13**, not applied here: `q3.py` is
uncommitted-modified by another lane right now and `git commit --only` on a
shared file carries a co-editor's in-flight work under my `Atom:` (§13, H19).

## The 56, which are the interesting ones

They are exactly the 14 `NO_RESULTS` programs × 4 workers. `key()` returns
`None` for an empty result member under a non-failed status — *"an empty capture
is not a measurement, so such a worker did not answer"* — so both the honest and
the lying envelope key to `None` and the lie changes nothing. **On those 14
programs a lie is not undetected; it is unexpressible**, because the envelope was
never being counted. That is the soundness fix working, and it is also the reason
no cheat-detection rate should be quoted against 64: the denominator is 50.

## Two threat models, one table, because "quorum catches cheats" is said about both

| attack | what is wrong | detected |
|---|---|---|
| **lying member** (this spike) — envelope altered after execution | the *report* | **200 / 200**, and named |
| **wrong replica** (M1.9) — `(< a a)` returns True | the *binary* | **0 / 64** |
| wrong replica — one extra stdlib rule | the *binary* | **0 / 64** |
| wrong replica — a wrong `-` | the *binary* | 4 / 64 |
| wrong replica — changed resolver message | the *binary* | 24 / 64 |

Byte compare is **certain** against a member that misreports and **blind** to a
member that is consistently wrong, because two replicas of the same wrong
computation agree. The M1.9 rates are quoted from that spike, not recomputed
here.

## No points arithmetic

`specs/D3_economics.md` publishes *"no recommended coverage. No `R`. No stake
floor. No price per job."* Any slashing number here would be invented rather than
derived — A26, a knob is not a mechanism — so the *"paid in points"* half of
item 5 stays open and its blocker is D3's own deliberate silence, not this
pipeline.

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_key_matches_committed` | **gating**: all 64 committed keys and agreement counts re-derived. **The first version of this spike reimplemented the agreement key from reading the code and got 0 of 64** — `key()` prefers a *canonicalised* `results_text` and falls back to `sorted_hash` only when there is none. The fix was to execute `q3.py`'s own function, not to adjust the reimplementation |
| `C_cheat_moves_the_key` | a cheat that leaves the key unchanged tests nothing (A29). Envelopes where none is expressible are **counted**, not skipped |
| `C_agreement_drops` | a lying member that did not cost the quorum an agreeing seat — then "caught" would be a claim about nothing |
| `C_worktree_key_agrees` | the pinned committed `q3.py` and the working-tree copy disagreeing on any of the 64 majority keys. The in-flight edit adds two argparse options and a `preflight.Policy` call inside `main()`, and *"I read the diff and it looked unrelated"* is not evidence |

Both inputs are **byte-pinned into this directory and hashed**: `q3_head.py`
(blob `ff60cf73`) and `result.head.json` (blob `e1d3bf85`). `spikes/M1_8_quorum3`
has 256 modified files from another lane's in-flight run, so a dep-directory
staleness check would be judging their work rather than this run's inputs.

## Scope

- **One committed run.** 64 programs, 4 workers, whose verdicts are
  `INSUFFICIENT_DOMAINS` 50 / `NO_RESULTS` 14 — that run never accepted a job,
  and attribution is measured on its envelopes, not on an accepted quorum.
- **One liar at a time.** Two colluding members holding the same wrong key would
  be a different measurement; with 4 workers and `MIN_DOMAINS = 3` the arithmetic
  changes, and nothing here says what happens then.
- **The cheat is injected at the envelope**, which tests the adjudicator, not the
  transport. A member that lies over the wire reaches the same code path only if
  the transport preserves the fields, which `M1.7` measures separately.
