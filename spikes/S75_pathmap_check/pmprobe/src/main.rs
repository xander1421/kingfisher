// S75 — does MORK's real pathmap agree with W2's Python trie on branching, and
// is pathmap's own `merkleize` usable as a commitment?
//
// Reads the length-prefixed key files W2/S73 wrote from the SAME corpora, so the
// comparison is on identical key sets rather than on a re-derived approximation.
use pathmap::PathMap;
use pathmap::counters::Counters;
use std::fs;

fn read_keys(path: &str) -> Vec<Vec<u8>> {
    let b = fs::read(path).expect("key file");
    let n = u32::from_le_bytes(b[0..4].try_into().unwrap()) as usize;
    let mut out = Vec::with_capacity(n);
    let mut i = 4usize;
    for _ in 0..n {
        let l = u16::from_le_bytes(b[i..i + 2].try_into().unwrap()) as usize;
        i += 2;
        out.push(b[i..i + l].to_vec());
        i += l;
    }
    out
}

fn main() {
    for (name, file) in [("atoms", "../keys_atoms.bin"), ("triples", "../keys_triples.bin")] {
        let keys = read_keys(file);
        let mut m = PathMap::from_iter(keys.iter().map(|k| (k.as_slice(), ())));
        let c = Counters::count_ocupancy(&m);
        let nodes = c.total_nodes();
        let items = c.total_child_items();
        let r = m.merkleize();
        println!("pathmap {:8} keys={:5} nodes={:5} child_items={:5} \
                  merkle_hash={:#034x} reused={} cloned={} replaced={}",
                 name, keys.len(), nodes, items, r.hash, r.reused, r.cloned, r.replaced);
        // merkleize is idempotent only if it is a function of content; run twice
        let r2 = m.merkleize();
        println!("pathmap {:8} second merkleize: same_hash={} reused={}",
                 name, r2.hash == r.hash, r2.reused);
    }
}
