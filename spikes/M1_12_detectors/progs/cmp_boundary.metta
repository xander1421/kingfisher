; Same defect reached through a rule, not a bare grounded call: a mutation that
; only shows in direct evaluation would be missed if every use went via matching.
(= (atmost $x $y) (if (<= $x $y) yes no))
(= (below $x $y) (if (< $x $y) yes no))
!(atmost 3 3)
!(below 3 3)
!(atmost 3 4)
!(below 4 3)
