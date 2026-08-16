//! S68 — is an interpreter-STATE commitment reachable?
//!
//! S65's commitment used `current_results()` — emitted output, not state. An
//! attacker forged its root in 6 lines of Python without running hyperon,
//! because 100% of the leaf content was "()\n" repeated. The rebuild target is
//! `Debug for RunnerState` (mod.rs:527-534), which exposes `interpreter_state`
//! including the plan stack and changes on ~100% of steps.
//!
//! Two known contaminants: raw code pointers (`ret: 0x...`) and
//! `Variables({...})` hash-set ordering. This measures whether either or both
//! still block a reproducible state commitment, at three levels of masking.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};

fn h(s: &str) -> String {
    let mut d = Sha256::new(); d.update(s.as_bytes());
    d.finalize().iter().take(8).map(|b| format!("{b:02x}")).collect()
}
/// mask every 0x… hex literal
fn mask_addr(s: &str) -> String {
    let mut o = String::with_capacity(s.len()); let b = s.as_bytes(); let mut i = 0;
    while i < b.len() {
        if b[i] == b'0' && i + 1 < b.len() && b[i+1] == b'x' {
            i += 2; while i < b.len() && (b[i] as char).is_ascii_hexdigit() { i += 1 }
            o.push_str("0xADDR");
        } else { o.push(b[i] as char); i += 1 }
    }
    o
}
/// additionally sort the contents of every Variables({...}) set
fn mask_vars(s: &str) -> String {
    let mut o = String::new(); let mut rest = s;
    while let Some(p) = rest.find("Variables({") {
        o.push_str(&rest[..p + 11]);
        let tail = &rest[p + 11..];
        if let Some(e) = tail.find("})") {
            let mut items: Vec<&str> = tail[..e].split(", ").collect();
            items.sort_unstable();
            o.push_str(&items.join(", ")); o.push_str("})");
            rest = &tail[e + 2..];
        } else { o.push_str(tail); rest = ""; }
    }
    o.push_str(rest); o
}

/// additionally mask `id: N` — the NEXT_VARIABLE_ID value baked into content
fn mask_ids(s: &str) -> String {
    let mut o = String::new(); let mut rest = s;
    while let Some(p) = rest.find("id: ") {
        o.push_str(&rest[..p + 4]);
        let t = &rest[p + 4..];
        let e = t.find(|c: char| !c.is_ascii_digit()).unwrap_or(t.len());
        o.push_str("N"); rest = &t[e..];
    }
    o.push_str(rest); o
}

fn run(src: &str, mode: u8) -> String {
    let m = Metta::new(None);
    let mut st = RunnerState::new_with_parser(&m, Box::new(SExprParser::new(src)));
    let mut acc = String::new();
    let mut n = 0u32;
    while !st.is_complete() {
        if st.run_step().is_err() { break }
        n += 1;
        if n > 400 { break }                 // bounded: this is a digest test
        let d = format!("{:?}", st);
        acc.push_str(&match mode { 0 => d, 1 => mask_addr(&d), 2 => mask_vars(&mask_addr(&d)),
            _ => mask_vars(&mask_ids(&mask_addr(&d))) });
    }
    h(&acc)
}

fn main() {
    let src = std::fs::read_to_string(std::env::args().nth(1).expect("prog")).unwrap();
    for (mode, name) in [(0u8, "raw Debug"), (1, "+ addresses masked"), (2, "+ Variables sorted"), (3, "+ variable ids masked")] {
        let mut set = std::collections::BTreeMap::new();
        for _ in 0..5 { *set.entry(run(&src, mode)).or_insert(0) += 1; }
        println!("  {:<22} {} distinct / 5   {}", name, set.len(),
                 if set.len() == 1 { "REPRODUCIBLE" } else { "no" });
    }
}
