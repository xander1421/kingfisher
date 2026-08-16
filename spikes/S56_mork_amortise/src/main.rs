//! S56 — which part of S55's 0.310 ms is amortisable?
//!
//! S55 measured whole-stage-2 in-process at 0.310 ms and I flagged, against
//! my own result, that it constructs a fresh `Space` and re-parses the program
//! every single query. A shard host would not: it holds the shard resident and
//! pays only the marginal per-query cost. If most of the 0.310 ms is setup,
//! the deployable number is far lower and the Amdahl re-opening in S55 is
//! wrong in the opposite direction from the one I claimed.
//!
//! So: time the four phases separately, then time a RESIDENT space answering
//! repeated queries, and report both. Reports median and MAD of 200 draws,
//! not best-of-N — S55 used best-of-20 and the ledger's own rule 6 says one
//! draw is not a measurement.

use std::time::Instant;

fn el_us(t: Instant) -> f64 { t.elapsed().as_secs_f64() * 1e6 }

fn stats(mut v: Vec<f64>) -> (f64, f64) {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let med = v[v.len() / 2];
    let mut d: Vec<f64> = v.iter().map(|x| (x - med).abs()).collect();
    d.sort_by(|a, b| a.partial_cmp(b).unwrap());
    (med, d[d.len() / 2])
}

fn main() {
    let path = std::env::args().nth(1).unwrap_or_else(|| "s45_short.mm2".into());
    let n: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(200);
    let src = std::fs::read(&path).expect("read");

    // ---- phase decomposition: fresh space every draw, each phase timed ----
    let (mut c_new, mut c_load, mut c_run, mut c_dump) =
        (vec![], vec![], vec![], vec![]);
    for _ in 0..n {
        let t = Instant::now(); let mut s = mork::space::Space::new(); c_new.push(el_us(t));
        let t = Instant::now(); s.add_all_sexpr(&src).expect("parse"); c_load.push(el_us(t));
        let t = Instant::now(); s.metta_calculus(1); c_run.push(el_us(t));
        let t = Instant::now();
        let mut o: Vec<u8> = Vec::with_capacity(1 << 16);
        s.dump_all_sexpr(&mut o).expect("dump"); c_dump.push(el_us(t));
    }

    // ---- resident: one space, N steps against it, no re-construction ----
    // This is the shard-host shape. Note it is NOT the same work as above:
    // the space accumulates, so this measures marginal step cost on a space
    // that is already loaded, which is the thing a resident agent pays.
    let mut s = mork::space::Space::new();
    s.add_all_sexpr(&src).expect("parse");
    let mut c_res = vec![];
    for _ in 0..n {
        let t = Instant::now(); s.metta_calculus(1); c_res.push(el_us(t));
    }

    let names = ["Space::new()", "add_all_sexpr", "metta_calculus(1)", "dump_all_sexpr"];
    let cols  = [c_new, c_load, c_run, c_dump];
    println!("S56 — stage 2 decomposed, {} draws, median +/- MAD (us)\n", n);
    let mut total = 0.0;
    for (nm, c) in names.iter().zip(cols) {
        let (m, d) = stats(c);
        total += m;
        println!("  {:<20} {:9.2} +/- {:6.2}", nm, m, d);
    }
    println!("  {:<20} {:9.2}   <- cold per-query total", "SUM", total);
    let (rm, rd) = stats(c_res);
    println!("\n  {:<20} {:9.2} +/- {:6.2}   <- resident space, marginal step only",
             "resident step", rm, rd);
    println!("\n  amortisable fraction: {:.1}%", 100.0 * (total - rm) / total);
    println!("  S55 reported 0.310 ms best-of-20 for the cold path.");
}
