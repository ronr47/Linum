use std::ptr;

fn main() {
    println!("┌────────────────────────────────────────────────────────┐");
    println!("│ ⚡ LINUM 2050: REAL mmap KERNEL RING-BUFFER JIT EXEC   │");
    println!("└────────────────────────────────────────────────────────┘");

    unsafe {
        // Allocate a page that is Read, Write, and Execute (PROT_READ | PROT_WRITE | PROT_EXEC)
        // This is what advanced JIT engines do to map bytecode straight into executable memory.
        let ptr = libc::mmap(
            ptr::null_mut(),
            4096,
            libc::PROT_READ | libc::PROT_WRITE | libc::PROT_EXEC,
            libc::MAP_ANON | libc::MAP_PRIVATE,
            -1,
            0,
        );

        if ptr == libc::MAP_FAILED {
            eprintln!("[!] mmap failed to allocate executable memory arena.");
            return;
        }

        println!("[✔] Allocated 4096 bytes of executable memory arena at: {:p}", ptr);

        // Machine code for a simple x86_64 function: `mov eax, 42; ret;`
        // Opcode bytes: 0xb8 (mov eax), followed by 4-byte integer 42 (0x2a, 0x00, 0x00, 0x00), then 0xc3 (ret)
        let code: [u8; 6] = [0xb8, 0x2a, 0x00, 0x00, 0x00, 0xc3];
        
        // Copy the raw machine instructions directly into the mmap'd executable memory region
        ptr::copy_nonoverlapping(code.as_ptr(), ptr as *mut u8, code.len());
        println!("[✔] Injected raw machine instructions (mov eax, 42; ret) into JIT arena.");

        // Cast the memory pointer into a Rust function pointer and execute it directly
        let jit_fn: extern "C" fn() -> i32 = std::mem::transmute(ptr);
        let result = jit_fn();

        println!("[✨] JIT EXECUTION SUCCESS -> Result from raw machine code: {}", result);

        // Clean up memory
        libc::munmap(ptr, 4096);
    }
}
