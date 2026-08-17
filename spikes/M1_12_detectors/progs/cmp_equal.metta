; `<` and `<=` differ ONLY at equality. The 64-program corpus never prints a
; comparison of equal values, so a replica wrong at every boundary agreed
; byte-identically. Print both sides of the boundary explicitly.
!(< 1 1)
!(<= 1 1)
!(> 2 2)
!(>= 2 2)
!(< 1 2)
!(< 2 1)
