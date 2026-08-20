// Linum 2050 AVX-512 Vector Lowering Dialect
module attributes {linum.align = 64 : i64, linum.target = "avx512f"} {
  func.func @vector_fma_kernel(%a: vector<16xf32>, %b: vector<16xf32>, %c: vector<16xf32>) -> vector<16xf32> {
    // 512-bit wide fused multiply-add on 16 contiguous single-precision floats
    %res = vector.fma %a, %b, %c : vector<16xf32>
    return %res : vector<16xf32>
  }
}
