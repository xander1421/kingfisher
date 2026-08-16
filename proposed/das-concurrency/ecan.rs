//! S67 — deterministic fixed-point ECAN, with the acceptance oracle.
//!
//! DAS's attention broker (elders/das/src/attention_broker) is the missing organ
//! in `analysis/THE_BRAIN.md`. Its semantics, read from StimulusSpreader.cc:
//!
//!     rent_i        = rent_rate * importance_i          (collect_rent:51)
//!     total_rent    = sum of rent_i                     (collect_rent:52)
//!     to_spread     = alienated_tokens + total_rent     (spread_stimuli:183)
//!     wages_i       = stim_i * to_spread / total_wages  (distribute_wages:147)
//!     importance_i' = importance_i - rent_i + wages_i   (consolidate:67-68)
//!
//! `typedef double ImportanceType` (HebbianNetwork.h:17), and `total_rent +=`
//! accumulates across a threaded trie walk. GUARDRAILS A11 predicts this is
//! nondeterministic NOT because addition is unsafe -- it is associative for
//! integers -- but because the rate multiplications ROUND, and float addition
//! is not associative, so thread order changes the sum.
//!
//! Two implementations, one oracle:
//!   double : faithful to DAS. Expected to FAIL.
//!   fixed  : A11 spec. Expected to PASS.
//!
//! Oracle: N threads and 1 thread must produce an identical per-epoch state
//! hash. This is a digest comparison, so it is load-insensitive (A10 scope).

use sha2::{Digest, Sha256};
use std::sync::{Arc, Mutex};
use std::thread;

const N_NODES: usize = 4096;
const EPOCHS: usize = 12;
const RENT_RATE_F: f64 = 0.03;
const RENT_RATE_Q: u64 = (0.03f64 * (1u64 << 32) as f64) as u64; // Q32.32

fn digest_f(v: &[f64]) -> String {
    let mut h = Sha256::new();
    for x in v { h.update(x.to_le_bytes()) }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}
fn digest_u(v: &[u64]) -> String {
    let mut h = Sha256::new();
    for x in v { h.update(x.to_le_bytes()) }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}

/// Faithful to DAS: double importance, total_rent accumulated across threads.
fn run_double(threads: usize, stim: &[u64]) -> String {
    let mut imp: Vec<f64> = (0..N_NODES).map(|i| 1.0 + (i % 97) as f64 * 0.013).collect();
    let total_wages: u64 = stim.iter().sum();
    for _ in 0..EPOCHS {
        let rent: Vec<f64> = imp.iter().map(|x| x * RENT_RATE_F).collect();
        // the defect: partial sums land in whatever order threads finish
        let acc = Arc::new(Mutex::new(0.0f64));
        let chunk = N_NODES.div_ceil(threads);
        thread::scope(|s| {
            for c in rent.chunks(chunk) {
                let acc = Arc::clone(&acc);
                s.spawn(move || {
                    let part: f64 = c.iter().sum();
                    let mut g = acc.lock().unwrap();
                    *g += part;              // float add: NOT associative
                });
            }
        });
        let to_spread = *acc.lock().unwrap();
        for i in 0..N_NODES {
            let wages = (stim[i] as f64) * to_spread / (total_wages as f64);
            imp[i] = imp[i] - rent[i] + wages;
        }
    }
    digest_f(&imp)
}

/// A11 spec: accumulate wide, round canonically, update synchronously.
fn run_fixed(threads: usize, stim: &[u64]) -> String {
    // Q32.32 importance
    let mut imp: Vec<u64> = (0..N_NODES)
        .map(|i| ((1.0 + (i % 97) as f64 * 0.013) * (1u64 << 32) as f64) as u64).collect();
    let total_wages: u128 = stim.iter().map(|&x| x as u128).sum();
    for _ in 0..EPOCHS {
        // ONE rounding site: the rate multiply, truncating, in u128 then back.
        let rent: Vec<u64> = imp.iter()
            .map(|&x| (((x as u128) * (RENT_RATE_Q as u128)) >> 32) as u64).collect();
        // accumulate WIDE and EXACT: u128 integer addition is associative, so
        // thread order cannot matter -- no rounding happens in the sum at all.
        let chunk = N_NODES.div_ceil(threads);
        let parts: Vec<u128> = thread::scope(|s| {
            let hs: Vec<_> = rent.chunks(chunk)
                .map(|c| s.spawn(move || c.iter().map(|&x| x as u128).sum::<u128>()))
                .collect();
            hs.into_iter().map(|h| h.join().unwrap()).collect()
        });
        // canonical fold order: by chunk index, never by completion order
        let to_spread: u128 = parts.iter().sum();
        // BSP: read epoch t, write t+1
        let mut next = vec![0u64; N_NODES];
        for i in 0..N_NODES {
            // one division = one rounding site
            let wages = ((stim[i] as u128) * to_spread / total_wages) as u64;
            next[i] = imp[i].saturating_sub(rent[i]).saturating_add(wages);
        }
        imp = next;
    }
    digest_u(&imp)
}

fn main() {
    let stim: Vec<u64> = (0..N_NODES).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
    println!("ECAN determinism oracle — {} nodes, {} epochs\n", N_NODES, EPOCHS);
    for (name, f) in [("double (as DAS ships)", run_double as fn(usize,&[u64])->String),
                      ("fixed  (A11 spec)",     run_fixed)] {
        let mut hs = std::collections::BTreeMap::new();
        for t in [1usize, 2, 4, 8] {
            let d = f(t, &stim);
            hs.entry(d).or_insert_with(Vec::new).push(t);
        }
        let ok = hs.len() == 1;
        println!("  {}", name);
        for (d, ts) in &hs { println!("      T={:?}  {}", ts, d); }
        println!("      ORACLE: {}\n", if ok { "PASS — N threads == 1 thread" }
                                       else { "*** FAIL — thread count changes the result ***" });
    }
}

#[cfg(test)]
mod check {
    use super::*;
    /// Guard against the S58 `b4` failure: an oracle that passes because the
    /// computation is degenerate proves nothing. Importance must actually move.
    #[test]
    fn fixed_point_is_not_degenerate() {
        let stim: Vec<u64> = (0..N_NODES).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
        let start: Vec<u64> = (0..N_NODES)
            .map(|i| ((1.0 + (i % 97) as f64 * 0.013) * (1u64 << 32) as f64) as u64).collect();
        // one epoch, single-threaded, inlined so we can see the state
        let total_wages: u128 = stim.iter().map(|&x| x as u128).sum();
        let rent: Vec<u64> = start.iter()
            .map(|&x| (((x as u128) * (RENT_RATE_Q as u128)) >> 32) as u64).collect();
        let to_spread: u128 = rent.iter().map(|&x| x as u128).sum();
        let next: Vec<u64> = (0..N_NODES).map(|i| {
            let w = ((stim[i] as u128) * to_spread / total_wages) as u64;
            start[i].saturating_sub(rent[i]).saturating_add(w)
        }).collect();
        let moved = (0..N_NODES).filter(|&i| next[i] != start[i]).count();
        let distinct: std::collections::BTreeSet<u64> = next.iter().copied().collect();
        assert!(to_spread > 0, "no rent collected — degenerate");
        assert!(moved > N_NODES/2, "only {moved}/{N_NODES} nodes moved — degenerate");
        assert!(distinct.len() > 100, "only {} distinct values — degenerate", distinct.len());
        assert!(next.iter().all(|&x| x > 0), "some node saturated to zero");
        println!("  moved {moved}/{N_NODES}, {} distinct values, to_spread {to_spread}",
                 distinct.len());
    }
}
