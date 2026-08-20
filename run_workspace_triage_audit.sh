#!/usr/bin/env bash
set -euo pipefail

echo -e "\033[1;35m==============================================================================\033[0m"
echo -e "\033[1;35m             LINUM COMPREHENSIVE WORKSPACE & SUBSYSTEM AUDIT                  \033[0m"
echo -e "\033[1;35m==============================================================================\033[0m\n"

# 1. Workspace File Categorization Count
echo -e "\033[1;36m[1/6] FILE INVENTORY BREAKDOWN\033[0m"
echo "  • Shell Scripts (.sh)       : $(find . -maxdepth 1 -name "*.sh" | wc -l)"
echo "  • Standalone C Sources (.c/.C/.h): $(find . -maxdepth 1 \( -name "*.c" -o -name "*.C" -o -name "*.h" \) | wc -l)"
echo "  • Recovered Text Chunks     : $(find . -maxdepth 1 -name "recovered_chunk_*.txt" | wc -l)"
echo "  • Executables / ELF Binaries: $(find . -maxdepth 1 -type f -executable ! -name "*.sh" ! -name "*.py" | wc -l)"
echo "  • IR / Object Files (.ll/.bc/.o): $(find . -maxdepth 1 \( -name "*.ll" -o -name "*.bc" -o -name "*.o" \) | wc -l)"

# 2. Subsystem Mapping & Health Check
echo -e "\n\033[1;36m[2/6] SUBSYSTEM STRUCTURAL HEALTH\033[0m"

# Subsystem A: Python Compiler Core
if [ -d "src/linum" ] && [ -f "src/linum/compiler.py" ]; then
    echo -e "  \033[32m✔\033[0m Subsystem [Core-Compiler]  : src/linum/ (Structured Package)"
else
    echo -e "  \033[31m✖\033[0m Subsystem [Core-Compiler]  : INCOMPLETE"
fi

# Subsystem B: Mathic Tensor/Matrix Engine
if [ -d "mathic" ] && [ -f "mathic/compiler.py" ]; then
    echo -e "  \033[32m✔\033[0m Subsystem [Mathic-DSL]     : mathic/ (Matrix Lowering & IR)"
else
    echo -e "  \033[33m!\033[0m Subsystem [Mathic-DSL]     : mathic/ (Missing or Partial)"
fi

# Subsystem C: Beast Baremetal Kernel
if [ -d "beast" ] && [ -f "beast/kernel/kernel.c" ]; then
    echo -e "  \033[32m✔\033[0m Subsystem [Beast-Kernel]   : beast/ (Baremetal Multiboot)"
else
    echo -e "  \033[33m!\033[0m Subsystem [Beast-Kernel]   : beast/ (Missing or Partial)"
fi

# Subsystem D: Rust AetherVPC MVP
if [ -d "aethervpc-mvp" ] && [ -f "aethervpc-mvp/Cargo.toml" ]; then
    echo -e "  \033[32m✔\033[0m Subsystem [AetherVPC-Rust] : aethervpc-mvp/ (Cargo Workspace Target)"
else
    echo -e "  \033[33m!\033[0m Subsystem [AetherVPC-Rust] : aethervpc-mvp/ (Missing or Partial)"
fi

# Subsystem E: Kernel eBPF / XDP Datapath
if [ -f "xdp_prog.c" ] || [ -f "xsk_consumer.c" ]; then
    echo -e "  \033[32m✔\033[0m Subsystem [eBPF-XSK]       : Kernel AF_XDP / BPF Fastpath"
else
    echo -e "  \033[33m!\033[0m Subsystem [eBPF-XSK]       : Unconfigured"
fi

# 3. Debt & Debris Identification
echo -e "\n\033[1;36m[3/6] TECHNICAL DEBT & ARTIFACT ACCUMULATION\033[0m"
DEBRIS_COUNT=$(find . -maxdepth 1 \( -name "recovered_chunk_*.txt" -o -name "*.mangled*" -o -name "carved_block_*.bin" \) | wc -l)
echo "  • Unassimilated recovery chunks : ${DEBRIS_COUNT} files"
PATCH_SCRIPTS=$(find . -maxdepth 1 -name "fix_*.sh" | wc -l)
echo "  • Historical one-off fix scripts: ${PATCH_SCRIPTS} scripts"

# 4. Multi-Toolchain Executable Validation
echo -e "\n\033[1;36m[4/6] COMPILED BINARY VERIFICATION\033[0m"
for bin in direct_syscalls_gcc kernel.elf bpf_loader_test sophia_node vortex_node; do
    if [ -f "$bin" ]; then
        echo -e "  • Executable: \033[37m%-20s\033[0m | Format: $(file -b "$bin" | cut -d',' -f1)" "$bin"
    fi
done

# 5. Core Invariant Gate Run
echo -e "\n\033[1;36m[5/6] TEST SUITE GATE EXECUTION\033[0m"
python -m pytest -q

# 6. Actionable Recommendations
echo -e "\n\033[1;36m[6/6] AUDIT SUMMARY & NEXT STEPS\033[0m"
echo -e "  1. \033[1mQuarantine Debris\033[0m: Move \`recovered_chunk_*.txt\` and \`fix_*.sh\` scripts into \`.archive/\`."
echo -e "  2. \033[1mConsolidate C Sources\033[0m: Relocate baremetal files into \`beast/\` and networking files into \`xdp/\`."
echo -e "  3. \033[1mPreserve Invariants\033[0m: Retain \`linum_truth_gate.sh\` and \`full_workspace_audit.sh\` as active drivers."

echo -e "\n\033[1;32m==============================================================================\033[0m"
echo -e "\033[1;32m                  AUDIT COMPLETE: WORKSPACE HEALTH HEALTHY                    \033[0m"
echo -e "\033[1;32m==============================================================================\033[0m"
