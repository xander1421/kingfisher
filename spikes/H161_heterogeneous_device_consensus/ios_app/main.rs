// Kingfisher F001 + F002 second-language verifier.
// rustc -O trace_verifier.rs  (zero crates)
// F001_PROBE_V1 and F002_TWO_BOUND. Not a MeTTa interpreter. Not F003.

mod sha256;

use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

const MAGIC: &[u8; 4] = b"KF01";
const MANIFEST_ID: &str = "F001.manifest.v1";

fn fuel_cost(rule: &str) -> Option<u64> {
    match rule {
        "PARSE" => Some(10),
        "BIND_SPACE" => Some(10),
        "UNIFY" => Some(100),
        "SUBSTITUTE" => Some(80),
        "CANONICALIZE" => Some(200),
        _ => None,
    }
}

#[derive(Clone, Debug, PartialEq)]
enum Term {
    Atom(String),
    List(Vec<Term>),
}

impl Term {
    fn is_var(&self) -> bool {
        matches!(self, Term::Atom(s) if s.starts_with('$'))
    }
    fn as_var(&self) -> Option<&str> {
        match self {
            Term::Atom(s) if s.starts_with('$') => Some(s.as_str()),
            _ => None,
        }
    }
}

fn parse_sexpr(src: &str) -> Result<Term, String> {
    let mut toks: Vec<String> = Vec::new();
    let b = src.trim().as_bytes();
    let mut i = 0;
    while i < b.len() {
        if b[i].is_ascii_whitespace() {
            i += 1;
            continue;
        }
        if b[i] == b'(' || b[i] == b')' {
            toks.push((b[i] as char).to_string());
            i += 1;
            continue;
        }
        let start = i;
        while i < b.len() && !b[i].is_ascii_whitespace() && b[i] != b'(' && b[i] != b')' {
            i += 1;
        }
        toks.push(String::from_utf8_lossy(&b[start..i]).into_owned());
    }
    fn read(toks: &[String], pos: usize) -> Result<(Term, usize), String> {
        if pos >= toks.len() {
            return Err("unexpected end of s-expression".into());
        }
        if toks[pos] == "(" {
            let mut items = Vec::new();
            let mut p = pos + 1;
            while p < toks.len() && toks[p] != ")" {
                let (item, np) = read(toks, p)?;
                items.push(item);
                p = np;
            }
            if p >= toks.len() {
                return Err("unclosed list".into());
            }
            Ok((Term::List(items), p + 1))
        } else if toks[pos] == ")" {
            Err("unexpected ')'".into())
        } else {
            Ok((Term::Atom(toks[pos].clone()), pos + 1))
        }
    }
    let (term, pos) = read(&toks, 0)?;
    if pos != toks.len() {
        return Err("trailing tokens in s-expression".into());
    }
    Ok(term)
}

fn pretty(term: &Term) -> String {
    match term {
        Term::Atom(s) => s.clone(),
        Term::List(xs) => {
            let inner: Vec<String> = xs.iter().map(pretty).collect();
            format!("({})", inner.join(" "))
        }
    }
}

fn deref<'a>(t: &'a Term, sigma: &'a BTreeMap<String, Term>) -> &'a Term {
    let mut cur = t;
    while let Some(v) = cur.as_var() {
        if let Some(n) = sigma.get(v) {
            cur = n;
        } else {
            break;
        }
    }
    cur
}

fn occurs(v: &str, t: &Term, sigma: &BTreeMap<String, Term>) -> bool {
    let t = deref(t, sigma);
    if let Some(w) = t.as_var() {
        return w == v;
    }
    if let Term::List(xs) = t {
        return xs.iter().any(|x| occurs(v, x, sigma));
    }
    false
}

fn apply_subst(t: &Term, sigma: &BTreeMap<String, Term>) -> Term {
    let t = deref(t, sigma);
    match t {
        Term::Atom(s) => Term::Atom(s.clone()),
        Term::List(xs) => Term::List(xs.iter().map(|x| apply_subst(x, sigma)).collect()),
    }
}

