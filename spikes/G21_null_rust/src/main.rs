//! G21 — G17's null loop in Rust, so the p-value stops being floor-limited.
//!
//! G17 reported `p = 0.040` from 24 degree-preserving shuffles. That is exactly
//! `1/(24+1)` — the smallest p 24 draws can express — and I chose 24 because it
//! is the smallest n where `p < 0.05` is *reachable*. Declaring that made it
//! honest; it did not make it strong. The limit was Python: each draw walks
//! every 2-hop path in a 217k-triple graph, ~25 s, so 24 draws was ~10 minutes
//! and 500 would have been three and a half hours.
//!
//! This is the same computation with the same exclusions, single-threaded per
//! draw and parallel across draws. Nothing about the statistic changes — only
//! how many times it can be run.
//!
//! EXCLUSIONS, identical to `G17_composition_redo/redo.py`:
//!   * self-loop edges (s == o) dropped at load
//!   * paths with a == b, b == c or c == a skipped
//!   * bodies whose `q` is >30% the reverse of `p` rejected (near-inverse)
//!   * heads with r == p or r == q rejected (restatement)
//!   * denominator is distinct (a,c) PAIRS, never paths
//!   * a candidate pair whose r-edge is already in train is skipped
//!
//! EQUIVALENCE GATE: the real-graph statistic must reproduce Python's 0.441 to
//! three decimals. A faster null loop that computes a different statistic tells
//! us nothing, and this is the same trap G19's sabotage control exists for.

use std::collections::{HashMap, HashSet};
use std::fs;

const MIN_PAIRS: usize = 30;
const INV_MAX: f64 = 0.30;
const TOP_N: usize = 12;

type Tri = (u32, u32, u32); // (pred, subj, obj)

fn load(path: &str) -> Vec<Tri> {
    let d = fs::read(path).expect("triples.bin");
    let nt = u32::from_le_bytes(d[0..4].try_into().unwrap()) as usize;
    let mut v = Vec::with_capacity(nt);
    for i in 0..nt {
        let o = 12 + i * 12;
        v.push((
            u32::from_le_bytes(d[o..o + 4].try_into().unwrap()),
            u32::from_le_bytes(d[o + 4..o + 8].try_into().unwrap()),
            u32::from_le_bytes(d[o + 8..o + 12].try_into().unwrap()),
        ));
    }
    v
}

/// xorshift64* — deterministic and seedable, so a draw is reproducible by seed.
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;
        self.0
    }
    fn below(&mut self, n: usize) -> usize {
        (self.next() % n as u64) as usize
    }
}

struct Index {
    out: HashMap<u32, Vec<(u32, u32)>>,   // subj -> [(pred, obj)]
    pair: HashMap<(u32, u32), HashSet<u32>>, // (subj,obj) -> {pred}
    byp: HashMap<u32, HashSet<(u32, u32)>>,  // pred -> {(s,o)}
}

fn index(t: &[Tri]) -> Index {
    let mut out: HashMap<u32, Vec<(u32, u32)>> = HashMap::new();
    let mut pair: HashMap<(u32, u32), HashSet<u32>> = HashMap::new();
    let mut byp: HashMap<u32, HashSet<(u32, u32)>> = HashMap::new();
    for &(p, s, o) in t {
        if s == o {
            continue; // self-loop edges dropped, as in redo.py
        }
        out.entry(s).or_default().push((p, o));
        pair.entry((s, o)).or_default().insert(p);
        byp.entry(p).or_default().insert((s, o));
    }
    Index { out, pair, byp }
}

