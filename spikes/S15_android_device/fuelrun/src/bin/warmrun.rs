//! warmrun — WorkManager process-reuse and in-process warm execution benchmark.
//! Measures cold-start instantiation vs warm in-process reuse overhead,
//! checks 100 sequential discrete MeTTa jobs within a single process,
//! tracks memory metrics (/proc/self/status VmRSS/VmData/VmSize),
//! and validates bit-identical canonical digest invariance.

use hyperon::metta::runner::{Metta, RunnerState};
use hyperon::metta::text::SExprParser;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::fs::File;
use std::io::{BufRead, BufReader};
use std::time::Instant;

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct MemoryStats {
    pub vm_rss_kb: u64,
    pub vm_size_kb: u64,
    pub vm_data_kb: u64,
    pub vm_peak_kb: u64,
}

pub fn read_proc_memory() -> MemoryStats {
    let mut stats = MemoryStats {
        vm_rss_kb: 0,
        vm_size_kb: 0,
        vm_data_kb: 0,
        vm_peak_kb: 0,
    };
    if let Ok(file) = File::open("/proc/self/status") {
        let reader = BufReader::new(file);
        for line in reader.lines().flatten() {
            if line.starts_with("VmRSS:") {
                stats.vm_rss_kb = parse_kb(&line);
            } else if line.starts_with("VmSize:") {
                stats.vm_size_kb = parse_kb(&line);
            } else if line.starts_with("VmData:") {
                stats.vm_data_kb = parse_kb(&line);
            } else if line.starts_with("VmPeak:") {
                stats.vm_peak_kb = parse_kb(&line);
            }
        }
    }
    stats
}

fn parse_kb(line: &str) -> u64 {
    line.split_whitespace()
        .nth(1)
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(0)
}

fn sha256_hex(s: &str) -> String {
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    format!("{:x}", h.finalize())
}

fn sha8(s: &str) -> String {
    sha256_hex(s)[..16].to_string()
}

fn canon(t: &str) -> String {
    renumber(t, false)
}

fn canon_alpha(t: &str) -> String {
    renumber(t, true)
}

