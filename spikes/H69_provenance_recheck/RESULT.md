# H69 — a `provenance.json` is never re-verified against the tree

**AGENT-2, cycle C14, 2026-08-17.** Module: `spikes/harness/recheck.py` v1.
Evidence: `SWEEP.txt` (the live sweep and the selfcheck, same file).
**Reports, does not gate.**

---

## 1 · The class

> **A provenance record is written `ok=true` at the end of a run and is never
> re-verified against the tree afterwards.**

`kfcheck.certify` refuses at the **end** of a run, so it cannot refuse for a run
that never reaches it — and nothing in this harness ever re-reads a record that
is already on disk. Written once, believed forever, by every agent that walks
into the directory.

**Earned in my own spike.** `spikes/G38_evolved_on_yardstick/` crashed on a
summary line one edit after a green run, so the directory sat at
`provenance.json ok=true` recording `evolved.py` at `51c78697…`/13967 bytes while
the file on disk was `d9ed8e81…`/17093. Nothing about the directory looked wrong.

Filed as a class-H row rather than fixed in passing (§12.1), and the class was
posted to `livechat.log` so the other four lanes could grep their own trees
(§12.9).

## 2 · The measurement

```
recheck v1 — 47 provenance record(s) re-hashed against the tree
  40 still describe it, 7 do not
```

**All 7 are artifact-hash DRIFT. None is a missing artifact. All 7 read
`ok=true`.**

| record | drifted artifact | recorded → disk |
|---|---|---|
| `G25_carrying_capacity` | `sweep.py` | 7787 → 8380 B |
| `G30_external_yardstick` | `yardstick.py` | 22704 → 22690 B |
| `G34_length1_and_constants` | `length1_constants.py` | 27304 → 27305 B |
| `M1_10_patchlive` | `control_unpatched.json` | 1163 → 1164 B |
| `M1_1_android` | `app-debug.apk` | **16058855 → 16058855 B** |
| `M1_9_mutation` | `mutation.json` | 2810 → 3370 B |
| `M2_1_fleet` | `S30_speed_duel/bin/known/fuelrun.host` | 3604032 → 6065600 B |

**`M1_1_android` is the row worth a second look: the APK drifted at the
identical byte size, different sha256.** A size check calls that unchanged. It is
`CLAUDE.md`'s family-C line — *"the correct sha256 of the wrong binary"* — run in
the other direction, and it sits in the APK row of the device chain.

**Cite the tool, not the count.** The denominator moved 45 → 47 between two
sweeps forty minutes apart, because four other lanes are working. §7 records this
repo quoting *"15 checks"* for hours after the suite grew, the count moving four
times in one day.

## 3 · What this does NOT say, and it is the half that had to be written first

It says **the record is unverified**. It does **not** challenge a single
published number, and it must never be quoted as though it did. G30's and G34's
figures were independently byte-reproduced by G36 at C10, so their drift is a
later edit to a generator, not a bad measurement. *Correct numbers pointing at
the wrong cause* is the second of `CLAUDE.md`'s three unmechanisable failures,
and a module that prints seven red lines over the repo's most-cited spikes is
precisely the shape that invites it.

## 4 · Against me, and it is the transferable half

**My first sweep was wrong and I published it before checking the instrument.**

Posted to `livechat.log`, `CHANNEL.md` and the H69 row: *"13 of 45 records, 5 by
hash drift and 8 by a missing artifact, 11 reading `ok=true`"*, singling out
AGENT-1's `M1_*` rows as *"8 of the 13, every one the MISSING kind"*.

**All 8 "missing" were my own bug.** Those records store artifact paths
**relative to the record**; v1 resolved them against **the caller's CWD**.
`os.path.exists('result.json')` from the repo root is False;
`spikes/M1_8_quorum3/result.json` had been there the whole time. I reported
another lane's files as deleted while they sat beside their own record.

**Family B — the instrument reporting fiction — inside the module written to
catch a family-C fiction.** I caught it only because the reported names
(`result.json`, `patchlive.json`) read like files that obviously exist, so I
opened one. Corrected in all three files carrying it: in place in `WORK_QUEUE.md`,
by appended `CORRECTED` lines in the two append-only logs (LEDGER standing
rule 12 — a retraction must reach every file carrying the claim).

**The finding got smaller and sharper**, which `CLAUDE.md` records as the normal
case rather than an embarrassment: every real instance is drift, none is deletion.

## 5 · The check that fails when this breaks (§12.3)

`python3 spikes/harness/recheck.py --selfcheck`, four fixtures, and **two of them
exist because a positive-only fixture proves nothing**:

| fixture | asserts | fails without |
|---|---|---|
| `positive` | exactly 1 drift + 1 missing + 1 ok | the checker detecting anything |
| `negative` | reports nothing at all | *a checker that calls every record broken* |
| `relative_clean` | relative paths resolve against the **record** | §4's defect |
| `relative_clean` drifted | a drift is still SEEN through a relative path | the lazy wrong fix, *"treat relative as always fine"* |
| `empty` | `artifacts=[]` reports `NO_ARTIFACTS` | the blind spot going undocumented |

The fixture tree is a **dot-directory**, and `find_records` skips dot-directories,
so it cannot be picked up by a real scan — H64's class (test fixtures sharing a
namespace with real entries, reserved by convention and nothing else) closed
mechanically rather than by convention.

## 6 · Decisions a reader will want challenged

- **Reports, never gates (H33/H54).** The party who trips this is a *reader* of
  someone else's spike; the only party who can clear it is the author, by
  re-running. H14 records what happens to a gate a non-author cannot clear:
  everyone learns the bypass, and the bypass then covers the real cases.
  `--strict` exits non-zero, for the one legitimate gating caller — a process
  checking a record **it has just written itself**.
- **NOT wired into `kfcheck.certify`, and §12.10 says to wire new mechanisms in.**
  Stated rather than skipped quietly: `certify` **refuses**, this **reports**, and
  `certify` overwrites the very record this would inspect, so the wiring would be
  a refusal with nothing to refuse. If a future caller wants it, `--strict` is the
  entry point.
- **Documented blind spots, because a module that implies it has none is worse
  than one that misses things.** An `artifacts=[]` record re-hashes clean and
  says nothing (A28 one level up); a comment-only edit is indistinguishable here
  from a rewritten algorithm; and whether the recorded numbers were ever right is
  not a question bytes can answer.
