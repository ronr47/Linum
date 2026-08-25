declare i32 @posix_memalign(ptr, i64, i64)

define i64 @deutsch_ctc_circuit(ptr %init_val_arg, ptr %val_42_arg) #0 {
entry_deutsch_ctc_circuit:
  %init_val_arg_int = ptrtoint ptr %init_val_arg to i64
  %val_42_arg_int = ptrtoint ptr %val_42_arg to i64
  %r1 = add i64 %init_val_arg_int, 0
  %q_state.1 = add i64 %r1, 0
  %r2 = add i64 %val_42_arg_int, 0
  %q_state.2 = add i64 %r2, 0
  %r3 = add i64 %q_state.2, 0
  ret i64 %r3
}
