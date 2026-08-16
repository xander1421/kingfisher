!(import! &self fileio)
!(file-read-to-string! "/etc/hosts")
!(file-open! "/etc/hosts" (read))
