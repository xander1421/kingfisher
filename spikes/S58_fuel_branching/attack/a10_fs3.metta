; Host state in the hash, with NO flip, NO &rng, NO random module at all.
!(import! &self fileio)
!(let $h (file-open! "/etc/hosts" (read)) (file-get-size! $h))
!(file-open! "/etc/hosts" (read))
