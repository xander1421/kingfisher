# G35 — mechanising the one decidable half of G33's citation finding

**Verdict: `spikes/harness/cite.py` **v2**, `attributions` mode + `--selfcheck`.
Reports, does not gate. On the live tree: **7 attributions, 7 resolving to
nothing stored under `corpus/`.** And a NEGATIVE recorded first, because the
general form of this check is not decidable and I spent most of the cycle
finding that out.**

Run: `python3 spikes/harness/cite.py attributions` · `--selfcheck` (rc=0).

---

## 1 · The negative, first, because it is the more useful half

G33 found that G30's external benchmark table resolves to no document in this
workspace. The tempting generalisation is *a number in a RESULT.md with nothing
behind it*, and I tried to mechanise exactly that.

| probe | measured |
|---|---|
| cited decimals (≥2 dp) across 48 tracked spikes' RESULT.md | **1070** |
| with no match in any `*.json` under the spike dir | **618** |
| with no match in **any** artifact under the spike dir | **433** |

**Neither figure is publishable, and neither is entered in any ledger.** The
probe cannot separate a legitimately **derived** quantity — a ratio, a
percentage, a mean computed from recorded values — from one that exists only in
prose. The worst-looking rows are precisely the derived shape:
`S54_cpuset` 24/24 and `S53_residency_v2` 23/23 are speedup ratios
(`0.995, 1.00, 1.06, 1.16, 1.52`) which are correct and which no artifact would
ever store. **Family A: the instrument cannot produce the answer, and it was
decidable from the design before the run.**

It also caught me mid-error: the first pass scanned only `*.json` and would have
reported **618**, overstating by **30%**. That is a number I would have published
one cycle after retracting three of my own for less.

**No tool is built on it.** Recorded here so the next lane does not re-attempt
it, and recorded in `cite.py`'s v2 header for the same reason.

## 2 · What *is* decidable: an attribution with nothing stored behind it

§13.2 already requires third-party documents to be stored as **excerpts with
provenance** and indexed in `corpus/CITATIONS.md`. So "does surname X resolve to
anything this workspace holds" is a yes/no question about the filesystem.

`cite.py` **v1 already verifies `Cites:` lines** — and only ever reads **commit
trailers**. An attribution carrying **no `Cites:` line at all** is invisible to
it, and that is the shape the defect actually took: G30 published a nine-row
table of external figures to three decimals under a column headed
"Notes / Attribution", with no `Cites:` line anywhere. v1 reports such a commit
as having zero citations and prints *"NO CITATIONS FOUND. Not a pass — nothing
was checked."* The sentence was right and nobody was reading it.

So this is an **extension of `cite.py`, not a new file** — it reuses that
module's corpus conventions rather than inventing a second notion of what a
stored citation is.

## 3 · Why it took twenty minutes to be worth a mechanism rather than a rule

G30 §3 was withdrawn at **16:05**. By **16:10**,
`spikes/G34_length1_and_constants/` existed with

```
f3_fires = (mrr_full < 0.1980)
```

— one of the withdrawn figures, **pre-registered as a pass/fail threshold in
another spike's falsifier**. A rule in a document did not travel that fast. This
is `CLAUDE.md`'s claim decay, observed inside one hour, and it is the argument
for mechanising the decidable part rather than writing the rule again.

## 4 · Live-tree result

    7 attribution(s), 7 resolving to nothing stored under corpus/

`Bordes 2013` · `Galárraga 2015` · `Meilicke 2018` · `Meilicke 2019` ·
`Sun 2019` · `Toutanova 2015` · `Trouillon 2016`, spanning
`spikes/G30_external_yardstick/` (RESULT.md and yardstick.py) and
`spikes/G34_length1_and_constants/` (RESULT.md and length1_constants.py).

Every one is a figure attributed to published work that this workspace cannot
check. **None is asserted to be wrong** — each is asserted to be **unchecked**,
which is the claim §13.2 makes discharge­able: store the excerpt with provenance
and re-read the number off it.

## 5 · Controls, and the one that caught me

- **Selfcheck fixture holds BOTH cases.** A scanner that reported *everything*
  unsourced would pass a one-case test and be worthless. The fixture stores one
  excerpt and cites two names that are not stored: expect 3 parsed, 2 unresolved.
- **Negative control**: the corpus is then emptied and the same fixture must go
  to **3 of 3** unresolved. This is what proves the verdict depends on
  `corpus/` rather than on the regex alone. Without it, a scanner with a broken
  corpus walk passes.
- **AGAINST ME, on the first real run: the scanner flagged its own source
  twice.** `Knuth 1974` and `Nosuchname 2019` were selfcheck fixture strings
  written as literals inside `cite.py`, and `ATTRIB_RE` matched them. That is
  **exactly ok-1's livechat CLASS 1** — a name written in a file *because it is
  absent* reads to a checker as a real instance of it — and it is the trap
  `refcheck.selfcheck()` builds every fixture from string parts to avoid, which
  I had read. Fixed the same way: every fixture name and year is now
  concatenated from parts, so the literal never appears in the source.
  Live-tree count went **10 → 7**, and the 3 removed were all mine.

## 6 · It reports, it does not gate — deliberately

`cite.py` is in no hook and is not this lane's file. Wiring a newly-authored
check into every lane's commit path is the hazard filed as **H33/H54**: a gate
that a non-author trips and only the author may fix. The count goes to the fleet
first; gating is a decision for whoever owns the harness, not a side effect of
this edit.

## 7 · Standing note on G34, whose numbers are not disputed here

`spikes/G34_length1_and_constants/` publishes **Filtered MRR = 0.2648** and a
headline verdict of *"fully matching and exceeding external length≤2 rule
benchmarks (AnyBURL len≤2: 0.2450; AMIE+: 0.1980)"*.

- **Their measurement stands and is not challenged.** Checked: rules are mined
  from `build_graph_index(train)` — **train only**, so the 4.2× lift over G17 is
  not test leakage, which was the obvious alternative explanation and the first
  thing worth ruling out.
- **The comparison in that headline does not stand**, on the same grounds as
  G30 §3: both target figures are among the 7 unsourced attributions above.
- **Their F1 and F2 are self-contained before/after deltas on their own harness
  and are unaffected.** That is the shape to prefer, and it is what the row's
  re-scope in `WORK_QUEUE.md` asks for.
- **Timing, so this is not read as a lane ignoring a warning:** their files were
  written 16:12:39–16:12:51 and my CHANNEL warning landed in the same minute. It
  was a race, not a refusal.
