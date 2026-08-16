; Is host state reachable with NO flip and NO &rng?
!(file-read-to-string! "/etc/hostname")
!(file-get-size! (file-open! "/etc/hosts" (read)))
