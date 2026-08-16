; Claimed: intersection-atom/subtraction-atom pick an arbitrary first match
; from a pointer-keyed HashMap traversal when wildcards are present.
!(intersection-atom ($x A) (A $x))
!(intersection-atom ($x $y A B) (A B $y $x))
!(subtraction-atom ($x A B) (A $y))
!(intersection-atom (A $x B $y C) ($y C A $x B))
