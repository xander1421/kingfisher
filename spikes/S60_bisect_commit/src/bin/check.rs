// Did reusing one Metta across iterations pollute the space and abort the run?
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
fn steps(m: &Metta, src: &str) -> (u64, usize) {
    let mut st = RunnerState::new_with_parser(m, Box::new(SExprParser::new(src)));
    let mut n = 0u64;
    while !st.is_complete() { if st.run_step().is_err() { break } n += 1; }
    (n, st.current_results().len())
}
fn main() {
    let src = std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
    let shared = Metta::new(None);
    println!("SHARED Metta (what S60 did):");
    for i in 0..3 { let (n,r) = steps(&shared, &src); println!("  iter {i}: {n} steps, {r} results"); }
    println!("FRESH Metta each iteration (correct):");
    for i in 0..3 { let m = Metta::new(None); let (n,r) = steps(&m, &src); println!("  iter {i}: {n} steps, {r} results"); }
}
