//! Attack round 2: force genuine overlap with a Barrier, then re-run the
//! CORRECTED (phase-atomic) model against the AS-FILED (no root lock) model.
//!
//! HandleTrie::traverse(keep_root_locked=true) holds root->trie_node_mutex for the
//! WHOLE traversal (HandleTrie.cc:203-233), so every visit_nodes() pass in
//! spread_stimuli is mutually exclusive with every other traversal/insert/lookup on
//! the same trie. The filed epochs.rs models NO such lock, which is the wrong
//! synchronisation model. Question: does the bug survive the correct model?

use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::sync::{Barrier, Mutex};
use std::thread;

const RR: f64 = 0.75;

fn digf(v: &[f64]) -> String {
    let mut h = Sha256::new();
    for x in v {
        h.update(x.to_le_bytes())
    }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}
fn fresh(n: usize) -> Vec<Mutex<f64>> {
    (0..n).map(|i| Mutex::new(1.0 + (i % 97) as f64 * 0.013)).collect()
}
fn snap(v: &[Mutex<f64>]) -> Vec<f64> {
    v.iter().map(|m| *m.lock().unwrap()).collect()
}
fn stimuli(n: usize) -> (Vec<u64>, u128) {
    let s: Vec<u64> = (0..n).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
    let t = s.iter().map(|&x| x as u128).sum();
    (s, t)
}

struct Net {
    imp: Vec<Mutex<f64>>,
    root: Mutex<()>,
}

/// phase_atomic=true  -> models the real root lock (each visit_nodes pass exclusive)
/// phase_atomic=false -> models what epochs.rs filed (per-node locks only)
fn epoch(net: &Net, stim: &[u64], tw: u128, phase_atomic: bool) { epoch_gap(net, stim, tw, phase_atomic, 0) }

/// gap = work between visit_nodes() passes, modelling alienate_tokens() +
/// distribute_wages() (which does one HandleTrie::insert per requested handle).
fn epoch_gap(net: &Net, stim: &[u64], tw: u128, phase_atomic: bool, gap: usize) {
    let n = net.imp.len();
    let mut rent = vec![0.0f64; n];
    let mut total_rent = 0.0f64;
    {
        let _g = phase_atomic.then(|| net.root.lock().unwrap());
        for i in 0..n {
            rent[i] = RR * *net.imp[i].lock().unwrap();
            total_rent += rent[i];
        }
    }
    // ---- root released here; real DAS runs alienate_tokens + distribute_wages ----
    {
        let mut sink: Vec<Box<(f64, f64)>> = Vec::with_capacity(gap);
        for k in 0..gap { sink.push(Box::new((k as f64, 0.0))); }   // ~ insert() per handle
        std::hint::black_box(&sink);
    }
    {
        let _g = phase_atomic.then(|| net.root.lock().unwrap());
        for i in 0..n {
            let wages = (stim[i] as f64) * total_rent / (tw as f64);
            let mut v = net.imp[i].lock().unwrap();
            *v -= rent[i];
            *v += wages;
        }
    }
}

fn run(n: usize, e: usize, trials: u32, phase_atomic: bool, barrier: bool) -> (usize, u32) {
    let (stim, tw) = stimuli(n);
    let net = Net { imp: fresh(n), root: Mutex::new(()) };
    for _ in 0..e {
        epoch_gap(&net, &stim, tw, phase_atomic, GAP.with(|g| *g));
    }
    let serial = digf(&snap(&net.imp));

    let mut seen: BTreeMap<String, u32> = BTreeMap::new();
    for _ in 0..trials {
        let net = Net { imp: fresh(n), root: Mutex::new(()) };
        let b = Barrier::new(e);
        thread::scope(|s| {
            for _ in 0..e {
                s.spawn(|| {
                    if barrier {
                        b.wait();
                    }
                    epoch(&net, &stim, tw, phase_atomic);
                });
            }
        });
        *seen.entry(digf(&snap(&net.imp))).or_insert(0) += 1;
    }
    (seen.len(), seen.get(&serial).copied().unwrap_or(0))
}

thread_local! { static GAP: usize = std::env::var("GAP").ok().and_then(|v| v.parse().ok()).unwrap_or(0); }

fn main() {
    let trials = 50u32;
    println!("{:<10} {:<8} {:<14} {:<9} {:>8} {:>8}", "N", "EPOCHS", "sync-model", "barrier", "distinct", "match");
    println!("{}", "-".repeat(64));
    for &(n, e) in &[(2048usize, 6usize), (16384, 6), (65536, 4), (65536, 8)] {
        for &pa in &[false, true] {
            for &bar in &[false, true] {
                let (d, m) = run(n, e, trials, pa, bar);
                println!(
                    "{n:<10} {e:<8} {:<14} {:<9} {d:>8} {m:>7}/{trials}",
                    if pa { "ROOT-LOCK(real)" } else { "per-node(filed)" },
                    bar
                );
            }
        }
    }
}
