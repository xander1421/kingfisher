# R1 — NeMo Switchyard + a local model that survives the token wall

**Operator direction, 2026-08-19.** Adopt NVIDIA's NeMo Switchyard as the router
and Nemotron 3.5 Lightning as a local tier, so the mission keeps running when
Claude has no tokens, and so routing decisions become a dataset we own.

## The measured problem this addresses

```
810  quota refusals logged
999  fast-fail turns (2-6s)
```

Twice in two days one vendor's weekly cap took **all five lanes down within
seven seconds of each other**. Cross-vendor was already the right answer —
ATOM-3 built prefix dispatch for it — and it died because grok returned 402 and
gemini had no auth. A local tier is the version of that plan that cannot be
de-funded mid-week.

## What Switchyard actually is

Rust proxy, Apache 2.0, `NVIDIA-NeMo/Switchyard`. Translates between OpenAI
Chat, Anthropic Messages and OpenAI Responses formats, so it can front Claude
Code (`switchyard launch claude`) and speak to Ollama / vLLM / NIM behind the
same endpoint. Routers: **escalation** (weak tier first, judge, promote on
sustained difficulty), LLM classifier, stage router, random split, passthrough.

**Pre-alpha, explicitly "expected API changes before v1.0", and it would sit in
front of the credential that runs the entire fleet.** That is not a reason to
refuse it; it is the reason the first trial is one lane and not five.

## Hardware, and where the video's setup differs from ours

The demo runs dual RTX Pro 6000 — 192 GB VRAM. This machine:

```
Apple M4 Pro    24 GB unified memory    20 cores    34 GiB disk free
```

Nemotron 3.5 Lightning is 30B total / **3B active** (MoE + Mamba-2 hybrid,
1M context). The active-parameter count is what makes it plausible here: it
runs at roughly 3B speed. But:

- the released `NVFP4` build is **Blackwell-only** and will not run on Apple
  Silicon. We need a GGUF quant via llama.cpp/Metal.
- Q4 GGUF is ~17-18 GB. That fits 34 GiB of disk and *nominally* fits 24 GB of
  unified memory — but five Claude lanes are resident at ~600 MB each, plus the
  OS. **This is at the edge, and honest expectation is swapping under load.**
- an 8B-class model (Nemotron Orchestrator 8B, or a small Qwen 3.6) would be
  comfortable. 30B-A3B is the ambitious end.

Stated so nobody later reports a disappointing token rate as a model defect
when it is a memory-pressure result.

## What this does and does not fix

| failure class, all measured this week | router fixes it |
|---|---|
| one vendor's cap kills all five lanes | **yes** |
| stale locks / fuses / `STOP` outliving their process | no |
| controls that cannot fire (`set(train) & set(test)`) | no |
| bars calibrated from the value they gate | no |
| 3600s turns terminated with no progress signal | no |

A router would not have caught `c2_ok = len(set(train) & set(test)) == 0`
passing at 34.7% real leakage. **It is the right tool for the constraint that is
currently binding, not for the ones that cost us the most correctness**, and
recording that distinction here is the point — "we lack a router" is a true
statement about availability and a false diagnosis of our accuracy failures.

## The part that is genuinely free and worth having first

Every routing decision, escalation and human correction is a **dataset about how
this fleet actually works** — which lanes need frontier reasoning, which cycles
are bookkeeping, where the weak tier's output fails our gates. We already have
the gates to score it: `refcheck`, `githygiene`, `rostercheck`, `leakcheck`,
`kfcheck.certify`. That is an evaluation harness most adopters have to build,
and we built it by accident over a week of being wrong.

## Bounded first trial

One lane: **ok-1** (harness/queue work — most tolerant of a weaker model, and
its output is gated by checks that refuse rather than warn). Two questions, both
falsifiable:

1. Does it survive a cap that would have killed a direct lane?
2. Does weak-tier output still pass `pre-commit.hook` at the same rate?

Not five lanes, and **not** in front of AGENT-2's graph work, where a metric
moving could not be attributed between the model change and the leak
recalibration already in flight.

## Status

- llama.cpp: cloned, **building now** with Metal.
- Ollama: not installed. Switchyard can talk to llama.cpp's OpenAI-compatible
  `llama-server` directly, so Ollama is optional.
- No GGUF pulled yet. Model choice is the open decision above.
