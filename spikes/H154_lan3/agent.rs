//! H154 device agent. Dial-out HTTP/1.0 only. No listen. No crates.
//!
//! S24 has no curl. This is std::net, not iroh/QUIC: LATENCY_FLOOR.md already
//! put persistent HTTP+NODELAY at 1 RTT. Connection: close here is fine —
//! this run is a 3-device transport proof, not a latency duel.
use std::env;
use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::process::Command;
use std::time::Duration;

struct Resp {
    status: u16,
    body: Vec<u8>,
}

fn parse_base(base: &str) -> (String, u16) {
    let rest = base
        .strip_prefix("http://")
        .unwrap_or_else(|| panic!("KF_BASE must be http://host:port, got {}", base));
    let (h, p) = rest
        .rsplit_once(':')
        .unwrap_or_else(|| panic!("KF_BASE missing port: {}", base));
    (h.to_string(), p.parse().expect("port"))
}

fn http(host: &str, port: u16, method: &str, path: &str, token: Option<&str>, body: Option<&[u8]>) -> Resp {
    let mut s = TcpStream::connect((host, port)).unwrap_or_else(|e| panic!("connect {}:{}: {}", host, port, e));
    s.set_read_timeout(Some(Duration::from_secs(35))).ok();
    s.set_nodelay(true).ok();
    let mut req = format!("{method} {path} HTTP/1.0\r\nHost: {host}:{port}\r\n");
    if let Some(t) = token {
        req.push_str(&format!("Authorization: Bearer {t}\r\n"));
    }
    if let Some(b) = body {
        req.push_str("Content-Type: application/json\r\n");
        req.push_str(&format!("Content-Length: {}\r\n", b.len()));
    }
    req.push_str("\r\n");
    s.write_all(req.as_bytes()).unwrap();
    if let Some(b) = body {
        s.write_all(b).unwrap();
    }
    let mut buf = Vec::new();
    s.read_to_end(&mut buf).unwrap();
    let sep = buf.windows(4).position(|w| w == b"\r\n\r\n").unwrap_or(0);
    let head = String::from_utf8_lossy(&buf[..sep]);
    let status = head
        .split_whitespace()
        .nth(1)
        .and_then(|x| x.parse().ok())
        .unwrap_or(0);
    let body = if sep + 4 <= buf.len() {
        buf[sep + 4..].to_vec()
    } else {
        Vec::new()
    };
    Resp { status, body }
}

fn json_str(s: &str, key: &str) -> Option<String> {
    let pat = format!("\"{key}\"");
    let i = s.find(&pat)?;
    let rest = &s[i + pat.len()..];
    let rest = rest.trim_start().trim_start_matches(':').trim_start();
    if !rest.starts_with('"') {
        return None;
    }
    let rest = &rest[1..];
    let j = rest.find('"')?;
    Some(rest[..j].to_string())
}

fn sha256_hex(path: &str) -> String {
    let out = Command::new("sha256sum")
        .arg(path)
        .output()
        .or_else(|_| Command::new("toybox").args(["sha256sum", path]).output())
        .expect("sha256sum");
    String::from_utf8_lossy(&out.stdout)
        .split_whitespace()
        .next()
        .unwrap_or("")
        .to_string()
}

fn main() {
    let base = env::var("KF_BASE").expect("KF_BASE");
    let (host, port) = parse_base(&base);
    if env::args().any(|a| a == "--probe-unauth") {
        let r = http(&host, port, "GET", "/stats", None, None);
        println!("{}", r.status);
        return;
    }
    let token = env::var("KF_TOKEN").expect("KF_TOKEN");
    let worker = env::var("KF_WORKER").unwrap_or_else(|_| "phone".into());
    let dir = env::var("KF_DIR").unwrap_or_else(|_| "/data/local/tmp/kf_lan3".into());
    let tv = env::var("KF_TV").unwrap_or_else(|_| format!("{dir}/tv"));
    let maxidle: u32 = env::var("KF_MAXIDLE")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(3);
    fs::create_dir_all(format!("{dir}/shards")).ok();
    let mut idle = 0u32;
    while idle < maxidle {
        let r = http(
            &host,
            port,
            "GET",
            &format!("/job?worker={worker}"),
            Some(&token),
            None,
        );
        if r.status != 200 || r.body.is_empty() {
            idle += 1;
            continue;
        }
        idle = 0;
        let job = String::from_utf8_lossy(&r.body);
        let cid = json_str(&job, "shard_cid").expect("shard_cid");
        let jid = json_str(&job, "job_id").unwrap_or_else(|| "unk".into());
        let want = json_str(&job, "shard_sha256").unwrap_or_default();
        let f = format!("{dir}/shards/{cid}");
        if !std::path::Path::new(&f).is_file() {
            let got = http(&host, port, "GET", &format!("/shard/{cid}"), Some(&token), None);
            if got.status != 200 || got.body.is_empty() {
                continue;
            }
            fs::write(&f, &got.body).unwrap();
        }
        let got_h = sha256_hex(&f);
        if !want.is_empty() && got_h != want {
            let _ = fs::remove_file(&f);
            continue;
        }
        let fx = format!("{dir}/fx_{jid}");
        let _ = fs::remove_dir_all(&fx);
        fs::create_dir_all(&fx).ok();
        let tar = Command::new("tar")
            .args(["xf", &f, "-C", &fx])
            .status()
            .or_else(|_| Command::new("toybox").args(["tar", "xf", &f, "-C", &fx]).status())
            .expect("tar");
        if !tar.success() {
            continue;
        }
        let out = Command::new(&tv).arg(&fx).output().expect("tv");
        let text = format!(
            "{}{}",
            String::from_utf8_lossy(&out.stdout),
            String::from_utf8_lossy(&out.stderr)
        );
        let digest = text
            .split("Consensus Digest:")
            .nth(1)
            .and_then(|s| s.split_whitespace().next())
            .unwrap_or("")
            .to_string();
        let verdict = if text.contains("[VERDICT] ACCEPTED") {
            "ACCEPTED"
        } else {
            "REJECTED"
        };
        let envj = format!(
            "{{\"job_id\":\"{jid}\",\"worker\":\"{worker}\",\"status\":\"{verdict}\",\"digest\":\"{digest}\",\"via\":\"{base}\"}}"
        );
        let _ = http(
            &host,
            port,
            "POST",
            "/result",
            Some(&token),
            Some(envj.as_bytes()),
        );
    }
    eprintln!("agent {worker} exiting after {idle} idle polls");
}
