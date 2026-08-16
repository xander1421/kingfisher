; CORRECTED b4: ONE generator, bound once, threaded through three draws.
; This is what "explicitly-seeded generator" has to mean for the spec rule
; to be about sequenced randomness rather than repeated re-seeding.
!(import! &self random)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
!(bind! &g (new-random-generator 42))
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
