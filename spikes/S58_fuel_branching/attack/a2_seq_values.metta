; ATTACK 2: ONE generator bound once, threaded through three draws.
!(import! &self random)
!(bind! &g (new-random-generator 42))
!(random-int &g 0 1000)
!(random-int &g 0 1000)
!(random-int &g 0 1000)
