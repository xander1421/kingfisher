; THIRD unpinnable entropy source, not in the ban list:
; reset-random-generator re-seeds an EXPLICITLY-SEEDED generator from OS entropy
; (random.rs:43-45 -> StdRng::from_os_rng). Every draw goes "through an
; explicitly-seeded generator" and the program is still nondeterministic.
!(import! &self random)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
!(bind! &g (new-random-generator 42))
!(reset-random-generator &g)
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
!(if (== (random-int &g 0 2) 0) (expensive) (cheap))
