; random-int TAKES a generator as arg 0, unlike flip which calls the global
; rand::random(). If an explicitly-seeded generator makes fuel AND output
; constant, then a nondeterministic job is verifiable provided it declares
; its RNG -- and `flip` must be banned from the job class.
!(import! &self random)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
(= (g) (new-random-generator 42))
!(if (== (random-int (g) 0 2) 0) (expensive) (cheap))
!(if (== (random-int (g) 0 2) 0) (expensive) (cheap))
!(if (== (random-int (g) 0 2) 0) (expensive) (cheap))
