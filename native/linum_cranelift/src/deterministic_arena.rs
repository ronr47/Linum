// ==============================================================================
// DETERMINISTIC CACHE-ALIGNED JIT EMISSION ARENA
// Design Objective: Zero heap allocation jitter during live XDP compilation loops
// ==============================================================================

use std::alloc::{alloc, dealloc, Layout};
use std::ptr::NonNull;

const CACHE_LINE_SIZE: usize = 64; // Strict alignment to maximize CPU L1/L2 cache efficiency
const ARENA_SIZE: usize = 4 * 1024 * 1024; // Fixed 4MB ultra-fast sequential allocation block

pub struct DeterministicJitArena {
    memory_pool: NonNull<u8>,
    current_offset: usize,
    capacity: usize,
}

impl DeterministicJitArena {
    /// Instantiates a completely flat, pre-allocated memory chunk aligned to CPU cache bounds
    pub fn new() -> Self {
        // Enforce strict 64-byte boundary alignment to prevent cache-line splitting
        let layout = Layout::from_size_align(ARENA_SIZE, CACHE_LINE_SIZE)
            .expect("CRITICAL: Invalid hardware memory layout parameters.");
        
        let raw_ptr = unsafe { alloc(layout) };
        let memory_pool = NonNull::new(raw_ptr).expect("CRITICAL: Operating system denied raw memory arena allocation.");

        Self {
            memory_pool,
            current_offset: 0,
            capacity: ARENA_SIZE,
        }
    }

    /// Fast sequential bump-allocation logic. Time Complexity: O(1) constant time.
    /// Guarantees that compilation memory is completely sequential in the L2/L3 cache rows.
    pub fn allocate_code_block(&mut self, size: usize) -> Option<*mut u8> {
        // Enforce 64-byte granularity rounding for the next block alignment
        let aligned_size = (size + CACHE_LINE_SIZE - 1) & !(CACHE_LINE_SIZE - 1);

        if self.current_offset + aligned_size > self.capacity {
            // Out of bounds - prevents dynamic heap resizing pauses during live network traffic
            return None;
        }

        unsafe {
            let allocation_ptr = self.memory_pool.as_ptr().add(self.current_offset);
            self.current_offset += aligned_size;
            Some(allocation_ptr)
        }
    }

    /// Reset the cursor back to zero without touching system resource handles. Time Complexity: O(1)
    pub fn purge_and_recycle(&mut self) {
        self.current_offset = 0;
    }
}

impl Drop for DeterministicJitArena {
    fn drop(&mut self) {
        let layout = Layout::from_size_align(ARENA_SIZE, CACHE_LINE_SIZE).unwrap();
        unsafe {
            dealloc(self.memory_pool.as_ptr(), layout);
        }
    }
}
