; Terminating variant: direct graph queries + bounded recursion. Used for the
; OK / byte-identical-result comparison; job_kb.metta is used for the
; FUEL_EXHAUSTED comparison.
(Inheritance human mammal)
(Inheritance chimp mammal)
(Inheritance monkey mammal)
(Inheritance rhino mammal)
(Inheritance mammal animal)
(Inheritance reptile animal)
(Inheritance snake reptile)
(Inheritance dinosaur reptile)
(Inheritance triceratops dinosaur)
(Inheritance earthworm animal)
(Inheritance vine plant)
(Inheritance ent plant)
(Inheritance plant organism)
(Inheritance animal organism)

(= (parent $x) (match &self (Inheritance $x $y) $y))
(= (grandparent $x) (match &self (Inheritance $x $y) (parent $y)))

; single equality per symbol: two equalities for the same head make MeTTa
; explore both branches, and an unguarded recursive clause then runs away.
(= (fib $n) (if (< $n 2) $n (+ (fib (- $n 1)) (fib (- $n 2)))))
(= (sumto $n) (if (== $n 0) 0 (+ $n (sumto (- $n 1)))))

!(match &self (Inheritance $x mammal) $x)
!(match &self (Inheritance $x animal) $x)
!(parent snake)
!(grandparent triceratops)
!(fib 10)
!(sumto 20)
