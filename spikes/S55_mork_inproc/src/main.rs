//! S55 — MORK as an in-process library, disproving my own LEDGER line 41.
//!
//! I wrote "MORK has no library surface — CLI only, so it cannot be a
//! per-query in-process engine", graded it E ("read, not measured"), and let
//! it gate the largest cost in the query path: S45 measured stage 2 at 5.66 ms
//! of which 5.25 ms is generic Android process creation. A reviewer found
//! kernel/src/lib.rs exporting `pub mod space`, and experiments/
//! unification_test_laws already calling mork::space::Space::new() in-process.
//!
//! This links MORK as a library and runs the same stage-2 job S45 ran as a
//! subprocess: load the prefilter shortlist, apply one exec rule, dump.
//! If the ~5.25 ms of exec() disappears, the architectural requirement
//! "stage 2 must run in-process" is satisfiable with MORK, not only hyperon.

use std::io::Write;
use std::time::Instant;

fn now_ms(t: Instant) -> f64 { t.elapsed().as_secs_f64() * 1e3 }

fn main() {
    let path = std::env::args().nth(1)
        .unwrap_or_else(|| "s45_short.mm2".to_string());
    let reps: usize = std::env::args().nth(2)
        .and_then(|s| s.parse().ok()).unwrap_or(20);
    let src = std::fs::read(&path).expect("cannot read program");

    // warm: first call pays lazy init, and we want the steady state that a
    // resident device agent would actually see
    let mut best = f64::MAX;
    let mut loaded = 0usize;
    let mut dumped = 0usize;
    for i in 0..reps {
        let t = Instant::now();
        let mut s = mork::space::Space::new();
        loaded = s.add_all_sexpr(&src).expect("parse");
        s.metta_calculus(1);
        let mut out: Vec<u8> = Vec::with_capacity(1 << 16);
        dumped = s.dump_all_sexpr(&mut out).expect("dump");
        let el = now_ms(t);
        if i > 0 && el < best { best = el; }
        if i == reps - 1 {
            let mut f = std::fs::File::create("s55_inproc_out.txt").unwrap();
            f.write_all(&out).unwrap();
        }
    }

    println!("S55 MORK in-process");
    println!("  program        {}", path);
    println!("  loaded         {} expressions", loaded);
    println!("  dumped         {} expressions", dumped);
    println!("  best of {:<3}    {:.3} ms   (whole stage 2: new + load + run + dump)", reps, best);
    println!();
    println!("  S45 subprocess  5.66 ms, of which ~5.25 ms was process creation");
    println!("  speedup         {:.1}x", 5.66 / best);
}
