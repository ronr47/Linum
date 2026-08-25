#!/usr/bin/env bash
# ==============================================================================
# FREESTANDING KERNEL STRUCTURAL DIAGNOSTIC
# Purpose: Non-destructive verification of bare-metal ELF layers
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
echo -e "${BLUE}          DIAGNOSING BARE-METAL INFRASTRUCTURE KERNEL                 ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Inspect the Entry Point Memory Space
if [ -f "./kernel.elf" ]; then
    log_success "Found newly synchronized freestanding substrate target: ./kernel.elf"
    
    if command -v readelf >/dev/null 2>&1; then
        ENTRY_ADDR=$(readelf -h ./kernel.elf | grep "Entry point address:" | awk '{print $4}')
        log_item "Kernel Entry Point Execution Memory Address: ${ENTRY_ADDR}"
        
        # 2. Check the section configurations for text, data, and bss segments
        echo -e "\n${BLUE}--- [CORE STRUCTURAL KERNEL SECTIONS] ---${NC}"
        readelf -S ./kernel.elf | grep -E '(idx|\.text|\.data|\.bss|Name)' || true
    else
        log_warn "readelf utility unavailable. Reading raw strings data..."
        strings ./kernel.elf | head -n 15 | sed 's/^/    /'
    fi
else
    log_warn "Target kernel.elf block has migrated or is inaccessible."
fi

echo -e "\n${BLUE}======================================================================${NC}"
