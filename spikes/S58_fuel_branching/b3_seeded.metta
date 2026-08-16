; Can a job PIN its randomness and become verifiable? Same branching program,
; seed fixed before any flip. If fuel AND output are constant, then a
; nondeterministic job is made replicable by pinning the seed in the hyperjob.
!(import! &self random)
!(set-random-seed &rng 42)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
!(if (flip) (expensive) (cheap))
!(if (flip) (expensive) (cheap))
!(if (flip) (expensive) (cheap))
