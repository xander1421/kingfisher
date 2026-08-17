# M1.1c — job N differs from job 1 inside one process. Process-per-job is required.

**The largest open M1 issue is now settled, in the negative. A fresh `metta_t`
per job is NOT sufficient; WorkManager's process reuse breaks determinism for a
characterisable class of programs.**

Same program, fresh `metta_t` each iteration, 40 iterations, one Android app
process, on device.

| program | stock `3f76dc4` | + our 3 patches |
|---|---|---|
| `var_alias` — `(pair $z $z)` matched by `(pair $x $y)` | **DIVERGES** 2 distinct, first at rep 5 | **DIVERGES** 2 distinct, first at rep 2 |
| `rule_inst` — two-rule instantiation | STABLE | STABLE |
| `chain` — three-rule chain, two queries | STABLE | STABLE |
| `arith_ctl` — `!(+ 1 2)` | STABLE | STABLE |
| `POSCTL_space` — `!(new-space)` | **DIVERGES 40/40 distinct** | **STABLE** |

## The positive control fires, and then our own patch silences it
Stock prints `GroundingSpace-0xb40000763c2352e8` — **40 distinct hashes in 40
runs**. So the harness can see in-process variation; the STABLE rows mean
something.

On the patched build the same control reads STABLE, because
`proposed/hyperon-nondeterminism/` patch 02 removes the address from `Display`.
That is **device-level verification of a patch previously only checked on the
host** — and it was nearly a methodological trap: the first run of this soak
used the patched tree, the control read STABLE, and the correct reading was not
"MeTTa is stable" but *"I disabled my own control."*

### How that happened, recorded
`elders/hyperon-experimental` was **not pristine**. All three patches were
applied in the working tree from the earlier fix-and-verify work and never
reverted, so:
- the first APK shipped **patched** hyperon while `RESULT.md` claimed `3f76dc4`;
- the M1.1 comparison against native `fuelrun` was patched-vs-unknown, not
  stock-vs-stock. The agreement stands; the provenance claim did not.
Both builds above were produced by `git stash` / `stash pop` around the build,
and pristine was verified by `git status --short | wc -l == 0`.

## What diverges, and what does not
`var_alias` is the case where **two distinct variables alias onto one**: the
binding map must pick a representative, and `$x` or `$y` wins depending on
iteration order. `VariableAtom` carries `id` in its derived `Hash`/`Eq`, and
`NEXT_VARIABLE_ID` is a process-global `AtomicUsize`, so **bucket assignment
depends on how many variables the process created earlier**.

This is Issue 3 of `proposed/hyperon-nondeterminism/`, filed as a report with
**no patch**. It now has a device reproducer.

Crucially, `rule_inst` and `chain` are STABLE despite both going through
`make_variables_unique`. **The hazard is narrower than "any program with
rules"** — it needs an ambiguous aliasing where the result depends on which
variable represents the class. That is a characterisable class, which matters
because it can be admitted or banned rather than only fixed.

## The class, characterised — and it is statically bannable

Twelve more programs, stock `3f76dc4`, 40 reps each, positive control live
(`!(new-space)` 40/40 distinct):

| group | program | shape | result |
|---|---|---|---|
| A1 | `(pair $z $z)` / `(pair $x $y)` | 2 pattern vars onto 1 | **DIVERGES** 2 |
| A2 | `(tri $z $z $z)` / `(tri $x $y $w)` | 3 onto 1 | **DIVERGES 3** |
| A3 | A1 projecting only `$x` | 2 onto 1 | **DIVERGES** 2 |
| A4 | `(o (i $z $z))` nested | 2 onto 1, nested | **DIVERGES** 2 |
| B1 | `(pair $z $w)` | distinct data vars | STABLE |
| B2 | `(pair A A)` | ground, repeated symbol | STABLE |
| B3 | `(pair $z $z)` / `(pair $x $x)` | repeat in the PATTERN | STABLE |
| C1/C2 | `(= (f $x) (g $x $x))` | aliasing made by a RULE | STABLE |
| D1 | `(pair $z A)` | one data variable | STABLE |
| D2 | `(pair $z $w)` | two distinct data variables | STABLE |
| D3 | `(tri $z $z A)` | **repeated** data variable | **DIVERGES** 2 |
| D4 | `(one $z)` `(two $z)` | same name, different atoms | STABLE |

**The number of distinct outcomes equals the number of aliased variables** —
A2 gives exactly 3. Whichever variable's `id` lands first in the bucket becomes
the representative.

The D group separates two candidate ban rules that both fit A/B/C:

- ~~"shard data must be ground"~~ — refuted by D1 and D2, which carry variables
  and are stable.
- **"no atom may contain the same variable more than once"** — fits every row.

That is a **per-atom, purely syntactic** check on shard data. It needs no
inter-atom analysis (D4), no knowledge of the query (B3 has the repeat in the
pattern and is stable), and no rule analysis (C1/C2). Cheap enough to enforce at
shard admission, and far weaker than requiring ground data.

## The ban predicate is REFUTED, and there are two mechanisms

Implemented as `spikes/harness/admission.py` (11 assertions) and run against
hyperon's own 67-program corpus:

```
ADMIT 33   REJECT 34   (51% rejected)
of the rejected: 21 have ALL violations inside `(= ...)` rule bodies
                 -- shapes C1/C2 MEASURED STABLE
```

**51% rejection is not an admission gate, it is a ban on MeTTa.** And the
over-conservatism was predictable from our own data: C1/C2 said rule bodies are
safe and the syntactic rule rejects them anyway.

Then the E-series found the rule is not merely blunt but **on an incomplete
axis**:

| program | query aliases? | result |
|---|---|---|
| E1 `(implies (Frog $x) (Green $x))` + `(implies $p $q)` | **no** | **DIVERGES 40/40** |
| E2 same data + `(implies (Frog $a) (Green $b))` | yes | DIVERGES 2 |
| E3 `(= (f $x) (g $x $x))` + `(= $h $b)` | no | **DIVERGES 40/40** |

E1's sample output is the whole story: `((Frog $x#24605) (Green $x#24605))`.

**Two mechanisms, needing different fixes:**

1. **Representative selection** — aliasing decides whether `$x` or `$y` survives.
   Bounded: outcomes equal the number of aliased variables (A2 gives exactly 3).
   The syntactic rule does catch this one.
2. **The counter is printed.** `VariableAtom::name()`
   (`hyperon-atom/src/lib.rs:307-313`) embeds `#{id}`, and `Display` at `:335`
   calls it. Any result containing a data-origin variable emits the
   process-global counter — **40 distinct outputs in 40 runs, with no aliasing
   anywhere**. No data-side syntactic rule can catch this; it depends on what
   the query projects.

Mechanism 2 is the severe one: it defeats result-hash comparison directly, which
is the project's core verification mechanism. It is also a small upstream fix.
`proposed/hyperon-nondeterminism/` Issue 3 has been **corrected** — it previously
claimed the id never reaches printed output, which was wrong and understated it.

Why S57's 66/67 corpus missed it: those programs return `()` and error atoms,
not unbound data-origin variables. That is a property of the corpus.

## Mechanism 2 is fixed at the comparison boundary — measured

`spikes/harness/canon.py` renumbers variables by **first appearance** in the
result, then hashes that. Same soak, raw hash vs canonical hash:

| program | raw | canon | |
|---|---|---|---|
| `CTL_arith` | 1 | 1 | stable both |
| `POSCTL_space` — heap address | 40 | **40** | **correctly preserved** |
| `E1_noalias` — counter only | 40 | **1** | **FIXED** |
| `E3_rulequery` — both mechanisms | 40 | **2** | counter stripped, aliasing exposed |
| A1–A4, D3, E2 — aliasing | 2–3 | 2–3 | correctly unchanged |
| B1–B4, C1–C2, D1–D2, D4 | 1 | 1 | stable both |

Three properties, each measured rather than argued:

1. **It fixes what it should.** E1 collapses 40 -> 1.
2. **It does not erase real divergence.** The heap-address control stays at
   40/40. A canonicaliser that "fixes" everything is just deleting the signal,
   and this one is shown not to.
3. **It separates the two mechanisms.** E3 carries both; canonicalisation takes
   it 40 -> 2, leaving exactly the aliasing divergence underneath.

**Renumber, do not strip.** `($x#1 $x#2)` and `($x#1 $x#1)` are different
answers — two distinct variables versus one variable twice. Stripping maps both
to `($x $x)`, which would make a wrong result compare equal to a right one. In a
system whose entire verification is result comparison that is the worst
available failure, so `canon` is injective on structure and invariant only to
process history.

Wired into `M1_8_quorum3/q3.py`'s agreement key. Where `fuelrun` returns result
text we canonicalise and key on that; where it returns only its own hash we
cannot, and the envelope is flagged rather than silently trusted.

**Mechanism 1 remains open** and is not ours to paper over: which variable
represents an aliased class is a genuine semantic choice, and it needs a
per-runner id space or an ordered binding map upstream.

## Consequence for M1.3 / WorkManager
`PORT_PLAN` M1.3 requires a fresh process per job on two derivations. This
measures the second one and it holds:

- **(1) atomspace pollution** — addressed by a fresh `metta_t`. Done here.
- **(2) process-global `NEXT_VARIABLE_ID`** — **not** addressed by a fresh
  `metta_t`, and now demonstrated: identical input, identical runner
  construction, different output by position in the process.

So `Worker` running in a reused app process is **not** equivalent to a forked
job, and the difference is observable in output, not merely in timing. Options
narrow to: run each job in a process that exits afterwards, ban the aliasing
class at admission, or fix `NEXT_VARIABLE_ID` upstream.

## Provenance
`provenance.json`, written before the write-up by `spikes/harness/provenance.py`:
`elders/hyperon-experimental` at `3f76dc4…ada83`, **tree verified clean** (our 3
patches held in `stash@{0}` for the duration), `libhyperonc.so`
`82d34485a478a344…`, 6,775,648 B, device `SM-S938B` / `BP4A.251205.006` /
`arm64-v8a`, positive control declared in advance and observed to fire 40/40.

The earlier M1.1 run had none of this and shipped a patched build under a stock
commit hash. See A19.

## Limits
- One device, 40 reps, five programs. Divergence was 2-valued here; nothing
  says it is bounded at 2.
- `rule_inst`/`chain` STABLE is evidence of narrowness, **not** proof of safety —
  40 reps of three programs does not characterise the class.
- `E4_typedecl` was removed, not measured: `(match &self (: $n $t) ...)` matches
  every type declaration in the loaded stdlib, returns thousands of atoms, and
  OOM-killed the process **before the controls ran**. Controls now run FIRST for
  that reason — a crash late in a sweep must not cost you the control.
- Dead controls burned on the way: `(flip)` is a Python-ext atom absent from the
  Rust stdlib and echoed unevaluated; `(random-int &rng ...)` echoed because
  `&rng` was unbound; and the first `var_alias` matched an atom never added to
  the space and returned **empty**. All three read as STABLE. Logging one sample
  output per program is what exposed them.
