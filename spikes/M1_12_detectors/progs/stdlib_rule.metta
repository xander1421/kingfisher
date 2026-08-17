; stdlib-init scored 0/64: fuel_used does not move when the stdlib grows, so an
; altered stdlib rule is invisible unless a dispatched program INVOKES it.
; Invoke the common ones directly.
!(if True yes no)
!(if False yes no)
!(and True False)
!(or True False)
!(not True)
