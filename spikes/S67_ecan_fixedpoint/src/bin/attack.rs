//! Adversarial re-test of the das-concurrency reproduction.
//!
//! Four questions:
//!  A. Does INTEGER (fixed-point) importance also diverge? (decisive: rounding vs interleaving)
//!  B. Does a GLOBAL LOCK (serialise-by-lock, arbitrary order) recover the serialised result?
//!     Epochs are identical, so any serial order must agree. Isolates interleaving from order.
//!  C. Distribution over 50 trials, several (N, EPOCHS) settings.
//!  D. A FAITHFUL model: adds the spreading step + neighbour delivery + alienate_tokens,
//!     including the unsynchronised cross-node write `edge->node2->importance += stimulus`.

use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Mutex;
use std::thread;

const RENT_RATE: f64 = 0.75; // real DAS value (AttentionBrokerServer.cc:8), not 0.03
const SPREAD_RATE: f64 = 0.10; // LOWERBOUND == UPPERBOUND == 0.10

fn dig<T: Copy, F: Fn(T) -> [u8; 8]>(v: &[T], f: F) -> String {
    let mut h = Sha256::new();
    for &x in v {
        h.update(f(x))
    }
    h.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}
fn digf(v: &[f64]) -> String {
    dig(v, |x| x.to_le_bytes())
}
fn digi(v: &[i64]) -> String {
    dig(v, |x| x.to_le_bytes())
}

// ---------------------------------------------------------------- float model (as filed)
fn epoch_f(net: &[Mutex<f64>], stim: &[u64], tw: u128, rent_rate: f64) {
    let n = net.len();
    let mut rent = vec![0.0f64; n];
    let mut total_rent = 0.0f64;
    for i in 0..n {
        let imp = *net[i].lock().unwrap();
        rent[i] = rent_rate * imp;
        total_rent += rent[i];
    }
    for i in 0..n {
        let wages = (stim[i] as f64) * total_rent / (tw as f64);
        let mut g = net[i].lock().unwrap();
        *g -= rent[i];
        *g += wages;
    }
}

// ------------------------------------------------- integer model, IDENTICAL control flow
// Q32.32 fixed point in i64. rent = imp * rr >> 32. Every op exact & deterministic.
const ONE: i64 = 1 << 32;
fn fxmul(a: i64, b: i64) -> i64 {
    ((a as i128 * b as i128) >> 32) as i64
}

fn epoch_i(net: &[Mutex<i64>], stim: &[u64], tw: u128, rent_rate: i64) {
    let n = net.len();
    let mut rent = vec![0i64; n];
    let mut total_rent = 0i64;
    for i in 0..n {
        let imp = *net[i].lock().unwrap();
        rent[i] = fxmul(rent_rate, imp);
        total_rent += rent[i];
    }
    for i in 0..n {
        let wages = ((stim[i] as i128 * total_rent as i128) / tw as i128) as i64;
        let mut g = net[i].lock().unwrap();
        *g -= rent[i];
        *g += wages;
    }
}

// ------------------------------------------------------------------- faithful model
// Adds: alienate_tokens, the spreading step (:76-78), and consolidate_stimulus /
// deliver_stimulus (:98-131) -- including the UNSYNCHRONISED cross-node write to
// edge->node2->importance, modelled with relaxed atomics (a real data race in C++).
struct Faithful {
    imp: Vec<Mutex<f64>>,
    spread: Vec<Mutex<f64>>,
    // node2 importance deltas: written with no lock at all in real DAS
    raw: Vec<AtomicU64>,
    nbr: Vec<Vec<usize>>,
    w: Vec<Vec<f64>>,
    tokens: Mutex<f64>,
}

fn epoch_faithful(f: &Faithful, stim: &[u64], tw: u128) {
    let n = f.imp.len();
    let mut rent = vec![0.0f64; n];
    let mut total_rent = 0.0f64;
    for i in 0..n {
        rent[i] = RENT_RATE * *f.imp[i].lock().unwrap(); // collect_rent :51
        total_rent += rent[i];
    }
    let mut total_to_spread = {
        let mut t = f.tokens.lock().unwrap();
        let a = *t;
        *t = 0.0;
        a
    }; // alienate_tokens
    total_to_spread += total_rent;

    for i in 0..n {
        // consolidate_rent_and_wages :67-78
        let wages = (stim[i] as f64) * total_to_spread / (tw as f64);
        let mut g = f.imp[i].lock().unwrap();
        *g -= rent[i];
        *g += wages;
        let to_spread = *g * SPREAD_RATE;
        *g -= to_spread;
        *f.spread[i].lock().unwrap() = to_spread;
    }
    for i in 0..n {
        // consolidate_stimulus :117-131
        let to_spread = *f.spread[i].lock().unwrap();
        let sum_w: f64 = f.w[i].iter().sum();
        if sum_w > 0.0 {
            for (k, &j) in f.nbr[i].iter().enumerate() {
                let s = (f.w[i][k] / sum_w) * to_spread;
                // edge->node2->importance += stimulus  -- NO LOCK IN REAL DAS
                let cur = f64::from_bits(f.raw[j].load(Ordering::Relaxed));
                f.raw[j].store((cur + s).to_bits(), Ordering::Relaxed);
            }
        }
        *f.spread[i].lock().unwrap() = 0.0;
    }
}

