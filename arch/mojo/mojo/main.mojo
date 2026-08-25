from sys.ffi import DLOpen
from memory import UnsafePointer

@value
@register_passable("trivial")
struct TensorDimensions:
    var dims: UnsafePointer[Int]
    var rank: Int

fn main() raises:
    print("============================================================")
    print(" 🏛️ PYRAMIDS MONASTIC RUNTIME: MOJO -> RUST FFI BRIDGE")
    print("============================================================")

    # 1. Allocate a flat 1x2x3x4 (24 element) tensor buffer
    alias TOTAL_ELEMENTS = 24
    var tensor_ptr = UnsafePointer[Float32].alloc(TOTAL_ELEMENTS)

    for i in range(TOTAL_ELEMENTS):
        tensor_ptr[i] = Float32(i + 1)

    print("[*] Pre-Transform Sample [Index 23]:", tensor_ptr[23])

    # 2. Build explicit shape metadata
    var rank_dims = UnsafePointer[Int].alloc(4)
    rank_dims[0] = 1
    rank_dims[1] = 2
    rank_dims[2] = 3
    rank_dims[3] = 4

    var payload = TensorDimensions(rank_dims, 4)

    # 3. Dynamic Shared Object Linkage
    var rust_runtime = DLOpen("./target/release/librust_sys_engine.so")
    var transform_fn = rust_runtime.get_function[
        fn(UnsafePointer[Float32], TensorDimensions) -> Int32
    ]("execute_hardware_tensor_transform")

    var status = transform_fn(tensor_ptr, payload)
    print("[✔] Rust FFI Transform Exit Status:", status)
    print("[★] Post-Transform Sample [Index 23] (24.0 * 2.5 + 1.25):", tensor_ptr[23])

    # Cleanup
    tensor_ptr.free()
    rank_dims.free()
