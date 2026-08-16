; Counter-example to the OTHER direction of the "iff": this program USES flip
; and is nonetheless perfectly replicable in fuel AND output.
!(import! &self random)
!(if (flip) 1 1)
!(let $x (flip) 42)
!(or (flip) True)