/// Mean held-out confidence over the top-N rules by held-out confidence.
fn statistic(train: &[Tri], test_pair: &HashMap<(u32, u32), HashSet<u32>>) -> f64 {
    let tr = index(train);
    let mut body: HashMap<(u32, u32), HashSet<(u32, u32)>> = HashMap::new();
    let mut head: HashMap<(u32, u32, u32), HashSet<(u32, u32)>> = HashMap::new();

    for (&a, edges) in tr.out.iter() {
        for &(p, b) in edges {
            if b == a {
                continue;
            }
            if let Some(next) = tr.out.get(&b) {
                for &(q, c) in next {
                    if c == a || c == b {
                        continue;
                    }
                    body.entry((p, q)).or_default().insert((a, c));
                    if let Some(rs) = tr.pair.get(&(a, c)) {
                        for &r in rs {
                            head.entry((p, q, r)).or_default().insert((a, c));
                        }
                    }
                }
            }
        }
    }

    // reverse sets, for the near-inverse test
    let rev: HashMap<u32, HashSet<(u32, u32)>> = tr
        .byp
        .iter()
        .map(|(&p, e)| (p, e.iter().map(|&(s, o)| (o, s)).collect()))
        .collect();

    // (ho_conf, ho_pairs) — the second is needed for the tie-break. Python
    // sorts by `(-ho_conf, -ho_pairs)` (redo.py:126); sorting by conf alone
    // lets ties at the top-12 boundary pick a different 12th rule, which moves
    // the statistic with no logic differing anywhere.
    let mut confs: Vec<(f64, usize)> = Vec::new();
    for (&(p, q, r), _) in head.iter() {
        let bp = match body.get(&(p, q)) {
            Some(b) if b.len() >= MIN_PAIRS => b,
            _ => continue,
        };
        if r == p || r == q {
            continue; // restatement
        }
        if let (Some(pe), Some(qr)) = (tr.byp.get(&p), rev.get(&q)) {
            if !pe.is_empty() {
                let shared = qr.intersection(pe).count() as f64;
                if shared / pe.len() as f64 > INV_MAX {
                    continue; // near-inverse body
                }
            }
        }
        let mut n = 0usize;
        let mut hits = 0usize;
        for ac in bp.iter() {
            if tr.pair.get(ac).map_or(false, |s| s.contains(&r)) {
                continue; // rule already saw this answer in train
            }
            n += 1;
            if test_pair.get(ac).map_or(false, |s| s.contains(&r)) {
                hits += 1;
            }
        }
        if n >= MIN_PAIRS {
            confs.push((hits as f64 / n as f64, n));
        }
    }
    confs.sort_by(|a, b| {
        b.0.partial_cmp(&a.0)
            .unwrap()
            .then_with(|| b.1.cmp(&a.1))
    });
    let k = TOP_N.min(confs.len());
    if k == 0 {
        return 0.0;
    }
    // Divide by k, not TOP_N — matches redo.py:189 `sum(top) / len(top)`,
    // which differs only when a draw yields fewer than 12 surviving rules.
    confs[..k].iter().map(|x| x.0).sum::<f64>() / k as f64
}

