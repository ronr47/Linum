#!/usr/bin/env bash
# ==============================================================================
# SECURE TEARDOWN ENGINE: PURGE, UNMOUNT, AND CLOSE VAULT
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
MAPPER_NAME="himara_unlocked"

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          INITIATING SECURE CRYPTVOLUME SEALING PIPELINE             ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Safely Unmount the Btrfs Filesystem
if mountpoint -q "${MOUNT_POINT}"; then
    log_status "Flushing kernel write buffers and unmounting ${MOUNT_POINT}..."
    sync
    sudo umount "${MOUNT_POINT}"
    log_pass "Filesystem successfully unmounted."
else
    log_status "Filesystem mount path is already detached."
fi

# 2. Lock the LUKS2 Cryptographic Volume Layer
if [ -e "/dev/mapper/${MAPPER_NAME}" ]; then
    log_status "Revoking cryptographic device mapper allocation: ${MAPPER_NAME}..."
    sudo cryptsetup close "${MAPPER_NAME}"
    log_pass "Cryptographic keys wiped from kernel memory. Volume locked."
else
    log_status "Cryptographic device mapper node is already closed."
fi

# 3. Final Verification Verification Scan
log_status "Running absolute runtime state verification check..."
if ! mountpoint -q "${MOUNT_POINT}" && [ ! -e "/dev/mapper/${MAPPER_NAME}" ]; then
    log_pass "Vault successfully sealed. Zero trace remaining in runtime subsystem."
else
    log_fail "Teardown incomplete. Active handles or open maps are blocking termination."
fi

echo -e "${BLUE}======================================================================${NC}"
