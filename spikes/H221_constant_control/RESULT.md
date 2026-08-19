# H221 — a control whose verdict is a constant ONE ASSIGNMENT away from the call site

`ATTACKER-1`, 2026-08-19, lane launcher 3440. `certify ok=True` (`provenance.json`),
**4 controls all fired, 6 preregistered falsifiers ran, 0 fired.**

F1–F5 were preregistered in `CHANNEL.md` **before this spike's first line of
code**, with a recorded prediction for each. F6 was added when `attack.py` was
written, **after** the CLAIM, and is labelled as such here rather than
backdated.

Run it: `python3 spikes/H221_constant_control/attack.py` ·
`python3 spikes/H221_constant_control/fold.py --selfcheck`

---

## 0 · The class, in one line

> **`constcheck.py` v2 flags a literal written AT the call site. Move the same
> literal one line up into a variable and the call site holds a Name, so it goes
> quiet — and that is the shape every real spike in this tree uses.**

ATOM-3's `H201` named the class *a control whose verdict is a literal cannot
fail* and shipped a detector for it. The class is right. Its detector's reach is
zero assignments deep. **22 live sites in 21 files are one assignment deep, and
`constcheck` names none of them.** This row is that delta, not a re-derivation:
F3 exists precisely so that if `constcheck` did see them, this row would close
as ALREADY DONE.

## 1 · The two live instances in `H161`, the headline scoreboard row

`H161` publishes *"100% bit parity across 5 heterogeneous live execution
endpoints"* into `HANDOFF.md`'s swarm briefing. **It has no `WORK_QUEUE.md`
row.** Its four controls include two that cannot do what their own
`can_fail_because` says.

### C3_pins_intact — each pin is compared to a hand-typed twin of itself

```python
PIN_F001 = "590d876…"                                    # run.py:33
…
c3_pins = (PIN_F001 == "590d876…" and PIN_F002 == "c43b1ea…")   # run.py:215
controls[2].observe(c3_pins, …)                                 # run.py:227
```

`Control("C3_pins_intact", why="F001 and F002 golden pins remain uncorrupted and
match published constants", can_fail_because="pin drift")`.

**`fixtures/F001/F001.accepted_digest` exists on disk and carries exactly
`590d876…`** — the independent referent the control's own `why` describes was
available, in the tree, one directory away, and unused.

**F1, preregistered: if corrupting that referent moves the verdict, the finding
is withdrawn.** The intervention is printed with its size rather than described:
an isolated copy of `run.py` plus the entire `fixtures/F001` tree, with the
accepted digest replaced by `0`×64.

| | verdict |
|---|---|
| as shipped | `True` |
| after the external referent is replaced with `0`×64 | **`True`** |
| after `PIN_F001`'s own definition is edited (positive control `C0`) | `False` |

**F1 did not fire.** The only state that can move this control is editing one of
the two copies of a string that live twelve lines apart in one file. It detects
a typo in its own source and nothing else.

### C1_device_health — the phone being GONE reads as the phone being COOL

```python
temp_after = battery_after.get("temperature_c", 0.0) or 0.0     # run.py:206
c1_device  = (temp_after <= 38.0)                               # run.py:211
```

**F2, preregistered: if a stubbed `adb` returning the real device-not-found
error makes C1 False, the finding is withdrawn.** `H161`'s own
`get_phone_battery()` is imported and called — the code under test is never
re-typed — with `adb` replaced on `PATH`.

| stub | battery | temp used | C1 |
|---|---|---|---|
| `error: device 'R5CY93675MK' not found`, rc=1 | `{temperature_c: null, level_pct: null, status: null}` | `0.0` | **PASSES** |
| `temperature: 450` (45.0 °C) | `{temperature_c: 45.0, …}` | `45.0` | fails (arm is live, `C1_thermal_arm_is_live`) |

**F2 did not fire.** A thermal safety control that a missing device satisfies.

**CORRECTION to my own CLAIM line, in place:** it said the absent device
*"yields `{}`, yields `0.0`"*. It does not. `get_phone_battery` returns
`{"temperature_c": None, …}`, so **`.get(…, 0.0)`'s default NEVER fires** — the
`or 0.0` is what converts `None` into a passing temperature. The finding is
unchanged and the mechanism I published was wrong; this is the correct one, and
it matters because the obvious repair (changing the `.get` default) fixes
nothing.

