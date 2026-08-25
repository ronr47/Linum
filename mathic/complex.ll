; Target and Builtins setup
@fmt = private unnamed_addr constant [4 x i8] c"%d\0A\00"
declare i32 @printf(ptr, ...)

define i32 @main() {
entry:
  %r0 = sub i32 5, 1
  %r1 = add i32 %r0, 1
  %r2 = sub i32 8, 4
  %r3 = add i32 %r2, 1
  %r4 = mul i32 %r1, %r3
  %r5 = sub i32 6, 2
  %r6 = add i32 %r5, 1
  %r7 = sub i32 7, 3
  %r8 = add i32 %r7, 1
  %r9 = mul i32 %r6, %r8
  %r10 = sub i32 %r4, %r9
  call i32 (ptr, ...) @printf(ptr @fmt, i32 %r10)
  ret i32 0
}
