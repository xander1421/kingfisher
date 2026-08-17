# G36 — independent byte-reproduction of another lane's G34

**Verdict: G34's numbers REPRODUCE. Falsifier stated first and it did NOT fire.
An independent re-run, from a clean copy, in a different directory, by a
different lane, differs in **7 leaf fields, all `elapsed_sec`, and in ZERO metric
fields.** Byte-identity does not hold, for one reason that is measured and
scoped: `elapsed_sec` is embedded in the metrics artifact. No tool was built —
the sweep says n=1.**

Run: `python3 spikes/G36_repro_g34/length1_constants.py` → `rerun.log`.

---

## 1 · Why re-run someone else's spike at all

This workspace's whole proposition is that **a result is trusted because anyone
can re-run it and compare bytes.** That had never been exercised on a G-series
result. G34 published **Filtered MRR = 0.2648** at 16:12 — the largest number
this series has produced, a 4.2× lift over G17 — by a lane other than mine, in
about two minutes. It is the right thing to point the proposition at.

I had already cleared the obvious alternative explanation before claiming this:
rules are mined from `build_graph_index(train)`, **train only**, so the lift is
not test leakage.

## 2 · Falsifier, stated in `CHANNEL.md` before the run

> If re-running `length1_constants.py` from a clean copy produces a
> `length1_constants.json` differing from the committed one in **any metric
> field**, G34's numbers do not reproduce and the row is reopened. If it differs
> **only** in timing fields, those are non-deterministic by nature and the
> metrics stand.

**It did not fire.**

| comparison | result |
|---|---|
| source sha256, their copy vs mine | `2955ff29946ee8a4…` — **identical**, so this is the same program |
| total leaf differences in the result JSON | **7** |
| differences in **timing** fields | **7** |
| differences in **metric** fields | **0** |
| artifact sha256 | **differs** — see §4 |

The seven, in full:

```
results.G17_2hop_only.elapsed_sec                 27.528543949127197 -> 25.349773168563843
results.Length1_only.elapsed_sec                   1.176059007644653 ->  1.050092935562134
results.G17_plus_Length1.elapsed_sec              27.297137022018433 -> 26.983206987380980
results.Constants_only.elapsed_sec                 0.707601785659790 ->  0.715391874313354
results.G34_Full_System (…).elapsed_sec           28.204926967620850 -> 27.469880104064940
results.Empty_baseline.elapsed_sec                 0.070299148559570 ->  0.070927143096923
results.C1_planted_control.elapsed_sec             0.002014160156250 ->  0.002299070358276
```

Every published metric — `0.2648` MRR, `0.3929` Hits@10, every arm, all four
controls, all three falsifier verdicts — came back identical. **G34's
measurement is independently reproduced.** Its headline *comparison* against
AnyBURL and AMIE+ remains unsourced (G33 finding 4, G35), and reproducing a
number says nothing about a figure it is compared to.

## 3 · The rail I ran into, and how it was observed

`length1_constants.py` writes `length1_constants.json` and `provenance.json`
next to its own `__file__`. **Running it in their directory would have clobbered
another lane's artifacts to test them** — the `b529081` / H10 shape. So the
script was copied into this spike's directory and run there; `HERE/..` still
resolves to `spikes/`, so its deps (`G17_composition_redo`, `harness`,
`S52_realkg`) resolved unchanged. Their four files are untouched, verified by
mtime.

That the script runs correctly outside its own directory is itself a small
positive reproducibility result, and it was not guaranteed — a script that only
works in the path it was born in is a finding, and I said so in the claim before
running.

## 4 · Why the bytes differ, measured rather than generalised

The artifact sha256 differs **only** because `elapsed_sec` shares a file with
the metrics. That is worth stating precisely, because the mission's verification
primitive (M1-DEMO item 5, *"byte-compare verdicts"*) cannot be applied to an
artifact that embeds a wall-clock reading.

**I expected this to be a class and swept for it. It is not.**

| sweep | measured |
|---|---|
| tracked spike JSON artifacts | 214 |
| embedding any volatile field | 34 |
| …of which are `provenance.json`, **where a timestamp is the point** | 33 |
| **result-side JSONs mixing metrics with a timing field** | **1 of 183** |

The one is `spikes/G30_external_yardstick/yardstick.json` — **mine**. G34's is
the second instance but is not yet tracked (§13; it shares the uncommitted-DONE
condition swept in G33's addendum).

**So no helper was built.** No byte-compare utility exists in `spikes/harness/`,
n=1, and writing one to drive a count of 1 to 0 is the over-fitting this repo
keeps paying for. Recorded instead: **if G30 is ever re-run, split `elapsed_sec`
out of the metrics artifact.** Editing a committed artifact now, to make a
checker I did not write report a number I would choose, is cosmetic.

## 5 · What this does and does not establish

- **Does:** G34's published metrics reproduce exactly under an independent run by
  another lane. The first time a G-series result has been reproduced by anyone
  other than its author.
- **Does:** the run is deterministic in every metric — no seed drift, no
  dict-ordering dependence, no path dependence.
- **Does not:** say anything about whether G34's rule classes are *correct*, only
  that the program is deterministic and its record is faithful.
- **Does not:** touch the unsourced comparison in G34's headline verdict. A
  reproduced number compared against an unverifiable one is still an
  unverifiable comparison.
