declare i32 @posix_memalign(ptr, i64, i64)

define i64 @test_main(i64 %uninit_stub_arg, i64 %val_42_arg) {
entry_test_main:
  %r1 = add i64 %uninit_stub_arg, 0
  %ptr_var.1 = add i64 %r1, 0
  %r2 = add i64 %val_42_arg, 0
  %q.1 = add i64 %r2, 0
  %r3 = add i64 %q.1, 0
  ret i64 %r3
}
