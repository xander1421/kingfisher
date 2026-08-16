; ATTACK 4: seeded random-float. Number::Float Displays via {:?} = shortest
; round-trip, so identical text <=> identical f64 bits.
; Also branch on a float and chain float arithmetic to amplify any ULP drift.
!(import! &self random)
!(bind! &g (new-random-generator 1))
!(random-float &g 0.0 1.0)
!(random-float &g -1000000.0 1000000.0)
!(bind! &x (random-float &g 0.0 1.0))
!(* (* &x &x) 1e15)
!(/ 1.0 (+ &x 1e-9))
!(if (< (random-float &g 0.0 1.0) 0.5) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1))))))))))  1)
