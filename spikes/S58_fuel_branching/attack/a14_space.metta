; No random module at all. `new-space` is core stdlib; its Display prints the
; heap address. Also &self and any state atom.
!(new-space)
!(new-state 5)
!&self
