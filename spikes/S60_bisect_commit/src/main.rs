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
//!   strbuild— control: build the result string every step, hash nothing (isolates hashing)
//!   lazyv   — properly lazy: cheap (len,last_len) version check BEFORE building the string
//!   dbg     — hash-chain over format!("{:?}", runner_state): interpreter plan IS public
//!   dbglazy — dbg, but only hash when the debug string changed
//!   gran    — one iteration, no timing: report steps / result-changes / dbg-changes / digests
//!   prof    — one iteration in lazy style, print elapsed per 500-step block (O(n^2) check)
//!
//! Reported as steps/second over a fixed time window, per GUARDRAILS A1
//! (never time a sub-second event) and A6 (variance is process-scoped, so the
//! caller must sample N processes, not N iterations).

use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};
use std::time::Instant;

const STEP_CAP: u64 = 2_000_000;

fn results_string(st: &RunnerState) -> String {
    let mut s = String::new();
    for g in st.current_results() {
        for at in g.iter() {
            s.push_str(&at.to_string());
            s.push('\n');
        }
    }
    s
}

fn cheap_version(st: &RunnerState) -> (usize, usize) {
    let r = st.current_results();
    (r.len(), r.last().map(|v| v.len()).unwrap_or(0))
}

fn fold(h: &mut [u8; 32], bytes: &[u8]) {
    let mut hasher = Sha256::new();
    hasher.update(*h);
    hasher.update(bytes);
    *h = hasher.finalize().into();
}