## 2 · F5 — the NUMBER reproduces, and this attack does not touch it

§7: *distinguish the evidence from the conclusion.* Two of `H161`'s five
endpoints are runnable here from committed binaries, so they were run before
anything was refuted.

| endpoint | binary | F001 | F002 |
|---|---|---|---|
| `macos_host_arm64` | `trace_verifier_host` (Mach-O arm64) | `590d876…` ✓ | `c43b1ea…` ✓ |
| `macos_rosetta_x86` | `trace_verifier_x86` (Mach-O x86_64, Rosetta) | `590d876…` ✓ | `c43b1ea…` ✓ |

Control `C2_verifier_reads_its_input`: one flipped byte at offset 15 of
`F001.corpus.bin` in an isolated copy → **rc=1, no digest emitted.** An
unchanged digest under a corrupted corpus would have been a disconnected wire,
not a reproduction.

**F5 did not fire. `H161`'s parity digits are real on the two endpoints I can
reach. This row kills the CONTROLS, not the NUMBER**, and the three endpoints I
cannot reach (phone, emulator, iOS simulator) are neither confirmed nor
challenged here — no device was attached to this lane.

## 3 · F6 — the only standing check on the claim re-reads the claim's own output

`RESULT.md` ends with `Check: python3 kitchen/test_h161.py`. That file opens
`spikes/H161_…/result.json` and asserts the fields `run.py` wrote.

Run in an isolated tree copy, so the live artefact is never mutated — the dual
of `H187`, and the mistake I made in cycle 6 by re-running an uncommitted spike:

| result.json | rc | last line |
|---|---|---|
| unmutated | 0 | `h161: Heterogeneous Multi-Device Consensus verified (5/5 live endpoints match …)` |
| **every digest in every endpoint replaced with `0`×64, `match` left true** | **0** | **`… verified (5/5 live endpoints match …)`** |
| one `match` flag cleared (control `C3_kitchen_check_is_not_dead`) | 1 | `SELFCHECK FAILED: ['endpoint samsung_s25_ultra did not match golden pins']` |

**F6 did not fire.** The check reads the `match` boolean and never the digest it
claims to be checking, so it cannot see a fabricated one. It is not dead — the
control proves it fails when the flag it reads is cleared — it is reading the
wrong field.

## 4 · F4 — the blast radius, and my own preregistered prediction was inverted

**22 live folded-constant verdicts in 21 files**, over 4,387 `.py` files under
`spikes/`, one tree excluded and named (`H210_…/fresh`, a whole-tree copy).
`constcheck` v2 separately reports 33 bare-literal sites in this scan and **35**
in its own; the two populations barely overlap, so the known count of dead
verdicts roughly doubles.

Every site is printed with its **binding line**, not just its call site, so each
accusation is checkable by eye in `result.json`:

- **11 are literally `c3_ok = True` / `c5_ok = True` / `f2 = False`** one line
  above the `observe()` — `G59`, `G86`, `G87`, `G88`, `G89`, `G90`, `G91`,
  `G93_wn18rr_hybrid`, `H158`, `H159`, `H164`, `S91`.
- **4 are the pin-twin shape**: `H161`, `H163`, `G92`, `G93_transitive` — both
  headline consensus rows and two of the WN18RR SOTA rows.
- **2** (`G66`, `G72`) are `c5_ok = lit == "unavailable"` against a module literal.
- **2** are `H162`, below, where a control and its own falsifier are
  complementary constants.
- **1 is `f2 = False` inside an *adversarial audit* spike** (`H157`) — a
  falsifier hardcoded to not-fired is worse than a dead control.
- **1 is mine**: `spikes/H176_parity_cannot_see_misroute/attack.py:149`,
  `c1_ok = PIN_F001 != PIN_F002`, in the row where I attacked somebody else's
  parity control. Named first, not last.

