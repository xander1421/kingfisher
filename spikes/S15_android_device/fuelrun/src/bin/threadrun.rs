//! Does CONCURRENCY inside one process perturb the result? (S28, ATTACKER-1.)
//!
//! `out/LEDGER.md:311` grades "Co-tenancy does not perturb results" **B** on 8
//! concurrent PROCESSES, and marks the in-process case `Untested` while naming
//! the mechanism it expects to fail:
//!
//!   "`NEXT_VARIABLE_ID.fetch_add(…, Relaxed)` keeps ids unique but makes WHICH
//!    thread gets which id scheduling-dependent. Each process starts its counter
//!    at 1, which is exactly why this passed."
//!
//! M1.3b answered the SEQUENTIAL case — many different jobs in one process, a
//! fresh `Metta` each — and a sequential run cannot exhibit a scheduling
//! -dependent property. This is the same job list run on N threads in ONE
//! process, repeated, so the digests can be compared run to run.
//!
//! It matters because the phone runs MeTTa IN-PROCESS (M1.1) and WorkManager
//! reuses the app process, so the deployed configuration is the untested one.
//!
//! `canon` and `canon_alpha` are COPIED VERBATIM from `soakrun.rs` in this same
//! crate, deliberately: C0 requires this binary to reproduce soakrun's digests at
//! one thread, and it cannot do that through a reimplementation. If they drift,
//! C0 goes red, which is the point.
//!
//! usage: threadrun <fuel> <threads> <repeats> <prog.metta>...
//! Prints one row per (repeat, position); the caller decides the verdict.
//!
//! v2 (S28, ATTACKER-1) — defect removed: **a numeric field sorted as a
//! string.** v1 built each row as text beginning `thread\tpos\t…` and called
//! `Vec<String>::sort()`, so at 13 jobs the printed order was 0,1,10,11,12,2,…
//! Control C0 — "reproduce `soakrun`'s digests on the same argv" — went RED on
//! a 13-job list and GREEN on the 6-job smoke test that preceded it, because
//! single-digit positions sort correctly and the defect only appears at the
//! first two-digit value. Rows are now `(thread, pos, text)` tuples sorted on
//! the numbers. No digest changes; only the print order does.
//!
//! v3 (S28) — `fuel_used` is now its own column. It was only ever folded into
//! the digest, so "did fuel move under concurrency?" could be answered only by
//! arguing that `canon` leaves the `fuel=` line alone. `fuel_used` is in M1.8's
//! agreement key `(status, fuel_used, sorted_hash)` and it is the quantity that
//! decides whether canonicalisation can repair a divergence at all, so it is
//! measured directly. Digests are unchanged: the same string is still hashed.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::{Arc, Barrier};

fn sha8(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    format!("{:x}", h.finalize())[..16].to_string()
}

fn canon(t: &str) -> String {
    renumber(t, false)
}
fn canon_alpha(t: &str) -> String {
    renumber(t, true)
}

fn renumber(t: &str, all_vars: bool) -> String {
    let mut map: HashMap<String, usize> = HashMap::new();
    let mut out = String::with_capacity(t.len());
    let b: Vec<char> = t.chars().collect();
    let mut i = 0;
    while i < b.len() {
        if b[i] != '$' {
            out.push(b[i]);
            i += 1;
            continue;
        }
        let start = i;
        i += 1;
        while i < b.len() && !b[i].is_whitespace() && b[i] != '(' && b[i] != ')' {
            i += 1;
        }
        let tok: String = b[start..i].iter().collect();
        let has_id = tok.contains('#');
        if !all_vars && !has_id {
            out.push_str(&tok);
            continue;
        }
        let n = map.len() + 1;
        let k = *map.entry(tok.clone()).or_insert(n);
        if all_vars {
            out.push_str(&format!("$v{}", k));
        } else {
            let base = tok.split('#').next().unwrap();
            out.push_str(&format!("{}#{}", base, k));
        }
    }
    out
}

