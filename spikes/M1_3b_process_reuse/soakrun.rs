//! Does job N differ from job 1 inside ONE process?
//!
//! PORT_PLAN M1.3 requires a fresh process per job. WorkManager reuses the app
//! process, so this is the question that decides whether the platform model is
//! usable. M1.1c answered it for 40 repeats of ONE program; the real case is
//! many DIFFERENT jobs sharing a process, because every job advances the
//! process-global NEXT_VARIABLE_ID for the ones after it.
//!
//! Each job gets a FRESH Metta (so S60/A8 atomspace pollution is out of scope);
//! only the process is shared. Reports raw / canon / alpha digests so the
//! normalisations built in M1.1c can be tested against the real usage pattern.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};
use std::collections::HashMap;

fn sha8(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    format!("{:x}", h.finalize())[..16].to_string()
}

/// Renumber `$name#id` by first appearance: strips process history, keeps
/// structure. Mirrors harness/canon.py::canon.
fn canon(t: &str) -> String {
    renumber(t, false)
}
/// Renumber EVERY variable by first appearance: alpha-equivalence.
fn canon_alpha(t: &str) -> String {
    renumber(t, true)
}

fn renumber(t: &str, all_vars: bool) -> String {
    let mut map: HashMap<String, usize> = HashMap::new();
    let mut out = String::with_capacity(t.len());
    let b: Vec<char> = t.chars().collect();
    let mut i = 0;
    while i < b.len() {
        if b[i] != '$' {
            out.push(b[i]);
            i += 1;
            continue;
        }
        let start = i;
        i += 1;
        while i < b.len() && !b[i].is_whitespace() && b[i] != '(' && b[i] != ')' {
            i += 1;
        }
        let tok: String = b[start..i].iter().collect();
        let has_id = tok.contains('#');
        if !all_vars && !has_id {
            out.push_str(&tok);           // canon touches only id-bearing vars
            continue;
        }
        let n = map.len() + 1;
        let k = *map.entry(tok.clone()).or_insert(n);
        if all_vars {
            out.push_str(&format!("$v{}", k));
        } else {
            let base = tok.split('#').next().unwrap();
            out.push_str(&format!("{}#{}", base, k));
        }
    }
    out
}

fn run_one(path: &str, fuel_limit: u64) -> String {
    let program = std::fs::read_to_string(path).unwrap_or_default();
    let metta = Metta::new(None);
    let parser = SExprParser::new(program.as_str());
    let mut state = RunnerState::new_with_parser(&metta, Box::new(parser));
    let mut fuel: u64 = 0;
    while !state.is_complete() {
        if fuel >= fuel_limit {
            break;
        }
        if state.run_step().is_err() {
            break;
        }
        fuel += 1;
    }
    let mut raw = String::new();
    for (i, group) in state.current_results().iter().enumerate() {
        for atom in group.iter() {
            raw.push_str(&format!("{}\t{}\n", i, atom));
        }
    }
    format!("fuel={}\n{}", fuel, raw)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!("usage: soakrun <fuel> <prog.metta>...");
        std::process::exit(2);
    }
    let fuel: u64 = args[1].parse().unwrap();
    let progs = &args[2..];
    println!("pos\tprogram\traw\tcanon\talpha");
    for (pos, p) in progs.iter().enumerate() {
        let out = run_one(p, fuel);
        println!(
            "{}\t{}\t{}\t{}\t{}",
            pos,
            std::path::Path::new(p).file_name().unwrap().to_string_lossy(),
            sha8(&out),
            sha8(&canon(&out)),
            sha8(&canon_alpha(&out))
        );
    }
}
