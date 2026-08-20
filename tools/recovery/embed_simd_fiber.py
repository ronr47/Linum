import re

c_file = "/home/ron/linum/kernel64_unified.c"
with open(c_file, "r") as f:
    code = f.read()

if "fiber_simd_tensor_worker" not in code:
    tensor_worker = """
/* ========================================================================== */
/* FIBER 3: BARE-METAL TENSOR SIMD SCALING WORKER                              */
/* ========================================================================== */
static float tensor_buffer[24] __attribute__((aligned(32)));

static void fiber_simd_tensor_worker(void) {
    while (1) {
        uart_puts(" [+] [FIBER-3] Running Bare-Metal Tensor SIMD Engine...\\r\\n");
        uint64_t t_start = rdtsc();

        /* 1. Initialize ramp sequence */
        for (int i = 0; i < 24; i++) {
            tensor_buffer[i] = (float)(i + 1);
        }

        /* 2. Vectorized affine scaling: elem = elem * 2.5f + 0.5f */
        for (int i = 0; i < 24; i++) {
            tensor_buffer[i] = (tensor_buffer[i] * 2.5f) + 0.5f;
        }

        uint64_t t_end = rdtsc();
        uint32_t val_int = (uint32_t)tensor_buffer[23]; /* 60 */

        uart_puts("     ▶ Transformed Element [Index 23]  : ");
        uart_put_hex(val_int);
        uart_puts(" (Expected: 0x3C = 60)\\r\\n");

        uart_puts("     ▶ Tensor Pass Execution Latency   : ");
        uart_put_hex(t_end - t_start);
        uart_puts(" TSC Cycles\\r\\n\\r\\n");

        fiber_yield();
    }
}
"""
    idx = code.find("void kernel_main(void)")
    if idx != -1:
        code = code[:idx] + tensor_worker + "\n" + code[idx:]
        code = code.replace("NUM_FIBERS 2", "NUM_FIBERS 3")
        code = code.replace(
            "fiber_init(&fibers[1], fiber_pmc_worker, &fiber_stacks[1][STACK_SIZE - 16]);",
            "fiber_init(&fibers[1], fiber_pmc_worker, &fiber_stacks[1][STACK_SIZE - 16]);\n    fiber_init(&fibers[2], fiber_simd_tensor_worker, &fiber_stacks[2][STACK_SIZE - 16]);"
        )
        with open(c_file, "w") as f:
            f.write(code)
        print("[✔] Injected FIBER-3 (Tensor SIMD Engine) into kernel64_unified.c")
    else:
        print("[-] kernel_main anchor not found.")
else:
    print("[*] FIBER-3 already present in kernel64_unified.c")
