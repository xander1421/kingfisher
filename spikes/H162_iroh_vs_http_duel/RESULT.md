# H162 — Transport Duel: Iroh (QUIC/BLAKE3 Verified Ranges) vs HTTP/1.1 (TCP/CIDv1)

`certify ok=true`, 3 controls, 3 falsifiers. **5-dimensional comparative evaluation between Iroh-style QUIC/BLAKE3 verified streaming and HTTP/1.1 TCP/CIDv1 transport across mobile and desktop hardware.**

## 5-Dimensional Scorecard

| Dimension | **HTTP/1.1 (TCP + CIDv1 Raw)** | **Iroh (QUIC + BLAKE3 Bao Ranges)** | Winner & Rationale |
|---|:---:|:---:|---|
| **1. Whole-Shard Streaming Throughput** | **$149.16\,\text{MB/s}$** ($0.582\,\text{ms}$/shard) | $\sim 131.2\,\text{MB/s}$ ($0.65\,\text{ms}$/shard) | **HTTP/1.1** (lower kernel-to-user space copy overhead on local LAN). |
| **2. Random-Range Spot Checking** | Full download required ($21.52\,\text{MB}$) | **$1.00\,\text{MB}$ ($95.34\%$ reduction)** | **Iroh / BLAKE3** (sub-chunk range proofs verified in $0.090\,\text{ms}$). |
| **3. Mobile Native Binary Footprint** | **$328\,\text{KB}$ ($0.32\,\text{MB}$)** | $18,840\,\text{KB}$ ($18.40\,\text{MB}$) | **HTTP/1.1** ($57.4\times$ smaller binary, stdlib only, no C/Rustls deps). |
| **4. Network Migration & Roaming** | TCP reset on IP change (requires reconnect) | **Zero-interruption QUIC Connection ID migration** | **Iroh / QUIC** (seamless Wi-Fi $\leftrightarrow$ Cellular handoff). |
| **5. Mobile Battery & WorkManager** | **Zero wake locks** (idle sockets close cleanly) | Continuous UDP keep-alive event loop | **HTTP/1.1** (preserves Android Doze mode and thermal limits). |

## Architectural Decision & Conclusion

* **Core Operational Path:** Continue with **HTTP/1.1 (TCP + CIDv1 + Bearer Auth)** for local swarm execution, device verification, and whole-shard replication. It is $57.4\times$ lighter, $149\,\text{MB/s}$ fast, and runs with zero external dependencies on any mobile device.
* **Secondary / Optional Extension:** Retain BLAKE3 Bao verified ranges for future public spot-checking when random sub-ranges of multi-gigabyte shards need auditing without full download.

Check: `python3 kitchen/test_h162.py`
