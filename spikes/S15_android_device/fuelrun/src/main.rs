//! fuelrun — a fuel-metered MeTTa job runner, built to run identically on a
//! desktop and on an Android phone.
//!
//! This is milestone M1.2 + M1.6 of the port plan in miniature:
//!   * drive evaluation one step at a time instead of calling run() to
//!     completion, so the step count IS the fuel meter;
//!   * stop deterministically when the fuel limit is hit, and report that as a
//!     *result* (FUEL_EXHAUSTED), not an error;
//!   * canonicalise the results and hash them, so two devices can be compared
//!     byte for byte.
//!
//! Two hashes are printed on purpose:
//!   raw_hash    — results in the order the interpreter produced them
//!   sorted_hash — results sorted
//! If raw_hash matches across architectures, evaluation order itself is
//! reproducible, which is a stronger claim than set equality and is what the
//! verification ladder actually needs.
//!
//! Usage: fuelrun <program.metta> <fuel_limit>

use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::time::Instant;

use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};

fn sha256_hex(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    h.finalize().iter().map(|b| format!("{:02x}", b)).collect()
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: fuelrun <program.metta> <fuel_limit>");
        std::process::exit(2);
    }
    let path = &args[1];
    let fuel_limit: u64 = args[2].parse().expect("fuel_limit must be a number");

    let program = std::fs::read_to_string(path).expect("cannot read program");

    let t_boot = Instant::now();
    // new_core + an explicit stdlib load keeps us off the filesystem-dependent
    // module catalogue; the phone has no writable XDG config dir.
    let metta = Metta::new(None);
    let boot_ms = t_boot.elapsed().as_millis();

    let t_run = Instant::now();
    let parser = SExprParser::new(program.as_str());
    let mut state = RunnerState::new_with_parser(&metta, Box::new(parser));

    let mut fuel: u64 = 0;
    let mut exhausted = false;
    let mut err: Option<String> = None;
    while !state.is_complete() {
        if fuel >= fuel_limit {
            exhausted = true;
            break;
        }
        if let Err(e) = state.run_step() {
            err = Some(e);
            break;
        }
        fuel += 1;
    }
    let run_ms = t_run.elapsed().as_millis();

    // Canonicalise: one line per result atom, results grouped per top-level
    // expression in the order the runner produced them.
    let mut raw = String::new();
    for (i, group) in state.current_results().iter().enumerate() {
        for atom in group.iter() {
            raw.push_str(&format!("{}\t{}\n", i, atom));
        }
    }
    let mut lines: Vec<&str> = raw.lines().collect();
    let n_results = lines.len();
    lines.sort_unstable();
    let sorted = lines.join("\n");

    // A cheap non-cryptographic hash too, purely to show that even the
    // platform's default hasher agrees (it is not seeded randomly here).
    let mut dh = DefaultHasher::new();
    raw.hash(&mut dh);

    let status = if let Some(ref e) = err {
        format!("ENGINE_ERROR: {}", e)
    } else if exhausted {
        "FUEL_EXHAUSTED".to_string()
    } else {
        "OK".to_string()
    };

    println!("program      {}", path);
    println!("arch         {}", std::env::consts::ARCH);
    println!("os           {}", std::env::consts::OS);
    println!("pointer_bits {}", usize::BITS);
    println!("status       {}", status);
    println!("fuel_limit   {}", fuel_limit);
    println!("fuel_used    {}", fuel);
    println!("n_results    {}", n_results);
    println!("boot_ms      {}", boot_ms);
    println!("run_ms       {}", run_ms);
    println!("raw_hash     {}", sha256_hex(&raw));
    println!("sorted_hash  {}", sha256_hex(&sorted));
    println!("default_hash {:016x}", dh.finish());
    println!("--- results ---");
    print!("{}", raw);
}