fn unify(a: &Term, b: &Term, sigma: &mut BTreeMap<String, Term>) -> bool {
    let a = apply_subst(a, sigma);
    let b = apply_subst(b, sigma);
    if let Some(v) = a.as_var() {
        if a == b {
            return true;
        }
        if occurs(v, &b, sigma) {
            return false;
        }
        sigma.insert(v.to_string(), b);
        return true;
    }
    if let Some(v) = b.as_var() {
        if occurs(v, &a, sigma) {
            return false;
        }
        sigma.insert(v.to_string(), a);
        return true;
    }
    match (&a, &b) {
        (Term::Atom(x), Term::Atom(y)) => x == y,
        (Term::List(xs), Term::List(ys)) if xs.len() == ys.len() => {
            xs.iter().zip(ys.iter()).all(|(x, y)| unify(x, y, sigma))
        }
        _ => false,
    }
}

fn pretty_bindings(sigma: &BTreeMap<String, Term>) -> String {
    let parts: Vec<String> = sigma
        .iter()
        .map(|(k, _)| format!("{}:{}", k, pretty(&apply_subst(&Term::Atom(k.clone()), sigma))))
        .collect();
    format!("{{{}}}", parts.join(","))
}

fn alpha_normalize(term: &Term) -> Term {
    let mut map: BTreeMap<String, String> = BTreeMap::new();
    fn walk(t: &Term, map: &mut BTreeMap<String, String>) -> Term {
        if let Some(v) = t.as_var() {
            if !map.contains_key(v) {
                let n = format!("${}", map.len());
                map.insert(v.to_string(), n);
            }
            return Term::Atom(map.get(v).unwrap().clone());
        }
        match t {
            Term::Atom(s) => Term::Atom(s.clone()),
            Term::List(xs) => Term::List(xs.iter().map(|x| walk(x, map)).collect()),
        }
    }
    walk(term, &mut map)
}

#[derive(Clone, Debug)]
struct Step {
    i: i64,
    rule: String,
    redex: String,
    contractum: String,
    fuel: u64,
}

#[derive(Clone, Debug)]
struct Witness {
    spec: String,
    corpus_root: String,
    manifest_id: String,
    fuel_table_id: String,
    steps: Vec<Step>,
    result: String,
    fuel_total: u64,
}

#[derive(Debug)]
enum J {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<J>),
    Obj(BTreeMap<String, J>),
}

struct Parser<'a> {
    s: &'a [u8],
    i: usize,
}

