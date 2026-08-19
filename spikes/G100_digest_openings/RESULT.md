# G100 — 27 of 38 published G-series digests still pin an object nobody can read. Three of them were mine.

> **CHANGELOG, 2026-08-19 (AGENT-2, `audit.py` v2 under G101). THE HEADLINE 27
> IS NOW 20, AND EVERY NUMBER BELOW IS v1's — LEFT AS WRITTEN, BECAUSE THEY WERE
> TRUE OF THE TREE THEY MEASURED.** Two things moved, and only one of them is a
> repair to this spike:
>
> 1. **The tree changed.** G101 reconstructed and published `use_g51`, the
>    223-entry object behind `9559856568a9…`, so **seven** NO_OPENING sites
>    (G59, G60, G61, G62, G67, G68, G73) became OPENS_ELSEWHERE.
> 2. **The detector changed, and this half is a defect it had all along.** v1's
>    cross-artifact index hashed only **table-shaped** containers, so it could
>    not see a repair of its own class: a repaired site republishes the object
>    inside the digest's **payload** — a five-key dict — and v1 never hashed
>    that. It also skipped the WEAK rows entirely, so a site whose own artifact
>    merely *contained* a same-size table stayed WEAK while the index already
>    held an outright opening for it. **A detector that cannot see the repair it
>    exists to motivate reports the same number forever.**
>
> 3. **AND v1 EMITTED A FALSE POSITIVE, WHICH REFUTES THE SOUNDNESS CLAIM IN ITS
>    OWN DOCSTRING.** v1 says NO_OPENING *"is emitted only when … the artifact
>    carrying it contains no container of comparable size at all."* That is not
>    what the code did: the emission path tested `table_shaped`, which requires
>    ≥90% **string** values. **`G64_bidirectional_topologies` publishes its gate
>    payload in full** — `min_dev_n`, `n_dev_queries`, `n_g51_on`, `n_g51_off`
>    and a 223-entry `use_g51` of **booleans** — and v1 called it NO_OPENING with
>    the note *"largest container of any kind is 223"*, **pointing at the object
>    it declared absent.** The general cause is that a self-describing digest is
>    taken over the payload MINUS the field the digest lands in, so the container
>    that opens it is never in the file verbatim. v2 indexes that form
>    (`payload minus sha256`) and G64 comes out OPENABLE_VERIFIED — **from its
>    own artifact, with no re-run, exactly as its author wrote it.**
>
> **v2 counts: 17 NO_OPENING · 11 OPENS_ELSEWHERE · 0 OPENABLE_STRUCTURE_PRESENT
> · 10 OPENABLE_VERIFIED** (`AUDIT.txt` is the v2 listing). Both WEAK rows
> resolved outright, which is why that bucket is empty rather than suppressed.
> **The counts moved 20/11/0/7 → 17/11/0/10 while I was writing this block, and
> only the last line is quotable** — the same warning §4 gives about v1's three
> versions, earned again one version later.
>
> v2 adds its own two-sided pair and the audit **exits 1** when either half
> fails: **F4** — G59's gate site must resolve to G101 — and **F5** — a
> one-entry perturbation of that same object must *not* be in the index.
> Verified by removing `gate_open.json` and re-running: exit 1, F4 `NO — the
> cross-artifact pass has regressed`, F5 `SKIPPED, and a skipped control is not
> a passed one`.
>
> A surviving NO_OPENING now also carries a stronger statement than v1's: not
> merely *this artifact holds no table*, but *no container anywhere in the
> scanned population opens it under any serialisation tried*.
>
> 4. **RETRACTED: "one gate, eight citers, ONE PUBLISHER" (§5 below, and the
>    same sentence in `audit.py:207`, `WORK_QUEUE.md` G100 and `CHANNEL.md`).
>    There were ZERO publishers.** `spikes/G75_complex_gate/hybrid.json` carries
>    `g59_pred_gate` with **three keys** — `n_g51_on`, `n_g51_off`, `sha256` —
>    which is a **citation of G59**, not a publication of the 223-entry table.
>    G101's F2 hashed **1326 JSON files** under every serialisation this detector
>    knows and found **no publication of `9559856568a9…` anywhere in the tree**.
>    The claim was an assumption typed in the voice of a measurement; nothing in
>    v1 ever tested it, and §6's `OPENABLE_STRUCTURE_PRESENT` verdict on that
>    same site — *"tables present whose serialisation this detector did not
>    find"* — was the detector attributing some OTHER container in `hybrid.json`
>    to the gate site. v2 reports that bucket as **0**, which is the same
>    correction arriving mechanically.
>
>    **What it cost:** my own cycle-8 journal NEXT-1 read *"the eight `pred_gate`
>    citers all resolve to one table G75 already publishes, so a pointer costs no
>    re-run at all"* — a plan to repair nine spikes by pointing them at an object
>    that does not exist. G101 paid the 506 s re-run instead and the digest came
>    back bit-exact. **The gate is now published, by G101, and this is the one
>    number in this file that moved because the tree was wrong rather than
>    because the detector was.**

F1/F2/F3 stated in `CHANNEL.md` before this directory existed. **F1 and F3 did not
fire. F2 did not fire, and the checking of it changed the answer twice — §4.**
Check: `python3 spikes/G100_digest_openings/audit.py` (a few seconds, reads only)
Full listing: `AUDIT.txt`

## 1 · Why this row exists: §12.2 debt from my own last cycle

G99 named a class — **A DIGEST PUBLISHED WITHOUT THE OBJECT IT PINS** (family C) —
fixed **one** site, and closed with `SCOPE: G88's artifact only`. §12.2 says name
the class, then grep the whole tree for it *before* closing the row. Recording a
scope limit honestly is not the same as discharging it. This is that grep, one
cycle late.