/// Degree-preserving: permute objects within each predicate.
fn shuffled(train: &[Tri], seed: u64) -> Vec<Tri> {
    let mut rng = Rng(seed | 1);
    let mut byp: HashMap<u32, Vec<(u32, u32)>> = HashMap::new();
    for &(p, s, o) in train {
        byp.entry(p).or_default().push((s, o));
    }
    let mut keys: Vec<u32> = byp.keys().copied().collect();
    keys.sort_unstable(); // deterministic order regardless of hash seed
    let mut out = Vec::with_capacity(train.len());
    for p in keys {
        let prs = &byp[&p];
        let mut objs: Vec<u32> = prs.iter().map(|&(_, o)| o).collect();
        for i in (1..objs.len()).rev() {
            let j = rng.below(i + 1);
            objs.swap(i, j);
        }
        for (i, &(s, _)) in prs.iter().enumerate() {
            out.push((p, s, objs[i]));
        }
    }
    out
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let draws: usize = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(500);
    let path = args
        .get(2)
        .cloned()
        .unwrap_or_else(|| "../S52_realkg/triples.bin".to_string());

    let tri = load(&path);
    // Same 80/20 split as redo.py: Python's random.Random(0xC0FFEE).shuffle on
    // an index list. Reproducing Python's Mersenne shuffle in Rust is not
    // worth it, so the split index is read from a file redo.py writes.
    let split: Vec<usize> = fs::read_to_string("split.txt")
        .expect("split.txt — run `python3 dump_split.py` first")
        .split_whitespace()
        .map(|s| s.parse().unwrap())
        .collect();
    let cut = (tri.len() as f64 * 0.8) as usize;
    let train: Vec<Tri> = split[..cut].iter().map(|&i| tri[i]).collect();
    let test: Vec<Tri> = split[cut..].iter().map(|&i| tri[i]).collect();
    let test_pair = index(&test).pair;

    // Read what Python actually computed, rather than a literal typed from a
    // rounded printout. The earlier gate was `|real - 0.441| < 0.0005` and
    // Python's value is 0.44054697045288443, leaving 0.00005 of margin on a
    // number I had transcribed by eye — the same declared-vs-observed defect
    // agent-1 found in the quorum's ISA axis.
    let real_py: f64 = fs::read_to_string("real_py.txt")
        .expect("real_py.txt — run `python3 dump_split.py` first")
        .trim()
        .parse()
        .unwrap();
    let real = statistic(&train, &test_pair);
    println!("real statistic {:.10}   (Python {:.10})", real, real_py);
    // 1e-9: the only legitimate difference is float summation order over 12
    // terms, which is ~1e-16. Anything larger is a logic difference.
    let gate = (real - real_py).abs() < 1e-9;
    println!(
        "EQUIVALENCE GATE: {}   (delta {:.3e})",
        if gate {
            "PASS — same statistic as the Python implementation"
        } else {
            "FAIL — different statistic; the null below would be meaningless"
        },
        (real - real_py).abs()
    );
    if !gate {
        std::process::exit(2);
    }

    let nthreads = std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(4)
        .min(12);
    let mut handles = Vec::new();
    let chunk = (draws + nthreads - 1) / nthreads;
    let train = std::sync::Arc::new(train);
    let test_pair = std::sync::Arc::new(test_pair);
    for t in 0..nthreads {
        let tr = train.clone();
        let tp = test_pair.clone();
        let lo = t * chunk;
        let hi = ((t + 1) * chunk).min(draws);
        handles.push(std::thread::spawn(move || {
            let mut v = Vec::new();
            for s in lo..hi {
                v.push(statistic(&shuffled(&tr, 1000 + s as u64), &tp));
            }
            v
        }));
    }
    let mut nulls: Vec<f64> = Vec::new();
    for h in handles {
        nulls.extend(h.join().unwrap());
    }

    // Dump every draw. The summary alone cannot answer whether the null's tail
    // is shaped such that a parametric statement is licensed, and with a
    // seeded RNG (1000+s) this file is reproducible rather than a one-off.
    fs::write(
        "nulls.txt",
        nulls.iter().map(|x| format!("{x}\n")).collect::<String>(),
    )
    .unwrap();

    let n = nulls.len() as f64;
    let mean = nulls.iter().sum::<f64>() / n;
    let sd = (nulls.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n).sqrt();
    let mx = nulls.iter().cloned().fold(f64::MIN, f64::max);
    let ge = nulls.iter().filter(|&&x| x >= real).count();
    let p = (ge as f64 + 1.0) / (n + 1.0);
    println!(
        "null n={}  mean {:.4}  sd {:.4}  max {:.4}",
        nulls.len(),
        mean,
        sd,
        mx
    );
    println!(
        "  >= real {}/{}   permutation p = {:.4}   (floor {:.4})",
        ge,
        nulls.len(),
        p,
        1.0 / (n + 1.0)
    );
    println!(
        "  VERDICT: {}",
        if p < 0.05 && p > 1.0 / (n + 1.0) {
            "ABOVE NULL, p is NOT floor-limited"
        } else if p <= 1.0 / (n + 1.0) {
            "ABOVE NULL but p is STILL at the floor — no null reached real"
        } else {
            "NOT ABOVE NULL"
        }
    );
}