impl<'a> Parser<'a> {
    fn new(s: &'a [u8]) -> Self {
        Self { s, i: 0 }
    }
    fn peek(&self) -> Option<u8> {
        self.s.get(self.i).copied()
    }
    fn bump(&mut self) -> Option<u8> {
        let c = self.peek()?;
        self.i += 1;
        Some(c)
    }
    fn skip_ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) {
            self.i += 1;
        }
    }
    fn parse(&mut self) -> Result<J, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'n') => {
                self.expect(b"null")?;
                Ok(J::Null)
            }
            Some(b't') => {
                self.expect(b"true")?;
                Ok(J::Bool(true))
            }
            Some(b'f') => {
                self.expect(b"false")?;
                Ok(J::Bool(false))
            }
            Some(b'"') => Ok(J::Str(self.parse_string()?)),
            Some(b'[') => self.parse_arr(),
            Some(b'{') => self.parse_obj(),
            Some(b'-') | Some(b'0'..=b'9') => self.parse_num(),
            _ => Err("json: unexpected token".into()),
        }
    }
    fn expect(&mut self, lit: &[u8]) -> Result<(), String> {
        for &c in lit {
            if self.bump() != Some(c) {
                return Err("json: bad literal".into());
            }
        }
        Ok(())
    }
    fn parse_string(&mut self) -> Result<String, String> {
        if self.bump() != Some(b'"') {
            return Err("json: expected string".into());
        }
        let mut out = String::new();
        loop {
            match self.bump() {
                None => return Err("json: unterminated string".into()),
                Some(b'"') => return Ok(out),
                Some(b'\\') => match self.bump() {
                    Some(b'"') => out.push('"'),
                    Some(b'\\') => out.push('\\'),
                    Some(b'/') => out.push('/'),
                    Some(b'n') => out.push('\n'),
                    Some(b't') => out.push('\t'),
                    Some(b'r') => out.push('\r'),
                    _ => return Err("json: bad escape".into()),
                },
                Some(c) => out.push(c as char),
            }
        }
    }
    fn parse_num(&mut self) -> Result<J, String> {
        let start = self.i;
        if self.peek() == Some(b'-') {
            self.i += 1;
        }
        while matches!(self.peek(), Some(b'0'..=b'9')) {
            self.i += 1;
        }
        if self.peek() == Some(b'.') {
            self.i += 1;
            while matches!(self.peek(), Some(b'0'..=b'9')) {
                self.i += 1;
            }
        }
        let s = std::str::from_utf8(&self.s[start..self.i]).unwrap();
        Ok(J::Num(s.parse().map_err(|_| "json: bad number")?))
    }
    fn parse_arr(&mut self) -> Result<J, String> {
        self.bump();
        let mut xs = Vec::new();
        self.skip_ws();
        if self.peek() == Some(b']') {
            self.bump();
            return Ok(J::Arr(xs));
        }
        loop {
            xs.push(self.parse()?);
            self.skip_ws();
            match self.bump() {
                Some(b']') => return Ok(J::Arr(xs)),
                Some(b',') => continue,
                _ => return Err("json: bad array".into()),
            }
        }
    }
    fn parse_obj(&mut self) -> Result<J, String> {
        self.bump();
        let mut m = BTreeMap::new();
        self.skip_ws();
        if self.peek() == Some(b'}') {
            self.bump();
            return Ok(J::Obj(m));
        }
        loop {
            self.skip_ws();
            let k = self.parse_string()?;
            self.skip_ws();
            if self.bump() != Some(b':') {
                return Err("json: expected ':'".into());
            }
            let v = self.parse()?;
            m.insert(k, v);
            self.skip_ws();
            match self.bump() {
                Some(b'}') => return Ok(J::Obj(m)),
                Some(b',') => continue,
                _ => return Err("json: bad object".into()),
            }
        }
    }
}

fn j_str<'a>(obj: &'a BTreeMap<String, J>, k: &str) -> Result<&'a str, String> {
    match obj.get(k) {
        Some(J::Str(s)) => Ok(s),
        _ => Err(format!("missing string {k}")),
    }
}
fn j_int(obj: &BTreeMap<String, J>, k: &str) -> Result<i64, String> {
    match obj.get(k) {
        Some(J::Num(n)) => Ok(*n as i64),
        _ => Err(format!("missing number {k}")),
    }
}

fn json_escape(s: &str) -> String {
    let mut out = String::from("\"");
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(c),
        }
    }
    out.push('"');
    out
}

fn dump_json(j: &J) -> String {
    match j {
        J::Null => "null".into(),
        J::Bool(true) => "true".into(),
        J::Bool(false) => "false".into(),
        J::Num(n) => {
            if n.fract() == 0.0 {
                format!("{}", *n as i64)
            } else {
                format!("{n}")
            }
        }
        J::Str(s) => json_escape(s),
        J::Arr(xs) => {
            let inner: Vec<String> = xs.iter().map(dump_json).collect();
            format!("[{}]", inner.join(","))
        }
        J::Obj(m) => {
            let inner: Vec<String> = m
                .iter()
                .map(|(k, v)| format!("{}:{}", json_escape(k), dump_json(v)))
                .collect();
            format!("{{{}}}", inner.join(","))
        }
    }
}

fn parse_json_value(raw: &[u8]) -> Result<J, String> {
    let mut p = Parser::new(raw);
    p.parse()
}

