# The nondeterminism patches are live in all four quorum binaries

`repro: spikes/M1_10_patchlive/probe.py`

**Falsifier, stated before running:** *all four quorum-member binaries carry the
patches live — every probe returns a single stable result on every binary.*

**Not refuted.** 4 members × 4 probes × 30 runs, every one `distinct=1`.

| worker | sha256 | intersection | subtraction | new_space | random_err |
|---|---|---|---|---|---|
| host-a | `f52d98196ad0` | 1 | 1 | 1 | 1 |
| host-min | `a867fbfa5f53` | 1 | 1 | 1 | 1 |
| host-x86 | `989da5cd3be7` | 1 | 1 | 1 | 1 |
| phone | `c90624244472` | 1 | 1 | 1 | 1 |

This was worth asking because M1.9 showed a patch applied to a `#[cfg]`-excluded
line is a silent no-op with a clean build, and **`host-min` is compiled with a
different feature set** (`--no-default-features --features pkg_mgmt`) while the
phone is a different ISA and OS. "The patch is in the tree" does not imply "the
patch is in this binary". It is, in all four — now verified rather than assumed.

## The actual finding is in the control

`distinct=1` means *stable*. It also means *measuring nothing*. A passing check
and an inert check are the same observation.

So: revert the three patched files, rebuild, and require every probe to change.

```
UNPATCHED build, 30 runs each        FIRST VERSION      after fix
  intersection   ($x B C)              distinct=3        distinct=3
  subtraction    (A $x B)              distinct=1  <<    distinct=3
  new_space      GroundingSpace-0x…    distinct=30       distinct=30
  random_err     (random-int …)        distinct=1  <<    distinct=30
```

**Two of the four probes were inert.** They reported `distinct=1` against a
build with the bug fully present — the same result they gave for the four real
binaries. Half the evidence in the table above was worthless until the control
exposed it, and nothing about the passing run looked wrong.

- **`random_err`** never reached the code it was testing. Builtin modules are
  `load_module_direct`'d but **not imported automatically**, so
  `!(random-int (new-random-generator 0) 5 0)` stayed unreduced as literal text.
  Stable, non-empty, well-formed, and measuring nothing. Fixed by prefixing
  `!(import! &self random)`; the unpatched build then prints
  `RandomGenerator-0x8f7214018`, exactly the signature the upstream report
  describes.
- **`subtraction`** used `(subtraction-atom (A $x B $y C) ($y C))`, which does
  not trigger the order-dependent wildcard collapse. The defect needs two
  variables positioned so the collapse evicts a live bucket. Fixed to
  `($y C A $x)`, which gives `distinct=3` unpatched.

## What this does and does not establish

- It establishes the four *binaries the quorum dispatches to today* are free of
  the four probed defects, on 30 runs each.
- It says nothing about **Issue 3**, the `NEXT_VARIABLE_ID` counter, which is
  reported upstream and deliberately **not patched**. That one is handled
  downstream by `canon` / `canon_alpha`, not in the binary.
- 30 runs bounds the detection floor: a defect firing on <3.3% of runs could
  pass. The pre-patch rates here were 40% (`intersection`) and 100%
  (`new_space`), so the margin is wide for these four — not for an arbitrary
  defect.
- The phone was checked **on-device**, over adb, under the §10 gate: the
  battery instrument is checked for a frozen override *before* it is read,
  because a stuck `dumpsys` once reported a discharging phone as charging for a
  whole session.

## The general form

M1.9 found a mutation that applied cleanly and never compiled. This found two
probes that ran cleanly and never tested anything. Same shape from opposite
directions: **the edit succeeded, the build succeeded, the check passed, and
nothing was verified.**

The only defence is a negative control — deliberately break the thing, and
require the check to notice. A check never run against a known-bad input is a
check with an unknown floor, and here that floor was zero for half the suite.
