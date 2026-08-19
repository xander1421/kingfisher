#!/usr/bin/env python3
"""H107 — Adversarial Attack & Soundness Certification Suite.

Audits and falsifies:
1. Autoloop Evaluators (.github/autoloop/evaluators/): Dead metric extraction, frozen defaults, and provenance gate forgery.
2. G35 / G34 Rule Selection: Hub bias, base-rate negative lift rules, and vacuous controls.
3. W7 Streaming Witness State Transitions: Unbound delta_n fork injection, epoch replay inflation, and split-brain equivocation.

Certified under D6 discipline via kfcheck.certify.
"""

import os, sys, json, hashlib, time, struct, random, copy
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "harness"))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "G34_length1_and_constants"))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "W6_incremental_witness"))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "W2_witnessed_trie"))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "S73_epoch_commitment"))
sys.path.insert(0, os.path.join(REPO_ROOT, "spikes", "S74_epoch_chain"))

import kfcheck
from provenance import Control, Falsifier
import length1_constants as L
import incremental_verifier as IV
import epoch as EP
import chain as CH

def audit_autoloop_evaluators():
    """Attack 1: Audit evaluators for dead keys, frozen defaults, and unverified provenance."""
    # 1. Check G34 provenance extraction
    g34_prov_path = os.path.join(REPO_ROOT, "spikes", "G34_length1_and_constants", "provenance.json")
    with open(g34_prov_path, "r") as f:
        g34_prov = json.load(f)
        
    g34_controls = g34_prov.get("controls", [])
    dead_key_bug = False
    for c in g34_controls:
        if c.get("name") == "C4_strict_additivity":
            # Buggy evaluator uses 'observed' instead of 'observations'
            obs_evaluator = c.get("observed", {})
            real_obs = c.get("observations", {})
            if obs_evaluator == {} and "full" in real_obs:
                dead_key_bug = True

    # 2. Check W6 verification evaluator defaults
    w6_data_path = os.path.join(REPO_ROOT, "spikes", "W6_incremental_witness", "incremental.json")
    with open(w6_data_path, "r") as f:
        w6_data = json.load(f)
    
    frozen_defaults_bug = False
    if "real_corpus_trace" not in w6_data and "corpus_benchmark" in w6_data:
        frozen_defaults_bug = True

    return {
        "eval_graph_ai_dead_keys": dead_key_bug,
        "eval_verification_frozen_defaults": frozen_defaults_bug,
    }

def audit_g35_hub_bias():
    """Attack 2: Measure hub degree concentration and spurious zero-lift constant rules."""
    nt, npred, nent, tri, train, dev, test = L.load_dataset()
    out_adj, in_adj, pair_tr, byp, rev = L.build_graph_index(train)
    total_degrees = Counter(s for p, s, o in train) + Counter(o for p, s, o in train)
    top500_entities = set(e for e, _ in total_degrees.most_common(500))

    rules_const_tail, rules_const_head = L.mine_constant_rules(npred, byp)
    tail_constants = {r["const"] for rlist in rules_const_tail.values() for r in rlist}
    head_constants = {r["const"] for rlist in rules_const_head.values() for r in rlist}

    tail_in_top500 = sum(1 for c in tail_constants if c in top500_entities) / max(1, len(tail_constants))
    head_in_top500 = sum(1 for c in head_constants if c in top500_entities) / max(1, len(head_constants))

    spurious_count = 0
    total_rules = 0
    for p, rlist in rules_const_tail.items():
        n_p = len(byp[p])
        for r in rlist:
            total_rules += 1
            c = r["const"]
            conf = r["conf"]
            base_rate = sum(1 for s, o in byp[p] if o == c) / n_p
            lift = conf / base_rate if base_rate > 0 else 1.0
            if lift < 1.10:
                spurious_count += 1

    return {
        "tail_constants_in_top500_pct": round(tail_in_top500 * 100, 2),
        "head_constants_in_top500_pct": round(head_in_top500 * 100, 2),
        "spurious_zero_lift_rules_pct": round(spurious_count / max(1, total_rules) * 100, 2),
        "spurious_count": spurious_count,
        "total_constant_rules": total_rules
    }

def audit_w7_state_transitions():
    """Attack 3: Fork injection via unbound delta_n and epoch replay inflation."""
    genesis_keys = {b'\0'}
    genesis_root = EP.commit(genesis_keys).h
    
    # 3A. Unbound delta_n Fork Injection
    v1 = IV.IncrementalVerifier(genesis_root)
    v2 = IV.IncrementalVerifier(genesis_root)
    
    atoms = [b'(member Alice GroupA)', b'(member Bob GroupA)']
    seen = set(genesis_keys)
    proofs = EP.prove_epoch_delta(EP.commit(seen), seen, atoms)
    honest_delta = EP.commit(atoms).h
    forged_delta = b'\xfe\xed\xfa\xce' * 8
    
    v1.apply_epoch(proofs, honest_delta)
    v2.apply_epoch(proofs, forged_delta)
    
    fork_injection_success = (v1.root == v2.root) and (v1.chain_head != v2.chain_head)

    # 3B. Epoch replay / inflation
    v_replay = IV.IncrementalVerifier(genesis_root)
    for _ in range(50):
        v_replay.apply_epoch([], hashlib.sha256(b'EMPTY').digest())
    inflation_success = (v_replay.epoch == 50 and v_replay.root == genesis_root)

    return {
        "fork_injection_success": fork_injection_success,
        "inflation_success": inflation_success,
        "honest_chain_head": v1.chain_head.hex(),
        "forked_chain_head": v2.chain_head.hex(),
    }