fn parse_witness(raw: &[u8]) -> Result<Witness, String> {
    let v = parse_json_value(raw)?;
    let J::Obj(o) = &v else {
        return Err("witness not object".into());
    };
    let J::Arr(steps_j) = o.get("steps").ok_or("missing steps")? else {
        return Err("steps not array".into());
    };
    let mut steps = Vec::new();
    for s in steps_j {
        let J::Obj(so) = s else {
            return Err("step not object".into());
        };
        steps.push(Step {
            i: j_int(so, "i")?,
            rule: j_str(so, "rule")?.to_string(),
            redex: j_str(so, "redex")?.to_string(),
            contractum: j_str(so, "contractum")?.to_string(),
            fuel: j_int(so, "fuel")? as u64,
        });
    }
    Ok(Witness {
        spec: j_str(o, "spec")?.to_string(),
        corpus_root: j_str(o, "corpus_root")?.to_string(),
        manifest_id: j_str(o, "manifest_id")?.to_string(),
        fuel_table_id: j_str(o, "fuel_table_id")?.to_string(),
        steps,
        result: j_str(o, "result")?.to_string(),
        fuel_total: j_int(o, "fuel_total")? as u64,
    })
}

fn canonical_witness_bytes(raw: &[u8]) -> Result<Vec<u8>, String> {
    let v = parse_json_value(raw)?;
    let mut dumped = dump_json(&v);
    dumped.push('\n');
    let rebuilt = dumped.into_bytes();
    if rebuilt.as_slice() != raw {
        return Err("WITNESS_NOT_CANONICAL: re-canonicalizing changed bytes".into());
    }
    Ok(rebuilt)
}

fn strip_lf(mut b: Vec<u8>) -> Vec<u8> {
    if b.ends_with(&[b'\n']) {
        b.pop();
    }
    b
}

fn read_file(p: &Path) -> Result<Vec<u8>, String> {
    fs::read(p).map_err(|_| format!("MISSING_FILE: {}", p.display()))
}

fn read_line(p: &Path) -> Result<String, String> {
    let b = strip_lf(read_file(p)?);
    String::from_utf8(b).map_err(|_| "not utf-8".into())
}

fn accepted_digest(
    corpus_root: &str,
    manifest_id: &str,
    query: &str,
    result: &str,
    fuel: u64,
    witness: &[u8],
) -> String {
    let cr = corpus_root.as_bytes();
    let mid = manifest_id.as_bytes();
    let q = query.as_bytes();
    let r = result.as_bytes();
    let wh = sha256::sha256(witness);
    let mut payload = Vec::new();
    payload.extend_from_slice(MAGIC);
    payload.extend_from_slice(&(cr.len() as u32).to_be_bytes());
    payload.extend_from_slice(cr);
    payload.extend_from_slice(&(mid.len() as u32).to_be_bytes());
    payload.extend_from_slice(mid);
    payload.extend_from_slice(&(q.len() as u32).to_be_bytes());
    payload.extend_from_slice(q);
    payload.extend_from_slice(&(r.len() as u32).to_be_bytes());
    payload.extend_from_slice(r);
    payload.extend_from_slice(&fuel.to_be_bytes());
    payload.extend_from_slice(&wh);
    sha256::hex_encode(&sha256::sha256(&payload))
}

fn fixture_class(root: &Path) -> &'static str {
    if root.join("F001.corpus.bin").is_file() {
        "F001"
    } else if root.join("F002.corpus.bin").is_file() {
        "F002"
    } else {
        "UNKNOWN"
    }
}

