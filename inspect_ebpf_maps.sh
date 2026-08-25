#!/usr/bin/env bash
# ==============================================================================
# eBPF / XDP DATA REGISTRY DIAGNOSTIC
# Purpose: Non-destructive verification of compiled kernel map structures
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
echo -e "${BLUE}          DIAGNOSING KERNEL BYPASS XDP MAP DESCRIPTORS                ${NC}"
echo -e "${BLUE}======================================================================${NC}"

XDP_OBJ="./bpf/xdp_prog.o"

if [ -f "$XDP_OBJ" ]; then
    log_success "Target eBPF object verified: $XDP_OBJ"
    
    # Check for structural definition patterns of standard BPF rings or maps
    echo -e "\n${BLUE}--- [EXTRACTED KERNEL DATA MAP DESCRIPTORS] ---${NC}"
    if command -v bpftool >/dev/null 2>&1; then
        sudo bpftool btf dump file "$XDP_OBJ" format c 2>/dev/null || log_warn "BTF logging unavailable for this object layout."
    else
        log_item "Extracting raw map configuration blocks using system symbol strings..."
        strings "$XDP_OBJ" | grep -E -i '(map|ring|xsk|queue|xsks_map)' || log_warn "No plaintext map identifiers exposed in binary strings."
    fi
else
    log_fail "Target object file $XDP_OBJ missing from storage node paths."
fi

echo -e "\n${BLUE}======================================================================${NC}"
