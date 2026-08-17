# REPORT — Kubernetes (scheduler + kubelet resource managers)

**An elder for the placement layer only — and it falsifies a second wedge claim.**
k8s has no verification, no replication-for-correctness, no Byzantine model and no
churn model, so it is silent on every hard problem in this workspace. It is
production reference for the one layer where we have almost none: matching,
spreading, and cpuset allocation across heterogeneous nodes.

## 1. Identity

| repo | HEAD | licence (read from `LICENSE` on disk) | clone |
|---|---|---|---|
| `kubernetes/kubernetes` | `a231bf3` | **Apache-2.0** | sparse, 12 MB of 1,475 MB |
| `kubernetes-sigs/descheduler` | `4233637` | **Apache-2.0** | full, 101 MB |

Sparse paths taken: `pkg/scheduler/framework/plugins/{imagelocality,podtopologyspread,interpodaffinity,noderesources}`, `pkg/kubelet/cm/{cpumanager,topologymanager,devicemanager}`.

## 2. `imagelocality` falsifies GAP row 4

`GAP_MATRIX` row 4 and `PROPOSAL_DRAFT`'s second wedge both assert:

> *"Golem and NuNet both match on **network** locality — region, ASN, RTT. Akash
> matches on resources and signed attributes. **Nothing matches on which data a
> device already holds.**"*

`pkg/scheduler/framework/plugins/imagelocality/image_locality.go:38`:

> *"ImageLocality is a score plugin that favors nodes that already have requested
> pod container's images."*

Scored per node by the **size** of the images already resident, clamped between
`minThreshold` and `maxContainerThreshold × imageCount`, then scaled to
`fwk.MaxScore` (`:96-105`). This is `prefer_cached_cids`, at cluster scale, under
Apache-2.0.

**Second wedge claim to fall to a repo nobody had cloned** — the first was GAP
row 6, falsified by `executorch/backends/qualcomm`.

## 3. The damping term is better than what we designed

`image_locality.go:142-147`:

```go
// This heuristic aims to mitigate the undesirable "node heating problem", i.e.,
// pods get assigned to the same or a few nodes due to image locality.
func scaledImageScore(imageState *fwk.ImageStateSummary, totalNumNodes int) int64 {
	spread := float64(imageState.NumNodes) / float64(totalNumNodes)
	return int64(float64(imageState.Size) * spread)
}
```

**They have a name for S61's finding — the "node heating problem" — and a fix.**
S61 measured load imbalance rising to **102×** at duty 1.0 under naive locality
matching, and proposed a per-device in-flight cap or ε-greedy. Both cap the
symptom.

k8s removes the *incentive*: an artefact's locality score is multiplied by
**how widely replicated it already is**. A shard held by one device scores near
zero for locality, so the scheduler does not prefer that device and does not
concentrate on it. A shard held by half the fleet scores full, because following
locality there cannot concentrate anything.

**This also addresses Q1 from the other side.** Q1 measured that one operator with
five devices captures **72%** of a pool-3 quorum, and the capture happens on
*rare* shards where the eligible pool is small. The k8s rule says: do not prefer
locality for rare artefacts. That spreads rare-shard work across the fleet and
**enlarges the honest pool where it is smallest** — which is exactly the variable
Q1 identified as the defence (`~25` before capture drops under 10%).

One mechanism, two open findings. It should be measured in S61's own harness
before being adopted: replace the locality preference with
`score × (holders / N)` and re-run the imbalance sweep.

## 4. `podtopologyspread` is `exclude_device_groups`, done properly

`podtopologyspread/filtering.go:358-360`:

```go
skew := matchNum + selfMatchNum - minMatchNum
if skew > int(c.MaxSkew) {
    // node fails the spread constraint
}
```

`minMatchNum` is the **global minimum across domains** (`:55-68`, with
`MinDomains` handling the case of fewer domains than expected). `TopologyKey`
(`:213`, `:286`, `:337`) is an arbitrary node label, so the failure domain is
configurable — zone, rack, or for us **operator, attestation root, network
origin**.

`PORT_PLAN` M3.4 invents `exclude_device_groups` as a blocklist. This is
strictly better: not *"exclude these groups"* but **"no domain may exceed the
global minimum by more than `maxSkew`."** It needs no knowledge of who the
adversary is, and it degrades gracefully as domains appear and vanish — which a
churning phone fleet does constantly.

Q1's adversary holding five devices under one operator would be capped at
`minMatchNum + maxSkew` seats regardless of how many devices it owns.

Also carried: `whenUnsatisfiable: DoNotSchedule | ScheduleAnyway` — the same
hard-filter-versus-soft-score distinction, which we have nowhere.

## 5. `cpumanager` / `topologymanager` — S54, solved upstream

S54 discovered Android's `background` cpuset (`0-1,4-5`) by probing the device
and declared every throughput figure in the workspace unreachable. `pkg/kubelet/cm/cpumanager`
and `topologymanager` are a production subsystem for exactly this: static cpuset
assignment by QoS class, with NUMA-topology alignment.

We did not need to invent the vocabulary. Not read in this pass — flagged.

## 6. Where k8s gives us nothing, stated so this report is not misused

| our problem | k8s |
|---|---|
| verification / replication for correctness | **absent** — nodes are trusted |
| Byzantine or colluding operators | **absent** |
| churn at 95%, device owners who unplug | **absent** — nodes are owned and always-on |
| settlement, payment, stake | **absent** |
| determinism, byte-comparison | **absent** |

k8s assumes you own the machines. Every claim in §LIVE-determinism of the LEDGER
is out of its scope. Cite it for placement, never for trust.

## 7. Not read

`interpodaffinity`, `noderesources`, `devicemanager`, all of `descheduler`, and
the `cpumanager`/`topologymanager` internals. `descheduler` is the closest
existing thing to S61's rebalancing problem and is the highest-value unread item
in this clone.

Nothing measured. Source read only — grade **E** on the LEDGER scale.

## 8. Actions

1. **Rewrite `GAP_MATRIX` row 4 and `PROPOSAL_DRAFT`'s locality wedge.** The
   "nothing matches on which data a node holds" premise is false.
2. **Measure the `holders/N` damping in S61.** It is a one-line change to the
   scoring and it targets a 102× imbalance with a production-proven heuristic.
3. **Replace `exclude_device_groups` with a skew constraint** in the M3.4 spec.
4. Read `descheduler` before designing any rebalancing.
