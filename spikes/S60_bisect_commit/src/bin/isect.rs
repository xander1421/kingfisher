// Verify the intersection-atom claim precisely: is the result set merely
// REORDERED between runs, or does its CARDINALITY change? Ordering is a
// cosmetic nuisance; changing cardinality means results are dropped or added
// depending on heap layout, which is a correctness bug.
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
fn main() {
    let src = std::env::args().nth(1).unwrap();
    let m = Metta::new(None);
    let mut st = RunnerState::new_with_parser(&m, Box::new(SExprParser::new(src.as_str())));
    while !st.is_complete() { if st.run_step().is_err() { break } }
    for g in st.current_results() {
        for a in g.iter() {
            let s = a.to_string();
            // count top-level children of the returned expression
            let inner = s.trim_start_matches('(').trim_end_matches(')');
            let n = if inner.trim().is_empty() { 0 } else {
                let mut d=0; let mut c=1;
                for ch in inner.chars() {
                    match ch { '('=>d+=1, ')'=>d-=1, ' ' if d==0 => c+=1, _=>{} }
                }
                c
            };
            println!("card={} body={}", n, s);
        }
    }
}
