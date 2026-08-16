# Papers fetched

All fetched 2026-08-16. Nothing here is redistributed; these are local copies for reading.

| file | source | what it is |
|---|---|---|
| `gensyn_verde_2502.19405.pdf` | arXiv 2502.19405 | **Verde: Verification via Refereed Delegation for Machine Learning Programs** (Gensyn) |
| `toploc_2501.16007.pdf` | arXiv 2501.16007 | TOPLOC: locality-sensitive hashing for verifiable inference (Prime Intellect) |
| `opencog_hyperon_2310.18318.pdf` | arXiv 2310.18318 | OpenCog Hyperon: a framework for AGI at the human level and beyond |
| `opendiloco_2407.07852.pdf` | arXiv 2407.07852 | OpenDiLoCo: globally distributed low-communication training |
| `boinc_design_2004.pdf` | boinc.berkeley.edu/grid_paper_04.pdf | Anderson, *BOINC: A System for Public-Resource Computing and Storage* (2004) |
| `iexec_whitepaper_v3.pdf` | github.com/iExecBlockchainComputing/whitepaper V3 | iExec white paper v3 (PoCo) |
| `nunet_whitepaper_2.0.pdf` | nunet.github.io/public/NuNet_Whitepaper_2.0.pdf | NuNet White Paper 2.0 |

URL notes: the iExec and NuNet whitepaper links advertised on their marketing sites both return HTML, not PDFs; the real files are on GitHub raw and on `nunet.github.io` respectively. The NuNet *yellow* paper is web-only (Docusaurus) and its per-section URLs 404 — only the overview page resolves.

## Verde — the one paper that changes our design

Read for the bisection protocol our rung 1 depends on. Three findings, quoted from the text:

1. **Refereed delegation with a deliberately weak referee.** *"we are most interested in the case where the referee is highly limited computationally, for example the client requesting the work themselves also acts as the referee."* The referee never re-runs the job; it only adjudicates a disagreement.
2. **Bisection on the divergence point.** Following Canetti et al. (2013): *"if two parties disagree on the output of a program, there must be some point of divergence in their computation path."* Binary-search the step index until the referee can check a single operation and *"prove that at least one party is incorrect"*. Requires only ⌈log₂(steps)⌉ round trips and one cheap step re-execution. This is exactly what hyperon's `interpret_init` / `interpret_step` / `step_to_str` C API makes possible for MeTTa (see `reports/REPORT_hyperon-experimental.md`), and it is why `BisectionProbe`/`BisectionResponse` are in the S4 schema.
3. **RepOps exists only because floating point is not associative.** *"hardware may provide different numerical results because floating point operations are not guaranteed to be associative, even when following the IEEE-754 standard: (a+b)+c and a+(b+c) can be different… To overcome this, we design RepOps (Reproducible Operators), a library that implements bitwise reproducible versions of popular ML operators."*

**Point 3 is the strategic finding of this whole mission.** Gensyn had to write, and must now maintain, an entire reproducible-operator library — for every operator, on every hardware backend — before refereed delegation could work at all. Our workload does not need one:
- MeTTa reduction is discrete symbolic rewriting; there is no floating-point associativity to lose. MORK's differential harness already demonstrates byte-identical spaces across two independently-written query engines over 98 programs (`spikes/S3_mork_bench/RESULT.md`).
- Our rung-2 similarity is INT8×INT8→INT32; integer addition *is* associative and exact, so reordering cannot change the result (`spikes/S7_toploc_adapt/RESULT.md`).

Verde also names the two practical problems it does not solve, and they are ours too: *"to ensure a high likelihood of at least one honest trainer, a robust ecosystem of trainers is needed, which are unlikely to collude or suffer related faults (e.g. by running the same third party data center)"* — our `ReplicationPolicy.exclude_device_groups` (S4) exists for precisely this — and *"incentives are needed to compensate trainers both for running the original"* computation and the verification of it, which is the verification-economics risk in `out/RISKS.md`.