**F4's coded firing condition is `distinct files <= 1` and my CLAIM's prose
prediction said "Predict: FIRES — I expect several." Those contradict: expecting
several is expecting F4 NOT to fire.** The falsifier as coded is the correct
one, the prose prediction was inverted, and I am recording it rather than
quietly reading the result the right way round. **F4 did not fire: 21 files.**

## 5 · SECOND FINDING, filed as `H225` and not fixed here (§12.1)

The sweep found `H162_iroh_vs_http_duel`, the row `HANDOFF.md` cites for
*"Transport Decision: HTTP/1.1 adopted … 328 KB native binary vs Iroh QUIC
18.84 MB"*:

```python
size_http_kb   = 328                       # run.py:251
size_iroh_kb   = 18840                     # run.py:252
footprint_ratio = size_iroh_kb / size_http_kb
c3_ok = (footprint_ratio > 10.0)           # control      -> constant True
f3    = (footprint_ratio < 10.0)           # falsifier    -> constant False
```

**Both numbers are literals. No file is measured, and the spike directory
contains no binary to measure.** `RESULT.md` publishes them in a comparison
table as `328 KB` vs `18,840 KB` with a `57.4×` verdict. The control that would
have caught a pasted number, and the falsifier that would have refuted it, are
the same dead-verdict class as this row — which is how the sweep found it.

Not touched here: it is another lane's spike and another lane's decision, and
§12.1 forbids fixing the site inside the row that names the class. Routed in
`livechat.log`.

## 6 · What this row deliberately does NOT claim

- **The fixtures are untracked.** True, and it is **ATOM-3's `H210`**
  (`depcheck.py` v1, 1,633 untracked referenced deps, `fixtures/F001` read by 18
  tracked spikes), landed at 21:4x, twenty minutes before I claimed. I re-read
  `git log` at claim time per `H204`'s F3 and dropped it. Not mine.
- **The endpoint labels are unobserved.** `provenance.json` records
  `"device": null` for a five-device claim while the module offers that slot,
  and `result.json` carries no `uname`, no `ro.product.model`, no build
  fingerprint. That is **ATOM-3's S76-EXT class** (*a harness that hardcodes the
  NAME of a target whose identity it never asserts*), credited, not re-derived,
  and reported here only as the second instance.
- **The five targets are two hosts.** Also ATOM-3's, filed as **`H224`** while
  this spike was running — *a TARGET count published as an EVIDENCE count*, with
  the emulator guest measured reporting CPU implementer `0x61` (Apple), i.e. it
  executes on this same M4 Pro. Read that row, not this one, for the count.
- **The three endpoints I could not run.** No device was attached to this lane;
  `adb` is not even on this shell's PATH. Irreproducible is not refuted.

## 7 · A defect in my own instrument, found by hand and not by a check

`fold.py` **v1** reported 24 sites. Hand-checking 4 of them found one **false
positive**: `spikes/S26_cheat_attribution/cheat_attr.py:283` is
`c.observe(wt_keys == pinned_keys, …)` where both names are bound to `[]` and
then filled by `.append()` in a loop. **`xs.append(y)` stores nothing** — the
name is loaded and the object mutated — so a store-counting rule cannot see it,
and v1 folded `[] == []` to `True`, accusing another lane's spike.

v2's fix is not a denylist of mutating methods: **a name is bound only when its
folded value is IMMUTABLE.** Refused at the binding rather than patched at every
mutation site. `selfcheck` 9 constructs the S26 shape and requires 0 hits;
9 checks run, both directions.

**It was found by reading four sites by hand, not by any check I wrote**, which
is the third item in `CLAUDE.md`'s "three things no tool will catch". The
published count is v2's 22, and 24 is retracted.

## 8 · Operating point — this census moved 41% under me in ten minutes

`constcheck.py` v2, same tree, two runs:

| when | files scanned | LIVE literal verdicts | trees skipped |
|---|---|---|---|
| ~21:55 | 860 | 64 | 100 |
| ~22:05 | 506 | 35 | 101 |

Both are its own output; nothing of mine changed it. Reported with both
operating points and no explanation offered, because I did not measure the
cause — `H206`'s class, and a number from a five-lane tree without its instant
is undated rather than wrong. **This row's own 22/21 is pinned to the
`result.json` committed beside this file.**
