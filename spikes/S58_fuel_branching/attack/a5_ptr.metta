; SUSPECT: RandomGenerator's Display prints Rc::as_ptr -> a heap address.
; If a generator atom ever lands in a result it poisons the hash even though
; the program is fully seeded. `flip`/`&rng` are not involved at all.
!(import! &self random)
!(bind! &g (new-random-generator 42))
!&g
