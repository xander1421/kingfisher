//! S67b — the oracle that models DAS's SHIPPING configuration.
//!
//! The first oracle compared N-thread vs 1-thread over one traversal. DAS has
//! no such mode: `visit_nodes` -> `HandleTrie::traverse` is serial and the trie
//! is content-keyed, so intra-epoch order is fixed. That oracle tested a defect
//! DAS does not have.
//!
//! What DAS does have: three async enqueues are commented out
//! (AttentionBrokerServer.cc:64, :96, :118) and replaced by inline calls, so
//! gRPC worker threads run WHOLE EPOCHS concurrently against one shared
//! HebbianNetwork, protected only by per-trie-node mutexes.
//!
//! The defect is not rounding order. `collect_rent` reads importance across a
//! traversal while another epoch is writing it (StimulusSpreader.cc:51), so
//! `total_rent` sums a TORN STATE that never existed as a consistent snapshot.
//! Per-node mutexes make each access atomic and guarantee nothing about the
//! aggregate. No amount of fixed-point arithmetic fixes this.
//!
//! Oracle: E epochs CONCURRENT vs the same E epochs SERIALISED.

use sha2::{Digest, Sha256};
use std::sync::Mutex;
use std::thread;

const N: usize = 2048;
const EPOCHS: usize = 6;
const RENT_RATE: f64 = 0.03;

fn digest(v: &[f64]) -> String {
    let mut h = Sha256::new();
    for x in v { h.update(x.to_le_bytes()) }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}

/// One `spread_stimuli`, faithful to StimulusSpreader.cc.
fn epoch(net: &[Mutex<f64>], stim: &[u64], total_wages: u128) {
    let mut rent = vec![0.0f64; N];
    let mut total_rent = 0.0f64;
    for i in 0..N {                              // serial, content-ordered
        let imp = *net[i].lock().unwrap();       // per-node mutex, :51
        rent[i] = RENT_RATE * imp;
        total_rent += rent[i];
    }
    for i in 0..N {
        let wages = (stim[i] as f64) * total_rent / (total_wages as f64);
        let mut g = net[i].lock().unwrap();      // :67-68
        *g -= rent[i];
        *g += wages;
    }
}

fn snapshot(net: &[Mutex<f64>]) -> Vec<f64> { net.iter().map(|m| *m.lock().unwrap()).collect() }
fn fresh() -> Vec<Mutex<f64>> { (0..N).map(|i| Mutex::new(1.0 + (i % 97) as f64 * 0.013)).collect() }

fn main() {
    let stim: Vec<u64> = (0..N).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
    let tw: u128 = stim.iter().map(|&x| x as u128).sum();

    let net = fresh();
    for _ in 0..EPOCHS { epoch(&net, &stim, tw); }
    let serial = digest(&snapshot(&net));

    let mut seen = std::collections::BTreeMap::new();
    for _ in 0..8 {
        let net = fresh();
        thread::scope(|s| { for _ in 0..EPOCHS { s.spawn(|| epoch(&net, &stim, tw)); } });
        *seen.entry(digest(&snapshot(&net))).or_insert(0) += 1;
    }

    println!("DAS shipping-configuration oracle — {N} nodes, {EPOCHS} epochs\n");
    println!("  serialised (async enqueue path)   {serial}");
    println!("  concurrent (inline gRPC dispatch), 8 trials:");
    for (d, n) in &seen {
        println!("      {d}  x{n}{}", if *d == serial { "   == serialised" } else { "" });
    }
    let m = seen.get(&serial).copied().unwrap_or(0);
    println!("\n  distinct concurrent outcomes : {}", seen.len());
    println!("  trials matching serialised   : {m}/8");
    println!("  ORACLE: {}", if seen.len() == 1 && m == 8 { "PASS" }
        else { "*** FAIL — concurrent epochs diverge from serialised ***" });
}