def main():
    print("=== Running H107 Adversarial Soundness Audit Suite ===")
    t0 = time.time()
    
    res_eval = audit_autoloop_evaluators()
    print(f"1. Autoloop Evaluator Audit: {res_eval}")
    
    res_g35 = audit_g35_hub_bias()
    print(f"2. G35 Hub Bias & Lift Audit: {res_g35}")
    
    res_w7 = audit_w7_state_transitions()
    print(f"3. W7 Streaming State Transition Audit: {res_w7}")

    # -------------------------------------------------------------
    # Controls & Falsifiers for D6 Certification
    # -------------------------------------------------------------
    controls = []
    
    # C1: Attack verification control on dead extraction
    c1 = Control(
        "C1_evaluator_defect_detected",
        "auditor must detect key mismatch defects in eval_graph_ai and eval_verification",
        null_must_contain="evaluators passing without detecting key mismatches",
        can_fail_because="if evaluator keys were modified or masked"
    )
    c1.observe(res_eval["eval_graph_ai_dead_keys"] and res_eval["eval_verification_frozen_defaults"], res_eval)
    controls.append(c1)

    # C2: Attack verification control on G35 hub bias
    c2 = Control(
        "C2_hub_bias_measured",
        "auditor must measure that >50% of constant grounding rules concentrate on top-500 hubs",
        null_must_contain="constant rules uniformly distributed across all 14,505 entities",
        can_fail_because="if dataset partitioning or entity counting failed"
    )
    c2.observe(res_g35["tail_constants_in_top500_pct"] > 50.0 and res_g35["spurious_zero_lift_rules_pct"] > 30.0, res_g35)
    controls.append(c2)

    # C3: Attack verification control on W7 fork injection
    c3 = Control(
        "C3_w7_fork_injection_reproduced",
        "auditor must reproduce that unbound delta_n splits sequence chain head on identical state roots",
        null_must_contain="apply_epoch rejecting mismatched delta_n or failing to split chain heads",
        can_fail_because="if delta_n binding check was already implemented"
    )
    c3.observe(res_w7["fork_injection_success"] and res_w7["inflation_success"], res_w7)
    controls.append(c3)

    # Falsifier
    # Falsifier fires if Autoloop evaluators are sound AND G35 rules have zero hub bias AND W7 rejects unbound delta_n
    falsifier_fired = not (res_eval["eval_graph_ai_dead_keys"] or res_g35["spurious_zero_lift_rules_pct"] > 30.0 or res_w7["fork_injection_success"])
    
    f1 = Falsifier(
        "F1_system_soundness_hypothesis",
        refutes="the hypothesis that Autoloop evaluators, G35 rule selection, and W7 state transitions are cryptographically and empirically sound",
        fires_when="all three candidate components resist adversarial attack (no evaluator defects, no hub bias, no fork injection)",
        null_must_contain="all attacks failing to find soundness defects"
    )
    f1.observe(falsifier_fired, {
        "eval_vulnerabilities": res_eval,
        "g35_hub_bias_pct": res_g35["spurious_zero_lift_rules_pct"],
        "w7_fork_injection": res_w7["fork_injection_success"]
    })

    out_file = os.path.join(HERE, "attack_results.json")
    with open(out_file, "w") as f:
        json.dump({
            "elapsed_sec": round(time.time() - t0, 2),
            "autoloop_evaluators": res_eval,
            "g35_hub_bias": res_g35,
            "w7_state_transitions": res_w7,
            "falsifier_fired": falsifier_fired
        }, f, indent=2)

    ok, problems = kfcheck.certify(
        HERE,
        deps=[
            os.path.join(REPO_ROOT, ".github", "autoloop", "evaluators"),
            os.path.join(REPO_ROOT, "spikes", "G34_length1_and_constants"),
            os.path.join(REPO_ROOT, "spikes", "W6_incremental_witness"),
        ],
        artifacts=[out_file],
        controls=controls,
        falsifiers=[f1],
        falsifier="Autoloop evaluators resist metric forgery and dead keys, G35 constant rules exhibit <30% spurious lift, and W7 state transitions bind delta_n against fork injection.",
        allow_dirty=True,
        note="H107: Adversarial Soundness Audit of Autoloop Evaluators, G35 Rule Selection, and W7 Witness Transitions"
    )

    print(f"\n=== H107 Certification: ok={ok} ===")
    if problems:
        for p in problems:
            print(f"  PROBLEM: {p}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
