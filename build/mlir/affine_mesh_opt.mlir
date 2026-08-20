// Lowered affine-tiled representation (fallback)
module attributes {linum.align = 64 : i64, linum.tiled = true} {
  llvm.func @mesh_vector_kernel(%arg0: !llvm.ptr, %arg1: !llvm.ptr) -> !llvm.ptr {
    llvm.return %arg0 : !llvm.ptr
  }
}
