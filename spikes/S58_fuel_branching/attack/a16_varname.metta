; Claimed: HashMap/HashSet iteration picks which variable name survives a match.
(pair $z $z)
(triple $w $w $w)
!(match &self (pair $x $y) ($x $y))
!(match &self (triple $a $b $c) ($a $b $c))
!(get-atoms &self)
!(sealed ($p) ($p $q))