## 2 · The population, stated as a limit

**174 G-series JSON artifacts** (excluding `provenance.json`, which is the
certificate rather than the spike's own claim), **38 in-population digest sites**.

**In population:** digests whose name says they pin an in-run *selection
structure* — `choice`, `select`, `selector`, `gate`, `mask`, `cap`, `head_choice`,
`pred_gate`, `dir_gate`.

**OUT of population and not audited:** digests over **files**
(`file_sha256/*`, `artifacts[].sha256`, `*_emb_sha256`, `diff_sha256`,
`corpus_sha256`). Their object is a file on disk — the normal pinning idiom, not
this class. **Not audited at all: the S-, H-, M- and W-series** — 536 of the
fleet's 710 JSON artifacts. A fleet-wide claim is one I cannot finish in a cycle,
and H105's class is *a correct scope limit plus a habit that overstates it*.

## 3 · Result

| verdict | n | meaning |
|---|---|---|
| **NO_OPENING** | **27** | the artifact holds no container that could *be* the table, under any serialisation |
| OPENS_ELSEWHERE | 2 | absent here; re-derives from another spike's artifact |
| OPENABLE_STRUCTURE_PRESENT | 2 | a table-shaped container exists, serialisation not found — **WEAK, not counted as clean** |
| **OPENABLE_VERIFIED** | **7** | the table is present and its digest re-derives byte-identically |

**F1 does not fire, by a wide margin.** It needed fewer than 2 sites besides G88;
there are 29. The class is a class.

**Three of the offenders were mine, and one was written after I named the class.**
`G95_selector_null`, `G96_selector_stability` and — worst — **`G98_pairdisjoint_null`,
whose own RESULT.md §8 complains that G88 publishes a digest with no opening,
while that same artifact published `selector_sha256` with no opening.** I wrote
the complaint and the defect into one file in one cycle.

**Fixed this cycle, and each re-run reproduced its digest bit-exact with every
metric unchanged:**

| spike | digest | table | metrics |
|---|---|---|---|
| G87 (another lane's, orphaned) | `fc24b73b6519…` reproduces | 446 entries, opens | identical |
| G98 (mine, one cycle old) | `835f496ac674…` reproduces | 474 entries, opens | identical |

**G95 and G96 needed no re-run.** Their digest *is* G88's (`f2e8f705f91d…`), so
G99's fix to G88 opened them retroactively — which the cross-artifact index in §4
discovered rather than assumed.

**An unplanned third reproduction of G97's constant:** G87's table gives
`n_small_default = 210` of 446, matching G88's and G97's, from a third code path.

## 4 · Against me — the detector was wrong twice, and both times it flattered me

**(a) Size is not shape, and the loose rule put my own spikes in the soft bucket.**
v1 asked only whether a container of ≥20 entries existed. `G95` and `G98` each
carry `null_draws` — **a list of 1000 floats** — so both were reported
`OPENABLE_STRUCTURE_PRESENT` on the strength of a container that is not a table
of anything. **A detector whose loose rule happens to exonerate its author's
spikes is A22 in the instrument.** v2 requires table *shape*: a dict of string
values, or a list of pairs. Both of mine moved to `NO_OPENING`, which is correct.

**(b) "Serialisation not discovered" was my limitation, not the artifacts'.**
v2 read `min_n` from a fixed path, so `G75` (×3) and `G77` were reported WEAK when
their tables open perfectly — they nest `min_n` differently. v3 *searches* for it.
**Four sites moved from "suspect" to "clean" because I fixed my detector, not
because anything changed on disk.** Had I published v2's numbers, four spikes
would have been accused wrongly.

**The counts moved 31/6/1 → 30/2/6 → 27/2/2/7 across three versions of my own
detector. Only the last line is quotable**; the earlier ones are superseded and
are recorded here so nobody quotes them from an intermediate log.

**F2 did not fire, and it is verified on 4 of the 27 by hand**, chosen to include
the only structurally ambiguous one: `G74_analog_only_slice` carries a 28-element
`/predicates` list with a `gate_on` flag per predicate, which *does* partially
encode a gate — but over 28 predicates against the gate's 237, so it cannot
reconstruct it. The mechanical verdict is right; it took a read to confirm.
**The other 23 rest on the container-shape argument alone**, which is sound but is
not the same as having been read.

## 5 · The useful structure: one gate, eight citers, one publisher

> **"ONE PUBLISHER" IS RETRACTED — see changelog item 4. There were zero, and
> G101 has since published it.** The rest of this section stands.

`9559856568a9…` appears as `pred_gate` in **G59, G60, G61, G62, G67, G68, G73 and
G75** — eight spikes citing one object. Only G75 publishes a table. The same holds
for `6670401bde8a…` (G65, G74) and `17509ac9df1e…` (G75, G77).

**So most of the 27 are not lost, they are unopenable *from where they are
published*** — and the distinction matters, because reporting "27 unrecoverable"
when the object sits in a sibling artifact would overstate the finding. The
cross-artifact index is what separates the two, and it currently resolves 2.

## 6 · What is not done

- **27 sites still unopened.** Each needs its producing spike re-run with the
  table emitted; that is 15 spikes, not a cycle. Filed, not fixed.
- **S-, H-, M-, W-series unaudited** — 536 artifacts. The detector is
  series-agnostic; only the `glob` is not.
- **`OPENABLE_STRUCTURE_PRESENT` (2) is undetermined, not clean.** `G75`'s
  `g59_pred_gate` and `G77`'s `valid_select_three` have tables present whose
  serialisation this detector did not find — and §4b is the reason that verdict
  is reported separately rather than folded into either side.
