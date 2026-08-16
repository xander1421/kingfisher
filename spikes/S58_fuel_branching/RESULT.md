# S58 — fuel under branching randomness

**Verdict: my instrument was degenerate and my rule was wrong in both directions. An attacker built the correct instrument, and the underlying claim came back TRUE and much stronger than I had evidence for. Two genuine upstream hyperon bugs fell out.**

## The headline experiment was invalid

`b4_seeded_gen.metta` used `(= (g) (new-random-generator 42))`. That is a **function**, re-evaluated on every call, so each draw constructs a *brand-new* `StdRng::seed_from_u64(42)` and returns the first output of the same stream. Verified:

```
!(random-int (g) 0 1000) x3   ->   526   526   526
```

At b4's actual range `0..2` all three draws are `1`, so `(== 1 0)` is False three times and **b4 never once takes the expensive branch.** It can emit only all-cheap or all-expensive, never a mixture. "fuel 1948, hash `16b0e4996b`, identical across 22 runs" is the observation that **a program with no live branch variation is constant.** True and vacuous.

**My defence of the method was also wrong.** I argued this was a safe kind of self-authored program because it shipped a matched control. The control (`b5`) tests the *entropy source*; it never tests whether the *treatment exercises the branch*. It fired perfectly while the treatment was inert. Section "Why this is a mechanism test…" is deleted — this spike is its counterexample.

## What is actually true — measured by the attacker, ~420 runs

The correct form binds **one** generator via `bind!` and threads it through. Its draws genuinely differ (`526 / 542 / 636`) and it produces mixed branch patterns.

| sweep | seeds | runs | result |
|---|---|---|---|
| `random-int` branching, 3 platforms | 12 | 108 | identical per seed |
| `random-float` + float branching + float arithmetic | 12 | 72 | identical per seed |
| mixed int+float+huge-range, 3 platforms | **40** | 120 | `diff` identical on all 40 rows |
| deep repeat, seeds 2 and 42 | 2 | 120 | one distinct value each |

40 seeds spanning `0 … 1234567890123` produced 40 *distinct* hashes (so non-degenerate) and **zero cross-ISA divergence**.

**`random-float` closes a gap S57 left open.** `Number::Float` displays via `{:?}` (shortest round-trip), so identical text ⟺ identical f64 bits, and full-precision floats *do* reach the hash as text (`0.5265574090027738`). S57's "no float ever reaches a hash as text" is wrong for this harness — this is a genuine bit-level cross-ISA float comparison, and it passes.

## Surviving from the original, reproduced
- **Fuel does not survive branching randomness.** 954 / 2059 / 3164 / 4269.
- **`flip` is unseedable** — `random.rs:186-188` calls global `rand::random()`, takes no generator. **`&rng`** is `from_os_rng()` bound at module load (`:127-128`).
- `fuel = 1687 + 1105 × heads`, exact at h=0,1,2,3. (1105 is the *difference* between arms; one `(expensive)` is 1185, one `(cheap)` 80.)

## The rule was wrong in both directions

**Not sufficient.** Three `Display` impls print raw heap addresses into the hashed text:

| leak | source | reachable from |
|---|---|---|
| `RandomGenerator-0x…` | `random.rs:64` | any seeded generator in a result — including error atoms |
| `GroundingSpace-0x…` | `space/grounding/mod.rs:217-227` | **`new-space`, core stdlib, no import** |
| `FileHandle-0x…` | `fileio.rs:94` | `file-open!` |

Verified here: `!(new-space)` alone gives **5 distinct hashes in 5 runs**.

**Not necessary.** `!(if (flip) 1 1)` is deterministic — 10 runs, 1 distinct. The ban is a sound *conservative over-approximation*, not an iff.

**And the ban list was incomplete.** `reset-random-generator` re-seeds an explicitly-seeded generator from OS entropy (`random.rs:43-45`, exposed `:117-120`). A program that is fully seeded, `flip`-free and `&rng`-free still gives fuel 1796/2901/4006/5111.

