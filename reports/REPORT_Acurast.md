# REPORT — Acurast

**The elder that should have been first.** Acurast is not an analogue of this
project; it is this project, in production, at **260,000+ smartphones across
175+ countries**. The recon manifest sampled adjacent systems (BOINC, Golem,
Akash, NuNet) and missed the identical one. Everything below is read-only; no
file copied.

## 1. Identity

| repo | HEAD | licence (read from file on disk) | LOC |
|---|---|---|---|
| `Acurast/acurast-substrate` | `b59f7d8` | **Unlicense** — *"free and unencumbered software released into the public domain"* | ~80k Rust |
| `Acurast/acurast-core` | `26d5688` | **MIT** (`LICENSE.md`, verbatim MIT, © 2023 Acurast Association) | — |
| `Acurast/acurast-docs` | `66e8a83` | **MIT** | — |
| `Acurast/acurast-kotlin-sdk` | `408429f` | **MIT** | — |

**Unlicense is the most permissive result the §7 licence gate can return** —
more permissive than anything else in `elders/`. There is no attribution
obligation and no copyleft. Contrast MORK (UNKNOWN), BOINC (LGPL-3.0), Golem
(GPL/LGPL).

The **on-device processor runtime is not in any public repo.** Coordination
layer open, device runtime closed. That split defines what we can learn.

## 2. Shape — `acurast-substrate/pallets/`

| pallet | LOC | what it is |
|---|---|---|
| `acurast` | 46,058 | job registry + **attestation** |
| `compute` | 12,557 | compute accounting / metering |
| `marketplace` | 7,852 | advertise → match → report → finalize |
| `processor-manager` | 3,700 | device identity, pairing, fleet management |
| `token-claim` / `token-conversion` | 4,062 | settlement |
| `hyperdrive` (+ibc, +token) | 4,872 | cross-chain messaging |
| `candidate-preselection` | 288 | pre-filtering matchable devices |
| `rewards-treasury` | 362 | payout |

Substrate/FRAME, Rust. This is `PORT_PLAN` M3 in its entirety — matcher,
settlement, attestation, device management — already written, already running,
already public domain.

## 3. The finding that matters: **there is no second run**

Counted across `pallets/{marketplace,acurast,compute}/src`:

```
slash / slashed / slashing / slashable / slasher / ...   366+
replicate                                                  4
quorum · redundancy · challenge · dispute · bisection       0
```

**Acurast has no replication, no quorum, no challenge protocol, and no dispute
mechanism.** Verification is entirely:

1. **Hardware attestation.** `pallets/acurast/src/lib.rs:347`
   `submit_attestation(attestation_chain: AttestationChain)` — an X.509 chain
   validated on-chain, i.e. Android Key Attestation: the device's hardware-backed
   key signs a statement, the chain roots to the vendor attestation root. Backed
   by an on-chain **certificate revocation list**
   (`update_certificate_revocation_list`, `StoredRevokedCertificate`) so a
   compromised batch can be cut off centrally.
2. **Economic slashing.** Providers stake, delegators back them, misbehaviour
   burns money.

Per the docs: the **Acurast Secure Hardware Runtime (ASHR)** *"executes inside
the phone's Trusted Execution Environment"*, and *"the silicon signs a statement
proving the hardware is genuine and the code loaded into it was not modified."*
There is also an **AZKR** zero-knowledge runtime as an alternative.

### What that does to our thesis

`out/FINAL_REPORT.md` names our central bet: *"deterministic symbolic reduction
makes verification nearly free"*, and names our biggest risk: *"nobody has an
answer for who pays for the second run."*

**Acurast answered it by not having a second run — and their answer works for
any workload, not only deterministic ones.** Our entire three-rung verification
ladder (optimistic + ⌈log₂(steps)⌉ bisection, LSH commitments, peer scoring)
addresses a problem they removed with a certificate chain.

What survives as our differentiator is narrower and should be stated as such:

