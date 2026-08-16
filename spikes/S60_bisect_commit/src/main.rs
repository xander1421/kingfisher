//! S60 — what does a per-step bisection commitment cost?
//!
//! R-NEW's recommended shape is optimistic settlement with proof-on-challenge:
//! bisect the disputed trace to ONE step, then prove that step. Bisection needs
//! the prover to commit to its state at arbitrary step k, and that commitment is
//! paid by EVERY job, disputed or not. This measures it.
//!
//! Modes:
//!   plain   — control: run_step only, no commitment
//!   chain   — hash-chain the results after every step (H_k = SHA256(H_{k-1} || R_k))
//!   lazy    — hash-chain, but only when current_results actually CHANGED
//!
//! Reported as steps/second over a fixed time window, per GUARDRAILS A1
//! (never time a sub-second event) and A6 (variance is process-scoped, so the
//! caller must sample N processes, not N iterations).

use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};
use std::time::Instant;

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 4 { eprintln!("usage: bisectcommit <prog.metta> <mode> <seconds>"); std::process::exit(2); }
    let src = std::fs::read_to_string(&a[1]).expect("read");
    let mode = a[2].clone();
    let window: f64 = a[3].parse().expect("seconds");

    let metta = Metta::new(None);
    // warm: first iteration pays module load; the window must measure steady state
    let mut iters: u64 = 0;
    let mut steps: u64 = 0;
    let mut commits: u64 = 0;
    let mut last_digest = [0u8; 32];
    let t0 = Instant::now();
    while t0.elapsed().as_secs_f64() < window {
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
        let mut prev = String::new();
        let mut h = [0u8; 32];
        while !st.is_complete() {
            if st.run_step().is_err() { break; }
            steps += 1;
            match mode.as_str() {
                "plain" => {}
                "chain" | "lazy" => {
                    // serialise the observable state. NOTE: RunnerState exposes
                    // only current_results() - the interpreter's internal plan
                    // stack is NOT public, so this commits to results only.
                    let mut s = String::new();
                    for g in st.current_results() { for at in g.iter() {
                        s.push_str(&at.to_string()); s.push('\n'); } }
                    if mode == "lazy" && s == prev { continue; }
                    prev = s.clone();
                    let mut hasher = Sha256::new();
                    hasher.update(h);
                    hasher.update(s.as_bytes());
                    h = hasher.finalize().into();
                    commits += 1;
                }
                _ => { eprintln!("bad mode"); std::process::exit(2); }
            }
        }
        last_digest = h;
        iters += 1;
    }
    let el = t0.elapsed().as_secs_f64();
    println!("mode {}  iters {}  steps {}  commits {}  steps_per_s {:.0}  digest {}",
        mode, iters, steps, commits, steps as f64 / el, hex(&last_digest));
}
fn hex(b: &[u8]) -> String { b.iter().take(8).map(|x| format!("{x:02x}")).collect() }
