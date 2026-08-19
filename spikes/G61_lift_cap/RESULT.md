# G61 — valid p95 true-lift cap is inert

G57: spray is huge lift on rare false candidates (5.40 vs 2.72 write);
signed `log(lift)` lost. Unread fix: cap lift at what true answers
actually use on valid.

Falsifiers stated in CHANNEL before the run.

| F | stated | observed |
|---|---|---|
| F1 | cap-all ≤ official G51 0.2585 | **quiet.** 0.2588 (−wait: **+0.0003**) |
| F2 | gated+cap ≤ G59 0.2679 | **quiet.** 0.2680 (**+0.0001**) |

`certify ok=true`. C1 20466. C2 leak=0. C3 G51 **0.2585**. C4 gated **0.2679**.
C5 cap hashed `cd8cfe45…` before test.

## Arms (official test)

| arm | MRR | Hits@10 |
|---|---:|---:|
| prior | 0.2334 | 0.3541 |
| G51 | 0.2585 | 0.3837 |
| valid-gated (G59) | **0.2679** | 0.4037 |
| cap-all (p95 true lift) | 0.2588 | 0.3837 |
| gated+cap | 0.2680 | 0.4035 |

Valid true-target lifts when a 2-hop fires: n=15,586, p95=**43,627**, max
even larger. True answers already sit in the spray regime. A p95 cap
does not separate them from the rare false entities G57 measured.

**+0.0003 / +0.0001 is not a new high** (same class as G57 lift>1
+0.0001). Scoreboard stays G59 **0.2679** official and G54 **0.2313**
pair-disjoint. Head gap unread. Literature unavailable.

Evidence: `lift_cap.json`. Check: `python3 kitchen/test_g61.py`.
