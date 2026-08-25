use std::slice;

#[repr(C)]
pub struct TensorDimensions {
    pub dims: *const usize,
    pub rank: usize,
}

#[no_mangle]
pub unsafe extern "C" fn execute_hardware_tensor_transform(
    data_ptr: *mut f32,
    dimensions: TensorDimensions,
) -> i32 {
    if data_ptr.is_null() || dimensions.dims.is_null() || dimensions.rank == 0 {
        return -1;
    }

    let shape = slice::from_raw_parts(dimensions.dims, dimensions.rank);
    let total_elements: usize = shape.iter().product();

    let tensor_slice = slice::from_raw_parts_mut(data_ptr, total_elements);

    // Apply high-throughput affine scaling vector transform
    for val in tensor_slice.iter_mut() {
        *val = (*val * 2.5) + 1.25;
    }

    0
}
