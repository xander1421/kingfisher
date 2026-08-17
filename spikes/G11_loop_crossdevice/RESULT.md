# G11 — determinism survives iteration

**Verdict: IDENTICAL at every cycle.** Six cycles of G10's loop, run on desktop
and phone, comparing `status`, `fuel_used` and `raw_hash` **per cycle** rather
than only at the end.

```
cyc  live    status   fuel_used   raw_hash              match
  0    60        OK     4829611   63398348e00517eef0…    YES
  1    54        OK     3975151   75d5d1342422c07ac8…    YES
  2    49        OK     3326351   b7b0b09c8276cfb72b…    YES
  3    45        OK     2848711   1e9fd5ba418b8a89f6…    YES
  4    41        OK     2407871   2db87e366ff38256e4…    YES
  5    37        OK     2003831   e109ea449fb6610bd2…    YES
```

## Why this is a different claim from G1 and G5

G1 and G5 proved single-pass byte-identity. A loop carries state: cycle *N*'s
importance is cycle *N−1*'s output, and cycle *N*'s graph is what *N−1* pruned.
A divergence therefore **compounds** rather than being observed once and
discarded.

**A single-pass test cannot detect drift**, and drift is the failure mode the
architecture rests on not having. Comparing only the final state would report
"differs" and lose the cycle at which it started — so the comparison is per
cycle and the verdict names the first divergent one. There was none.

Fuel falls monotonically with the live set (4.83M at 60 nodes → 2.00M at 37),
which is the expected shape and a cheap plausibility gate on the run.

## Scope, stated precisely

**What is verified cross-device: the ECAN epoch**, at every cycle, on inputs
derived from the previous cycle's output. That is where the arithmetic and the
state-carrying live.

**What ran host-side only: the query and prune steps.** The Python orchestration
computes stimulus and selects the prune set on the desktop, then ships the epoch
program to both machines. So the honest claim is *"the state-carrying step is
identical at every cycle"*, not *"the whole loop is deterministic cross-device"*.
Closing that needs the orchestration on-device, which is M1.1/M1.3 and does not
exist.

**Both machines are aarch64** — cross-OS/cross-libc (macOS/libSystem against
Android/bionic), **not cross-ISA**, per S57's correction of S15.

## Other limits

- Six cycles, not G10's ten. Each cycle is two full runs plus an adb round trip;
  six was the budget. G10 established the loop survives to ten host-side.
- Device gate OPEN at start (`cpu_busy 4.2%`, thermal 35.5 C, battery 100%).
  Nothing here is timed, so the gate matters only for the run completing.
- 60 nodes, one graph, one prune rate. Unchanged from G10.

## Reproduce

```sh
cd spikes/G11_loop_crossdevice && python3 loop_xdev.py    # ~2 min
```
