; A hypergraph reasoning job: transitive closure over an Inheritance graph,
; plus a recursive arithmetic workload to give the fuel meter something to
; count. Deliberately mixes graph pattern matching (order-sensitive, the thing
; we need to be reproducible) with pure reduction (deep, the thing that makes
; the step count large).

; --- the knowledge graph -----------------------------------------------
(Inheritance human mammal)
(Inheritance chimp mammal)
(Inheritance monkey mammal)
(Inheritance rhino mammal)
(Inheritance mammal animal)
(Inheritance reptile animal)
(Inheritance snake reptile)
(Inheritance triceratops dinosaur)
(Inheritance dinosaur reptile)
(Inheritance earthworm animal)
(Inheritance vine plant)
(Inheritance ent plant)
(Inheritance plant organism)
(Inheritance animal organism)

; --- transitive closure -------------------------------------------------
(= (isa $x $y) (match &self (Inheritance $x $y) $y))
(= (isa $x $z)
   (let $y (match &self (Inheritance $x $y) $y)
        (isa $y $z)))

; --- recursive arithmetic ----------------------------------------------
(= (fib 0) 0)
(= (fib 1) 1)
(= (fib $n) (+ (fib (- $n 1)) (fib (- $n 2))))

(= (sumto 0) 0)
(= (sumto $n) (+ $n (sumto (- $n 1))))

; --- the queries --------------------------------------------------------
!(isa human $a)
!(isa snake $a)
!(isa triceratops $a)
!(match &self (Inheritance $x mammal) $x)
!(fib 15)
!(sumto 60)
