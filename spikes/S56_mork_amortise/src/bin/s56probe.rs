//! Does metta_calculus(1) still do work on a resident space, or has the space
//! reached a fixed point? If it is a no-op, S56's "99.9% amortisable" is
//! timing an empty function and the number is worthless.
fn main() {
    let src = std::fs::read(std::env::args().nth(1).unwrap()).unwrap();
    let mut s = mork::space::Space::new();
    s.add_all_sexpr(&src).unwrap();
    let mut prev = String::new();
    for step in 0..6 {
        let mut o: Vec<u8> = Vec::new();
        let n = s.dump_all_sexpr(&mut o).unwrap();
        let cur = String::from_utf8_lossy(&o).to_string();
        println!("step {}: {} exprs, {} bytes, changed={}", step, n, o.len(), cur != prev);
        prev = cur;
        s.metta_calculus(1);
    }
}
