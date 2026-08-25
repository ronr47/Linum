// src/bench.rs - The High-Frequency Pulse

/// Reads the raw CPU time-stamp counter (TSC) for ultra-low latency timing
#[inline(always)]
pub fn read_cpu_cycles() -> u64 {
    let mut low: u32;
    let mut high: u32;
    
    unsafe {
        // Interrogate the x86-64 hardware clock cycle counter directly
        core::arch::asm!(
            "rdtsc",
            out("eax") low,
            out("edx") high,
            options(nomem, nostack, preserves_flags)
        );
    }
    
    ((high as u64) << 32) | (low as u64)
}

/// Measures execution latency down to the individual clock tick
#[inline(always)]
pub fn profile_operation<F, R>(operation: F) -> (R, u64) 
where
    F: FnOnce() -> R,
{
    let start = read_cpu_cycles();
    let result = operation();
    let end = read_cpu_cycles();
    
    (result, end.saturating_sub(start))
}
