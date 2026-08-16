; ULP PROBE - the harness must SHOW a 1-ULP input difference or it is blind.
; First attempt used sin(pi/2), which is flat at its maximum: 1 ULP in gave
; 0 ULP out and the probe read as "insensitive" when it was badly sited.
!(sin-math 1000.0)
!(sin-math 1000.0000000000001)
!(sin-math 12345.6789)
!(sin-math 12345.678900000003)
!(sin-math 0.7853981633974483)
!(sin-math 0.7853981633974484)
!(log-math 2.718281828459045 7.0)
!(log-math 2.718281828459045 7.000000000000001)
!(log-math 2.718281828459045 1000000.0)
!(log-math 2.718281828459045 1000000.0000000001)
