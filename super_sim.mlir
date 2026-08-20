module attributes {linum.align = 64 : i64} {
  func.func @main_kernel() -> i32 {
    %base_ptr = memref.alloc() : memref<16xf32>
    %particle_offset = arith.constant 42 : i32
    %computed_ptr = arith.addi %base_ptr, %particle_offset : i32
    return %particle_offset : i32
  }
}