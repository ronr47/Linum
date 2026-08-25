#!/usr/bin/env bash
# ==============================================================================
# MAIN ARTIFACT HEADER & SEGMENT INSPECTION PIPELINE
# Purpose: Non-destructive verification of compiled engine configurations
# ==============================================================================

set -euo pipefail

BLUE='\033[1;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_item()    { echo -e "  ${BLUE}[*]${NC} $1"; }
log_success() { echo -e "  ${GREEN}[✔]${NC} $1"; }
log_warn()    { echo -e "  ${YELLOW}[!]${NC} $1"; }

WORKSPACE="$HOME/linum"
cd "$WORKSPACE"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          RUNNING INTERNALS INSPECTION ON HIGH-UTILITY BINARIES        ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Inspect eBPF Object Named Section Layouts
echo -e "\n${BLUE}--- [SECTION ARTIFACT: ./bpf/xdp_prog.o] ---${NC}"
if command -v llvm-objdump >/dev/null 2>&1; then
    llvm-objdump -h ./bpf/xdp_prog.o | grep -E '(idx|Name|xdp|maps)' || true
elif command -v objdump >/dev/null 2>&1; then
    objdump -h ./bpf/xdp_prog.o | grep -E '(Name|xdp|maps|Data)' || true
else
    log_warn "Standard objdump utility unavailable. Parsing sections using alternative text stream..."
    strings ./bpf/xdp_prog.o | grep -E '(xdp|maps|license)' || true
fi

# 2. Check Symbol Stripping Status on Cross-Architecture Targets
echo -e "\n${BLUE}--- [SYMBOL STRIPPING: Cross-Compilation Layer] ---${NC}"
for bin in "./build/riscv64/fx_lightweight" "./build/aarch64/fx_lightweight"; do
    if [ -f "$bin" ]; then
        if file "$bin" | grep -q "not stripped"; then
            log_warn "${bin} is NOT stripped. Contains layout symbols."
        else
            log_success "${bin} is stripped to clean, minimized production parameters."
        fi
    fi
done

# 3. Security Check: Verify GNU_STACK Permissions
echo -e "\n${BLUE}--- [MEMORY SECURITY: Executable Stack Analysis] ---${NC}"
if command -v readelf >/dev/null 2>&1; then
    STACK_CHECK=$(readelf -l ./build/linum_fast 2>/dev/null | grep -i "STACK" || true)
    if echo "$STACK_CHECK" | grep -q "RWE"; then
        log_warn "SECURITY FAULT: ./build/linum_fast has an EXECUTABLE STACK (RWE)!"
    else
        log_success "./build/linum_fast secure stack verified (RW-)."
    fi
else
    log_item "readelf utility missing. Skipping deep architecture register audit."
fi

echo -e "\n${BLUE}======================================================================${NC}"
