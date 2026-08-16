; CONTROL for b4 — identical but the generator comes from the OS entropy token
; &rng instead of a pinned seed. Must vary, or b4 proves nothing.
!(import! &self random)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
!(if (== (random-int &rng 0 2) 0) (expensive) (cheap))
!(if (== (random-int &rng 0 2) 0) (expensive) (cheap))
!(if (== (random-int &rng 0 2) 0) (expensive) (cheap))