> **Acurast's verification requires trusting Qualcomm, Google and Samsung
> silicon plus a vendor-rooted certificate chain and a centrally-maintained
> revocation list. Ours requires trusting nothing — a byte comparison anyone can
> re-run on any hardware.**

That is a real distinction (TEEs are broken periodically; a revocation list is a
central point of control) but it is now the *whole* distinction. `PROPOSAL_DRAFT`
currently leads with "verification is nearly free", which is no longer
differentiating and should be rewritten.

## 4. Marketplace API — `pallets/marketplace/src/lib.rs`

```
advertise                   :508    delete_advertisement       :523
propose_matching            :542    acknowledge_match          :556
acknowledge_execution_match :568    propose_execution_matching :651
report                      :590    finalize_job               :617/:637
deploy                      :711    edit_script                :811
update_min_fee_per_millisecond :877  update_price_settings     :923
cleanup_assignments / cleanup_job_assignments / cleanup_job_matcher
```

Four things to take:

1. **Matching is *proposed*, then *acknowledged*.** `propose_matching` →
   `acknowledge_match` is a two-phase handshake, not an assignment. A device
   confirms it will do the work before it is bound — which is exactly what a
   phone that may be unplugged at any moment requires. Our S4 schema has no
   acknowledgement step.
2. **They price by time: `update_min_fee_per_millisecond`.**
   `out/STATE_OF_THE_UNION.md` asserts *"All six NuNet models meter time or
   resources — the wrong unit for a device you cannot audit."* Acurast meters
   milliseconds at 260k devices, because **TEE attestation makes time
   auditable.** Our claim was conditional on our own trust model and was
   presented as general. It should be qualified.
3. **`candidate-preselection` is a separate pallet.** Matching is filtered
   before it is scored — the cheap structural narrowing S55 models as candidate
   sampling exists here as its own module.
4. **Four `cleanup_*` extrinsics.** A third of the marketplace surface is
   garbage collection of assignments that never completed. That is what a real
   phone fleet costs, and nothing in `PORT_PLAN` M3 budgets for it.

## 5. Also in their stack, matching unbuilt M1 rows

| our gap | their repo |
|---|---|
| M1.5 shard store | `Acurast/ipfs-mobile` (Go) |
| M1.7 phone-initiated transport | `Acurast/acup2p` (Kotlin), `Acurast/quic-tunnel` (Rust) |
| M1.1 app skeleton | `Acurast/acurast-kotlin-sdk` (**MIT**) |
| on-device model execution | GGUF via an integrated llama server |

`acurast-kotlin-sdk` being MIT is directly relevant to M1.1, which is currently
"nothing built".

## 6. What was NOT read

Budget was one recon pass. Unread: the 46k-LOC `acurast` pallet beyond the
attestation extrinsics; all of `compute` (12.5k) — which is where metering and
therefore the unit-of-payment question lives; `hyperdrive`; the Kotlin SDK's
job lifecycle; and the docs site (45 MB). **`pallets/compute` is the highest-value
unread thing in this repo** — it is the direct counterpart to our fuel metering.

Nothing was measured. This is a source read, grade **E** on `out/LEDGER.md`'s
scale.

## 7. Recommended actions

1. **Rewrite `PROPOSAL_DRAFT` §wedge.** "Verification is nearly free" is table
   stakes now. The claim is *trust-free* verification versus *TEE-trusted*.
2. **Add an acknowledgement phase to `hyperjob_v0.proto`.** Two-phase matching
   is proven at fleet scale and we do not have it.
3. **Read `pallets/compute` before any more metering design.**
4. **Reconsider TEE attestation as a complement, not a rival.** `PORT_PLAN` M3.6
   already proposes Play Integrity. Acurast shows the on-chain half —
   certificate chain plus revocation list — and it is public domain.
5. **Add Acurast to `RISKS.md`.** They are a funded, live competitor with a
   two-order-of-magnitude head start on fleet size, and no risk register in this
   workspace mentions a competitor at all.
