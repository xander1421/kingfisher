// What does the trie actually return per candidate?
use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
fn main(){
    let m = Metta::new(None);
    let p = "!(intersection-atom (A $x B $y C) ($y C A $x B))";
    let mut st = RunnerState::new_with_parser(&m, Box::new(SExprParser::new(p)));
    while !st.is_complete(){ if st.run_step().is_err(){break} }
    for g in st.current_results(){ for a in g.iter(){ println!("{}", a); } }
}
