// S77 — S75 and S76 both turned node DEPTH into proof SIZE by multiplying. This
// walks the real paths and counts what a proof would actually have to carry.
//
// An authentication path carries, at each node it passes through, the digests of
// the SIBLING subtries it did not take. A node with one child has no siblings and
// therefore costs a proof nothing but the step itself. So the quantity that
// decides proof bytes is not the number of nodes on the path -- it is the number
// of siblings summed along it, and those are different numbers whenever a path
// has long unbranched runs. Which is exactly what a 1,155-byte key produces.
//
// Reads the same length-prefixed key files S75/S76 wrote, so the key sets are
// identical to the ones whose depths were measured, not re-derived.
//
// usage: pmproof <keyfile> [<keyfile> ...]     (paths relative to CWD)
use pathmap::PathMap;
use pathmap::zipper::{Zipper, ZipperMoving};
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
    let args: Vec<String> = std::env::args().skip(1).collect();
    // Self-check first, on a trie whose shape is decidable by hand, so a
    // misreading of the zipper API cannot pass as a finding. Keys "aa" and "ab"
    // branch once at depth 1: descending "aa" must see exactly one node with two
    // children and the rest with one, i.e. exactly 1 sibling on the path.
    {
        let t = PathMap::from_iter([(b"aa".as_slice(), ()), (b"ab".as_slice(), ())]);
        let mut z = t.read_zipper();
        let mut sib = 0usize;
        let mut steps = 0usize;
        for b in b"aa" {
            let c = z.child_count();
            if c > 0 { sib += c - 1; }
            steps += 1;
            z.descend_to_byte(*b);
        }
        println!("selfcheck two_keys_one_branch siblings={} steps={} expect siblings=1", sib, steps);
    }

    for file in args {
        let keys = read_keys(&file);
        let m = PathMap::from_iter(keys.iter().map(|k| (k.as_slice(), ())));

        // Every key, not a sample: the whole point is the DISTRIBUTION of
        // branching along real paths, and a sample would hide the tail.
        let mut tot_sib = 0u64;
        let mut tot_steps = 0u64;
        let mut tot_bytes = 0u64;
        let mut max_sib = 0usize;
        let mut branch_nodes = 0u64;      // nodes on a path with >1 child
        for k in &keys {
            let mut z = m.read_zipper();
            let mut sib = 0usize;
            for b in k {
                let c = z.child_count();
                if c > 1 {
                    sib += c - 1;
                    branch_nodes += 1;
                }
                z.descend_to_byte(*b);
            }
            tot_sib += sib as u64;
            tot_steps += k.len() as u64;
            tot_bytes += k.len() as u64;
            if sib > max_sib { max_sib = sib; }
        }
        let n = keys.len() as f64;
        println!("path {:14} keys={:5} mean_siblings={:9.3} max_siblings={:5} \
                  mean_byte_steps={:9.3} mean_key_bytes={:9.3} branch_nodes_total={}",
                 file, keys.len(), tot_sib as f64 / n, max_sib,
                 tot_steps as f64 / n, tot_bytes as f64 / n, branch_nodes);
    }
}