fn main() {
    let a: Vec<String> = std::env::args().collect();
    if a.len() < 4 {
        eprintln!("usage: bisectcommit <prog.metta> <mode> <seconds>");
        std::process::exit(2);
    }
    let src = std::fs::read_to_string(&a[1]).expect("read");
    let mode = a[2].clone();
    let window: f64 = a[3].parse().expect("seconds");

    let metta = Metta::new(None);

    // --- one-shot diagnostic modes ------------------------------------------
    if mode == "gran" {
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
        let (mut steps, mut rchg, mut dchg) = (0u64, 0u64, 0u64);
        let mut prev_r = String::new();
        let mut prev_d = String::new();
        let mut hr = [0u8; 32];
        let mut hd = [0u8; 32];
        let t0 = Instant::now();
        while !st.is_complete() && steps < STEP_CAP {
            if st.run_step().is_err() { break; }
            steps += 1;
            let r = results_string(&st);
            if r != prev_r { rchg += 1; prev_r = r.clone(); fold(&mut hr, r.as_bytes()); }
            if steps <= window as u64 {
                let d = format!("{:?}", st);
                if d != prev_d { dchg += 1; prev_d = d.clone(); fold(&mut hd, d.as_bytes()); }
            }
        }
        println!(
            "gran file {} steps {} result_changes {} dbg_steps {} dbg_changes {} steps_per_rchg {:.1} steps_per_dchg {:.2} rdigest {} ddigest {} secs {:.2}",
            a[1], steps, rchg, steps.min(window as u64), dchg,
            steps as f64 / rchg.max(1) as f64,
            steps.min(window as u64) as f64 / dchg.max(1) as f64,
            hex(&hr), hex(&hd), t0.elapsed().as_secs_f64()
        );
        return;
    }
    if mode == "prof" {
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
        let mut steps = 0u64;
        let mut prev = String::new();
        let mut h = [0u8; 32];
        let t0 = Instant::now();
        let mut blk = Instant::now();
        while !st.is_complete() && steps < STEP_CAP {
            if st.run_step().is_err() { break; }
            steps += 1;
            let s = results_string(&st);
            if s != prev { prev = s.clone(); fold(&mut h, s.as_bytes()); }
            if steps % 500 == 0 {
                println!("prof block {} us_per_step {:.3} resultlen {}",
                    steps / 500, blk.elapsed().as_secs_f64() * 1e6 / 500.0, prev.len());
                blk = Instant::now();
            }
        }
        println!("prof total steps {} secs {:.3}", steps, t0.elapsed().as_secs_f64());
        return;
    }
    if mode == "dbgdump" {
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
        let mut steps = 0u64;
        while !st.is_complete() && steps < window as u64 {
            if st.run_step().is_err() { break; }
            steps += 1;
        }
        println!("{:?}", st);
        return;
    }
    if mode == "iterdbg" {
        // how does iteration N differ from iteration 1 under a REUSED Metta?
        for i in 0..window as u64 {
            let parser = SExprParser::new(src.as_str());
            let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
            let mut steps = 0u64;
            let mut err = String::from("-");
            while !st.is_complete() && steps < STEP_CAP {
                match st.run_step() {
                    Ok(()) => {}
                    Err(e) => { err = e.chars().take(90).collect(); break; }
                }
                steps += 1;
            }
            let last = st.current_results().last().map(|v| v.iter().map(|a| a.to_string()).collect::<Vec<_>>().join(" | ")).unwrap_or_default();
            println!("iter {} steps {} results {} err {} last {}", i, steps, st.current_results().len(), err, &last.chars().take(160).collect::<String>());
        }
        return;
    }
    if mode == "profplain" {
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(&metta, Box::new(parser));
        let mut steps = 0u64;
        let t0 = Instant::now();
        let mut blk = Instant::now();
        while !st.is_complete() && steps < STEP_CAP {
            if st.run_step().is_err() { break; }
            steps += 1;
            if steps % 500 == 0 {
                println!("profplain block {} us_per_step {:.3}",
                    steps / 500, blk.elapsed().as_secs_f64() * 1e6 / 500.0);
                blk = Instant::now();
            }
        }
        println!("profplain total steps {} secs {:.3}", steps, t0.elapsed().as_secs_f64());
        return;
    }

    // --- timed throughput modes ---------------------------------------------
    // FRESH=1: build a new Metta per iteration so every iteration runs the SAME
    // program against a clean space (the reused-Metta version measures iteration
    // 2..N, which aborts early on a duplicate-definition assertion failure).
    // Setup time is excluded from the clock; only the step loop is timed.
    let fresh = std::env::var("FRESH").ok().as_deref() == Some("1");
    let mut iters: u64 = 0;
    let mut steps: u64 = 0;
    let mut commits: u64 = 0;
    let mut last_digest = [0u8; 32];
    let mut sink: usize = 0;
    let mut run_secs = 0f64;
    let t0 = Instant::now();
    while t0.elapsed().as_secs_f64() < window {
        let local_metta;
        let metta = if fresh { local_metta = Metta::new(None); &local_metta } else { &metta };
        let parser = SExprParser::new(src.as_str());
        let mut st = RunnerState::new_with_parser(metta, Box::new(parser));
        let t_run = Instant::now();
        let mut prev = String::new();
        let mut prev_v = (usize::MAX, usize::MAX);
        let mut h = [0u8; 32];
        while !st.is_complete() {
            if st.run_step().is_err() { break; }
            steps += 1;
            if steps % 256 == 0 && t0.elapsed().as_secs_f64() > window { break; }
            match mode.as_str() {
                "plain" => {}
                "strbuild" => {
                    // control: pay the serialisation, skip the SHA-256
                    let s = results_string(&st);
                    sink = sink.wrapping_add(s.len());
                }
                "chain" | "lazy" => {
                    let s = results_string(&st);
                    if mode == "lazy" && s == prev { continue; }
                    prev = s;
                    fold(&mut h, prev.as_bytes());
                    commits += 1;
                }
                "lazyv" => {
                    // properly lazy: O(1) version probe first, serialise only on change
                    let v = cheap_version(&st);
                    if v == prev_v { continue; }
                    prev_v = v;
                    let s = results_string(&st);
                    fold(&mut h, s.as_bytes());
                    commits += 1;
                }
                "dbg" | "dbglazy" => {
                    let s = format!("{:?}", st);
                    if mode == "dbglazy" && s == prev { continue; }
                    prev = s;
                    fold(&mut h, prev.as_bytes());
                    commits += 1;
                }
                _ => { eprintln!("bad mode"); std::process::exit(2); }
            }
        }
        run_secs += t_run.elapsed().as_secs_f64();
        last_digest = h;
        iters += 1;
    }
    println!(
        "mode {}  fresh {}  iters {}  steps {}  steps_per_iter {}  commits {}  steps_per_s {:.0}  digest {}  sink {}",
        mode, fresh, iters, steps, steps / iters.max(1), commits,
        steps as f64 / run_secs, hex(&last_digest), sink & 0
    );
}
fn hex(b: &[u8]) -> String { b.iter().take(8).map(|x| format!("{x:02x}")).collect() }
