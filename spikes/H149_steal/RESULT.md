# H149 — pull queue finds 3:1 without being told

## Claim decay this spike exists to stop

A peer write-up treated retracted H141 walls as a straggler model:

- `max(200 × 8.3 ms, 200 × 24.3 ms) = 6.87 s` — **false**.
  `200 × 24.3 ms = 4.86 s` (H139 n=200 S24). `6.87 s = 1.65 + 5.22`,
  the sequential `submit().result()` sum.
- “Parallel” 3:1 = `5.17 s` — **false**. If parallel, wall is
  `max(2.50, 2.67) ≈ 2.67 s`. `5.17 s` is the same sum.
- “2.0 × over 1:1” is not an H141 number (published ratio was 0.753).
- “Mission achieved / full stack verified” is false: Gate 3 open,
  `F001_DRAFT`, §8 UNPROVEN, 0 ACCEPTED. Two phones are not `operator=2`.

## Falsifier (stated first)

Steal wall of 400 not < 0.90 of static 1:1 **and** not within 20% of
oracle 3:1 k=2. Then pulling does not replace knowing the weights.

It did not fire.

## Operating point

Same pair as H148. Chunk = 50 verifies. 2 workers on S25 + 2 on S24.
Unread-thermal override on S24 only. Pin `590d8769…`.

| mode | wall | jobs/s | S25 took | S24 took |
|---|---:|---:|---:|---:|
| static 1:1 | 4.739s | — | 200 | 200 |
| S25 k=2 | 1.692s | 236 | 400 | 0 |
| oracle 3:1 k=2 | 1.271s | 315 | 300 | 100 |
| **steal chunk=50** | **1.368s** | **292** | **300** | **100** |

Steal / 1:1 = **0.289**. Steal / oracle = **1.077**. Steal / S25 k=2 = **0.809**.

The queue assigned 300/100 with no baked ratio. Two devices still beat
one Snapdragon. Not a new ISA. Not a new operator domain.

Evidence: `steal.json`. Check: `python3 kitchen/test_h149.py`.