fn fresh_f(n: usize) -> Vec<Mutex<f64>> {
    (0..n).map(|i| Mutex::new(1.0 + (i % 97) as f64 * 0.013)).collect()
}
fn fresh_i(n: usize) -> Vec<Mutex<i64>> {
    (0..n).map(|i| Mutex::new(ONE + (i % 97) as i64 * 55834574)).collect()
}
fn snap_f(v: &[Mutex<f64>]) -> Vec<f64> {
    v.iter().map(|m| *m.lock().unwrap()).collect()
}
fn snap_i(v: &[Mutex<i64>]) -> Vec<i64> {
    v.iter().map(|m| *m.lock().unwrap()).collect()
}
fn stimuli(n: usize) -> (Vec<u64>, u128) {
    let s: Vec<u64> = (0..n).map(|i| ((i * 2654435761) % 1000 + 1) as u64).collect();
    let t = s.iter().map(|&x| x as u128).sum();
    (s, t)
}

fn report(label: &str, serial: &str, seen: &BTreeMap<String, u32>, trials: u32) {
    let m = seen.get(serial).copied().unwrap_or(0);
    println!("  {label:<44} distinct={:<3} match_serial={m}/{trials}", seen.len());
}

fn run_float(n: usize, epochs: usize, trials: u32, rr: f64) -> (String, BTreeMap<String, u32>) {
    let (stim, tw) = stimuli(n);
    let net = fresh_f(n);
    for _ in 0..epochs {
        epoch_f(&net, &stim, tw, rr);
    }
    let serial = digf(&snap_f(&net));
    let mut seen = BTreeMap::new();
    for _ in 0..trials {
        let net = fresh_f(n);
        thread::scope(|s| {
            for _ in 0..epochs {
                s.spawn(|| epoch_f(&net, &stim, tw, rr));
            }
        });
        *seen.entry(digf(&snap_f(&net))).or_insert(0) += 1;
    }
    (serial, seen)
}

fn run_int(n: usize, epochs: usize, trials: u32) -> (String, BTreeMap<String, u32>) {
    let (stim, tw) = stimuli(n);
    let rr = fxmul(ONE, (0.75 * ONE as f64) as i64); // exact: 0.75 is representable
    let net = fresh_i(n);
    for _ in 0..epochs {
        epoch_i(&net, &stim, tw, rr);
    }
    let serial = digi(&snap_i(&net));
    let mut seen = BTreeMap::new();
    for _ in 0..trials {
        let net = fresh_i(n);
        thread::scope(|s| {
            for _ in 0..epochs {
                s.spawn(|| epoch_i(&net, &stim, tw, rr));
            }
        });
        *seen.entry(digi(&snap_i(&net))).or_insert(0) += 1;
    }
    (serial, seen)
}

