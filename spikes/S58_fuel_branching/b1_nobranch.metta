; CONTROL — replicates test_gnd_conv's shape: random value consumed, never
; branched on. Fuel must be constant; this is the case S57 already measured.
!(import! &self random)
!(xor (flip) (flip))
!(and (flip) True)
