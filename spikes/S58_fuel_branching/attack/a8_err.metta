; ACCIDENTAL address leak: an empty-range error echoes the original expression,
; which contains the generator atom -> its heap address lands in the output.
; No flip, no &rng, fully seeded. A static ban catches none of this.
!(import! &self random)
!(bind! &g (new-random-generator 42))
!(random-int &g 5 0)