fn main() {
    let trials = 50u32;

    println!("=== A. INTEGER (Q32.32) vs FLOAT, same control flow, rent_rate=0.75 ===");
    for &(n, e) in &[(2048usize, 6usize), (512, 8), (4096, 4)] {
        let (s, seen) = run_float(n, e, trials, 0.75);
        report(&format!("float  N={n} E={e}"), &s, &seen, trials);
        let (s, seen) = run_int(n, e, trials);
        report(&format!("INT    N={n} E={e}"), &s, &seen, trials);
    }

    println!("\n=== A'. float at the report's rent_rate=0.03 (not DAS's value) ===");
    for &(n, e) in &[(2048usize, 6usize)] {
        let (s, seen) = run_float(n, e, trials, 0.03);
        report(&format!("float  N={n} E={e} rr=0.03"), &s, &seen, trials);
    }

    println!("\n=== B. GLOBAL LOCK around epoch (arbitrary order, no interleave) ===");
    {
        let (n, e) = (2048usize, 6usize);
        let (stim, tw) = stimuli(n);
        let net = fresh_f(n);
        for _ in 0..e {
            epoch_f(&net, &stim, tw, 0.75);
        }
        let serial = digf(&snap_f(&net));
        let mut seen = BTreeMap::new();
        for _ in 0..trials {
            let net = fresh_f(n);
            let gl = Mutex::new(());
            thread::scope(|s| {
                for _ in 0..e {
                    s.spawn(|| {
                        let _g = gl.lock().unwrap();
                        epoch_f(&net, &stim, tw, 0.75);
                    });
                }
            });
            *seen.entry(digf(&snap_f(&net))).or_insert(0) += 1;
        }
        report("global-lock float N=2048 E=6", &serial, &seen, trials);
    }

    println!("\n=== C. 2-thread minimum (E=2 concurrent epochs) ===");
    for &(n, e) in &[(2048usize, 2usize), (64, 2), (8, 2)] {
        let (s, seen) = run_float(n, e, trials, 0.75);
        report(&format!("float  N={n} E={e}"), &s, &seen, trials);
        let (s, seen) = run_int(n, e, trials);
        report(&format!("INT    N={n} E={e}"), &s, &seen, trials);
    }

    println!("\n=== D. FAITHFUL model (spreading + neighbour delivery + alienate_tokens) ===");
    {
        let (n, e) = (2048usize, 6usize);
        let (stim, tw) = stimuli(n);
        let mk = || {
            let nbr: Vec<Vec<usize>> =
                (0..n).map(|i| vec![(i + 1) % n, (i + 7) % n, (i * 13 + 3) % n]).collect();
            let w: Vec<Vec<f64>> = (0..n)
                .map(|i| vec![1.0 + (i % 5) as f64, 2.0 + (i % 3) as f64, 0.5])
                .collect();
            Faithful {
                imp: fresh_f(n),
                spread: (0..n).map(|_| Mutex::new(0.0)).collect(),
                raw: (0..n).map(|_| AtomicU64::new(0f64.to_bits())).collect(),
                nbr,
                w,
                tokens: Mutex::new(1.0),
            }
        };
        // fold raw deltas into imp for the digest
        let final_state = |f: &Faithful| -> Vec<f64> {
            (0..n)
                .map(|i| {
                    *f.imp[i].lock().unwrap() + f64::from_bits(f.raw[i].load(Ordering::Relaxed))
                })
                .collect()
        };
        let f = mk();
        for _ in 0..e {
            epoch_faithful(&f, &stim, tw);
        }
        let serial = digf(&final_state(&f));
        let mut seen = BTreeMap::new();
        for _ in 0..trials {
            let f = mk();
            thread::scope(|s| {
                for _ in 0..e {
                    s.spawn(|| epoch_faithful(&f, &stim, tw));
                }
            });
            *seen.entry(digf(&final_state(&f))).or_insert(0) += 1;
        }
        report("faithful float N=2048 E=6", &serial, &seen, trials);
    }

    corrected();
}

// ==================================================================================
// E. CORRECTED model. HandleTrie::traverse(keep_root_locked=true) holds the ROOT
// mutex for the WHOLE traversal (HandleTrie.cc:208,227-233), so each visit_nodes()
// pass is atomic against every other traversal/insert/lookup on the same trie.
// Interleaving is therefore only possible BETWEEN the phases of spread_stimuli,
// never inside collect_rent. Does divergence survive that?
#[allow(dead_code)]
pub fn corrected() {
    use std::sync::Mutex as M;
    let (n, e, trials) = (2048usize, 6usize, 50u32);
    let (stim, tw) = stimuli(n);

    struct Net { imp: Vec<M<f64>>, root: M<()> }
    let mk = || Net { imp: fresh_f(n), root: M::new(()) };

    let epoch = |net: &Net| {
        let mut rent = vec![0.0f64; n];
        let mut total_rent = 0.0f64;
        {   // visit_nodes(true, collect_rent) -- ATOMIC, root held
            let _g = net.root.lock().unwrap();
            for i in 0..n { rent[i] = RENT_RATE * *net.imp[i].lock().unwrap(); total_rent += rent[i]; }
        }
        // <-- root released here; another epoch can run its whole collect_rent+consolidate
        {   // visit_nodes(true, consolidate_rent_and_wages) -- ATOMIC, root held
            let _g = net.root.lock().unwrap();
            for i in 0..n {
                let wages = (stim[i] as f64) * total_rent / (tw as f64);
                let mut v = net.imp[i].lock().unwrap();
                *v -= rent[i]; *v += wages;
            }
        }
    };

    let net = mk();
    for _ in 0..e { epoch(&net); }
    let serial = digf(&snap_f(&net.imp));
    let mut seen = BTreeMap::new();
    for _ in 0..trials {
        let net = mk();
        thread::scope(|s| { for _ in 0..e { s.spawn(|| epoch(&net)); } });
        *seen.entry(digf(&snap_f(&net.imp))).or_insert(0) += 1;
    }
    println!("\n=== E. CORRECTED (root lock makes each traversal atomic) ===");
    report("phase-atomic float N=2048 E=6", &serial, &seen, trials);
}
