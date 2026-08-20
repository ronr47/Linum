def emit():
    return r'''; Matrix2x2 multiplication + determinant
;
; C = A * B
; det(C)

define i32 @main() {
entry:
  ; A = [[1,2],[3,4]]
  ; B = [[5,6],[7,8]]

  ; C00 = 1*5 + 2*7 = 19
  ; C01 = 1*6 + 2*8 = 22
  ; C10 = 3*5 + 4*7 = 43
  ; C11 = 3*6 + 4*8 = 50

  %c00 = add i32 5, 14
  %c01 = add i32 6, 16
  %c10 = add i32 15, 28
  %c11 = add i32 18, 32

  ; det(C) = C00*C11 - C01*C10
  ;        = 19*50 - 22*43
  ;        = 4

  %p0 = mul i32 %c00, %c11
  %p1 = mul i32 %c01, %c10
  %det = sub i32 %p0, %p1

  ret i32 %det
}
'''


if __name__ == "__main__":
    print(emit())
