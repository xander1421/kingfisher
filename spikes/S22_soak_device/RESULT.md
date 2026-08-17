# S22 — M1.3b's soak on the phone: process reuse is safe on the deployment target

**AGENT-1, 2026-08-17.** `python3 soak_device.py` · `soak_device.json` ·
`device_soak.tsv` · `certify ok=true`, 4 controls all fire, **the falsifier did
NOT fire, and a second falsifier DID**.

## The gap, in M1.3b's own words

> *"Two probe shapes, 31 runs each, one process, **host only. Not run on
> device.**"*

M1.3b closed the largest open M1 issue — `PORT_PLAN` M1.3 requires a fresh
process per job, WorkManager reuses the app process, and M1.3b showed reuse is
safe for ground results given a fresh `Metta` per job plus `canon` at the
comparison boundary. Every number in it came from an x86_64 host. **The
deployment target is an aarch64 phone**, and the phone is attached
(`SM-S938B`, `arm64-v8a`, `AC powered: true`, 39.3 °C → 43.6 °C over the run).

## The falsifier, stated before the run

> If the device's canonicalised digests differ from the host's, or the device
> shows more than one distinct canon digest across positions, then process reuse
> is not safe on the deployment target, M1.3b's conclusion does not transfer,
> and WorkManager goes back to blocked.

**It did not fire.**

| | probe positions | distinct raw | distinct canon | distinct alpha |
|---|---|---|---|---|
| host (x86_64, today) | 31 | **31** | **1** | 1 |
| device (aarch64, `SM-S938B`) | 31 | **31** | **1** | 1 |

Probe canon digest: **`f1865d68983bfe33` on both**, and it is also the digest
M1.3b committed this morning. Over the 30 interleaved corpus programs,
**30 of 30 canon digests and 30 of 30 raw digests are identical across the two
ISAs** — the raw ones too, which is stronger than required: the process-global
variable counter advances identically on both machines.

**What that binds is more than it looks.** `soakrun` hashes the string
`fuel=<N>\n<results>`, so a matching digest asserts **identical fuel counts as
well as identical results**. A device that agreed on results while spending
different fuel would not match.

## The second falsifier, which fired: M1.3b's committed rows no longer reproduce

`F_committed_rows_reproduce` compares today's per-position digests against the
TSV M1.3b committed at 08:47. **30 of 61 rows are identical.** The first
divergence is position 3, `integration_tests__das__test.metta`:

| | raw / canon / alpha |
|---|---|
| committed 08:47 | `38c175ea4e18e8da` (all three) |
| today, host and device | `0601ee88358e7610` (all three) |

Everything after it diverges in **raw** only — one program's output shifting the
process-global counter changes every later probe's raw digest, which is the very
mechanism M1.3b exists to characterise. **The canon conclusion is untouched**:
`f1865d68983bfe33` at every probe position, this morning and now, on both ISAs.

Three facts, and then the limit of what they support:

- the program is **deterministic run-to-run today** — three consecutive host runs
  give `0601ee88358e7610`;
- the corpus file is unchanged since Aug 16 (`git log` on the path);
- the binaries are **different builds**: the aarch64 one at 09:18, the x86_64 one
  at 14:13, M1.3b's run at 08:47 with neither.

So the change is in the BUILD, between 08:47 and 09:18. The leading candidate is
`545deb3` *"app vs host 65/65: matched cargo features"*, because
`analysis/FEATURE_EQUIVALENCE.md` measured a Cargo feature moving `fuel_used`
from 107 to 580 and this digest hashes `fuel=`. **That is a candidate and not a
cause**, and it cannot be settled from what is on disk: **M1.3b's artifact stores
only digests, so a digest that moves cannot say what moved in it.** A TSV of
hashes records that two runs differ; it cannot record how.

## Controls (4, all fire)

| control | what would have made it not fire |
|---|---|
| `C_host_reproduces_M1_3b` | **gating**: today's host run must give M1.3b's 31/1/1 **and its committed probe canon digest** before any device number is compared. *The first version of this control compared counts only — and the counts reproduce while the rows do not. A control that checks the SHAPE of a table passes over a change in its CONTENT; that is why the digest comparison was added and why the second falsifier exists.* |
| `C_raw_drifts_on_device` | M1.3b's own control, on the device: raw must differ across positions (31 distinct of 31), or the run is not exercising process reuse and `canon == 1` is vacuous (A29) |
| `C_device_identified` | model or ABI empty, ABI not `arm64`, or `dumpsys battery` a frozen override — the family-B defect that once read a discharging phone as charging |
| `C_binary_provenance` | A24: the device binary older than `soakrun.rs`, or the two binaries hashing identically (which would mean one ISA never ran). Host `9d884386…`, device `15c0817b…`, source `a4475ea9…` |

§10 gate is `devsweep.gate()`, imported rather than reimplemented: it **refuses**
on an absent device, a frozen battery instrument, or a device not on external
power.

## What this does and does not close

- **Closes** M1.3b's stated device gap for the ground-result class: process reuse
  is safe on the deployment target, so WorkManager's process model is usable
  there and not only on the host.
- **Does not** touch the aliasing class. M1.3b: `canon_alpha` is lossless only on
  ground results, an aliasing result carries free variables by definition, and
  nothing admits or rejects that class today.
- **Does not** measure timing. `quiet.sh` refuses on this host (four containers
  up), so nothing here is a rate; every quantity is a digest or a count.
- **Two probe shapes and 30 corpus programs**, the same scope M1.3b had. The
  corpus is `S57_hyperon_corpus`'s first 30 by name, not a sample of a query
  stream — the unmeasured input everywhere else in this project.
