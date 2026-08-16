; No flip, no &rng, no random module. Host state and a heap address both land
; in raw_hash. The static ban catches neither.
!(import! &self fileio)
!(let $h (file-open! "/tmp/s58host.txt" "r") (file-read-to-string! $h))
!(file-open! "/tmp/s58host.txt" "r")