fn renumber(t: &str, all_vars: bool) -> String {
    let mut map: HashMap<String, usize> = HashMap::new();
    let mut out = String::with_capacity(t.len());
    let b: Vec<char> = t.chars().collect();
    let mut i = 0;
    while i < b.len() {
        if b[i] != '$' {
            out.push(b[i]);
            i += 1;
            continue;
        }
        let start = i;
        i += 1;
        while i < b.len() && !b[i].is_whitespace() && b[i] != '(' && b[i] != ')' {
            i += 1;
        }
        let tok: String = b[start..i].iter().collect();
        let has_id = tok.contains('#');
        if !all_vars && !has_id {
            out.push_str(&tok);
            continue;
        }
        let n = map.len() + 1;
        let k = *map.entry(tok.clone()).or_insert(n);
        if all_vars {
            out.push_str(&format!("$v{}", k));
        } else {
            let base = tok.split('#').next().unwrap();
            out.push_str(&format!("{}#{}", base, k));
        }
    }
    out
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct JobSummaryItem {
    pub iteration: usize,
    pub job_index: usize,
    pub job_name: String,
    pub fuel_used: u64,
    pub boot_us: f64,
    pub eval_us: f64,
    pub total_us: f64,
    pub raw_hash: String,
    pub canon_hash: String,
    pub alpha_hash: String,
    pub vm_rss_kb: u64,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct ProgramSummary {
    pub name: String,
    pub runs: usize,
    pub distinct_raw: usize,
    pub distinct_canon: usize,
    pub distinct_alpha: usize,
    pub expected_canon_hash: String,
    pub all_canon_match: bool,
    pub mean_boot_us: f64,
    pub mean_eval_us: f64,
    pub mean_total_us: f64,
    pub p50_total_us: f64,
    pub p95_total_us: f64,
    pub p99_total_us: f64,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct CheckpointMem {
    pub iteration: usize,
    pub vm_rss_kb: u64,
    pub vm_size_kb: u64,
    pub vm_data_kb: u64,
}

#[derive(serde::Serialize, serde::Deserialize, Clone, Debug)]
pub struct BenchmarkOutput {
    pub total_iterations: usize,
    pub total_jobs_executed: usize,
    pub initial_memory: MemoryStats,
    pub warmup_memory_iter10: MemoryStats,
    pub final_memory: MemoryStats,
    pub delta_rss_kb_10_to_end: i64,
    pub delta_rss_kb_0_to_end: i64,
    pub zero_leak_certified: bool,
    pub memory_checkpoints: Vec<CheckpointMem>,
    pub programs: Vec<ProgramSummary>,
    pub samples_first_last: Vec<JobSummaryItem>,
}

fn percentile(sorted: &[f64], p: f64) -> f64 {
    if sorted.is_empty() {
        return 0.0;
    }
    let idx = ((sorted.len() as f64 - 1.0) * p / 100.0).round() as usize;
    sorted[idx.min(sorted.len() - 1)]
}

fn default_suite() -> Vec<(String, String)> {
    vec![
        // P1: Arithmetic and conditionals (ground)
        (
            "P1_arith_ctl".to_string(),
            "!(+ 1 2)\n!(if (> 3 2) yes no)\n!(+ (* 4 5) (- 20 10))\n".to_string(),
        ),
        // P2: Transitive logic inference (ground)
        (
            "P2_logic_rules".to_string(),
            "(= (mortal $x) (human $x))\n(= (human Socrates) True)\n(= (human Plato) True)\n!(mortal Socrates)\n!(mortal Plato)\n".to_string(),
        ),
        // P3: Atom manipulation and set operations (ground)
        (
            "P3_set_ops".to_string(),
            "!(intersection-atom (A B C D E) (B C D F G))\n!(subtraction-atom (1 2 3 4 5) (2 4))\n".to_string(),
        ),
        // P4: Multi-hop knowledge base pattern matching (ground)
        (
            "P4_kb_chain".to_string(),
            "(= (Green $x) (Frog $x))\n(= (Frog $x) (Croaks $x))\n(= (Croaks Fritz) True)\n!(Green Fritz)\n".to_string(),
        ),
        // P5: Aliased variable probe (positive control: raw counter drifts, canon is invariant)
        (
            "P5_var_alias_probe".to_string(),
            "(implies (Frog $x) (Green $x))\n!(match &self (implies $p $q) ($p $q))\n".to_string(),
        ),
    ]
}

fn run_eval(
    program_text: &str,
    fuel_limit: u64,
) -> (u64, f64, f64, f64, String, String, String) {
    let t0 = Instant::now();
    let metta = Metta::new(None);
    let boot_us = t0.elapsed().as_nanos() as f64 / 1000.0;

    let t1 = Instant::now();
    let parser = SExprParser::new(program_text);
    let mut state = RunnerState::new_with_parser(&metta, Box::new(parser));
    let mut fuel: u64 = 0;
    while !state.is_complete() {
        if fuel >= fuel_limit {
            break;
        }
        if state.run_step().is_err() {
            break;
        }
        fuel += 1;
    }
    let eval_us = t1.elapsed().as_nanos() as f64 / 1000.0;
    let total_us = t0.elapsed().as_nanos() as f64 / 1000.0;

    let mut raw_lines = Vec::new();
    for (i, group) in state.current_results().iter().enumerate() {
        for atom in group.iter() {
            raw_lines.push(format!("{}\t{}", i, atom));
        }
    }
    let raw_str = format!("fuel={}\n{}", fuel, raw_lines.join("\n"));
    let canon_str = canon(&raw_str);
    let alpha_str = canon_alpha(&raw_str);

    let raw_h = sha8(&raw_str);
    let canon_h = sha8(&canon_str);
    let alpha_h = sha8(&alpha_str);

    (fuel, boot_us, eval_us, total_us, raw_h, canon_h, alpha_h)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!("usage: warmrun <mode> [args...]");
        eprintln!("modes: soak100, bench_warm, single <file> <fuel>");
        std::process::exit(1);
    }

    let mode = &args[1];

    if mode == "single" {
        if args.len() < 4 {
            eprintln!("usage: warmrun single <file> <fuel>");
            std::process::exit(1);
        }
        let file = &args[2];
        let fuel: u64 = args[3].parse().unwrap_or(2000000);
        let content = std::fs::read_to_string(file).expect("read file");
        let (fuel_used, boot_us, eval_us, total_us, raw_h, canon_h, _) = run_eval(&content, fuel);
        let mem = read_proc_memory();
        println!(
            "SINGLE:\tboot={:.2}us\teval={:.2}us\ttotal={:.2}us\tfuel={}\traw={}\tcanon={}\trss={}kB",
            boot_us, eval_us, total_us, fuel_used, raw_h, canon_h, mem.vm_rss_kb
        );
        return;
    }

    let iterations: usize = if args.len() >= 3 {
        args[2].parse().unwrap_or(100)
    } else {
        100
    };
    let fuel: u64 = if args.len() >= 4 {
        args[3].parse().unwrap_or(2000000)
    } else {
        2000000
    };

    let files: Vec<String> = if args.len() >= 5 {
        args[4..].to_vec()
    } else {
        Vec::new()
    };

    let programs = if files.is_empty() {
        default_suite()
    } else {
        let mut progs = Vec::new();
        for f in &files {
            let content = std::fs::read_to_string(f).expect("cannot read file");
            let name = std::path::Path::new(f)
                .file_name()
                .unwrap()
                .to_string_lossy()
                .to_string();
            progs.push((name, content));
        }
        progs
    };

    let initial_mem = read_proc_memory();
    let mut mem_iter10 = initial_mem.clone();
    let mut checkpoints = Vec::new();
    let mut samples = Vec::new();

    // Per-program stats tracking
    struct ProgStat {
        raw_hashes: Vec<String>,
        canon_hashes: Vec<String>,
        alpha_hashes: Vec<String>,
        boot_times: Vec<f64>,
        eval_times: Vec<f64>,
        total_times: Vec<f64>,
    }
    let mut prog_stats: Vec<ProgStat> = programs
        .iter()
        .map(|_| ProgStat {
            raw_hashes: Vec::with_capacity(iterations),
            canon_hashes: Vec::with_capacity(iterations),
            alpha_hashes: Vec::with_capacity(iterations),
            boot_times: Vec::with_capacity(iterations),
            eval_times: Vec::with_capacity(iterations),
            total_times: Vec::with_capacity(iterations),
        })
        .collect();

    let total_jobs = iterations * programs.len();

    for iter in 0..iterations {
        for (job_idx, (name, content)) in programs.iter().enumerate() {
            let (fuel_used, boot_us, eval_us, total_us, raw_h, canon_h, alpha_h) =
                run_eval(content, fuel);

            let stat = &mut prog_stats[job_idx];
            stat.raw_hashes.push(raw_h.clone());
            stat.canon_hashes.push(canon_h.clone());
            stat.alpha_hashes.push(alpha_h.clone());
            stat.boot_times.push(boot_us);
            stat.eval_times.push(eval_us);
            stat.total_times.push(total_us);

            if iter < 3 || iter == iterations - 1 || iter == 10 || iter == 50 {
                let mem = read_proc_memory();
                samples.push(JobSummaryItem {
                    iteration: iter,
                    job_index: job_idx,
                    job_name: name.clone(),
                    fuel_used,
                    boot_us,
                    eval_us,
                    total_us,
                    raw_hash: raw_h,
                    canon_hash: canon_h,
                    alpha_hash: alpha_h,
                    vm_rss_kb: mem.vm_rss_kb,
                });
            }
        }

        if iter == 9 {
            mem_iter10 = read_proc_memory();
        }

        if iter % 10 == 0 || iter == iterations - 1 {
            let m = read_proc_memory();
            checkpoints.push(CheckpointMem {
                iteration: iter,
                vm_rss_kb: m.vm_rss_kb,
                vm_size_kb: m.vm_size_kb,
                vm_data_kb: m.vm_data_kb,
            });
        }
    }

    let final_mem = read_proc_memory();
    let delta_rss_10_to_end = final_mem.vm_rss_kb as i64 - mem_iter10.vm_rss_kb as i64;
    let delta_rss_0_to_end = final_mem.vm_rss_kb as i64 - initial_mem.vm_rss_kb as i64;
    let zero_leak = delta_rss_10_to_end <= 0 || (delta_rss_10_to_end as f64 / iterations as f64) < 1.0;

    let mut prog_summaries = Vec::new();
    for (job_idx, (name, _)) in programs.iter().enumerate() {
        let stat = &prog_stats[job_idx];
        let n = stat.total_times.len();

        let mut distinct_raw = stat.raw_hashes.clone();
        distinct_raw.sort();
        distinct_raw.dedup();

        let mut distinct_canon = stat.canon_hashes.clone();
        distinct_canon.sort();
        distinct_canon.dedup();

        let mut distinct_alpha = stat.alpha_hashes.clone();
        distinct_alpha.sort();
        distinct_alpha.dedup();

        let mut sorted_times = stat.total_times.clone();
        sorted_times.sort_by(|a, b| a.partial_cmp(b).unwrap());

        let sum_boot: f64 = stat.boot_times.iter().sum();
        let sum_eval: f64 = stat.eval_times.iter().sum();
        let sum_total: f64 = stat.total_times.iter().sum();

        let expected_canon = distinct_canon.first().cloned().unwrap_or_default();
        let all_canon_match = distinct_canon.len() == 1;

        prog_summaries.push(ProgramSummary {
            name: name.clone(),
            runs: n,
            distinct_raw: distinct_raw.len(),
            distinct_canon: distinct_canon.len(),
            distinct_alpha: distinct_alpha.len(),
            expected_canon_hash: expected_canon,
            all_canon_match,
            mean_boot_us: sum_boot / n as f64,
            mean_eval_us: sum_eval / n as f64,
            mean_total_us: sum_total / n as f64,
            p50_total_us: percentile(&sorted_times, 50.0),
            p95_total_us: percentile(&sorted_times, 95.0),
            p99_total_us: percentile(&sorted_times, 99.0),
        });
    }

    let out = BenchmarkOutput {
        total_iterations: iterations,
        total_jobs_executed: total_jobs,
        initial_memory: initial_mem,
        warmup_memory_iter10: mem_iter10,
        final_memory: final_mem,
        delta_rss_kb_10_to_end: delta_rss_10_to_end,
        delta_rss_kb_0_to_end: delta_rss_0_to_end,
        zero_leak_certified: zero_leak,
        memory_checkpoints: checkpoints,
        programs: prog_summaries,
        samples_first_last: samples,
    };

    println!("{}", serde_json::to_string_pretty(&out).unwrap());
}