fn parse_corpus(raw: &[u8]) -> Result<(Vec<(String, String)>, BTreeMap<String, String>), String> {
    let text = String::from_utf8(strip_lf(raw.to_vec())).map_err(|_| "corpus not utf8")?;
    let mut cites = Vec::new();
    let mut verdicts = BTreeMap::new();
    for line in text.split('\n') {
        let line = line.trim();
        if let Some(rest) = line.strip_prefix("(cites ") {
            if let Some(inner) = rest.strip_suffix(')') {
                let mut it = inner.split_whitespace();
                let a = it.next().ok_or("cites missing src")?;
                let b = it.next().ok_or("cites missing dst")?;
                if it.next().is_some() {
                    return Err("cites extra tokens".into());
                }
                cites.push((a.to_string(), b.to_string()));
            }
        } else if let Some(rest) = line.strip_prefix("(verdict ") {
            if let Some(inner) = rest.strip_suffix(')') {
                let mut it = inner.split_whitespace();
                let a = it.next().ok_or("verdict missing entity")?;
                let v = it.next().ok_or("verdict missing colour")?;
                verdicts.insert(a.to_string(), v.to_string());
            }
        }
    }
    Ok((cites, verdicts))
}

fn derive_hits(
    cites: &[(String, String)],
    verdicts: &BTreeMap<String, String>,
) -> BTreeSet<(String, String)> {
    let mut out: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    let mut inc: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    for (a, b) in cites {
        out.entry(a.clone()).or_default().insert(b.clone());
        inc.entry(b.clone()).or_default().insert(a.clone());
    }
    let mut hits = BTreeSet::new();
    for (z, ys) in &out {
        for y in ys {
            if verdicts.get(y).map(|s| s.as_str()) == Some("RED") {
                if let Some(xs) = inc.get(z) {
                    for x in xs {
                        hits.insert((x.clone(), y.clone()));
                    }
                }
            }
        }
    }
    hits
}

fn result_of(hits: &BTreeSet<(String, String)>) -> String {
    let inner: Vec<String> = hits
        .iter()
        .map(|(x, y)| format!("(hit {x} {y})"))
        .collect();
    format!("({})", inner.join(" "))
}

fn hits_from_result(result: &str) -> Result<BTreeSet<(String, String)>, String> {
    let term = parse_sexpr(result)?;
    let Term::List(xs) = term else {
        return Err("RESULT_NOT_DERIVED: result is not a hit list".into());
    };
    let mut out = BTreeSet::new();
    for item in xs {
        match item {
            Term::List(parts)
                if parts.len() == 3 && matches!(&parts[0], Term::Atom(s) if s == "hit") =>
            {
                out.insert((pretty(&parts[1]), pretty(&parts[2])));
            }
            _ => return Err("RESULT_NOT_DERIVED: not a (hit x y) list".into()),
        }
    }
    Ok(out)
}

fn manifest_id_of(root: &Path, prefix: &str, fallback: &str) -> String {
    let p = root.join(format!("{prefix}.manifest.json"));
    let Ok(raw) = read_file(&p) else {
        return fallback.to_string();
    };
    let Ok(v) = parse_json_value(&raw) else {
        return fallback.to_string();
    };
    if let J::Obj(o) = v {
        if let Ok(s) = j_str(&o, "manifest_id") {
            return s.to_string();
        }
        if let Ok(s) = j_str(&o, "id") {
            return s.to_string();
        }
    }
    fallback.to_string()
}

fn check_fuel_v1(w: &Witness, fuel_declared: u64) -> Result<u64, String> {
    if w.fuel_table_id != "FT_METTA_CORE_V1" {
        return Err("FUEL_TABLE_MISMATCH".into());
    }
    if w.steps.len() != 5 {
        return Err(format!("BAD_STEP_COUNT: expected 5, got {}", w.steps.len()));
    }
    let required = ["PARSE", "BIND_SPACE", "UNIFY", "SUBSTITUTE", "CANONICALIZE"];
    let mut derived = 0u64;
    for (i, exp) in required.iter().enumerate() {
        let s = &w.steps[i];
        if s.i != i as i64 {
            return Err(format!("STEP_INDEX: step {i} has i={}", s.i));
        }
        let Some(cost) = fuel_cost(&s.rule) else {
            return Err(format!("ILLEGAL_OPCODE: step {i} op '{}'", s.rule));
        };
        if s.rule != *exp {
            return Err(format!("STEP_SHAPE: step {i} wanted {exp}, got {}", s.rule));
        }
        if s.fuel != cost {
            return Err(format!(
                "FUEL_DIVERGENCE: step {i}: op '{}' declared {} fuel, table dictates {cost}",
                s.rule, s.fuel
            ));
        }
        derived += s.fuel;
    }
    if derived != w.fuel_total {
        return Err(format!(
            "FUEL_TOTAL_MISMATCH: derived sum = {derived}, declared witness fuel_total = {}",
            w.fuel_total
        ));
    }
    if derived != fuel_declared {
        return Err(format!(
            "FUEL_FILE_MISMATCH: derived sum = {derived}, declared fixture fuel = {fuel_declared}"
        ));
    }
    Ok(derived)
}

