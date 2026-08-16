; TREATMENT — the random value selects between two arms of very different cost.
; If fuel tracks work, fuel MUST vary run to run.
!(import! &self random)
(= (cheap) 1)
(= (expensive) (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 (+ 1 1)))))))))))
!(if (flip) (expensive) (cheap))
!(if (flip) (expensive) (cheap))
!(if (flip) (expensive) (cheap))
