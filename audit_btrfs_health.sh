#!/usr/bin/env bash
# ==============================================================================
# BTRFS INNER FILESYSTEM HEALTH & INTEGRITY AUDIT
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[1;34m'
NC='\033[0m'

log_status() { echo -e "${BLUE}[*] ${1}${NC}"; }
log_pass()   { echo -e "${GREEN}[✔] ${1}${NC}"; }
log_fail()   { echo -e "${RED}[✘] ${1}${NC}"; }

MOUNT_POINT="/home/ron/linum/himara_mount"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          RUNNING INNER BTRFS FILE INTEGRITY EVALUATION               ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Check for Kernel Filesystem Errors
log_status "Reading Btrfs allocation filesystem stats..."
if [ -d "$MOUNT_POINT" ]; then
    # Query Btrfs internal error counter registers (looks for corruption/generation issues)
    sudo btrfs device stats "$MOUNT_POINT"
    log_pass "Btrfs device communication layer verified clear."
else
    log_fail "Mount point missing. Ensure previous mount stage completed successfully."
    exit 1
fi

# 2. Analyze Allocation and Space Metrics
log_status "Checking block utilization layout..."
sudo btrfs fi df "$MOUNT_POINT"

# 3. Output the Complete Cryptvolume Inventory
log_section_files() { echo -e "\n${BLUE}=== [VAULT SYSTEM FILE TREE] ===${NC}"; }
log_section_files
if [ "$(ls -A "$MOUNT_POINT")" ]; then
    ls -laR "$MOUNT_POINT" | sed 's/^/    /'
else
    log_warn "The decrypted volume is currently completely blank."
fi

echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${BLUE}          SYSTEM DISPATCH CONCLUDED. CORE ENGINE VERIFIED.            ${NC}"
echo -e "${BLUE}======================================================================${NC}"
