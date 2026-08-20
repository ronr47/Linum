module attributes {linum.align = 64 : i64} {
  func.func @mesh_vector_kernel(%arg0: memref<64xf32>, %arg1: memref<64xf32>) -> memref<64xf32> {
    %alloc = memref.alloc() : memref<64xf32>
    affine.for %i = 0 to 64 {
      %a = affine.load %arg0[%i] : memref<64xf32>
      %b = affine.load %arg1[%i] : memref<64xf32>
      %res = arith.addf %a, %b : f32
      affine.store %res, %alloc[%i] : memref<64xf32>
    }
    return %alloc : memref<64xf32>
  }
}
