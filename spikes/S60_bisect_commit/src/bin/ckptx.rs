//! ADVERSARIAL PROBE (not part of S65). Same instrumentation as ckpt.rs but
//! dumps the actual leaf CONTENT so the "reproducible root" claim can be
//! inspected rather than trusted. Also reports leaf-content byte totals.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};

fn h(parts: &[&[u8]]) -> [u8; 32] {
    let mut d = Sha256::new();
    for p in parts { d.update(p) }
    d.finalize().into()
}
fn hex(b: &[u8]) -> String { b.iter().take(8).map(|x| format!("{x:02x}")).collect() }

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

struct Out { steps: u64, root: [u8;32], inner: usize, contents: Vec<(u64, String)> }

fn run(src: &str) -> Out {
    let m = Metta::new(None);
    let mut st = RunnerState::new_with_parser(&m, Box::new(SExprParser::new(src)));
    let mut steps = 0u64;
    let mut prev_len = usize::MAX;
    let mut leaves: Vec<[u8;32]> = Vec::new();
    let mut contents: Vec<(u64, String)> = Vec::new();
    while !st.is_complete() {
        if st.run_step().is_err() { break }
        steps += 1;
        let n = st.current_results().len();
        if n != prev_len {
            prev_len = n;
            let mut s = String::new();
            for g in st.current_results() { for a in g.iter() { s.push_str(&a.to_string()); s.push('\n') } }
            leaves.push(h(&[&steps.to_le_bytes(), s.as_bytes()]));
            contents.push((steps, s));
        }
    }
    let (root, inner) = merkle(&leaves);
    Out { steps, root, inner, contents }
}

fn main() {
    let path = std::env::args().nth(1).expect("usage: ckptx <prog.metta> [runs] [--dump]");
    let runs: usize = std::env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(3);
    let dump = std::env::args().any(|a| a == "--dump");
    let src = match std::fs::read_to_string(&path) { Ok(s) => s, Err(e) => { println!("{path}\tREADERR\t{e}"); return } };
    let mut roots = std::collections::BTreeMap::new();
    let mut last: Option<Out> = None;
    for _ in 0..runs {
        let o = run(&src);
        *roots.entry(hex(&o.root)).or_insert(0) += 1;
        last = Some(o);
    }
    let o = last.unwrap();
    let n = o.contents.len();
    // how many leaves have content identical to the previous leaf's content?
    let mut dup_prev = 0usize;
    for i in 1..n { if o.contents[i].1 == o.contents[i-1].1 { dup_prev += 1 } }
    let distinct: std::collections::BTreeSet<&String> = o.contents.iter().map(|(_, s)| s).collect();
    let content_bytes: usize = o.contents.iter().map(|(_, s)| s.len()).sum();
    let empty = o.contents.iter().filter(|(_, s)| s.is_empty()).count();
    println!("{path}\tsteps={}\tckpt={n}\tdistinct_content={}\tdup_of_prev={dup_prev}\tempty={empty}\tleafhash_bytes={}\tcontent_bytes={content_bytes}\tinner={}\troots={}\t{}",
        o.steps, distinct.len(), n*32, o.inner, roots.len(),
        if roots.len()==1 {"REPRO"} else {"NONREPRO"});
    if dump {
        for (i, (step, s)) in o.contents.iter().enumerate() {
            println!("  leaf[{i}] step={step} len={} content={:?}", s.len(),
                if s.len() > 300 { format!("{}...<{}B>", &s[..300], s.len()) } else { s.clone() });
        }
    }
}
