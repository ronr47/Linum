#ifndef LINUM_OPS_TD
#define LINUM_OPS_TD

include "mlir/IR/OpBase.td"
include "mlir/Interfaces/SideEffectInterfaces.td"
include "mlir/Interfaces/InferTypeOpInterface.td"

def Linum_Dialect : Dialect {
    let name = "linum";
    let summary = "Linum High-Performance Quantum & Affine IR Dialect";
    let cppNamespace = "::mlir::linum";
}

class Linum_Op<string mnemonic, list<Trait> traits = []> :
    Op<Linum_Dialect, mnemonic, traits>;

def Linum_VectorAllocOp : Linum_Op<"vec_alloc", [Pure]> {
    let summary = "Allocates a 64-byte aligned vector register region";
    let arguments = (ins I64Attr:$elements, TypeAttr:$element_type);
    let results = (outs AnyMemRef:$output);
    let assemblyFormat = "$elements `x` $element_type attr-dict `:` type($output)";
}

def Linum_AffineKernelOp : Linum_Op<"affine_kernel"> {
    let summary = "Encapsulates affine loop nests for polyhedral vector optimization";
    let regions = (region SizedRegion<1>:$body);
    let assemblyFormat = "regions attr-dict";
}

#endif // LINUM_OPS_TD
