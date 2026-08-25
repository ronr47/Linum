declare i32 @posix_memalign(ptr, i64, i64)

define i64 @test_complex(ptr %uninit_stub_arg, i64 %val_42_arg) {
entry_test_complex:
  %r1 = getelementptr i8, ptr %uninit_stub_arg, i64 0
  %base.1 = getelementptr i8, ptr %r1, i64 0
  %r2 = add i64 %val_42_arg, 0
  %factor.1 = add i64 %r2, 0
  %r4 = getelementptr i8, ptr %base.1, i64 0
  %r5 = add i64 %factor.1, 0
  %r3 = getelementptr i8, ptr %r4, i64 %r5
  %computed.1 = getelementptr i8, ptr %r3, i64 0
  %r6 = add i64 %factor.1, 0
  ret i64 %r6
}
