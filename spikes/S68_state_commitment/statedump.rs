use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
fn mask_addr(s:&str)->String{let mut o=String::new();let b=s.as_bytes();let mut i=0;
 while i<b.len(){ if b[i]==b'0'&&i+1<b.len()&&b[i+1]==b'x'{i+=2;while i<b.len()&&(b[i] as char).is_ascii_hexdigit(){i+=1}o.push_str("0xADDR")}else{o.push(b[i] as char);i+=1}} o}
fn mask_vars(s:&str)->String{let mut o=String::new();let mut r=s;
 while let Some(p)=r.find("Variables({"){o.push_str(&r[..p+11]);let t=&r[p+11..];
  if let Some(e)=t.find("})"){let mut v:Vec<&str>=t[..e].split(", ").collect();v.sort_unstable();
   o.push_str(&v.join(", "));o.push_str("})");r=&t[e+2..];}else{o.push_str(t);r="";}}
 o.push_str(r);o}
fn mask_ids(s:&str)->String{let mut o=String::new();let mut r=s;
 while let Some(p)=r.find("id: "){o.push_str(&r[..p+4]);let t=&r[p+4..];
  let e=t.find(|c:char|!c.is_ascii_digit()).unwrap_or(t.len());o.push_str("N");r=&t[e..];}
 o.push_str(r);o}
fn main(){
    let src=std::fs::read_to_string(std::env::args().nth(1).unwrap()).unwrap();
    let m=Metta::new(None);
    let mut st=RunnerState::new_with_parser(&m,Box::new(SExprParser::new(src.as_str())));
    let nstep: u32 = std::env::var("NSTEP").ok().and_then(|s| s.parse().ok()).unwrap_or(120); let mut n=0u32; let mut out=String::new();
    while !st.is_complete(){ if st.run_step().is_err(){break} n+=1; if n>nstep {break}
        out.push_str(&mask_vars(&mask_ids(&mask_addr(&format!("{:?}\n",st))))); }
    print!("{out}");
}
