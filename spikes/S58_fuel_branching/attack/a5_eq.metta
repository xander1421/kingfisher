!(import! &self random)
!(bind! &g (new-random-generator 42))
!(== &g &g)
!(== (new-random-generator 42) (new-random-generator 42))
