(imp 0 a 100)
(imp 0 b 900)
!(match &self (imp 0 $c $v) (if (< $v 500) (remove-atom &self (imp 0 $c $v)) ()))
!(collapse (match &self (imp 0 $c $v) ($c $v)))