fn run_one(path: &str, fuel_limit: u64) -> (u64, String) {
    let program = std::fs::read_to_string(path).unwrap_or_default();
    let metta = Metta::new(None);
    let parser = SExprParser::new(program.as_str());
    let mut state = RunnerState::new_with_parser(&metta, Box::new(parser));
    let mut fuel: u64 = 0;
    while !state.is_complete() {
        if fuel >= fuel_limit {
            break;
        }
        if state.run_step().is_err() {
            break;
        }
        fuel += 1;
    }
    let mut raw = String::new();
    for (i, group) in state.current_results().iter().enumerate() {
        for atom in group.iter() {
            raw.push_str(&format!("{}\t{}\n", i, atom));
        }
    }
    // v3: fuel returned ALONGSIDE the digest input, not only folded into it.
    // `fuel_used` is in M1.8's agreement key, so "did fuel move under
    // concurrency?" must be readable directly instead of inferred from the fact
    // that `canon` leaves the `fuel=` line alone.
    (fuel, format!("fuel={}\n{}", fuel, raw))
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 5 {
        eprintln!("usage: threadrun <fuel> <threads> <repeats> <prog.metta>...");
        std::process::exit(2);
    }
    let fuel: u64 = args[1].parse().unwrap();
    let threads: usize = args[2].parse().unwrap();
    let repeats: usize = args[3].parse().unwrap();
    let progs: Vec<String> = args[4..].to_vec();

    // C2: the intervention size is printed, not implied. An unchanged digest
    // under a small intervention is a disconnected wire, so the reader gets the
    // thread count, the repeat count and the job count on every run.
    println!(
        "# threadrun threads={} repeats={} programs={} fuel={} jobs_per_repeat={}",
        threads,
        repeats,
        progs.len(),
        fuel,
        progs.len()
    );
    println!("repeat\tthread\tpos\tprogram\tfuel_used\traw\tcanon\talpha");

    for rep in 0..repeats {
        // A BARRIER, so the threads are actually concurrent. Without it a fast
        // thread can finish before a slow one starts and the "concurrent" run is
        // sequential with extra steps -- the control that cannot fail.
        let barrier = Arc::new(Barrier::new(threads));
        let mut handles = Vec::new();
        for t in 0..threads {
            let barrier = Arc::clone(&barrier);
            let progs = progs.clone();
            // Each thread runs EVERY program, so with threads>1 the same job list
            // is interleaved across threads inside one process. That is the
            // configuration the LEDGER row marks Untested.
            handles.push(std::thread::spawn(move || {
                barrier.wait();
                let mut rows: Vec<(usize, usize, String)> = Vec::new();
                for (pos, p) in progs.iter().enumerate() {
                    let (used, out) = run_one(p, fuel);
                    rows.push((
                        t,
                        pos,
                        format!(
                        "{}\t{}\t{}\t{}\t{}\t{}\t{}",
                        t,
                        pos,
                        std::path::Path::new(p)
                            .file_name()
                            .unwrap()
                            .to_string_lossy(),
                        used,
                        sha8(&out),
                        sha8(&canon(&out)),
                        sha8(&canon_alpha(&out))
                    ),
                    ));
                }
                rows
            }));
        }
        // Collected in thread-spawn order and printed sorted, so the OUTPUT order
        // is deterministic even when the EXECUTION order is not. Otherwise a
        // scheduling difference would show up as a diff in the report even if
        // every digest matched.
        //
        // Sorted on the NUMBERS (v2). Sorting the formatted row instead ordered
        // position 10 before position 2 -- see the header.
        let mut all: Vec<(usize, usize, String)> = Vec::new();
        for h in handles {
            all.extend(h.join().unwrap());
        }
        all.sort_by_key(|(t, pos, _)| (*t, *pos));
        for (_, _, row) in all {
            println!("{}\t{}", rep, row);
        }
    }
}
