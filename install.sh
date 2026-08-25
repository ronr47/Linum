#!/usr/bin/env bash
# ==============================================================================
# AUTOMATED DEPLOYMENT & VERIFICATION ENGINE (COMMERCIAL DROP-IN)
# Purpose: Single-click installation, validation, and diagnostic pipeline
# ==============================================================================

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_pass()   { echo -e "${GREEN}[✔] ${1}${NC}"; }
log_warn()   { echo -e "${YELLOW}[!] ${1}${NC}"; }
log_fail()   { echo -e "${RED}[✘] ${1}${NC}"; }

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          INITIALIZING SYSTEM OVERLAY DEPLOYMENT WINDOW               ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Host Environment Attestation
log_status "Checking host operating system parameters..."
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_fail "Deployment aborted: Core kernel bypass requires a Linux-gnu host interface."
    exit 1
fi
log_pass "Linux target context confirmed: $(uname -r)"

# 2. Check for Critical Execution Substrates
log_status "Validating internal architecture artifacts..."
if [ -s "./kernel.elf" ] && [ -s "./build/linum_fast" ]; then
    log_pass "Freestanding substrate kernel (i386) and fast host modules verified."
else
    log_fail "Corruption alert: Essential engine binaries are empty or missing."
    exit 1
fi

# 3. Check for Runtime Toolchain Dependencies
log_status "Checking local toolchain binary locations..."
for cmd in python3 openssl cryptsetup; do
    if command -v "$cmd" >/dev/null 2>&1; then
        log_pass "Dependency resolved: $(which "$cmd")"
    else
        log_warn "Missing non-essential toolchain utility: $cmd"
    fi
done

# 4. Fire the System Verification Datapath Loop
log_status "Executing dynamic infrastructure verification pass..."
if [ -f "./launch_orchestrator_datapath.sh" ]; then
    chmod +x ./launch_orchestrator_datapath.sh
    if ./launch_orchestrator_datapath.sh; then
        log_pass "INSTALLATION VERIFIED: All multi-tier layers successfully synchronized."
    else
        log_fail "Verification loop failure. Check system log arrays."
        exit 1
    fi
else
    log_fail "Critical initialization driver (launch_orchestrator_datapath.sh) missing."
    exit 1
fi

echo -e "${BLUE}======================================================================${NC}"
echo -e "${GREEN}          DEPLOYMENT COMPLETE. ORCHESTRATOR IS OPERATIONAL.           ${NC}"
echo -e "${BLUE}======================================================================${NC}"