fn verify_f002(root: &Path) -> Result<(u64, String, String), String> {
    let prefix = "F002";
    let corpus_bin = read_file(&root.join(format!("{prefix}.corpus.bin")))?;
    let corpus_root_file = read_line(&root.join(format!("{prefix}.corpus_root")))?;
    let recomputed_root = sha256::hex_encode(&sha256::sha256(&corpus_bin));
    if recomputed_root != corpus_root_file {
        return Err(format!(
            "CORPUS_ROOT_MISMATCH: declared {corpus_root_file}, recomputed {recomputed_root}"
        ));
    }
    let query = read_line(&root.join(format!("{prefix}.query")))?;
    let fuel_declared: u64 = read_line(&root.join(format!("{prefix}.fuel")))?
        .parse()
        .map_err(|_| "bad fuel file")?;
    let expected = read_line(&root.join(format!("{prefix}.accepted_digest")))?;
    let raw_w = read_file(&root.join(format!("{prefix}.witness.json")))?;
    let _ = canonical_witness_bytes(&raw_w)?;
    let w = parse_witness(&raw_w)?;
    if w.spec != "kingfisher.trace/v1" {
        return Err(format!("BAD_SPEC: {}", w.spec));
    }
    if w.corpus_root != corpus_root_file {
        return Err("WITNESS_CORPUS_ROOT_MISMATCH".into());
    }
    let mid = manifest_id_of(root, prefix, "F002.manifest.v1");
    if w.manifest_id != mid {
        return Err(format!("MANIFEST_MISMATCH: {}", w.manifest_id));
    }
    let derived_fuel = check_fuel_v1(&w, fuel_declared)?;

    let (cites, verdicts) = parse_corpus(&corpus_bin)?;
    let derived = derive_hits(&cites, &verdicts);
    let claimed = hits_from_result(&w.result)?;
    let legal = result_of(&derived);
    if derived != claimed || w.result != legal {
        return Err(format!(
            "RESULT_NOT_DERIVED: derived {} claimed {} want {legal}",
            derived.len(),
            claimed.len()
        ));
    }
    for s in &w.steps {
        if s.rule != "UNIFY" {
            continue;
        }
        if let Some(rest) = s.contractum.strip_prefix("(n ") {
            if let Some(n_s) = rest.strip_suffix(')') {
                let n: i64 = n_s.parse().unwrap_or(-1);
                if n as usize != derived.len() {
                    return Err(format!(
                        "SEMANTIC_UNIFICATION_FAILURE: UNIFY (n {n}) != derived {}",
                        derived.len()
                    ));
                }
            }
        }
        if query.contains("(verdict $y RED)") && s.redex.contains("(verdict $y GREEN)") {
            return Err(
                "SEMANTIC_UNIFICATION_FAILURE: UNIFY redex GREEN vs query RED".into(),
            );
        }
    }
    if w.steps[0].redex != query || w.steps[0].contractum != query {
        return Err("PARSE_SEMANTICS: PARSE redex/contractum must equal query".into());
    }
    let want_space = format!("(space {corpus_root_file})");
    if w.steps[1].contractum != want_space {
        return Err(format!(
            "BIND_SEMANTICS: BIND_SPACE want {want_space}, got {}",
            w.steps[1].contractum
        ));
    }

    let digest = accepted_digest(&corpus_root_file, &mid, &query, &w.result, derived_fuel, &raw_w);
    if digest != expected {
        return Err(format!(
            "DIGEST_MISMATCH: computed: {digest}\n      expected: {expected}"
        ));
    }
    Ok((
        derived_fuel,
        sha256::hex_encode(&sha256::sha256(&raw_w)),
        digest,
    ))
}

