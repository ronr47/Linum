#!/usr/bin/env bash
# ==============================================================================
# MAIN ARTIFACTS DEEP INSPECTION ENGINE
# Purpose: Non-destructive binary analysis of compiled orchestrator engines
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_section() { echo -e "\n${BLUE}=== [ARTIFACT MATRIX: $1] ===${NC}"; }
log_item()    { echo -e "  ${BLUE}[*]${NC} $1"; }
log_found()   { echo -e "  ${GREEN}[✔]${NC} $1"; }

WORKSPACE="$HOME/linum"
cd "$WORKSPACE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          INSPECTING COMPILED LINUM ORCHESTRATOR ARTIFACTS           ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Audit Target-Specific Binary Executables & Shared Libraries
log_section "COMPILED MACHINE BINARIES (ELF / STATIC LIBS)"
find ./build ./zig-out ./target -type f \( -executable -o -name "*.a" -o -name "*.so" \) 2>/dev/null | while read -r binary; do
    # Skip directories or basic shell wrappers we've already seen
    if file "$binary" | grep -qE '(ELF|archive|shared object)'; then
        BIN_TYPE=$(file "$binary" | awk -F: '{print $2}' | cut -d',' -f1-2)
        BIN_SIZE=$(du -sh "$binary" | awk '{print $1}')
        log_found "${binary} (${BIN_SIZE})"
        echo "      Type:${BIN_TYPE}"
    fi
done

# 2. Audit Kernel-Space Kernel Bypass Hooks
log_section "COMPILED KERNEL BYPASS OVERLAYS (eBPF / XDP)"
find ./build/xdp_prog ./build/bpf ./bpf -type f -name "*.o" 2>/dev/null | while read -r obj; do
    if file "$obj" | grep -q 'ELF'; then
        log_found "Compiled eBPF Object: ${obj}"
        # Inspect interface section headers to verify map structures if readelf is present
        if command -v readelf >/dev/null 2>&1; then
            echo "      Active Sections: $(readelf -S "$obj" | grep -E '(maps|xdp|prog)' | awk '{print $2}' | tr '\n' ' ')"
        fi
    fi
done

# 3. Audit WebAssembly Sandboxed Engines
log_section "PORTABLE SANDBOX RUNTIMES (WASM)"
find ./build/wasm -type f -name "*.wasm" 2>/dev/null | while read -r wasm_mod; do
    WASM_SIZE=$(du -sh "$wasm_mod" | awk '{print $1}')
    log_found "Wasm Module: ${wasm_mod} (${WASM_SIZE})"
done

# 4. Audit Active Cryptographic Token Files
log_section "ORCHESTRATOR VERIFICATION TOKENS & MANIFESTS"
find ./build/artifacts -type f \( -name "*.sha256" -o -name "*.sig" -o -name "*.txt" \) 2>/dev/null | while read -r sig_file; do
    log_item "Manifest Token: ${sig_file} ($(basename "$sig_file"))"
done

echo -e "\n${BLUE}======================================================================${NC}"
