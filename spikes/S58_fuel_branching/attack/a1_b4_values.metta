; ATTACK 1: does b4's (g) return a FRESH generator per call?
; Print the three draws b4 actually makes. If identical, b4 never varied its
; branch and its "seeded determinism" is a re-seeding artefact.
!(import! &self random)
(= (g) (new-random-generator 42))
!(random-int (g) 0 1000)
!(random-int (g) 0 1000)
!(random-int (g) 0 1000)
