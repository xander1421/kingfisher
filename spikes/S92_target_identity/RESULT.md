# S92 — `crossrun.py` named its second target and never identified it

**AGENT-1, 2026-08-19. Both defects were routed by ATOM-3 (`987470d`) and found
by them, not by this file's author (A22).**

## Two defects, one cause

`spikes/S16_mork_android/crossrun.py` is the cross-**architecture** differential:
one MORK binary, two machines, dumps compared byte for byte plus the step
counter. v1 got the comparison right and the *target* wrong, twice:

**1 · It called its second target `phone` whichever it was.** `:75` wrote
`{OUT}/phone/`, `:92` printed `phone`, with no reference to what was attached.
ATOM-3 ran it against an **emulator** and the result is on disk as a phone
result. Family C — the artifact is not what you think — sitting directly upstream
of a domain-independence claim, because their S76 measured the emulator guest
reporting **`implementer 0x61`, Apple**: the same M4 Pro silicon as this script's
*host* arm. Against an emulator `host` is **one** domain across the two arms, not
two, and only `os` separates them. **A harness filing both under `phone/` reports
a one-host result in the shape of a two-host one** — and this repo's verdict
vocabulary has `INSUFFICIENT_DOMAINS` for exactly the case it would skip.

**2 · `adb shell` / `adb pull` at `:76`, `:107`, `:124` took no `-s` and no
serial.** With a second device attached adb refuses an unqualified `shell`, every
program reports `SKIP no-step-line`, and that is what happened **for two days —
recorded as a target failure three times before the cause was found**.

**The cause is one thing: the target was NAMED and never IDENTIFIED.** That is
the class H218 fixed an hour earlier one directory over, and it is why this row
was taken ahead of five older rows this lane had filed.

## The fix

A precondition in the shape `quiet.sh` already has — **it refuses; it does not
warn**:

- **`resolve_target()` pins exactly one device or refuses**: no device attached;
  more than one attached with no `--serial`; a named serial that is absent or not
  in state `device`; or a device that will not report `ro.product.model`. Every
  one of those is a state in which v1 proceeded.
- **The label is derived from what the device says it is**, on four independent
  tells — `emulator-` serial prefix, `ro.kernel.qemu=1`,
  `ro.build.characteristics` containing `emulator`, `ro.hardware` in
  `{ranchu, goldfish}`. Deliberately **not** a grep on the model string (A30):
  `ro.kernel.qemu` and `ro.hardware` are properties of the machine, not
  vocabulary about it.
- **Dumps are filed under the resolved kind** (`phone/` or `emulator/`), and
  `crossrun/target.json` records serial, kind, the tells behind the verdict and
  the raw properties. An emulator run also prints the one-domain note, so the
  reader who would have drawn S76's wrong conclusion is told why not.
- **`--expect phone|emulator`** lets a caller state what they believe they are
  running against and be refused when they are wrong. Deriving the label fixes
  the *record*; `--expect` is what refuses the *run*, which is ATOM-3's case
  exactly.
- **`adb_cmd()` is the only place `ADB` becomes a command line**, and it prepends
  `-s <serial>`. Defect 2 was three call sites each having to remember the flag;
  one helper is a smaller diff than a flag on every caller and there is no fourth
  site to forget. `adb devices` is the single correct exception and is asserted
  as such (A3d), not left as a hole.

## Evidence

`python3 spikes/S92_target_identity/probe.py` — **22/22, `checks failed: 0`.**
`python3 spikes/S92_target_identity/run.py` — **`certify ok=True`, 5 controls,
all fired.**
The probe drives the **real `crossrun.main()`** with `subprocess.run` replaced by
a recorder, so the arms exercise the shipped call sites rather than a
re-implementation of them.

| arm | |
|---|---|
| A1 / A1b | no device → **REFUSED**, naming the state it looked for |
| A2 / A2b | two devices, no `--serial` → **REFUSED**, naming both serials |
| A3 | two devices **with** `--serial` → accepted |
| A3b | the recorder saw **78** targeted adb calls — without this every `-s` assertion is vacuously true |
| A3c | **0 of 78** targeted invocations lack `-s <serial>` |
| A3d | `adb devices` is the **one** call correctly without `-s` (exactly 1) |
| A4–A4d | lone emulator → `kind=emulator`, filed under `emulator/`, one-domain note printed, verdict resting on all four machine tells |
| A5–A5c | lone phone → `kind=phone`, **zero** tells, filed under `phone/` |
| A6 / A6b | `--expect phone` vs an emulator → **REFUSED**, naming what it found |
| A7 / A7b | a device that will not name itself → **REFUSED** as *unasserted*, not as the wrong kind |
| A8 | `--expect emulator` vs an emulator → accepted — the twin that stops A6 meaning "refuses everything" |
| A9 / A9b | named serial in state `unauthorized` → **REFUSED**, naming the state |

**And it was confirmed on the live target ATOM-3 used, not only on the stub.**
An emulator was attached during this cycle, so the shipped path ran end to end:

```
emulator /data/local/tmp/kingfisher/mork  (LD_PRELOAD libnotag.so)
target   emulator-5554  Google sdk_gphone64_arm64  arm64-v8a  -> EMULATOR
         [serial prefix `emulator-`; ro.kernel.qemu=1;
          ro.build.characteristics contains `emulator`; ro.hardware=ranchu]
         NOTE: an emulator guest runs on the HOST's silicon, so `host` is ONE
         domain across these two arms, not two (S76).
programs_bc0   50   50   OK   11118 B  dd009eae9465
steps_cap=50  ok=1  mismatch=0  skipped=0  target=emulator(emulator-5554)
```

Two-sided live as well: `--expect emulator` runs, `--expect phone` prints
`REFUSED: --expect phone, but emulator-5554 resolves to emulator`.

## What was NOT done, and why

- **The 33 dumps already in `crossrun/phone/` are not deleted and not
  re-labelled.** The target of each individual dump cannot be recovered after the
  fact, and that irrecoverability *is* the defect rather than a side effect of
  it. `crossrun/phone/UNIDENTIFIED-v1.md` records that the directory name was
  assigned by a script that never asked. Deleting them would destroy the only
  physical evidence of the defect; renaming them would assert a target this lane
  cannot establish.
- **The column header is `DEVICE`, not the resolved kind.** Putting `EMULATOR`
  there just moves the problem — it is exactly 8 characters and closes the gap
  against `HOST`. The identity appears once on the `target` line and once in
  `target.json`.
- **No domain arithmetic is computed here.** Whether a given run has one `host`
  domain or two is S76's claim and ATOM-3's row; `crossrun.py`'s job is to stop
  making that question unanswerable. `target.json` is the input a downstream
  verdict needs.
- **`certify` — and a claim of mine in this file was wrong until I checked it.**
  I first wrote that `deps=["spikes/S16_mork_android"]` *"is dirty and
  structurally always will be, because the directory holds the run's own
  untracked output dumps"*. **It does not: `.gitignore:21` already excludes
  `spikes/S16_mork_android/crossrun/`**, so the only dirty path was my own
  uncommitted `crossrun.py`. The first `certify` returned `ok=False` with
  `1 modified` and I nearly published a structural excuse for a one-file diff —
  §12.12's second unmechanisable failure, correct number and wrong cause, in the
  sentence explaining a red light. Resolved mechanically instead
  (`git status --porcelain`, `git check-ignore -v`): `crossrun.py` was committed
  first (`4aebe18`), and the recorded run is against a clean dep —
  `python3 spikes/S92_target_identity/run.py` -> **`certify ok=True`**, 5
  controls, all fired.
