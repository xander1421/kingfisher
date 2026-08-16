//! S67c — oracle on the CORRECT synchronisation model.
//!
//! epochs.rs modelled per-node locks. That is wrong: `visit_nodes` calls
//! `HandleTrie::traverse(keep_root_locked=true, ...)`, and HandleTrie.cc:227-233
//! skips unlocking root inside the walk, releasing it only after the pass. Since
//! `insert()` and `fetch()` both lock root first, **each traversal is atomic
//! against every other traversal, insert and lookup**. There is no torn read
//! inside collect_rent.
//!
//! The real defect is INTER-phase. `spread_stimuli` runs several root-locked
//! passes and releases root between them, so two epochs can interleave at those
//! boundaries: A collects rent, B collects rent AND consolidates, then A
//! consolidates using rent computed from a state B has already superseded.
//!
//! Reports `match_serialised` over 50 trials. `distinct` is machine-dependent
//! (core count, allocator timing, N) and is not a headline number.

use sha2::{Digest, Sha256};
use std::sync::Mutex;
use std::thread;

const N: usize = 2048;
const EPOCHS: usize = 6;
const RENT_RATE: f64 = 0.75;   // AttentionBrokerServer.cc:8 — was wrongly 0.03

fn digest(v: &[f64]) -> String {
    let mut h = Sha256::new();
    for x in v { h.update(x.to_le_bytes()) }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}

struct Net { imp: Mutex<Vec<f64>>, root: Mutex<()> }

/// Faithful: each pass takes the root lock; root is RELEASED between passes.
fn epoch(net: &Net, stim: &[u64], tw: u128, gap: usize) {
    let (rent, total_rent) = {
        let _r = net.root.lock().unwrap();              // pass 1: collect_rent
        let imp = net.imp.lock().unwrap();
        let rent: Vec<f64> = imp.iter().map(|x| RENT_RATE * x).collect();
        let t: f64 = rent.iter().sum();
        (rent, t)
    };                                                   // <-- root released here
    for _ in 0..gap { std::hint::spin_loop() }           // alienate_tokens + distribute_wages
    {
        let _r = net.root.lock().unwrap();              // pass 2: consolidate
        let mut imp = net.imp.lock().unwrap();
        for i in 0..N {
            let w = (stim[i] as f64) * total_rent / (tw as f64);
            imp[i] = imp[i] - rent[i] + w;
        }
    }
}

fn fresh() -> Net {
    Net { imp: Mutex::new((0..N).map(|i| 1.0 + (i % 97) as f64 * 0.013).collect()),
          root: Mutex::new(()) }
}

fn main() {
    let gap: usize = std::env::var("GAP").ok().and_then(|s| s.parse().ok()).unwrap_or(100);
    let trials = 50;
    let stim: Vec<u64> = (0..N).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
    let tw: u128 = stim.iter().map(|&x| x as u128).sum();

    let net = fresh();
    for _ in 0..EPOCHS { epoch(&net, &stim, tw, gap); }
    let serial = digest(&net.imp.lock().unwrap());

    let mut m_un = 0; let mut d_un = std::collections::BTreeSet::new();
    for _ in 0..trials {
        let net = fresh();
        thread::scope(|s| { for _ in 0..EPOCHS { s.spawn(|| epoch(&net, &stim, tw, gap)); } });
        let d = digest(&net.imp.lock().unwrap());
        if d == serial { m_un += 1 } d_un.insert(d);
    }

    let mut m_fx = 0; let mut d_fx = std::collections::BTreeSet::new();
    for _ in 0..trials {
        let net = fresh(); let ep = Mutex::new(());
        thread::scope(|s| { for _ in 0..EPOCHS {
            s.spawn(|| { let _g = ep.lock().unwrap(); epoch(&net, &stim, tw, gap); }); } });
        let d = digest(&net.imp.lock().unwrap());
        if d == serial { m_fx += 1 } d_fx.insert(d);
    }

    println!("root-lock model, N={N} EPOCHS={EPOCHS} GAP={gap}, {trials} trials");
    println!("  unpatched  match_serialised {m_un}/{trials}   ({} distinct)", d_un.len());
    println!("  epoch_mutex match_serialised {m_fx}/{trials}   ({} distinct)", d_fx.len());
    println!("  VERDICT: {}", if m_un < trials && m_fx == trials {
        "bug reproduces AND the patch fixes it" } else if m_un == trials {
        "*** bug does NOT reproduce under this model ***" } else { "patch insufficient" });
}
