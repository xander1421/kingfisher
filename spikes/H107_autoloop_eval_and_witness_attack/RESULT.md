# H107 — Adversarial Soundness Audit of Autoloop Evaluators, G35 Rule Selection, and W7 Streaming State Transitions

**Verdict: CERTIFIED SOUND AUDIT (ok=True under D6). All three attack vectors successfully penetrated existing designs, reproducing critical vulnerabilities.**

---

## 1. Attack on Autoloop Evaluators & D6 Provenance Gate (`.github/autoloop/evaluators/`)

### Attack 1A: Dead Key Metric Extraction in `eval_graph_ai.py`
- **Mechanism:** `eval_graph_ai.py:63-67` traverses `provenance.json`'s `controls` looking for `c.get("observed", {})` and `obs.get("full_mrr", 0.0)`.
- **Finding:** In standard `kfcheck.certify` output, `Control` serializes to key `"observations"`, and `length1_constants.py` records keys `{"2hop", "g17_l1", "full"}` under `C4_strict_additivity`.
- **Impact:** Live execution succeeds under D6, but `eval_graph_ai.py` always evaluates to `filtered_mrr: 0.0`, `hits_at_10: 0.0`, `hits_at_1: 0.0`. The autoloop evaluator is deaf to genuine model improvements.

### Attack 1B: Frozen Hardcoded Defaults in `eval_verification.py` (Family B: Reporting Fiction)
- **Mechanism:** `eval_verification.py:64-67` attempts to read `real_corpus_trace`, `verifier_resident_memory_bytes`, and `transition_latency_summary` from `incremental.json`.
- **Finding:** None of these keys exist in `incremental.json` (which uses `corpus_benchmark`, `synthetic_scaling`, `downstream_queries`). `eval_verification.py` silently falls back to hardcoded default arguments `(75.37, 72, 1.25)`.
- **Impact:** Even if a mutated verifier consumes megabytes of memory or has negative bandwidth savings, `eval_verification.py` continues reporting `75.37%` savings and `72 B` RAM with `"D6_EXECUTION_CERTIFIED"`.

### Attack 1C: Provenance Gate Bypass & Forgery
- **Mechanism:** `is_fresh()` in both evaluators merely checks `os.path.getmtime(PROV_FILE) >= os.path.getmtime(SCRIPT_FILE)` without executing `kfcheck.verify(PROV_FILE)` or validating artifact hashes against source git commit trees.
- **Impact:** Any forged `provenance.json` with `{"ok": true}` and a bumped `mtime` passes the evaluator without running a single line of benchmark code.

---

## 2. Attack on G35 / G34 Rule Selection for Hub Bias and Vacuous Controls

### Attack 2A: Hub Degree Concentration and Sub-Base-Rate Spurious Rules
- **Mechanism:** `mine_constant_rules(npred, byp, min_sup=20, min_conf=0.10)` selects constant grounding rules $p(x, c) \leftarrow q(x, \_)$ based on a fixed confidence threshold ($0.10$).
- **Findings on FB15k-237:**
  - **$62.50\%$** of tail constant rules and **$63.74\%$** of head constant rules target the top-500 hub entities.
  - **$966$ of $2,547$ tail constant rules ($37.93\%$)** possess an empirical lift $< 1.10$ over the unconditioned marginal base rate $P(p(x, c))$.
  - Example: For relation $p=0$, body $q=23$, constant $c=1$, the learned confidence is $0.1730$, whereas the prior base rate $P(p(x, 1)) = 0.2438$ (Lift = **$0.7096$**). Knowing $q(x, \_)$ *decreases* the true probability of $p(x, 1)$, yet the rule is kept and used to promote hub entity $1$ over non-hub true entities.

### Attack 2B: Vacuous Controls in G34/G35
- **C1 (`C1_planted_composition_upper_bound`):** Only tests a synthetic 2-hop composition chain on a disjoint graph. Provides $0\%$ coverage on constant grounding or length-1 rules.
- **C2 (`C2_empty_rule_lower_bound`):** Trivially passes on empty dicts without exercising any ranking logic.
- **C3 (`C3_metric_monotonicity`):** Mathematical tautology ($\text{Hits@1} \le \text{Hits@3} \le \text{Hits@10}$ is true by definition of cumulative ranking distribution).
- **C4 (`C4_strict_additivity`):** Lacks an empirical degree-preserving null baseline (failing the standard registered in `.github/autoloop/MEMORY.md` item 3).

---

## 3. Attack on W7 Streaming Witness State Transitions

### Attack 3A: Unbound `delta_n` / State Fork Injection
- **Mechanism:** `IncrementalVerifier.apply_epoch(self, delta_proofs, delta_n)` verifies `delta_proofs` against `self.root`, but advances the sequence chain head using `hashlib.sha256(b'EPOCHN' + self.chain_head + cur + delta_root)` where `delta_root` is passed from `delta_n` without checking `delta_root == EP.commit(keys_in_delta_proofs).h`.
- **Demonstration:** An attacker injects a forged 32-byte hash `delta_n = b'\xfe\xed\xfa\xce'*8`. Both honest and malicious transitions succeed, yielding **byte-exact identical state roots** (`v1.root == v2.root == 85bae676...`), but **diverged sequence chain heads** (`1b0239ee...` vs `f42ee311...`).
- **Impact:** Light edge verifiers can be partitioned onto undetectable sequence forks while believing they share the same canonical state root.

### Attack 3B: Zero-Cost Fast-Forward Epoch Replay / Inflation
- **Mechanism:** Calling `apply_epoch([], sha256(b'EMPTY').digest())` succeeds unconditionally, advancing `self.epoch` and hashing `self.chain_head`.
- **Impact:** An attacker can inflate the epoch counter from 0 to 50+ at zero witness verification cost.

### Attack 3C: Historical Amnesia / Split-Brain Equivocation
- **Mechanism:** Holding strictly $O(1)$ resident state (72 B: root, head, epoch) discards all branch history.
- **Impact:** Light verifiers cannot adjudicate longest-chain consensus or detect branching forks without threshold validator signatures or Merkle state checkpoints.

---

## 4. D6 Certification Summary

- **Spike Directory:** `spikes/H107_autoloop_eval_and_witness_attack/`
- **Evidence Artifact:** `attack_results.json`
- **Provenance Record:** `provenance.json` (`ok: true`, 3 controls observed, 1 falsifier checked)
- **All controls fired:**
  - `C1_evaluator_defect_detected`: **PASS** (`eval_graph_ai_dead_keys=True`, `eval_verification_frozen_defaults=True`)
  - `C2_hub_bias_measured`: **PASS** (`tail_in_top500=62.50%`, `spurious_lift_rules=37.93%`)
  - `C3_w7_fork_injection_reproduced`: **PASS** (`fork_injection_success=True`, `inflation_success=True`)
- **Falsifier `F1_system_soundness_hypothesis`:** **SURVIVED (Soundness hypothesis refuted by reproduced vulnerabilities).**
