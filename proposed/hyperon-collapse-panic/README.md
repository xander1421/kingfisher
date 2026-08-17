# SUPERSEDED — see `proposed/hyperon-match-arity/`

This draft attributed the ≥1024 panic to `collapse`. **That attribution was
wrong.** `spikes/G18_ecan_ceiling` showed a bare `match` with no `collapse`
panics identically, so the primitive is the matcher, not the aggregation.

Two further corrections the rewrite carries:

- the exact bound is **1022**, not 1024 — the expression holds a head and a
  wrapper alongside the payload;
- the actionable defect is that **conjunction order decides between a result and
  an abort**, which this draft did not mention at all.

Do not file this text. `proposed/hyperon-match-arity/README.md` replaces it.
