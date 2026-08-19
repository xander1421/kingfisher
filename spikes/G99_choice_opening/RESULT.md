# G99 — G88's `choice_sha256` was a commitment with no opening. It has one now, and it reproduces bit-exact.

F1/F2/F3 stated in `CHANNEL.md` before any edit; **none fired.**
Check: `python3 spikes/G99_choice_opening/verify.py` (<1 s, artifacts only)

## 1 · The defect

`spikes/G88_5way_hybrid/result.json` published `"choices"` as **five integers —
the per-arm counts — and a 64-hex `choice_sha256`**. The digest is taken over
`{min_n, choice}` (`mix.py:124`), where `choice` is the per-(predicate,direction)
table. **That table was in no artifact.**

So the frozen selector every downstream row cites could not be compared against
anything — a re-fit, another split, a later run — without re-executing G88's
whole pipeline. **Found the hard way:** G98 wanted the official-vs-pair-disjoint
per-key agreement, could not get it, and had to record it as uncomputable.

**CLASS: A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS.** Family C. This is
**worse than publishing neither**: a reader takes the digest as evidence the
table is fixed, and has no way to discover the table is unavailable. `mix.py`
computed the object and threw it away one line later — `freeze_dir_select`
returns it in the *same payload* the digest is taken from.

## 2 · The fix, and why it emits rather than rebuilds

`mix.py` **v2** emits `payload["choice"]`, `["min_n"]`, `["n_keys"]` and
`["n_small_default"]`. **The same object the digest is computed from, not a second
construction of it** — a rebuilt table could disagree with the digest, which is
the same defect one level up.

## 3 · What the re-run says

| falsifier | result |
|---|---|
| **F1** re-run digest ≠ published `f2e8f705f91de769…` | **quiet** — reproduces **bit-exact** |
| **F2** table length ≠ `n_keys`, or its own recomputed digest ≠ the emitted one | **quiet** — 446 = 446, digest re-derives |
| **F3** any metric differs from the published `result.json` | **quiet** — `mrr/hits1/hits3/hits10` = 0.3143 / 0.2289 / 0.3443 / 0.4815, identical; counts identical |

`D6 Provenance Certified: ok=True`, 143.02 s.

**F1 was the one worth stating.** Had the digest moved, the finding would have
been far larger than a missing key — it would mean G88's frozen selector is not
reproducible from its own committed inputs. It did not move, so **the digest was
always honest; it was merely unopenable.**

**One number falls out and it is a cross-check nobody designed:** the table shows
`n_small_default = 210` of 446 keys, reproducing **G97's** figure for how many
keys `MIN_N=20` sends to the default, and **G98 §4a's** correction, through an
artifact rather than through either spike's code.

## 4 · The check is the deliverable, not the edit

`verify.py` re-derives the digest from the published table and refuses if they
disagree, so `result.json` cannot again carry a digest that does not open. It
also asserts the **counts are derivable from the table** — the property that
keeps the five integers and the table one object rather than two records that
can drift apart (H39's shape). Reads artifacts only, under a second.

## 5 · Scope

Only G88's artifact. `G77`, `G87` and `G82` publish selectors of their own and
**were not inspected**; whether they carry the same shape is unmeasured here and
is stated as unmeasured rather than assumed either way.
