//! Checkpoint cadence, redone. S60 went RED for four reasons; three are fixed
//! and the fourth is deferred:
//!   - shared `Metta` across iterations (A8)      -> fresh state per run
//!   - commitment over address-leaking Display    -> PATCHED, and this tests it
//!   - hash CHAIN with no opening at step k       -> Merkle tree instead
//!   - timing on a contended machine (A10)        -> not timed here; counts only
//!
//! Everything reported is a COUNT or a DIGEST, both load-insensitive, so this is
//! valid while `quiet.sh` refuses. Throughput is deliberately not measured.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};

fn h(parts: &[&[u8]]) -> [u8; 32] {
    let mut d = Sha256::new();
    for p in parts { d.update(p) }
    d.finalize().into()
}
fn hex(b: &[u8]) -> String { b.iter().take(8).map(|x| format!("{x:02x}")).collect() }

/// Merkle root over per-checkpoint digests. A chain cannot open at position k;
/// a tree can, which is what bisection actually needs.
fn merkle(leaves: &[[u8; 32]]) -> ([u8; 32], usize) {
    if leaves.is_empty() { return ([0u8; 32], 0) }
    let mut lvl: Vec<[u8;32]> = leaves.to_vec();
    let mut hashes = 0usize;
    while lvl.len() > 1 {
        let mut nxt = Vec::with_capacity(lvl.len().div_ceil(2));
        for c in lvl.chunks(2) {
            nxt.push(if c.len() == 2 { hashes += 1; h(&[&c[0], &c[1]]) } else { c[0] });
        }
        lvl = nxt;
    }
    (lvl[0], hashes)
}

fn run(src: &str) -> (u64, usize, [u8;32], usize, usize) {
    let m = Metta::new(None);                       // fresh per run, A8
    let mut st = RunnerState::new_with_parser(&m, Box::new(SExprParser::new(src)));
    let mut steps = 0u64;
    let mut prev_len = usize::MAX;
    let mut leaves: Vec<[u8;32]> = Vec::new();
    while !st.is_complete() {
        if st.run_step().is_err() { break }
        steps += 1;
        // O(1) change probe: `results` is append-only (mod.rs:1043 is a push)
        let n = st.current_results().len();
        if n != prev_len {
            prev_len = n;
            let mut s = String::new();
            for g in st.current_results() { for a in g.iter() { s.push_str(&a.to_string()); s.push('\n') } }
            leaves.push(h(&[&steps.to_le_bytes(), s.as_bytes()]));   // step index IS committed
        }
    }
    let (root, inner) = merkle(&leaves);
    (steps, leaves.len(), root, inner, leaves.len()*32)
}

fn main() {
    let path = std::env::args().nth(1).expect("usage: ckpt <prog.metta> [runs]");
    let runs: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(5);
    let src = std::fs::read_to_string(&path).expect("read");
    let mut roots = std::collections::BTreeMap::new();
    let (mut steps, mut ck, mut inner, mut bytes) = (0, 0, 0, 0);
    for _ in 0..runs {
        let (s, c, r, i, b) = run(&src);
        steps = s; ck = c; inner = i; bytes = b;
        *roots.entry(hex(&r)).or_insert(0) += 1;
    }
    println!("program        {}", path);
    println!("steps          {}", steps);
    println!("checkpoints    {}  (1 per {} steps)", ck, if ck>0 {steps as usize/ck} else {0});
    println!("merkle inner   {} hashes   retained {} bytes", inner, bytes);
    println!("bisect probes  {}", (ck as f64).max(1.0).log2().ceil() as u32);
    println!("roots over {} runs:", runs);
    for (r,n) in &roots { println!("   {} x{}", r, n); }
    println!("REPRODUCIBLE   {}", if roots.len()==1 {"YES"} else {"NO"});
}