Also outside the story entirely: all of `fileio` (verified — host file *contents* enter the hash), and **eleven `das-*` network ops that are on by default** (`lib/Cargo.toml:47`, `default = ["pkg_mgmt", "das"]`), which make `!(match &das …)` a network query. No wall-clock op is exposed to MeTTa at all — a genuine and useful absence.

## The biggest finding is not about randomness

**`fuel + raw_hash` is not a sound replication oracle.** Pure stdlib programs with *zero* randomness return different results run to run:

- `!(intersection-atom (A $x B $y C) ($y C A $x B))` — **3 distinct hashes in 10 runs here**, 7 distinct result bodies in 15 for the attacker, *with different cardinality*. Cause: `hyperon-common/src/multitrie.rs:302-364` iterates a `HashMap` **keyed by raw pointer** (`end_of_expr: HashMap<*mut Self, _>`), and `stdlib/atom.rs` takes `.next()` off that unordered traversal. **This is a semantic correctness bug in hyperon, not a hashing nuisance** — it also affects `subtraction-atom`, `intersection`, `subtraction`.
- **Variable naming in every `match`** — `HashMap` iteration decides which name survives a var-equality group (`hyperon-atom/src/matcher.rs:193-756`). `(pair $z $z)` matched by `(pair $x $y)` returns `($x $x)` or `($y $y)`. Every `match`/`unify`/space query routes through this.

Fuel is stable in both cases. So **the fuel+hash test has a live false-negative channel for any program whose results contain variables — essentially all real MeTTa.** b4/b6 dodge it only because they return bare integers.

Verified *safe*, worth recording: atomspace/`match`/`superpose`/`unique-atom` iteration order **is** deterministic and byte-identical on all three platforms (`hyperon-space/src/index/trie.rs` walks insertion-ordered `SmallVec`s), and tokenizer regex matching is anchored, so a literal grep for `&rng` is sound.

## Harness defect
`Metta::new(None)` — what `fuelrun` calls — resolves to `Environment::common_env_arc()`, which executes the **host config dir's** `init.metta` and `environment.metta` (`runner/mod.rs:223-248`). Both exist and are populated on this Mac; the phone has `HOME=/` and no config dir. So the three-platform comparison ran with two platforms loading host files and one loading none. Their contents are inert (comment-only, plus an `#includePath` and a `#gitCatalog` inert without the `git` feature), so **it did not confound the result** — but it is an uncontrolled, user-writable, silently-executed input. Pin with `EnvBuilder::test_env()`.

## Replacement rule

> A MeTTa job is replicable and fuel-auditable only if:
> **(a)** every draw goes through a generator from `new-random-generator` with a declared seed, bound **once** via `bind!`/`let` — never `(= (g) …)`, which re-seeds per call;
> **(b)** the program contains none of `flip`, `&rng`, `reset-random-generator`;
> **(c)** no grounded value with an address-derived `Display` (`RandomGenerator`, `GroundingSpace`/`new-space`, `FileHandle`) reaches the output, **including via error atoms**;
> **(d)** no result contains variables, and the program avoids `intersection-atom`/`subtraction-atom` on variable-bearing arguments;
> **(e)** the runner pins its environment (`EnvBuilder::test_env()`).
>
> **(a)–(b) are statically checkable** over the transitive `include`/`import!` closure. **(c) and (d) are not.** Pin the `rand` version alongside the seed — this build is `rand 0.9.5` and `StdRng` is not stable across crate versions.

Two upstream fixes would collapse most of this, and both are small: make the three `Display` impls content-derived rather than pointer-derived (kills (c)), and order the multitrie/bindings traversals — `BTreeMap`/`IndexMap`, or sort before `.next()` — which kills (d) **and fixes a genuine correctness bug at the same time.**

## Still open
Transcendental libm — `pow/log/sin/cos/tan/asin/acos/atan-math` delegate to platform libm and are not IEEE-754 correctly-rounded, so last-ULP cross-ISA drift is possible. Not measured. `sqrt-math` is exempt. This is the one cross-ISA risk nobody has closed.
