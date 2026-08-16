; Space iteration / match order and unique-atom: if these use a randomly-seeded
; HashMap, raw_hash (order-sensitive) breaks with no RNG op in sight.
(f a) (f b) (f c) (f d) (f e) (f g) (f h) (f i) (f j) (f k) (f l) (f m)
!(collapse (get-atoms &self))
!(collapse (match &self (f $x) $x))
!(unique-atom (superpose (z y x w v u t s r q p o n)))
