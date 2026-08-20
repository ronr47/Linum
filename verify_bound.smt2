
(set-logic QF_BV)
(declare-const x (_ BitVec 64))
(declare-const y (_ BitVec 64))
(declare-const max_bound (_ BitVec 64))

; Preconditions
(assert (bvule x (_ bv1024 64)))
(assert (bvule y (_ bv313 64)))
(assert (= max_bound (_ bv4294967295 64)))

; Negate invariant to find counterexamples (Prove overflow is impossible)
(assert (bvugt (bvadd x y) max_bound))

(check-sat)
