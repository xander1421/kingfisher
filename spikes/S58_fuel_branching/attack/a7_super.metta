; A seeded generator is a SHARED MUTABLE stream. MeTTa evaluation is
; nondeterministic (superpose / multiple equalities), so which branch consumes
; which draw depends on traversal order, not on the seed.
!(import! &self random)
!(bind! &g (new-random-generator 42))
(= (pick) A)
(= (pick) B)
(= (pick) C)
!(collapse (Draw (pick) (random-int &g 0 1000)))
!(collapse (superpose ((random-int &g 0 1000) (random-int &g 0 1000) (random-int &g 0 1000))))
!(collapse (match &self (= (pick) $x) ($x (random-int &g 0 1000))))