fn verify(root: &Path) -> Result<(u64, String, String), String> {
    match fixture_class(root) {
        "F001" => verify_f001(root),
        "F002" => verify_f002(root),
        _ => Err(
            "WRONG_FIXTURE_CLASS: rust checker is F001_PROBE_V1 + F002_TWO_BOUND (no matching corpus.bin)".into(),
        ),
    }
}

fn verify_f001(root: &Path) -> Result<(u64, String, String), String> {
    let corpus_bin = read_file(&root.join("F001.corpus.bin"))?;
    let corpus_root_file = read_line(&root.join("F001.corpus_root"))?;
    let recomputed_root = sha256::hex_encode(&sha256::sha256(&corpus_bin));
    if recomputed_root != corpus_root_file {
        return Err(format!(
            "CORPUS_ROOT_MISMATCH: declared {corpus_root_file}, recomputed {recomputed_root}"
        ));
    }
    let query = read_line(&root.join("F001.query"))?;
    let fuel_declared: u64 = read_line(&root.join("F001.fuel"))?
        .parse()
        .map_err(|_| "bad fuel file")?;
    let expected = read_line(&root.join("F001.accepted_digest"))?;
    let raw_w = read_file(&root.join("F001.witness.json"))?;
    let _ = canonical_witness_bytes(&raw_w)?;
    let w = parse_witness(&raw_w)?;
    if w.spec != "kingfisher.trace/v1" {
        return Err(format!("BAD_SPEC: {}", w.spec));
    }
    if w.corpus_root != corpus_root_file {
        return Err("WITNESS_CORPUS_ROOT_MISMATCH".into());
    }
    if w.manifest_id != MANIFEST_ID {
        return Err(format!("MANIFEST_MISMATCH: {}", w.manifest_id));
    }
    if w.fuel_table_id != "FT_METTA_CORE_V1" {
        return Err("FUEL_TABLE_MISMATCH".into());
    }
    if w.steps.len() != 5 {
        return Err(format!("BAD_STEP_COUNT: expected 5, got {}", w.steps.len()));
    }
    let required = ["PARSE", "BIND_SPACE", "UNIFY", "SUBSTITUTE", "CANONICALIZE"];
    let mut derived = 0u64;
    for (i, exp) in required.iter().enumerate() {
        let s = &w.steps[i];
        if s.i != i as i64 {
            return Err(format!("STEP_INDEX: step {i} has i={}", s.i));
        }
        let Some(cost) = fuel_cost(&s.rule) else {
            return Err(format!("ILLEGAL_OPCODE: step {i} op '{}'", s.rule));
        };
        if s.rule != *exp {
            return Err(format!("STEP_SHAPE: step {i} wanted {exp}, got {}", s.rule));
        }
        if s.fuel != cost {
            return Err(format!(
                "FUEL_DIVERGENCE: step {i}: op '{}' declared {} fuel, table dictates {cost}",
                s.rule, s.fuel
            ));
        }
        derived += s.fuel;
    }
    if derived != w.fuel_total {
        return Err(format!(
            "FUEL_TOTAL_MISMATCH: derived sum = {derived}, declared witness fuel_total = {}",
            w.fuel_total
        ));
    }
    if derived != fuel_declared {
        return Err(format!(
            "FUEL_FILE_MISMATCH: derived sum = {derived}, declared fixture fuel = {fuel_declared}"
        ));
    }

    let fact_src = String::from_utf8(strip_lf(corpus_bin.clone())).map_err(|_| "corpus not utf8")?;
    let query_term = parse_sexpr(&query)?;
    let fact_term = parse_sexpr(&fact_src)?;
    let s0 = &w.steps[0];
    let s1 = &w.steps[1];
    let s2 = &w.steps[2];
    let s3 = &w.steps[3];
    let s4 = &w.steps[4];
    if s0.redex != query || s0.contractum != query {
        return Err("PARSE_SEMANTICS: PARSE redex/contractum must equal query".into());
    }
    if s1.redex != query || s1.contractum != fact_src {
        return Err("BIND_SEMANTICS: BIND_SPACE must bind corpus fact".into());
    }
    let mut sigma = BTreeMap::new();
    if !unify(&query_term, &fact_term, &mut sigma) {
        return Err("UNIFY_IMPOSSIBLE: query does not unify with corpus fact".into());
    }
    let legal_bindings = pretty_bindings(&sigma);
    if s2.redex != query || s2.contractum != legal_bindings {
        return Err(format!(
            "SEMANTIC_UNIFICATION_FAILURE: step 2 bindings do not match redex unification (want {legal_bindings}, got {})",
            s2.contractum
        ));
    }
    if s3.redex != "($p $q)" {
        return Err(format!("SUBSTITUTE_REDEX: {}", s3.redex));
    }
    let tmpl = parse_sexpr("($p $q)")?;
    let legal_subst = pretty(&apply_subst(&tmpl, &sigma));
    if s3.contractum != legal_subst {
        return Err(format!(
            "BINDINGS_NOT_DERIVED: SUBSTITUTE must apply unify(σ); want {legal_subst}, got {}",
            s3.contractum
        ));
    }
    let legal_canon = pretty(&alpha_normalize(&parse_sexpr(&legal_subst)?));
    if s4.redex != legal_subst || s4.contractum != legal_canon {
        return Err(format!(
            "CANONICALIZE_FAILURE: want {legal_canon} from {legal_subst}, got {}",
            s4.contractum
        ));
    }
    if w.result != legal_canon {
        return Err(format!(
            "RESULT_NOT_DERIVED: re-exec {legal_canon}, claimed {}",
            w.result
        ));
    }
    let digest = accepted_digest(&corpus_root_file, MANIFEST_ID, &query, &w.result, derived, &raw_w);
    if digest != expected {
        return Err(format!(
            "DIGEST_MISMATCH: computed: {digest}\n      expected: {expected}"
        ));
    }
    Ok((derived, sha256::hex_encode(&sha256::sha256(&raw_w)), digest))
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let mut targets: Vec<PathBuf> = Vec::new();
    if args.is_empty() {
        println!("=== Kingfisher iOS On-Device Trace Verifier ===");
        // Check current exe directory / bundle resources
        let exe_dir = env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
        let bundle_dir = exe_dir.parent().unwrap_or(&exe_dir);
        let candidate_dirs = [
            bundle_dir.join("fixtures"),
            PathBuf::from("fixtures"),
            PathBuf::from("/data/local/tmp/fixtures"),
        ];

        let mut found = false;
        for c in &candidate_dirs {
            let f1 = c.join("F001");
            let f2 = c.join("F002_specv1");
            if f1.is_dir() && f2.is_dir() {
                targets.push(f1);
                targets.push(f2);
                found = true;
                break;
            }
        }
        if !found {
            eprintln!("usage: trace_verifier <fixture-dir> [fixture-dir...]");
            process::exit(2);
        }
    } else {
        for a in &args {
            targets.push(PathBuf::from(a));
        }
    }

    let mut worst = 0;
    for t in &targets {
        println!("-------------------------------------------------------");
        println!("TARGET: {}", t.display());
        match verify(t) {
            Ok((fuel, wsha, digest)) => {
                println!("  [VERDICT] ACCEPTED");
                println!("    -> Derived Fuel:     {fuel}");
                println!("    -> Witness SHA-256:  {wsha}");
                println!("    -> Consensus Digest: {digest}");
            }
            Err(e) => {
                worst = 1;
                println!("  [VERDICT] REJECTED: {e}");
            }
        }
    }
    println!("-------------------------------------------------------");
    process::exit(worst);
}
